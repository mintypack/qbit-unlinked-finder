import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function useRescan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (force?: boolean) => api.rescan(force),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["meta"] }),
  });
}
