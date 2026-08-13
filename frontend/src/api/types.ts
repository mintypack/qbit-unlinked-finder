export type LinkStatus =
  | "UNLINKED"
  | "CROSS_SEEDED"
  | "LINKED"
  | "LINKED_ELSEWHERE"
  | "PARTIAL"
  | "EMPTY";
export type ManagedStatus = "MANAGED" | "UNMANAGED" | "UNKNOWN";

export interface DestinationRoot {
  path: string;
  label: string;
  categories: string[];
  linkable: boolean;
  reason: string | null;
}

export interface Counts {
  total: number;
  unlinked: number;
  cross_seeded: number;
  partial: number;
  linked: number;
  linked_elsewhere: number;
  empty: number;
  unmanaged: number;
}

export interface Meta {
  scan_state: "scanning" | "ready";
  last_scan_at: string | null;
  last_scan_duration_seconds: number | null;
  last_scan_error: string | null;
  scan_warnings: number;
  qbit_state: "connected" | "disconnected";
  qbit_error: string | null;
  downloads_root: string;
  destination_roots: DestinationRoot[];
  counts: Counts;
}

export interface Item {
  name: string;
  rel_path: string;
  is_dir: boolean;
  total_size: number;
  file_count: number;
  category: string;
  managed_status: ManagedStatus;
  link_status: LinkStatus;
  non_portable: boolean;
  added_at: number;
}

export interface FileRow {
  rel_path: string;
  size: number;
  nlink: number;
  link_status: LinkStatus;
  linked_targets: string[];
}

export interface HardlinkBody {
  source_rel_path: string;
  dest_root: string;
  subpath: string;
}

export interface PlanFile {
  source_rel_path: string;
  dest_path: string;
  action: "LINK" | "SKIP" | "COLLISION";
}

export interface Preview {
  dest_path: string;
  will_link: number;
  will_skip: number;
  collisions: string[];
  files: PlanFile[];
}

export interface ExecuteResult {
  dest_path: string;
  linked: number;
  skipped: number;
  rolled_back: boolean;
}
