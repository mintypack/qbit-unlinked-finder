import RefreshIcon from "@mui/icons-material/Refresh";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import { useRescan } from "../hooks/useRescan";

export function RescanButton({ scanning }: { scanning: boolean }) {
  const rescan = useRescan();
  return (
    <Button
      size="small"
      variant="outlined"
      color="inherit"
      startIcon={
        scanning ? <CircularProgress size={14} color="inherit" /> : <RefreshIcon />
      }
      disabled={scanning}
      onClick={() => rescan.mutate(false)}
    >
      {scanning ? "Scanning" : "Rescan"}
    </Button>
  );
}
