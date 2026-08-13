import type {
  ExecuteResult,
  FileRow,
  HardlinkBody,
  Item,
  Meta,
  Preview,
} from "./types";

export class ApiError extends Error {
  code: string;
  rolledBack?: boolean;
  constructor(code: string, message: string, rolledBack?: boolean) {
    super(message);
    this.code = code;
    this.rolledBack = rolledBack;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  const body = await resp.json().catch(() => null);
  if (!resp.ok) {
    const err = body?.error;
    throw new ApiError(
      err?.code ?? "HTTP_" + resp.status,
      err?.message ?? resp.statusText,
      body?.rolled_back,
    );
  }
  return body as T;
}

export const api = {
  getMeta: () => request<Meta>("/api/meta"),
  getEntries: (params: {
    q?: string;
    link_status?: string;
    managed_status?: string;
  }) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v) as [string, string][],
    );
    return request<{ items: Item[] }>(`/api/entries?${qs}`);
  },
  getFiles: (relPath: string) =>
    request<{ files: FileRow[] }>(
      `/api/files?rel_path=${encodeURIComponent(relPath)}`,
    ),
  previewHardlink: (body: HardlinkBody) =>
    request<Preview>("/api/hardlink/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  executeHardlink: (body: HardlinkBody) =>
    request<ExecuteResult>("/api/hardlink", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  rescan: (force = false) =>
    request<{ scan_state: string }>("/api/rescan", {
      method: "POST",
      body: JSON.stringify({ force }),
    }),
};
