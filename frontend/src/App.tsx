import Alert from "@mui/material/Alert";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { useMeta } from "./hooks/useMeta";
import { useRescan } from "./hooks/useRescan";
import { RescanButton } from "./components/RescanButton";

export default function App() {
  const meta = useMeta();
  const rescan = useRescan();
  const scanning = meta.data?.scan_state === "scanning";

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
          {meta.data && <MainView counts={meta.data.counts}
                                  roots={meta.data.destination_roots} />}
        </Stack>
      </Container>
    </Box>
  );
}

import type { Counts, DestinationRoot } from "./api/types";

// Grid, search, and filters land in the next task
function MainView(_props: { counts: Counts; roots: DestinationRoot[] }) {
  return null;
}
