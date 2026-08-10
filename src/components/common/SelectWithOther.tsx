import { OTHER } from "../../constants/options";

type Props = {
  id?: string;
  label: string;
  options: readonly string[];
  value: string;
  otherValue: string;
  onChange: (value: string) => void;
  onOtherChange: (value: string) => void;
  otherPlaceholder?: string;
};

/**
 * Dropdown with a trailing "Other" choice that reveals a free-text field.
 * `value` is the selected option label; resolved custom text lives in `otherValue`.
 */
export function SelectWithOther({
  id,
  label,
  options,
  value,
  otherValue,
  onChange,
  onOtherChange,
  otherPlaceholder = "Type your own…",
}: Props) {
  const isOther = value === OTHER;
  const selectId = id ?? label.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="field">
      <label htmlFor={selectId}>{label}</label>
      <select id={selectId} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
      {isOther && (
        <input
          className="mt-2"
          value={otherValue}
          onChange={(e) => onOtherChange(e.target.value)}
          placeholder={otherPlaceholder}
          aria-label={`${label} custom value`}
        />
      )}
    </div>
  );
}
