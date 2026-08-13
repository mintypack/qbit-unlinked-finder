import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import type { Counts } from "../api/types";

export interface Filters {
  linkStatus?: string;
  managedStatus?: string;
}

const LINK_CHIPS: { key: string; label: (c: Counts) => string }[] = [
  {
    key: "not_linked",
    label: (c) => `Not hardlinked (${c.unlinked + c.cross_seeded + c.partial})`,
  },
  { key: "UNLINKED", label: (c) => `Unlinked (${c.unlinked})` },
  { key: "CROSS_SEEDED", label: (c) => `Cross-seeded (${c.cross_seeded})` },
  { key: "PARTIAL", label: (c) => `Partial (${c.partial})` },
  { key: "LINKED", label: (c) => `Linked (${c.linked})` },
  {
    key: "LINKED_ELSEWHERE",
    label: (c) => `Linked elsewhere (${c.linked_elsewhere})`,
  },
];

export function StatusFilter({
  counts,
  filters,
  onChange,
}: {
  counts: Counts;
  filters: Filters;
  onChange: (f: Filters) => void;
}) {
  return (
    <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
      <Chip
        size="small"
        label={`All (${counts.total})`}
        color={!filters.linkStatus && !filters.managedStatus ? "primary" : "default"}
        onClick={() => onChange({})}
      />
      {LINK_CHIPS.map((c) => (
        <Chip
          key={c.key}
          size="small"
          label={c.label(counts)}
          color={filters.linkStatus === c.key ? "primary" : "default"}
          onClick={() =>
            onChange({
              ...filters,
              linkStatus: filters.linkStatus === c.key ? undefined : c.key,
            })
          }
        />
      ))}
      <Chip
        size="small"
        label={`Unmanaged (${counts.unmanaged})`}
        color={filters.managedStatus === "UNMANAGED" ? "primary" : "default"}
        onClick={() =>
          onChange({
            ...filters,
            managedStatus:
              filters.managedStatus === "UNMANAGED" ? undefined : "UNMANAGED",
          })
        }
      />
    </Stack>
  );
}
