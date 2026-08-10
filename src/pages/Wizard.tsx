import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { SelectWithOther } from "../components/common/SelectWithOther";
import {
  AGE_RATINGS,
  ETHNICITIES,
  EYE_COLORS,
  HAIR_COLORS,
  HAIR_STYLES,
  HUMORS,
  LOOK_STYLES,
  NICHES,
  OTHER,
  TONES,
  resolveSelectValue,
} from "../constants/options";
import type { AgeRating } from "../types";

export function Wizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [personalityId, setPersonalityId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [niche, setNiche] = useState<string>("Tech");
  const [nicheOther, setNicheOther] = useState("");
  const [ageRating, setAgeRating] = useState<AgeRating>("Family");
  const [tone, setTone] = useState<string>("Friendly");
  const [toneOther, setToneOther] = useState("");
  const [humor, setHumor] = useState<string>("Witty");
  const [humorOther, setHumorOther] = useState("");
  const [lookName, setLookName] = useState("");
  const [age, setAge] = useState(25);
  const [ethnicity, setEthnicity] = useState<string>("Caucasian");
  const [ethnicityOther, setEthnicityOther] = useState("");
  const [hairColor, setHairColor] = useState<string>("Brown");
  const [hairColorOther, setHairColorOther] = useState("");
  const [hairStyle, setHairStyle] = useState<string>("Long straight");
  const [hairStyleOther, setHairStyleOther] = useState("");
  const [eyeColor, setEyeColor] = useState<string>("Brown");
  const [eyeColorOther, setEyeColorOther] = useState("");
  const [style, setStyle] = useState<string>("Casual");
  const [styleOther, setStyleOther] = useState("");
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [facePreview, setFacePreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!faceFile) {
      setFacePreview(null);
      return;
    }
    const url = URL.createObjectURL(faceFile);
    setFacePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [faceFile]);

  const resolvedNiche = resolveSelectValue(niche, nicheOther);
  const resolvedTone = resolveSelectValue(tone, toneOther);
  const resolvedHumor = resolveSelectValue(humor, humorOther);
  const resolvedEthnicity = resolveSelectValue(ethnicity, ethnicityOther);
  const resolvedHairColor = resolveSelectValue(hairColor, hairColorOther);
  const resolvedHairStyle = resolveSelectValue(hairStyle, hairStyleOther);
  const resolvedEyeColor = resolveSelectValue(eyeColor, eyeColorOther);
  const resolvedStyle = resolveSelectValue(style, styleOther);

  const personalityReady =
    Boolean(name.trim()) &&
    Boolean(resolvedNiche) &&
    Boolean(resolvedTone) &&
    !(niche === OTHER && !nicheOther.trim()) &&
    !(tone === OTHER && !toneOther.trim()) &&
    !(humor === OTHER && !humorOther.trim());

  const looksReady =
    Boolean(resolvedEthnicity) &&
    Boolean(resolvedHairColor) &&
    Boolean(resolvedHairStyle) &&
    Boolean(resolvedEyeColor) &&
    Boolean(resolvedStyle) &&
    !(ethnicity === OTHER && !ethnicityOther.trim()) &&
    !(hairColor === OTHER && !hairColorOther.trim()) &&
    !(hairStyle === OTHER && !hairStyleOther.trim()) &&
    !(eyeColor === OTHER && !eyeColorOther.trim()) &&
    !(style === OTHER && !styleOther.trim());

  const create = useMutation({
    mutationFn: async () => {
      const personality = await api.createPersonality({
        name: name.trim(),
        bio,
        niche: resolvedNiche,
        age_rating: ageRating,
        traits: { tone: resolvedTone, humor: resolvedHumor },
      });
      setPersonalityId(personality.id);
      const looks = await api.createLooks({
        name: lookName.trim() || `${name.trim()}'s Look`,
        age,
        ethnicity: resolvedEthnicity,
        hair_color: resolvedHairColor,
        hair_style: resolvedHairStyle,
        eye_color: resolvedEyeColor,
        style: resolvedStyle,
      });
      if (faceFile) {
        await api.uploadFaceSeed(looks.id, faceFile);
      }
      const influencer = await api.createInfluencer({
        personality_id: personality.id,
        looks_id: looks.id,
        name: name.trim(),
      });
      // Queue a first studio portrait so the dashboard has a model image ASAP.
      await api.createGeneration({
        influencer_id: influencer.id,
        user_prompt:
          "studio headshot portrait, soft key light, looking at camera, sharp focus, natural skin",
        aspect_ratio: "1:1",
        workflow_type: "image",
      });
      return influencer;
    },
    onSuccess: () => navigate("/"),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Create influencer</h1>
        <p className="muted mt-1">
          Step {step} of 2 — {step === 1 ? "Personality" : "Looks"}. A first portrait is queued after
          create so you can see your model on the Studio page.
        </p>
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
          <SelectWithOther
            label="Niche"
            options={NICHES}
            value={niche}
            otherValue={nicheOther}
            onChange={setNiche}
            onOtherChange={setNicheOther}
            otherPlaceholder="e.g. Sustainable living"
          />
          <SelectWithOther
            label="Tone"
            options={TONES}
            value={tone}
            otherValue={toneOther}
            onChange={setTone}
            onOtherChange={setToneOther}
          />
          <SelectWithOther
            label="Humor"
            options={HUMORS}
            value={humor}
            otherValue={humorOther}
            onChange={setHumor}
            onOtherChange={setHumorOther}
          />
          <div className="field">
            <label>Age rating</label>
            <select value={ageRating} onChange={(e) => setAgeRating(e.target.value as AgeRating)}>
              {AGE_RATINGS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
            <p className="muted mt-1 text-xs">Fixed ratings for content policy — not customizable.</p>
          </div>
          <button className="btn" disabled={!personalityReady} onClick={() => setStep(2)}>
            Continue to Looks
          </button>
        </div>
      ) : (
        <div className="panel">
          <div className="field">
            <label>Look name</label>
            <input
              value={lookName}
              onChange={(e) => setLookName(e.target.value)}
              placeholder={`${name || "Influencer"}'s Look`}
            />
          </div>
          <div className="field">
            <label>Age ({age})</label>
            <input type="range" min={18} max={80} value={age} onChange={(e) => setAge(Number(e.target.value))} />
          </div>
          <SelectWithOther
            label="Ethnicity / appearance"
            options={ETHNICITIES}
            value={ethnicity}
            otherValue={ethnicityOther}
            onChange={setEthnicity}
            onOtherChange={setEthnicityOther}
          />
          <SelectWithOther
            label="Hair color"
            options={HAIR_COLORS}
            value={hairColor}
            otherValue={hairColorOther}
            onChange={setHairColor}
            onOtherChange={setHairColorOther}
          />
          <SelectWithOther
            label="Hair style"
            options={HAIR_STYLES}
            value={hairStyle}
            otherValue={hairStyleOther}
            onChange={setHairStyle}
            onOtherChange={setHairStyleOther}
          />
          <SelectWithOther
            label="Eye color"
            options={EYE_COLORS}
            value={eyeColor}
            otherValue={eyeColorOther}
            onChange={setEyeColor}
            onOtherChange={setEyeColorOther}
          />
          <SelectWithOther
            label="Style"
            options={LOOK_STYLES}
            value={style}
            otherValue={styleOther}
            onChange={setStyle}
            onOtherChange={setStyleOther}
          />
          <div className="field">
            <label>Face Seed (optional reference)</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFaceFile(e.target.files?.[0] ?? null)}
            />
            {facePreview && (
              <img
                src={facePreview}
                alt="Face seed preview"
                className="mt-3 h-48 w-full rounded-xl object-cover"
              />
            )}
          </div>
          {error && <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
          <div className="flex gap-3">
            <button className="btn secondary" onClick={() => setStep(1)}>
              Back
            </button>
            <button
              className="btn"
              disabled={!looksReady || create.isPending}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Creating…" : personalityId ? "Finish" : "Create influencer"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
