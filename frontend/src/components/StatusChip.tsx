import Chip from "@mui/material/Chip";
import type { LinkStatus, ManagedStatus } from "../api/types";

const LINK_STYLES: Record<
  LinkStatus,
  { color: "error" | "warning" | "success" | "default"; variant?: "outlined" }
> = {
  UNLINKED: { color: "error" },
  CROSS_SEEDED: { color: "warning" },
  PARTIAL: { color: "warning", variant: "outlined" },
  LINKED: { color: "success" },
  LINKED_ELSEWHERE: { color: "default" },
  EMPTY: { color: "default", variant: "outlined" },
};

export function LinkChip({ value }: { value: LinkStatus }) {
  const s = LINK_STYLES[value];
  return (
    <Chip
      size="small"
      label={value.toLowerCase().replace("_", " ")}
      color={s.color}
      variant={s.variant ?? "filled"}
    />
  );
}

export function ManagedChip({ value }: { value: ManagedStatus }) {
  if (value === "MANAGED")
    return <Chip size="small" label="managed" variant="outlined" />;
  if (value === "UNKNOWN")
    return <Chip size="small" label="unknown" color="default" />;
  return <Chip size="small" label="unmanaged" color="error" variant="outlined" />;
}
