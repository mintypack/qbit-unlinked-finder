from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

ITEM_FIELDS = ("name", "rel_path", "is_dir", "total_size", "file_count",
               "category", "managed_status", "link_status", "non_portable")
FILE_FIELDS = ("rel_path", "size", "nlink", "link_status", "linked_targets")


def _pick(obj, fields):
    return {f: getattr(obj, f) for f in fields}


@router.get("/api/entries")
def get_entries(request: Request, q: str = "",
                link_status: str | None = None,
                managed_status: str | None = None) -> dict:
    items = request.app.state.refresh.index.search(
        q=q, link_status=link_status, managed_status=managed_status)
    return {"items": [_pick(i, ITEM_FIELDS) for i in items]}


@router.get("/api/files")
def get_files(request: Request, rel_path: str) -> dict:
    item = request.app.state.refresh.index.by_rel_path.get(rel_path)
    if item is None:
        raise HTTPException(status_code=404, detail="unknown item")
    return {"files": [_pick(f, FILE_FIELDS) for f in item.files]}
