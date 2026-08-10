import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AgeRating } from "../types";

export function Wizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [personalityId, setPersonalityId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [niche, setNiche] = useState("Tech");
  const [ageRating, setAgeRating] = useState<AgeRating>("Family");
  const [tone, setTone] = useState("friendly");
  const [lookName, setLookName] = useState("");
  const [age, setAge] = useState(25);
  const [ethnicity, setEthnicity] = useState("Caucasian");
  const [hairColor, setHairColor] = useState("Brown");
  const [hairStyle, setHairStyle] = useState("Long straight");
  const [eyeColor, setEyeColor] = useState("Brown");
  const [style, setStyle] = useState("Casual");
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: async () => {
      const personality = await api.createPersonality({
        name,
        bio,
        niche,
        age_rating: ageRating,
        traits: { tone, humor: "witty" },
      });
      setPersonalityId(personality.id);
      const looks = await api.createLooks({
        name: lookName || `${name}'s Look`,
        age,
        ethnicity,
        hair_color: hairColor,
        hair_style: hairStyle,
        eye_color: eyeColor,
        style,
      });
      if (faceFile) {
        await api.uploadFaceSeed(looks.id, faceFile);
      }
      await api.createInfluencer({
        personality_id: personality.id,
        looks_id: looks.id,
        name,
      });
    },
    onSuccess: () => navigate("/"),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Create influencer</h1>
        <p className="muted mt-1">Step {step} of 2 — {step === 1 ? "Personality" : "Looks"}</p>
      </header>

      {step === 1 ? (
        <div className="panel">
          <div className="field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Elena" />
          </div>
          <div className="field">
            <label>Bio</label>
            <textarea value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
          </div>
          <div className="field">
            <label>Niche</label>
            <input value={niche} onChange={(e) => setNiche(e.target.value)} />
          </div>
          <div className="field">
            <label>Tone</label>
            <input value={tone} onChange={(e) => setTone(e.target.value)} />
          </div>
          <div className="field">
            <label>Age rating</label>
            <select value={ageRating} onChange={(e) => setAgeRating(e.target.value as AgeRating)}>
              {["Family", "Teen", "Adult", "18+"].map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          <button className="btn" disabled={!name} onClick={() => setStep(2)}>
            Continue to Looks
          </button>
        </div>
      ) : (
        <div className="panel">
          <div className="field">
            <label>Look name</label>
            <input value={lookName} onChange={(e) => setLookName(e.target.value)} />
          </div>
          <div className="field">
            <label>Age ({age})</label>
            <input type="range" min={18} max={80} value={age} onChange={(e) => setAge(Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Ethnicity</label>
            <input value={ethnicity} onChange={(e) => setEthnicity(e.target.value)} />
          </div>
          <div className="field">
            <label>Hair color</label>
            <input value={hairColor} onChange={(e) => setHairColor(e.target.value)} />
          </div>
          <div className="field">
            <label>Hair style</label>
            <input value={hairStyle} onChange={(e) => setHairStyle(e.target.value)} />
          </div>
          <div className="field">
            <label>Eye color</label>
            <input value={eyeColor} onChange={(e) => setEyeColor(e.target.value)} />
          </div>
          <div className="field">
            <label>Style</label>
            <input value={style} onChange={(e) => setStyle(e.target.value)} />
          </div>
          <div className="field">
            <label>Face Seed (optional reference)</label>
            <input type="file" accept="image/*" onChange={(e) => setFaceFile(e.target.files?.[0] ?? null)} />
          </div>
          {error && <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
          <div className="flex gap-3">
            <button className="btn secondary" onClick={() => setStep(1)}>
              Back
            </button>
            <button className="btn" disabled={create.isPending} onClick={() => create.mutate()}>
              {create.isPending ? "Creating…" : personalityId ? "Finish" : "Create influencer"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
