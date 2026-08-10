import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function useVault() {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["vault-status"],
    queryFn: api.vaultStatus,
    refetchInterval: 5000,
  });
  const setup = useMutation({
    mutationFn: (pin: string) => api.vaultSetup(pin),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vault-status"] }),
  });
  const unlock = useMutation({
    mutationFn: (pin: string) => api.vaultUnlock(pin),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vault-status"] });
      qc.invalidateQueries({ queryKey: ["vault-generations"] });
    },
  });
  const lock = useMutation({
    mutationFn: () => api.vaultLock(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vault-status"] });
      qc.invalidateQueries({ queryKey: ["vault-generations"] });
    },
  });
  const vaultPending = useMutation({
    mutationFn: () => api.vaultPendingNsfw(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vault-status"] });
      qc.invalidateQueries({ queryKey: ["vault-generations"] });
      qc.invalidateQueries({ queryKey: ["generations"] });
    },
  });
  return { status, setup, unlock, lock, vaultPending };
}
