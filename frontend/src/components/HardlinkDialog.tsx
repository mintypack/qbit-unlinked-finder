import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import { ApiError } from "../api/client";
import type { DestinationRoot, Item, Preview } from "../api/types";
import { useHardlink } from "../hooks/useHardlink";

export function HardlinkDialog({
  item,
  roots,
  open,
  onClose,
}: {
  item: Item;
  roots: DestinationRoot[];
  open: boolean;
  onClose: (successMessage?: string) => void;
}) {
  const defaultRoot =
    roots.find((r) => item.category && r.categories.includes(item.category))
      ?.path ?? "";
  const [root, setRoot] = useState(defaultRoot);
  const [subpath, setSubpath] = useState(item.name);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { preview: previewMut, execute: executeMut } = useHardlink();

  const selected = roots.find((r) => r.path === root);
  const canPreview =
    !!selected && selected.linkable && subpath.trim() !== "" &&
    !previewMut.isPending;
  const clean = preview !== null && preview.collisions.length === 0;
  const body = { source_rel_path: item.rel_path, dest_root: root, subpath };

  const invalidate = () => {
    setPreview(null);
    setError(null);
  };

  const describe = (e: unknown) => {
    if (e instanceof ApiError) {
      const note = e.rolledBack === true ? " (changes were rolled back)" : "";
      return `${e.message}${note}`;
    }
    return String(e);
  };

  const doPreview = () => {
    setError(null);
    previewMut.mutate(body, {
      onSuccess: setPreview,
      onError: (e) => setError(describe(e)),
    });
  };

  const doExecute = () => {
    setError(null);
    executeMut.mutate(body, {
      onSuccess: (r) =>
        onClose(`Linked ${r.linked} files (${r.skipped} skipped)`),
      onError: (e) => setError(describe(e)),
    });
  };

  return (
    <Dialog open={open} onClose={() => onClose()} fullWidth maxWidth="sm">
      <DialogTitle>Hardlink {item.name}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            select
            label="Destination"
            value={root}
            onChange={(e) => {
              setRoot(e.target.value);
              invalidate();
            }}
            fullWidth
          >
            {roots.map((r) => (
              <MenuItem key={r.path} value={r.path}>
                {r.label}
              </MenuItem>
            ))}
          </TextField>
          {selected && !selected.linkable && (
            <Alert severity="error">{selected.reason}</Alert>
          )}
          <TextField
            label="Subpath"
            value={subpath}
            onChange={(e) => {
              setSubpath(e.target.value);
              invalidate();
            }}
            fullWidth
            helperText={
              item.is_dir
                ? "Folder created inside the destination root"
                : "File name inside the destination root"
            }
          />
          {error && <Alert severity="error">{error}</Alert>}
          {preview && (
            <Stack spacing={1}>
              <Typography variant="body2">
                Will link {preview.will_link}, skip {preview.will_skip} already
                linked{preview.collisions.length > 0 &&
                  `, ${preview.collisions.length} collision(s)`}
              </Typography>
              <Table size="small">
                <TableBody>
                  {preview.files.map((f) => (
                    <TableRow key={f.source_rel_path}>
                      <TableCell sx={{ fontFamily: "monospace" }}>
                        {f.source_rel_path}
                        {f.existing_target && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: "block" }}
                          >
                            already at {f.existing_target}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{
                          color:
                            f.action === "COLLISION"
                              ? "error.main"
                              : f.action === "SKIP"
                                ? "text.secondary"
                                : "success.main",
                        }}
                      >
                        {f.action.toLowerCase()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {preview.collisions.length > 0 && (
                <Alert severity="error">
                  Collision: a different file already exists at the destination.
                  Nothing will be linked.
                </Alert>
              )}
            </Stack>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => onClose()}>Cancel</Button>
        <Button onClick={doPreview} disabled={!canPreview}>
          Preview
        </Button>
        <Button
          variant="contained"
          onClick={doExecute}
          disabled={!clean || executeMut.isPending}
        >
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
}
