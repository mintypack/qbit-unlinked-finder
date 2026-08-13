import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: api.getMeta,
    refetchInterval: 5000,
  });
}
