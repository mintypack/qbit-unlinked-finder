import AddLinkIcon from "@mui/icons-material/AddLink";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import type { Item } from "../api/types";
import { humanSize } from "../lib/format";
import { FileList } from "./FileList";
import { LinkChip, ManagedChip } from "./StatusChip";

export function EntriesGrid({
  items,
  loading,
  expanded,
  onExpand,
  onLink,
}: {
  items: Item[];
  loading: boolean;
  expanded: string | null;
  onExpand: (relPath: string | null) => void;
  onLink: (item: Item) => void;
}) {
  const columns: GridColDef<Item>[] = [
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 320,
      renderCell: (p) => (
        <Stack direction="row" spacing={1}
               sx={{ alignItems: "center", minWidth: 0 }}>
          {p.row.non_portable && (
            <Tooltip title="Filename is not valid UTF-8, rename on disk to hardlink">
              <WarningAmberIcon fontSize="small" color="warning" />
            </Tooltip>
          )}
          <Typography variant="body2" noWrap>
            {p.row.name}
          </Typography>
        </Stack>
      ),
    },
    {
      field: "category",
      headerName: "Category",
      width: 120,
      renderCell: (p) =>
        p.row.category ? (
          <Chip size="small" variant="outlined" label={p.row.category} />
        ) : null,
    },
    {
      field: "added_at",
      headerName: "Added",
      width: 110,
      valueFormatter: (value: number) =>
        value ? new Date(value * 1000).toLocaleDateString() : "",
    },
    {
      field: "total_size",
      headerName: "Size",
      width: 100,
      valueFormatter: (value: number) => humanSize(value),
    },
    { field: "file_count", headerName: "Files", width: 70 },
    {
      field: "link_status",
      headerName: "Link",
      width: 150,
      renderCell: (p) => <LinkChip value={p.row.link_status} />,
    },
    {
      field: "managed_status",
      headerName: "Managed",
      width: 120,
      renderCell: (p) => <ManagedChip value={p.row.managed_status} />,
    },
    {
      field: "actions",
      headerName: "",
      width: 60,
      sortable: false,
      renderCell: (p) => (
        <Tooltip
          title={
            p.row.non_portable
              ? "Rename on disk first"
              : p.row.link_status === "EMPTY"
                ? "Nothing to link"
                : "Create hardlinks"
          }
        >
          <span>
            <IconButton
              size="small"
              disabled={p.row.non_portable || p.row.link_status === "EMPTY"}
              onClick={(e) => {
                e.stopPropagation();
                onLink(p.row);
              }}
            >
              <AddLinkIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      ),
    },
  ];

  const expandedItem = expanded
    ? items.find((i) => i.rel_path === expanded)
    : null;

  return (
    <Box>
      <DataGrid
        rows={items}
        columns={columns}
        getRowId={(r) => r.rel_path}
        loading={loading}
        density="compact"
        disableRowSelectionOnClick={false}
        onRowClick={(p) =>
          onExpand(expanded === p.row.rel_path ? null : p.row.rel_path)
        }
        initialState={{
          pagination: { paginationModel: { pageSize: 100 } },
          sorting: { sortModel: [{ field: "added_at", sort: "desc" }] },
        }}
        pageSizeOptions={[25, 50, 100]}
        sx={{ "& .MuiDataGrid-cell": { display: "flex", alignItems: "center" } }}
      />
      {expandedItem && (
        <Box sx={{ mt: 1.5 }}>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            Files in {expandedItem.name}
          </Typography>
          <FileList relPath={expandedItem.rel_path} />
        </Box>
      )}
    </Box>
  );
}
