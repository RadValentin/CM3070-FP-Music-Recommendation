from collections import defaultdict
import orjson
import uuid

MAP_SIZE = 1024 * 1024 * 1024 * 2  # 2GB

def mbid_bytes(m: str) -> bytes:
    return uuid.UUID(m).bytes

def mbid_str(b: bytes) -> str:
    return str(uuid.UUID(bytes=b))

class LMDBTrackIndex:
    def __init__(self, path, map_size=MAP_SIZE, batch=10_000):
        self.store = defaultdict(list)

    def append(self, key: str, value):
        self.store[key].append(value)

    def __setitem__(self, key: str, values):
        self.store[key] = values

    def get(self, key: str, default=None):
        if key in self.store:
            return self.store[key]
        return default if default is not None else []

    def __getitem__(self, key: str):
        if key not in self.store:
            raise KeyError(key)
        return self.store[key]

    def items(self):
        return self.store.items()

    def keys(self):
        return self.store.keys()

    def values(self):
        return self.store.values()

    def flush(self):
        pass

    def close(self):
        pass