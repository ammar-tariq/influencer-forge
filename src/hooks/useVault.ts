import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function useVault() {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["vault-status"],
    queryFn: api.vaultStatus,
    refetchInterval: 5000,
  });
  const bustVaultCaches = () => {
    qc.invalidateQueries({ queryKey: ["vault-status"] });
    qc.invalidateQueries({ queryKey: ["vault-generations"] });
    qc.invalidateQueries({ queryKey: ["generations"] });
  };
  const setup = useMutation({
    mutationFn: (pin: string) => api.vaultSetup(pin),
    onSuccess: bustVaultCaches,
  });
  const unlock = useMutation({
    mutationFn: (pin: string) => api.vaultUnlock(pin),
    onSuccess: bustVaultCaches,
  });
  const lock = useMutation({
    mutationFn: () => api.vaultLock(),
    onSuccess: bustVaultCaches,
  });
  const vaultPending = useMutation({
    mutationFn: () => api.vaultPendingNsfw(),
    onSuccess: bustVaultCaches,
  });
  return { status, setup, unlock, lock, vaultPending };
}
