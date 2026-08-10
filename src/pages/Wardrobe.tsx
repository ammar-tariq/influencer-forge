import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { SelectWithOther } from "../components/common/SelectWithOther";
import { OTHER, WARDROBE_CATEGORIES, resolveSelectValue } from "../constants/options";

export function Wardrobe() {
  const qc = useQueryClient();
  const items = useQuery({ queryKey: ["wardrobe"], queryFn: api.listWardrobe });
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [category, setCategory] = useState<string>("Full Outfit");
  const [categoryOther, setCategoryOther] = useState("");
  const [assignInf, setAssignInf] = useState<number | "">("");
  const [assignItem, setAssignItem] = useState<number | "">("");

  const resolvedCategory = resolveSelectValue(category, categoryOther);
  const canCreate =
    Boolean(name.trim()) &&
    Boolean(keywords.trim()) &&
    Boolean(resolvedCategory) &&
    !(category === OTHER && !categoryOther.trim());

  const create = useMutation({
    mutationFn: () =>
      api.createWardrobe({
        name: name.trim(),
        category: resolvedCategory,
        prompt_keywords: keywords.trim(),
        is_shared: false,
      }),
    onSuccess: () => {
      setName("");
      setKeywords("");
      setCategory("Full Outfit");
      setCategoryOther("");
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
        <SelectWithOther
          label="Category"
          options={WARDROBE_CATEGORIES}
          value={category}
          otherValue={categoryOther}
          onChange={setCategory}
          onOtherChange={setCategoryOther}
          otherPlaceholder="e.g. Jewelry set"
        />
        <div className="field">
          <label>Prompt keywords</label>
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="gray oversized hoodie, relaxed fit"
          />
        </div>
        <button className="btn" disabled={!canCreate} onClick={() => create.mutate()}>
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
