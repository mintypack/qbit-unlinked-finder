import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useFiles } from "../hooks/useFiles";
import { humanSize } from "../lib/format";
import { LinkChip } from "./StatusChip";

export function FileList({ relPath }: { relPath: string }) {
  const files = useFiles(relPath, true);

  if (files.isPending) return <CircularProgress size={20} sx={{ m: 2 }} />;
  if (files.isError)
    return (
      <Typography color="error" sx={{ m: 2 }}>
        Failed to load files.
      </Typography>
    );

  return (
    <Paper variant="outlined" sx={{ overflow: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>File</TableCell>
            <TableCell align="right">Size</TableCell>
            <TableCell align="right">nlink</TableCell>
            <TableCell>Link status</TableCell>
            <TableCell>Targets</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {files.data.files.map((f) => (
            <TableRow key={f.rel_path} hover>
              <TableCell sx={{ fontFamily: "monospace" }}>{f.rel_path}</TableCell>
              <TableCell align="right">{humanSize(f.size)}</TableCell>
              <TableCell align="right">{f.nlink}</TableCell>
              <TableCell>
                <LinkChip value={f.link_status} />
              </TableCell>
              <TableCell sx={{ maxWidth: 420 }}>
                {f.linked_targets.length > 0 && (
                  <Tooltip title={f.linked_targets.join("\n")}>
                    <Typography variant="body2" noWrap color="text.secondary">
                      {f.link_status === "CROSS_SEEDED" ? "cross-seed: " : ""}
                      {f.linked_targets.join(", ")}
                    </Typography>
                  </Tooltip>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}
