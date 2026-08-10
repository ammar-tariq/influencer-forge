import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useSystemStats(enabled = true) {
  return useQuery({
    queryKey: ["system-stats"],
    queryFn: api.stats,
    refetchInterval: 2000,
    enabled,
  });
}
