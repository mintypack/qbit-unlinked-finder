import Alert from "@mui/material/Alert";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Snackbar from "@mui/material/Snackbar";
import { useCallback, useState } from "react";
import type { Item } from "./api/types";
import { EntriesGrid } from "./components/EntriesGrid";
import { HardlinkDialog } from "./components/HardlinkDialog";
import { RescanButton } from "./components/RescanButton";
import { SearchBar } from "./components/SearchBar";
import { StatusFilter, type Filters } from "./components/StatusFilter";
import { useEntries } from "./hooks/useEntries";
import { useMeta } from "./hooks/useMeta";
import { useRescan } from "./hooks/useRescan";

export default function App() {
  const meta = useMeta();
  const rescan = useRescan();
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState<Filters>({});
  const [expanded, setExpanded] = useState<string | null>(null);
  const [linkTarget, setLinkTarget] = useState<Item | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const entries = useEntries(q, filters.linkStatus, filters.managedStatus);
  const scanning = meta.data?.scan_state === "scanning";
  const onSearch = useCallback((next: string) => setQ(next), []);

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar position="sticky" color="transparent" elevation={0}
              sx={{ borderBottom: 1, borderColor: "divider",
                    bgcolor: "background.paper" }}>
        <Toolbar variant="dense" sx={{ gap: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, flexGrow: 0 }}>
            qbit-unlinked-finder
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
            {scanning
              ? "scanning..."
              : meta.data?.last_scan_at
                ? `last scan ${new Date(meta.data.last_scan_at).toLocaleTimeString()}`
                : ""}
          </Typography>
          <RescanButton scanning={!!scanning} />
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 2 }}>
        <Stack spacing={1.5}>
          {meta.data?.qbit_state === "disconnected" && (
            <Alert severity="warning">
              qBittorrent unreachable, managed status may be stale or unknown.
              {meta.data.qbit_error && ` Reason: ${meta.data.qbit_error}`}
            </Alert>
          )}
          {meta.data?.last_scan_error && (
            <Alert
              severity="error"
              action={
                <Button color="inherit" size="small"
                        onClick={() => rescan.mutate(true)}>
                  Force rescan
                </Button>
              }
            >
              {meta.data.last_scan_error}
            </Alert>
          )}
          <SearchBar value={q} onChange={onSearch} />
          {meta.data && (
            <StatusFilter counts={meta.data.counts} filters={filters}
                          onChange={setFilters} />
          )}
          <EntriesGrid
            items={entries.data?.items ?? []}
            loading={entries.isPending || !!scanning}
            expanded={expanded}
            onExpand={setExpanded}
            onLink={setLinkTarget}
          />
          {linkTarget && meta.data && (
            <HardlinkDialog
              item={linkTarget}
              roots={meta.data.destination_roots}
              open
              onClose={(msg) => {
                setLinkTarget(null);
                if (msg) setToast(msg);
              }}
            />
          )}
          <Snackbar
            open={toast !== null}
            autoHideDuration={5000}
            onClose={() => setToast(null)}
            message={toast ?? ""}
          />
        </Stack>
      </Container>
    </Box>
  );
}
