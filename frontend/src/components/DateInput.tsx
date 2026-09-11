import { useEffect, useRef, useState, type FocusEventHandler } from "react";
import { isoDate, parseDisplayDate } from "../format";
import { useT } from "../i18n";

function display(value: string): string {
  return value ? isoDate(value) : "";
}

/** A date field that always reads dd/mm/yyyy. A native date input follows the operating
 * system's locale, so an English Windows shows mm/dd/yyyy on a Vietnamese screen and
 * 03/04 reads as the wrong day. Values in and out stay ISO `YYYY-MM-DD`. */
export function DateInput({
  value,
  onChange,
  min,
  max,
  required,
  onFocus,
}: {
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
  required?: boolean;
  onFocus?: FocusEventHandler<HTMLInputElement>;
}) {
  const t = useT();
  const inputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState(() => display(value));
  const [syncedValue, setSyncedValue] = useState(value);
  const [blurred, setBlurred] = useState(false);

  // A new value from outside (a preset, the calendar, a reset) replaces what is shown,
  // unless the typed text already says that same date.
  if (value !== syncedValue) {
    setSyncedValue(value);
    if (parseDisplayDate(text) !== value) setText(display(value));
  }

  const inRange = (iso: string) => !((min && iso < min) || (max && iso > max));
  const parsed = parseDisplayDate(text);
  const error = !text.trim()
    ? ""
    : parsed === null
      ? t.common.invalidDate
      : inRange(parsed)
        ? ""
        : t.common.dateOutOfRange;

  // Keeps a form from submitting the last good date while the field shows a bad one.
  useEffect(() => {
    inputRef.current?.setCustomValidity(error);
  }, [error]);

  const showError = blurred && error !== "";

  return (
    <input
      ref={inputRef}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      maxLength={10}
      placeholder={t.common.datePlaceholder}
      value={text}
      required={required}
      aria-invalid={showError || undefined}
      title={showError ? error : undefined}
      onFocus={onFocus}
      onChange={(event) => {
        const next = event.target.value;
        setText(next);
        setBlurred(false);
        if (!next.trim()) {
          onChange("");
          return;
        }
        const nextDate = parseDisplayDate(next);
        if (nextDate && inRange(nextDate)) onChange(nextDate);
      }}
      onBlur={() => {
        setBlurred(true);
        if (parsed && inRange(parsed)) setText(display(parsed));
      }}
    />
  );
}
