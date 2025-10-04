import lmdb, orjson, uuid
import zstandard as zstd


class LMDBTrackIndex:
    """
    Disk-based index that stores track data grouped by their MusicBrainz ID (mbid), a 36 character 
    string in UUID format. Interface mimics standard Python dict.
    
    Keys are internally they're serialized to bytes. Externally they're strings.
    Values are stored compressed (optional) and serialized to JSON bytes. Externally they're 
    returned as lists of JSON dicts as tracks can have duplicates.
    """

    def __init__(self, path, map_size=1024 * 1024 * 1024 * 2, disable_compression=False):
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
        with self.env.begin(write=True, db=self.db) as txn:
            current = txn.get(key_bytes)
            if current:
                lst = self._deserialize_values(current)
                lst.append(value)
            else:
                lst = [value]
            txn.put(key_bytes, self._serialize_values(lst))

    def __setitem__(self, key: str, values):
        key_bytes = self._serialize_key(key)
        if values is None:
            with self.env.begin(write=True, db=self.db) as txn:
                txn.delete(key_bytes)
            return
        if not isinstance(values, list):
            raise ValueError("Value must be a list")
        with self.env.begin(write=True, db=self.db) as txn:
            txn.put(key_bytes, self._serialize_values(values))

    def get(self, key: str, default=None):
        key_bytes = self._serialize_key(key)
        with self.env.begin(db=self.db) as txn:
            val = txn.get(key_bytes)
            if val is None:
                return default if default is not None else []
            return self._deserialize_values(val)

    def __getitem__(self, key: str):
        result = self.get(key)
        if not result:
            raise KeyError(key)
        return result

    def items(self):
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for key_bytes, values_bytes in cur:
                    yield self._deserialize_key(key_bytes), self._deserialize_values(values_bytes)

    def keys(self):
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                return set(
                    self._deserialize_key(key)
                    for key in cur.iternext(keys=True, values=False)
                )
            
    def first_key(self) -> str | None:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                if cur.first():
                    key_bytes = cur.key()
                    return self._deserialize_key(key_bytes)
                return None

    def values(self):
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for _, values_bytes in cur:
                    yield self._deserialize_values(values_bytes)

    def first_value(self, raw=False):
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                if cur.first():
                    _, values_bytes = cur.item()
                    if raw:
                        return values_bytes
                    return self._deserialize_values(values_bytes)
                return None, None

    def flush(self):
        self.env.sync()

    def close(self):
        self.flush()
        self.env.close()

    def size_pages(self):
        with self.env.begin(db=self.db) as txn:
            st = txn.stat()
            return (st["branch_pages"] + st["leaf_pages"] + st["overflow_pages"]) * st["psize"]

    def map_size(self):
        return self.env.info()["map_size"]