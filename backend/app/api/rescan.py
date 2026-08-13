import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class RescanBody(BaseModel):
    force: bool = False


@router.post("/api/rescan", status_code=202)
async def rescan(request: Request, body: RescanBody | None = None) -> dict:
    rm = request.app.state.refresh
    force = bool(body and body.force)
    asyncio.ensure_future(rm.run_scan(force=force))
    await asyncio.sleep(0)
    return {"scan_state": rm.scan_state}
