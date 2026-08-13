from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/meta")
def get_meta(request: Request) -> dict:
    rm = request.app.state.refresh
    settings = request.app.state.settings
    return {
        "scan_state": rm.scan_state,
        "last_scan_at": rm.last_scan_at,
        "last_scan_duration_seconds": rm.last_scan_duration,
        "last_scan_error": rm.last_scan_error,
        "scan_warnings": rm.scan_warnings,
        "qbit_state": rm.qbit_state,
        "downloads_root": str(settings.scan.downloads_root),
        "destination_roots": rm.roots_meta(),
        "counts": dict(rm.index.counts),
    }
