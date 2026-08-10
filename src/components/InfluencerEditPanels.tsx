import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { SelectWithOther } from "./common/SelectWithOther";
import {
  AGE_RATINGS,
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
  splitSelectValue,
} from "../constants/options";
import type { AgeRating, InfluencerDetail, Looks } from "../types";

type Props = {
  detail: InfluencerDetail;
  onSaved: (opts?: { faceLockStale?: boolean }) => void;
};

function initSelect(value: string | null | undefined, options: readonly string[]) {
  return splitSelectValue(value ?? "", options);
}

export function InfluencerEditPanels({ detail, onSaved }: Props) {
  const personality = detail.personality;
  const looks = detail.looks;
  const [editingPersonality, setEditingPersonality] = useState(false);
  const [editingLooks, setEditingLooks] = useState(false);

  const [name, setName] = useState(personality?.name ?? detail.name);
  const [bio, setBio] = useState(personality?.bio ?? "");
  const [niche, setNiche] = useState("Lifestyle");
  const [nicheOther, setNicheOther] = useState("");
  const [ageRating, setAgeRating] = useState<AgeRating>("Adult");
  const [tone, setTone] = useState("Friendly");
  const [toneOther, setToneOther] = useState("");
  const [humor, setHumor] = useState("Witty");
  const [humorOther, setHumorOther] = useState("");

  const [lookName, setLookName] = useState(looks?.name ?? "");
  const [age, setAge] = useState(looks?.age ?? 25);
  const [gender, setGender] = useState("Female");
  const [genderOther, setGenderOther] = useState("");
  const [ethnicity, setEthnicity] = useState("Caucasian");
  const [ethnicityOther, setEthnicityOther] = useState("");
  const [hairColor, setHairColor] = useState("Brown");
  const [hairColorOther, setHairColorOther] = useState("");
  const [hairStyle, setHairStyle] = useState("Long straight");
  const [hairStyleOther, setHairStyleOther] = useState("");
  const [eyeColor, setEyeColor] = useState("Brown");
  const [eyeColorOther, setEyeColorOther] = useState("");
  const [style, setStyle] = useState("Casual");
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

  useEffect(() => {
    if (!personality) return;
    setName(personality.name);
    setBio(personality.bio ?? "");
    setAgeRating(personality.age_rating);
    const n = initSelect(personality.niche, NICHES);
    setNiche(n.value);
    setNicheOther(n.other);
    const t = initSelect(personality.traits?.tone, TONES);
    setTone(t.value);
    setToneOther(t.other);
    const h = initSelect(personality.traits?.humor, HUMORS);
    setHumor(h.value);
    setHumorOther(h.other);
  }, [personality]);

  useEffect(() => {
    if (!looks) return;
    setLookName(looks.name);
    setAge(looks.age ?? 25);
    const g = initSelect(looks.gender, GENDERS);
    setGender(g.value);
    setGenderOther(g.other);
    const e = initSelect(looks.ethnicity, ETHNICITIES);
    setEthnicity(e.value);
    setEthnicityOther(e.other);
    const hc = initSelect(looks.hair_color, HAIR_COLORS);
    setHairColor(hc.value);
    setHairColorOther(hc.other);
    const hs = initSelect(looks.hair_style, HAIR_STYLES);
    setHairStyle(hs.value);
    setHairStyleOther(hs.other);
    const ey = initSelect(looks.eye_color, EYE_COLORS);
    setEyeColor(ey.value);
    setEyeColorOther(ey.other);
    const st = initSelect(looks.style, LOOK_STYLES);
    setStyle(st.value);
    setStyleOther(st.other);
    const body = looks.body ?? {};
    const sk = initSelect(body.skin_tone, SKIN_TONES);
    setSkinTone(sk.value);
    setSkinOther(sk.other);
    const ht = initSelect(body.height, HEIGHTS);
    setHeight(ht.value);
    setHeightOther(ht.other);
    const bt = initSelect(body.body_type, BODY_TYPES);
    setBodyType(bt.value);
    setBodyTypeOther(bt.other);
    const br = initSelect(body.breast_size, BREAST_SIZES);
    setBreastSize(br.value);
    setBreastOther(br.other);
    const ch = initSelect(body.chest, CHEST_BUILDS);
    setChest(ch.value);
    setChestOther(ch.other);
    const w = initSelect(body.waist, WAIST_SIZES);
    setWaist(w.value);
    setWaistOther(w.other);
    const hi = initSelect(body.hips, HIP_SIZES);
    setHips(hi.value);
    setHipsOther(hi.other);
    const bu = initSelect(body.butt_size, BUTT_SIZES);
    setButt(bu.value);
    setButtOther(bu.other);
    const m = initSelect(body.muscle_tone, MUSCLE_TONES);
    setMuscle(m.value);
    setMuscleOther(m.other);
  }, [looks]);

  const savePersonality = useMutation({
    mutationFn: () =>
      api.updatePersonality(detail.personality_id, {
        name: name.trim(),
        bio,
        niche: resolveSelectValue(niche, nicheOther),
        age_rating: ageRating,
        traits: {
          tone: resolveSelectValue(tone, toneOther),
          humor: resolveSelectValue(humor, humorOther),
        },
      }),
    onSuccess: () => {
      setEditingPersonality(false);
      onSaved();
    },
  });

  const resolvedGender = resolveSelectValue(gender, genderOther);
  const isMasculine = resolvedGender.toLowerCase() === "male";

  const saveLooks = useMutation({
    mutationFn: () => {
      const body: Record<string, string> = {
        skin_tone: resolveSelectValue(skinTone, skinOther),
        height: resolveSelectValue(height, heightOther),
        body_type: resolveSelectValue(bodyType, bodyTypeOther),
        waist: resolveSelectValue(waist, waistOther),
        hips: resolveSelectValue(hips, hipsOther),
        butt_size: resolveSelectValue(butt, buttOther),
        muscle_tone: resolveSelectValue(muscle, muscleOther),
      };
      if (isMasculine) body.chest = resolveSelectValue(chest, chestOther);
      else body.breast_size = resolveSelectValue(breastSize, breastOther);
      return api.updateLooks(detail.looks_id, {
        name: lookName.trim() || `${name.trim()}'s Look`,
        age,
        gender: resolvedGender,
        ethnicity: resolveSelectValue(ethnicity, ethnicityOther),
        hair_color: resolveSelectValue(hairColor, hairColorOther),
        hair_style: resolveSelectValue(hairStyle, hairStyleOther),
        eye_color: resolveSelectValue(eyeColor, eyeColorOther),
        style: resolveSelectValue(style, styleOther),
        body,
      });
    },
    onSuccess: (updated: Looks) => {
      setEditingLooks(false);
      onSaved({ faceLockStale: Boolean(updated.face_lock_stale) });
    },
  });

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="panel">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg">Personality</h2>
          <button
            type="button"
            className="btn secondary"
            onClick={() => setEditingPersonality((v) => !v)}
          >
            {editingPersonality ? "Cancel" : "Edit"}
          </button>
        </div>
        {!editingPersonality && personality && (
          <dl className="muted mt-3 space-y-2 text-sm">
            <div>
              <dt className="font-semibold text-[var(--ink)]">Name</dt>
              <dd>{personality.name}</dd>
            </div>
            <div>
              <dt className="font-semibold text-[var(--ink)]">Niche</dt>
              <dd>{personality.niche}</dd>
            </div>
            <div>
              <dt className="font-semibold text-[var(--ink)]">Age rating</dt>
              <dd>{personality.age_rating}</dd>
            </div>
            {Object.entries(personality.traits || {}).map(([k, v]) => (
              <div key={k}>
                <dt className="font-semibold capitalize text-[var(--ink)]">{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        )}
        {!editingPersonality && !personality && (
          <p className="muted mt-2 text-sm">No personality data.</p>
        )}
        {editingPersonality && (
          <div className="mt-3 space-y-1">
            <div className="field">
              <label>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="field">
              <label>Bio</label>
              <textarea rows={2} value={bio} onChange={(e) => setBio(e.target.value)} />
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
            </div>
            {savePersonality.isError && (
              <p className="text-sm text-[var(--danger)]">{(savePersonality.error as Error).message}</p>
            )}
            <button
              className="btn"
              disabled={savePersonality.isPending || !name.trim() || (niche === OTHER && !nicheOther.trim())}
              onClick={() => savePersonality.mutate()}
            >
              {savePersonality.isPending ? "Saving…" : "Save personality"}
            </button>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg">Looks & body</h2>
          <button type="button" className="btn secondary" onClick={() => setEditingLooks((v) => !v)}>
            {editingLooks ? "Cancel" : "Edit"}
          </button>
        </div>
        {!editingLooks && looks && (
          <dl className="muted mt-3 space-y-2 text-sm">
            <div>
              <dt className="font-semibold text-[var(--ink)]">Gender</dt>
              <dd>{looks.gender ?? "—"}</dd>
            </div>
            <div>
              <dt className="font-semibold text-[var(--ink)]">Age</dt>
              <dd>{looks.age ?? "—"}</dd>
            </div>
            <div>
              <dt className="font-semibold text-[var(--ink)]">Appearance</dt>
              <dd>
                {[looks.ethnicity, looks.hair_color, looks.hair_style, looks.eye_color, looks.style]
                  .filter(Boolean)
                  .join(" · ") || "—"}
              </dd>
            </div>
            {Object.entries(looks.body || {})
              .filter(([, v]) => Boolean(v))
              .map(([k, v]) => (
                <div key={k}>
                  <dt className="font-semibold capitalize text-[var(--ink)]">{k.replace(/_/g, " ")}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
          </dl>
        )}
        {!editingLooks && !looks && <p className="muted mt-2 text-sm">No looks data.</p>}
        {editingLooks && (
          <div className="mt-3 max-h-[28rem] space-y-1 overflow-y-auto pr-1">
            <div className="field">
              <label>Look name</label>
              <input value={lookName} onChange={(e) => setLookName(e.target.value)} />
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
              <input
                type="range"
                min={18}
                max={80}
                value={age}
                onChange={(e) => setAge(Number(e.target.value))}
              />
            </div>
            <SelectWithOther
              label="Ethnicity"
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
              label="Butt"
              options={BUTT_SIZES}
              value={butt}
              otherValue={buttOther}
              onChange={setButt}
              onOtherChange={setButtOther}
            />
            <SelectWithOther
              label="Muscle"
              options={MUSCLE_TONES}
              value={muscle}
              otherValue={muscleOther}
              onChange={setMuscle}
              onOtherChange={setMuscleOther}
            />
            {saveLooks.isError && (
              <p className="text-sm text-[var(--danger)]">{(saveLooks.error as Error).message}</p>
            )}
            <button className="btn" disabled={saveLooks.isPending} onClick={() => saveLooks.mutate()}>
              {saveLooks.isPending ? "Saving…" : "Save looks"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
