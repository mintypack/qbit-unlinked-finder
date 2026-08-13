from fastapi import APIRouter

from . import entries, hardlink, meta, rescan

api_router = APIRouter()
for mod in (meta, entries, hardlink, rescan):
    api_router.include_router(mod.router)
