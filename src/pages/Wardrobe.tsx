import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function Wardrobe() {
  const qc = useQueryClient();
  const items = useQuery({ queryKey: ["wardrobe"], queryFn: api.listWardrobe });
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [category, setCategory] = useState("Full Outfit");
  const [assignInf, setAssignInf] = useState<number | "">("");
  const [assignItem, setAssignItem] = useState<number | "">("");

  const create = useMutation({
    mutationFn: () =>
      api.createWardrobe({
        name,
        category,
        prompt_keywords: keywords,
        is_shared: false,
      }),
    onSuccess: () => {
      setName("");
      setKeywords("");
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
    },
  });

  const assign = useMutation({
    mutationFn: () => api.assignWardrobe(Number(assignInf), Number(assignItem)),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Wardrobe</h1>
        <p className="muted mt-1">Outfit keywords injected into generation prompts.</p>
      </header>
      <div className="panel">
        <div className="field">
          <label>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label>Category</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {["Top", "Bottom", "Full Outfit", "Accessory"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Prompt keywords</label>
          <input value={keywords} onChange={(e) => setKeywords(e.target.value)} />
        </div>
        <button className="btn" disabled={!name || !keywords} onClick={() => create.mutate()}>
          Add outfit
        </button>
      </div>
      <div className="panel">
        <h2 className="text-lg">Assign to influencer</h2>
        <div className="mt-3 flex flex-wrap gap-3">
          <select value={assignInf} onChange={(e) => setAssignInf(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Influencer…</option>
            {(influencers.data ?? []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.name}
              </option>
            ))}
          </select>
          <select value={assignItem} onChange={(e) => setAssignItem(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Outfit…</option>
            {(items.data ?? []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.name}
              </option>
            ))}
          </select>
          <button className="btn secondary" disabled={!assignInf || !assignItem} onClick={() => assign.mutate()}>
            Assign
          </button>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {(items.data ?? []).map((item) => (
          <div key={item.id} className="panel">
            <h3 className="text-lg">{item.name}</h3>
            <p className="muted text-sm">{item.category}</p>
            <p className="mt-2 text-sm">{item.prompt_keywords}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
