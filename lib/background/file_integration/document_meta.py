from typing import NamedTuple


class DocumentMeta(NamedTuple):
    uuid: str
    original_path: str
    storage_key: str
    timestamp: str
    name: str
    scan_id: int
    ext: str
    tracked_folder: int = None
