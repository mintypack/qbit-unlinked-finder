# qbit-unlinked-finder

Web UI that answers two questions about a qBittorrent downloads folder: which
files are already hardlinked into your organized media roots, and which files
are not managed by qBittorrent at all. Creates hardlinks (single file or whole
torrent folder) into a chosen destination root, replacing a manual `cp -lr`.

Runs as one container: FastAPI backend serving the built React UI. No
database; the index lives in memory, built by a full scan at startup and
refreshed when qBittorrent reports torrent changes, on a daily timer, or on
demand.

# Screenshots

![](/assets/screenshot-1.png)
![](/assets/screenshot-2.png)

## Requirements

- Downloads and every destination root must live on one host filesystem,
  reachable through one bind mount. Hardlinks cannot cross filesystems or
  mounts. On Unraid this means the same share.
- qBittorrent with the WebUI API enabled.
- No auth of its own. Keep it on a trusted LAN or behind an authenticating
  reverse proxy. Do not expose it to the internet.

## Setup

Example layout (unRAID-style, one share holding both downloads and media):

```
host                          this app         qBittorrent
/mnt/user/data                /data
/mnt/user/data/downloads      /data/downloads  /config/qBittorrent/downloads
/mnt/user/data/Media          /data/Media
```

1. Copy `config.example.toml` to `config.toml` and adjust paths.

```toml
[qbittorrent]
url = "http://qbittorrent:8080"
username = "admin"

# qBittorrent reports paths as ITS container sees them. Rewrite that prefix
# to this app's view of the same files.
[[qbittorrent.path_mappings]]
from = "/config/qBittorrent/downloads"
to = "/data/downloads"

[scan]
downloads_root = "/data/downloads"
rescan_interval_seconds = 86400

[[destination_roots]]
path = "/data/Media/Movies"
label = "Movies"
categories = ["movies"]

[[destination_roots]]
path = "/data/Media/TV-Shows"
label = "TV"
categories = ["tv-shows"]

[server]
# Every name or IP you will type into the browser to reach this app
allowed_hosts = ["localhost", "127.0.0.1", "nas.local"]
```

2. Set the qBittorrent password and start:

```bash
QBIT_PASSWORD=... docker compose up -d
```

```yaml
services:
  qbit-unlinked-finder:
    build: .
    ports:
      - "8000:8000"
    environment:
      - QUF_QBITTORRENT__PASSWORD=${QBIT_PASSWORD}
    volumes:
      - ./config.toml:/config/config.toml:ro
      - /mnt/user/data:/data
```

3. Open `http://<host>:8000`.

## Notes

- On Unraid, `/mnt/user` shares can still return `EXDEV` when source and
  destination land on different physical disks. The app catches that case,
  rolls back cleanly, and names the cause.
- Any TOML key can be overridden by env var: prefix `QUF_`, nesting with
  `__`, e.g. `QUF_SCAN__RESCAN_INTERVAL_SECONDS=1800`.

## Development

```bash
cd backend && uv sync && uv run pytest        # backend + tests
cd frontend && npm install && npm run dev     # UI dev server, proxies /api
```
