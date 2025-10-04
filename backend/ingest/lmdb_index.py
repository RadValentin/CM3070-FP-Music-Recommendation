import lmdb
import orjson
import uuid

def mbid_bytes(m: str) -> bytes:
    return uuid.UUID(m).bytes

def mbid_str(b: bytes) -> str:
    return str(uuid.UUID(bytes=b))

class LMDBTrackIndex:
    def __init__(self, path, map_size=1024 * 1024 * 1024 * 2, batch=10_000):
        self.env = lmdb.open(
            path, map_size=map_size, subdir=True, max_dbs=2,
            lock=True, writemap=True,
            map_async=True,
            metasync=False,
            sync=False,
            readahead=True,   
        )
        self.db = self.env.open_db(b"main")

    def append(self, key: str, value):
        key_bytes = mbid_bytes(key)
        with self.env.begin(write=True, db=self.db) as txn:
            current = txn.get(key_bytes)
            if current:
                lst = orjson.loads(current)
                lst.append(value)
            else:
                lst = [value]
            txn.put(key_bytes, orjson.dumps(lst), db=self.db)

    def __setitem__(self, key: str, values):
        key_bytes = mbid_bytes(key)
        if values is None:
            with self.env.begin(write=True, db=self.db) as txn:
                txn.delete(key_bytes)
            return
        if not isinstance(values, list):
            raise ValueError("Value must be a list")
        with self.env.begin(write=True, db=self.db) as txn:
            txn.put(key_bytes, orjson.dumps(values))

    def get(self, key: str, default=None):
        key_bytes = mbid_bytes(key)
        with self.env.begin(db=self.db) as txn:
            val = txn.get(key_bytes)
            if val is None:
                return default if default is not None else []
            return orjson.loads(val)

    def __getitem__(self, key: str):
        result = self.get(key)
        if not result:
            raise KeyError(key)
        return result

    def items(self):
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for key_bytes, value in cur:
                    yield mbid_str(key_bytes), orjson.loads(value)

    def keys(self):
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                return set(mbid_str(key) for key in cur.iternext(keys=True, values=False))

    def values(self):
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for _, value in cur:
                    yield orjson.loads(value)

    def flush(self):
        self.env.sync()

    def close(self):
        self.flush()
        self.env.close()

    def size(self):
        with self.env.begin(db=self.db) as txn:
            entries = txn.stat()["entries"]
            psize = txn.stat()["psize"]
            return psize * entries