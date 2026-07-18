"""File storage for experiment/notebook photos.

Local disk in development; the same save/load interface swaps to S3 in
production without changing the routers.
"""

from app.storage.local import LocalStorage, get_storage

__all__ = ["LocalStorage", "get_storage"]
