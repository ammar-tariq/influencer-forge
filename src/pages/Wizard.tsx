import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { SelectWithOther } from "../components/common/SelectWithOther";
import {
  AGE_RATINGS,
  BODY_HAIR,
  BODY_TYPES,
  BREAST_SIZES,
  BUTT_SIZES,
  CHEST_BUILDS,
  ETHNICITIES,
  EYE_COLORS,
  GENDERS,
  HAIR_COLORS,
  HAIR_STYLES,
  HEIGHTS,
  HIP_SIZES,
  HUMORS,
  LOOK_STYLES,
  MUSCLE_TONES,
  NICHES,
  OTHER,
  SKIN_TONES,
  TONES,
  WAIST_SIZES,
  resolveSelectValue,
} from "../constants/options";
import type { AgeRating } from "../types";

const STEPS = ["Personality", "Face", "Body"] as const;

export function Wizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [niche, setNiche] = useState<string>("Lifestyle");
  const [nicheOther, setNicheOther] = useState("");
  const [ageRating, setAgeRating] = useState<AgeRating>("Adult");
  const [tone, setTone] = useState<string>("Friendly");
  const [toneOther, setToneOther] = useState("");
  const [humor, setHumor] = useState<string>("Witty");
  const [humorOther, setHumorOther] = useState("");
  const [lookName, setLookName] = useState("");
  const [age, setAge] = useState(25);
  const [gender, setGender] = useState<string>("Female");
  const [genderOther, setGenderOther] = useState("");
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
  const [skinTone, setSkinTone] = useState("Light-medium");
  const [skinOther, setSkinOther] = useState("");
  const [height, setHeight] = useState('Average (5\'4"–5\'7" / 163–170cm)');
  const [heightOther, setHeightOther] = useState("");
  const [bodyType, setBodyType] = useState("Curvy");
  const [bodyTypeOther, setBodyTypeOther] = useState("");
  const [breastSize, setBreastSize] = useState("Medium");
  const [breastOther, setBreastOther] = useState("");
  const [chest, setChest] = useState("Not applicable");
  const [chestOther, setChestOther] = useState("");
  const [waist, setWaist] = useState("Narrow waist");
  const [waistOther, setWaistOther] = useState("");
  const [hips, setHips] = useState("Wide hips");
  const [hipsOther, setHipsOther] = useState("");
  const [butt, setButt] = useState("Round / medium");
  const [buttOther, setButtOther] = useState("");
  const [muscle, setMuscle] = useState("Lightly toned");
  const [muscleOther, setMuscleOther] = useState("");
  const [bodyHair, setBodyHair] = useState("Smooth / shaved");
  const [bodyHairOther, setBodyHairOther] = useState("");
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
  const resolvedGender = resolveSelectValue(gender, genderOther);
  const resolvedEthnicity = resolveSelectValue(ethnicity, ethnicityOther);
  const resolvedHairColor = resolveSelectValue(hairColor, hairColorOther);
  const resolvedHairStyle = resolveSelectValue(hairStyle, hairStyleOther);
  const resolvedEyeColor = resolveSelectValue(eyeColor, eyeColorOther);
  const resolvedStyle = resolveSelectValue(style, styleOther);
  const isMasculine = resolvedGender.toLowerCase() === "male";

  const body: Record<string, string> = {
    skin_tone: resolveSelectValue(skinTone, skinOther),
    height: resolveSelectValue(height, heightOther),
    body_type: resolveSelectValue(bodyType, bodyTypeOther),
    waist: resolveSelectValue(waist, waistOther),
    hips: resolveSelectValue(hips, hipsOther),
    butt_size: resolveSelectValue(butt, buttOther),
    muscle_tone: resolveSelectValue(muscle, muscleOther),
    body_hair: resolveSelectValue(bodyHair, bodyHairOther),
  };
  if (isMasculine) {
    body.chest = resolveSelectValue(chest, chestOther);
  } else {
    body.breast_size = resolveSelectValue(breastSize, breastOther);
  }

  const personalityReady =
    Boolean(name.trim()) &&
    Boolean(resolvedNiche) &&
    Boolean(resolvedTone) &&
    !(niche === OTHER && !nicheOther.trim()) &&
    !(tone === OTHER && !toneOther.trim()) &&
    !(humor === OTHER && !humorOther.trim());

  const faceReady =
    Boolean(resolvedGender) &&
    Boolean(resolvedEthnicity) &&
    Boolean(resolvedHairColor) &&
    Boolean(resolvedHairStyle) &&
    Boolean(resolvedEyeColor) &&
    Boolean(resolvedStyle) &&
    !(gender === OTHER && !genderOther.trim()) &&
    !(ethnicity === OTHER && !ethnicityOther.trim());

  const bodyReady = Boolean(body.skin_tone) && Boolean(body.height) && Boolean(body.body_type);

  const create = useMutation({
    mutationFn: async () => {
      const personality = await api.createPersonality({
        name: name.trim(),
        bio,
        niche: resolvedNiche,
        age_rating: ageRating,
        traits: { tone: resolvedTone, humor: resolvedHumor },
      });
      const looks = await api.createLooks({
        name: lookName.trim() || `${name.trim()}'s Look`,
        age,
        gender: resolvedGender,
        ethnicity: resolvedEthnicity,
        hair_color: resolvedHairColor,
        hair_style: resolvedHairStyle,
        eye_color: resolvedEyeColor,
        style: resolvedStyle,
        body,
      });
      if (faceFile) {
        await api.uploadFaceSeed(looks.id, faceFile);
      }
      const influencer = await api.createInfluencer({
        personality_id: personality.id,
        looks_id: looks.id,
        name: name.trim(),
      });
      // First identity lock shot — full body so base portrait is not only a head crop.
      await api.createGeneration({
        influencer_id: influencer.id,
        user_prompt:
          "full body shot, head to toe visible in frame, standing naturally, wearing casual everyday outfit, clean photo studio background",
        aspect_ratio: "9:16",
        workflow_type: "image",
        is_nsfw: false,
      });
      return influencer;
    },
    onSuccess: (inf) => navigate("/generate", { state: { createdId: inf.id, name: inf.name } }),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Create influencer</h1>
        <p className="muted mt-1">
          Step {step} of 3 — {STEPS[step - 1]}. We’ll queue a first full-body photo, then take you to
          Generate.
        </p>
        <ol className="mt-4 flex gap-2 text-xs">
          {STEPS.map((label, i) => {
            const n = (i + 1) as 1 | 2 | 3;
            const active = step === n;
            const done = step > n;
            return (
              <li
                key={label}
                className={`flex-1 rounded-full px-2 py-2 text-center ${
                  active
                    ? "bg-[var(--accent)] text-[#062116]"
                    : done
                      ? "bg-[var(--bg2)] text-[var(--ink)]"
                      : "bg-[var(--bg2)] muted"
                }`}
              >
                {n}. {label}
              </li>
            );
          })}
        </ol>
      </header>

      {step === 1 && (
        <div className="panel">
          <div className="field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Natasha" />
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
            <p className="muted mt-1 text-xs">Use Adult or 18+ for explicit content later.</p>
          </div>
          <button className="btn" disabled={!personalityReady} onClick={() => setStep(2)}>
            Continue to Face
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="panel">
          <div className="field">
            <label>Look name</label>
            <input
              value={lookName}
              onChange={(e) => setLookName(e.target.value)}
              placeholder={`${name || "Influencer"}'s Look`}
            />
          </div>
          <SelectWithOther
            label="Gender"
            options={GENDERS}
            value={gender}
            otherValue={genderOther}
            onChange={setGender}
            onOtherChange={setGenderOther}
          />
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
            label="Fashion aesthetic"
            options={LOOK_STYLES}
            value={style}
            otherValue={styleOther}
            onChange={setStyle}
            onOtherChange={setStyleOther}
          />
          <div className="field">
            <label>Face Seed (optional — best for consistency)</label>
            <input type="file" accept="image/*" onChange={(e) => setFaceFile(e.target.files?.[0] ?? null)} />
            {facePreview && (
              <img src={facePreview} alt="Face seed preview" className="mt-3 h-48 w-full rounded-xl object-cover" />
            )}
          </div>
          <div className="flex gap-3">
            <button className="btn secondary" onClick={() => setStep(1)}>
              Back
            </button>
            <button className="btn" disabled={!faceReady} onClick={() => setStep(3)}>
              Continue to Body
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="panel">
          <p className="muted mb-4 text-sm">
            These shape the full body in every generation — not just the face.
          </p>
          <SelectWithOther
            label="Skin tone"
            options={SKIN_TONES}
            value={skinTone}
            otherValue={skinOther}
            onChange={setSkinTone}
            onOtherChange={setSkinOther}
          />
          <SelectWithOther
            label="Height"
            options={HEIGHTS}
            value={height}
            otherValue={heightOther}
            onChange={setHeight}
            onOtherChange={setHeightOther}
          />
          <SelectWithOther
            label="Body type"
            options={BODY_TYPES}
            value={bodyType}
            otherValue={bodyTypeOther}
            onChange={setBodyType}
            onOtherChange={setBodyTypeOther}
          />
          {isMasculine ? (
            <SelectWithOther
              label="Chest"
              options={CHEST_BUILDS}
              value={chest}
              otherValue={chestOther}
              onChange={setChest}
              onOtherChange={setChestOther}
            />
          ) : (
            <SelectWithOther
              label="Breast size"
              options={BREAST_SIZES}
              value={breastSize}
              otherValue={breastOther}
              onChange={setBreastSize}
              onOtherChange={setBreastOther}
            />
          )}
          <SelectWithOther
            label="Waist"
            options={WAIST_SIZES}
            value={waist}
            otherValue={waistOther}
            onChange={setWaist}
            onOtherChange={setWaistOther}
          />
          <SelectWithOther
            label="Hips"
            options={HIP_SIZES}
            value={hips}
            otherValue={hipsOther}
            onChange={setHips}
            onOtherChange={setHipsOther}
          />
          <SelectWithOther
            label="Butt size"
            options={BUTT_SIZES}
            value={butt}
            otherValue={buttOther}
            onChange={setButt}
            onOtherChange={setButtOther}
          />
          <SelectWithOther
            label="Muscle tone"
            options={MUSCLE_TONES}
            value={muscle}
            otherValue={muscleOther}
            onChange={setMuscle}
            onOtherChange={setMuscleOther}
          />
          <SelectWithOther
            label="Body hair"
            options={BODY_HAIR}
            value={bodyHair}
            otherValue={bodyHairOther}
            onChange={setBodyHair}
            onOtherChange={setBodyHairOther}
          />
          {error && <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
          <div className="flex flex-wrap gap-3">
            <button className="btn secondary" onClick={() => setStep(2)}>
              Back
            </button>
            <button className="btn" disabled={!bodyReady || create.isPending} onClick={() => create.mutate()}>
              {create.isPending ? "Creating…" : "Create & go to Generate"}
            </button>
            <Link className="btn secondary" to="/">
              Cancel
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
