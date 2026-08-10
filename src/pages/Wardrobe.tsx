import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { BackLink } from "../components/common/BackLink";
import { SelectWithOther } from "../components/common/SelectWithOther";
import { OTHER, WARDROBE_CATEGORIES, resolveSelectValue } from "../constants/options";

export function Wardrobe() {
  const qc = useQueryClient();
  const items = useQuery({ queryKey: ["wardrobe"], queryFn: api.listWardrobe });
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [category, setCategory] = useState<string>("Swimwear");
  const [categoryOther, setCategoryOther] = useState("");
  const [shared, setShared] = useState(false);
  const [assignInf, setAssignInf] = useState<number | "">("");
  const [message, setMessage] = useState<string | null>(null);

  const resolvedCategory = resolveSelectValue(category, categoryOther);
  const canCreate =
    Boolean(name.trim()) &&
    Boolean(keywords.trim()) &&
    Boolean(resolvedCategory) &&
    !(category === OTHER && !categoryOther.trim());

  const create = useMutation({
    mutationFn: async () => {
      const item = await api.createWardrobe({
        name: name.trim(),
        category: resolvedCategory,
        prompt_keywords: keywords.trim(),
        is_shared: shared,
        description: null,
      });
      if (assignInf !== "") {
        await api.assignWardrobe(Number(assignInf), item.id);
      }
      return item;
    },
    onSuccess: (item) => {
      setName("");
      setKeywords("");
      setCategory("Swimwear");
      setCategoryOther("");
      setShared(false);
      setMessage(
        assignInf !== ""
          ? `Created “${item.name}” and assigned to influencer`
          : `Created “${item.name}”. Assign it below or mark shared.`,
      );
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const assign = useMutation({
    mutationFn: ({ infId, itemId }: { infId: number; itemId: number }) =>
      api.assignWardrobe(infId, itemId),
    onSuccess: () => {
      setMessage("Outfit assigned — it will appear when creating posts for that influencer.");
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackLink fallbackTo="/" label="Back" />
      </div>
      <header>
        <h1 className="text-3xl tracking-tight">Wardrobe</h1>
        <p className="muted mt-1">
          Create reusable outfits (e.g. small cute red bikini). Assign to an influencer, then select
          that outfit when creating a post — the same keywords are used every time.
        </p>
      </header>

      <div className="panel space-y-1">
        <h2 className="text-lg">New outfit</h2>
        <div className="field">
          <label>Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Cute red bikini"
          />
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
          <label>Prompt keywords (what she wears)</label>
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="small cute red bikini, matching bottoms, bare midriff"
          />
          <p className="muted mt-1 text-xs">
            These exact words are injected into every SFW generation that selects this outfit.
          </p>
        </div>
        <div className="field">
          <label>Assign to influencer on create (optional)</label>
          <select
            value={assignInf}
            onChange={(e) => setAssignInf(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">None yet</option>
            {(influencers.data ?? []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.name}
              </option>
            ))}
          </select>
        </div>
        <label className="mb-3 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={shared} onChange={(e) => setShared(e.target.checked)} />
          Shared with all influencers
        </label>
        <button className="btn" disabled={!canCreate || create.isPending} onClick={() => create.mutate()}>
          {create.isPending ? "Saving…" : "Add outfit"}
        </button>
        {message && <p className="mt-3 text-sm text-[var(--accent-2)]">{message}</p>}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {(items.data ?? []).map((item) => (
          <div key={item.id} className="panel space-y-3">
            <div>
              <h3 className="text-lg">{item.name}</h3>
              <p className="muted text-sm">
                {item.category}
                {item.is_shared ? " · shared" : ""}
              </p>
              <p className="mt-2 text-sm">{item.prompt_keywords}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                defaultValue=""
                onChange={(e) => {
                  const infId = e.target.value ? Number(e.target.value) : 0;
                  if (infId) assign.mutate({ infId, itemId: item.id });
                  e.target.value = "";
                }}
              >
                <option value="">Assign to…</option>
                {(influencers.data ?? []).map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name}
                  </option>
                ))}
              </select>
              <Link className="btn secondary" to="/generate">
                Use in Create post
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
