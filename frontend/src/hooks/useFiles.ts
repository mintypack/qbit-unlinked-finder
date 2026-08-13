import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useFiles(relPath: string, enabled: boolean) {
  return useQuery({
    queryKey: ["files", relPath],
    queryFn: () => api.getFiles(relPath),
    enabled,
  });
}
