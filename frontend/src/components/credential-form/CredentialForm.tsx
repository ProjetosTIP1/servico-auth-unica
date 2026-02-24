"use client";

import { useState } from "react";

import style from "./style.module.css";
import hideIcon from "@/assets/icons/eye-off.png";
import showIcon from "@/assets/icons/eye.png";

export default function CredentialForm({
  onChange,
  value,
  id,
  type,
  label,
  autoFocus,
  onKeyDown,
}: {
  onChange: (value: string) => void;
  value: string;
  id: string;
  type: string;
  label: string;
  autoFocus?: boolean;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}) {
  const [showPassword, setShowPassword] = useState(false);

  const isPassword = type === "password";

  return (
    <div className={style.container}>
      <input
        type={isPassword && !showPassword ? "password" : "text"}
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        // The space in the placeholder is crucial for the floating label effect
        placeholder=" "
        className={style.input}
        autoFocus={autoFocus}
        onKeyDown={onKeyDown}
      />
      <label htmlFor={id} className={style.label}>
        {label}
      </label>
      {isPassword && (
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className={style.toggle}
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? (
            <img src={hideIcon} alt="Hide password icon" />
          ) : (
            <img src={showIcon} alt="Show password icon" />
          )}
        </button>
      )}
    </div>
  );
}
