from fastapi import APIRouter, Request

from ..linker import HardlinkRequest

router = APIRouter()


@router.post("/api/hardlink/preview")
def preview(request: Request, body: HardlinkRequest) -> dict:
    plan = request.app.state.linker.preview(body, request.app.state.refresh.index)
    return {
        "dest_path": plan.dest_path,
        "will_link": plan.will_link,
        "will_skip": plan.will_skip,
        "collisions": list(plan.collisions),
        "files": [{"source_rel_path": f.source_rel_path,
                   "dest_path": f.dest_path, "action": f.action}
                  for f in plan.files],
    }


@router.post("/api/hardlink")
def execute(request: Request, body: HardlinkRequest) -> dict:
    rm = request.app.state.refresh
    result = request.app.state.linker.execute(body, rm.index)
    rm.apply_link_patch(result.patch)
    return {
        "dest_path": result.dest_path,
        "linked": result.linked,
        "skipped": result.skipped,
        "rolled_back": result.rolled_back,
    }
