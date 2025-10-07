import lmdb, orjson, uuid
import zstandard as zstd
import numpy as np
from collections import defaultdict
from numpy.typing import NDArray
from typing import Iterator

class LMDBTrackIndex:
    """
    Disk-based index that stores track data grouped by their MusicBrainz ID (mbid), a 36 character 
    string in UUID format. Interface mimics standard Python dict.
    
    Keys are internally they're serialized to bytes. Externally they're strings.
    Values are stored compressed (optional) and serialized to JSON bytes. Externally they're 
    returned as lists of JSON dicts as tracks can have duplicates.
    """

    def __init__(self, path, map_size=2 * 1024**3, disable_compression=False, batch=10000):
        self.env = lmdb.open(
            path,
            map_size=map_size,
            subdir=True,
            max_dbs=2,
            lock=True,
            writemap=True,
            map_async=True,
            metasync=False,
            sync=False,
            readahead=True,
        )
        self.db = self.env.open_db(b"main", create=True)
        self.disable_compression = disable_compression
        if not disable_compression:
            self.compressor = zstd.ZstdCompressor(level=1)
            self.decompressor = zstd.ZstdDecompressor()
        self.stats = defaultdict(int)
        # batch writes
        self._txn = None
        self._n = 0
        self._batch = batch

    def _serialize_key(self, key: str) -> bytes:
        """Convert a key to bytes representation for internal use"""
        return uuid.UUID(key).bytes

    def _deserialize_key(self, key: bytes) -> str:
        """Convert a key from bytes to string for external use"""
        return str(uuid.UUID(bytes=key))
    
    def _serialize_values(self, data: list) -> bytes:
        """Compress (optional) and encode values to JSON bytes"""
        json_bytes = orjson.dumps(data)
        if not self.disable_compression:
            compressed = self.compressor.compress(json_bytes)
            return compressed
        return json_bytes

    def _deserialize_values(self, data: bytes) -> list:
        """Decompress (optional) and decode values from JSON bytes to list of dicts"""
        if self.disable_compression:
            return orjson.loads(data)
    
        decompressed = self.decompressor.decompress(data)
        return orjson.loads(decompressed)

    def append(self, key: str, value):
        key_bytes = self._serialize_key(key)

        if self._txn is None:
            self._txn = self.env.begin(write=True, db=self.db, buffers=True)
            self._n = 0

        current = self._txn.get(key_bytes)
        if current:
            lst = self._deserialize_values(current)
            lst.append(value)
            self.stats["duplicates"] += 1
        else:
            lst = [value]
        
        self._txn.put(key_bytes, self._serialize_values(lst))
        self._n += 1
        if self._n >= self._batch:
            self._txn.commit()
            self._txn = None

    def __setitem__(self, key: str, values):
        key_bytes = self._serialize_key(key)
        if self._txn is None:
            self._txn = self.env.begin(write=True, db=self.db)
            self._n = 0
        if values is None:
            self._txn.delete(key_bytes)
        else:
            if not isinstance(values, list):
                raise ValueError("Value must be a list")
            self._txn.put(key_bytes, self._serialize_values(values))
        
        self._n += 1
        if self._n >= self._batch:
            self._txn.commit()
            self._txn = None

    def get(self, key: str, default=None) -> list:
        key_bytes = self._serialize_key(key)

        txn = self._txn if self._txn is not None else self.env.begin(db=self.db)
        val = txn.get(key_bytes)
        if val is None:
            return default if default is not None else []
        return self._deserialize_values(val)

    def __getitem__(self, key: str) -> list:
        result = self.get(key)
        if not result:
            raise KeyError(key)
        return result

    def items(self) -> Iterator[tuple[str, list]]:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for key_bytes, values_bytes in cur:
                    yield self._deserialize_key(key_bytes), self._deserialize_values(values_bytes)

    def keys(self) -> set[str]:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                return set(
                    self._deserialize_key(key)
                    for key in cur.iternext(keys=True, values=False)
                )
            
    def keys_np(self) -> NDArray[np.bytes_]:
        """Return all keys as a NumPy array of fixed-size 16-byte records (UUID bytes)."""
        with self.env.begin(db=self.db) as txn:
            stat = txn.stat()
            n = stat["entries"]
            arr = np.empty(n, dtype="V16")
            with txn.cursor() as cur:
                i = 0
                for key, _ in cur:
                    arr[i] = np.frombuffer(key, dtype="V16")
                    i += 1
        return arr
            
    def first_key(self) -> str | None:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                if cur.first():
                    key_bytes = cur.key()
                    return self._deserialize_key(key_bytes)
                return None

    def values(self) -> Iterator[list]:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for _, values_bytes in cur:
                    yield self._deserialize_values(values_bytes)

    def first_value(self, raw=False) -> tuple | None:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                if cur.first():
                    _, values_bytes = cur.item()
                    if raw:
                        return values_bytes
                    return self._deserialize_values(values_bytes)
                return None

    def flush(self):
        # commit any pending batch then fsync (needed due to sync=False in env.open)
        if self._txn is not None:
            self._txn.commit()
            self._txn = None
            self._n = 0
        self.env.sync()

    def close(self):
        self.flush()
        self.env.close()

    def size_pages(self) -> int:
        with self.env.begin(db=self.db) as txn:
            st = txn.stat()
            return (st["branch_pages"] + st["leaf_pages"] + st["overflow_pages"]) * st["psize"]

    def map_size(self) -> int:
        return self.env.info()["map_size"]