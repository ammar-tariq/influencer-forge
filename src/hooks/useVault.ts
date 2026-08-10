import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function useVault() {
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });
  const setup = useMutation({
    mutationFn: (pin: string) => api.vaultSetup(pin),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vault-status"] }),
  });
  const unlock = useMutation({
    mutationFn: (pin: string) => api.vaultUnlock(pin),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vault-status"] }),
  });
  const lock = useMutation({
    mutationFn: () => api.vaultLock(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vault-status"] }),
  });
  return { status, setup, unlock, lock };
}
