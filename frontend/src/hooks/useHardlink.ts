import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function useHardlink() {
  const qc = useQueryClient();
  const preview = useMutation({ mutationFn: api.previewHardlink });
  const execute = useMutation({
    mutationFn: api.executeHardlink,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["entries"] });
      qc.invalidateQueries({ queryKey: ["meta"] });
      qc.invalidateQueries({ queryKey: ["files"] });
    },
  });
  return { preview, execute };
}
