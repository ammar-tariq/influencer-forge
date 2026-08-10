import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useQueue(enabled = true) {
  return useQuery({
    queryKey: ["queue"],
    queryFn: api.queue,
    refetchInterval: 1500,
    enabled,
  });
}
