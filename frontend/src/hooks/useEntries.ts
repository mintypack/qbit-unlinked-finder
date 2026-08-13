import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useEntries(
  q: string,
  linkStatus?: string,
  managedStatus?: string,
) {
  return useQuery({
    queryKey: ["entries", q, linkStatus, managedStatus],
    queryFn: () =>
      api.getEntries({
        q,
        link_status: linkStatus,
        managed_status: managedStatus,
      }),
    placeholderData: (prev) => prev,
  });
}
