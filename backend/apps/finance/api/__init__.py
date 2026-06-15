from __future__ import annotations

from .lpr_api import router as lpr_router
from .collection_api import router as collection_router

routers = [lpr_router, collection_router]
