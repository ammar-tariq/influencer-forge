import { useState } from "react";
import { useVault } from "../hooks/useVault";

export function Vault() {
  const { status, setup, unlock, lock } = useVault();
  const [pin, setPin] = useState("");

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Privacy Vault</h1>
        <p className="muted mt-1">PIN-protected AES-256-GCM storage for sensitive outputs.</p>
      </header>
      <div className="panel">
        <p className="text-sm">
          Configured: {status.data?.configured ? "yes" : "no"} · Unlocked:{" "}
          {status.data?.unlocked ? "yes" : "no"}
        </p>
        <div className="field mt-4">
          <label>PIN</label>
          <input type="password" value={pin} onChange={(e) => setPin(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-3">
          {!status.data?.configured ? (
            <button className="btn" disabled={pin.length < 4} onClick={() => setup.mutate(pin)}>
              Set PIN
            </button>
          ) : (
            <>
              <button className="btn" disabled={pin.length < 4} onClick={() => unlock.mutate(pin)}>
                Unlock
              </button>
              <button className="btn secondary" onClick={() => lock.mutate()}>
                Lock
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
