import lmdb
import orjson
import uuid

MAP_SIZE = 1024 * 1024 * 1024 * 2  # 2GB

def mbid_bytes(m: str) -> bytes:
    return uuid.UUID(m).bytes

def mbid_str(b: bytes) -> str:
    return str(uuid.UUID(bytes=b))

class LMDBTrackIndex:
    def __init__(self, path, map_size=MAP_SIZE, batch=10_000):
        self.env = lmdb.open(
            path, map_size=map_size, subdir=True,
            writemap=True, max_dbs=1, lock=True
        )
        self.db = self.env.open_db(b"main")
        self._txn = None
        self._n = 0
        self._batch = batch

    def append(self, key: str, value):
        if self._txn is None:
            self._txn = self.env.begin(write=True, db=self.db)
            self._n = 0

        key_bytes = mbid_bytes(key)
        current = self._txn.get(key_bytes, db=self.db)
        if current:
            lst = orjson.loads(current)
            lst.append(value)
        else:
            lst = [value]
        self._txn.put(key_bytes, orjson.dumps(lst), db=self.db)
        self._n += 1
        if self._n >= self._batch:
            self._txn.commit()
            self._txn = None

    def __setitem__(self, key: str, values):
        key_bytes = mbid_bytes(key)
        if values is None:
            with self.env.begin(write=True) as txn:
                txn.delete(key_bytes, db=self.db)
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
        if self._txn is not None:
            self._txn.commit()
            self._txn = None
        self.env.sync()

    def close(self):
        self.env.close()