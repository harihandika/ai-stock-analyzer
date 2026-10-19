import React, { InputHTMLAttributes, forwardRef, useState, useId } from "react";
import clsx from "clsx";
import { Eye, EyeOff } from "lucide-react";
import styles from "./input.module.css";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, type, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const generatedId = useId();
    const id = props.id || generatedId;
    const isPassword = type === "password";

    return (
      <div className={styles.wrapper}>
        {label && (
          <label htmlFor={id} className={styles.label}>
            {label}
          </label>
        )}
        <div className={styles.relative}>
          {icon && <div className={styles.icon}>{icon}</div>}
          <input
            ref={ref}
            type={isPassword ? (showPassword ? "text" : "password") : type}
            className={clsx(
              styles.input,
              icon && styles.withIcon,
              isPassword && styles.withPasswordToggle,
              error && styles.errorInput,
              className,
            )}
            {...props}
            id={id}
            aria-invalid={!!error || undefined}
            aria-describedby={error ? id + "-error" : props["aria-describedby"]}
          />
          {isPassword && (
            <button
              type="button"
              className={styles.passwordToggle}
              onClick={() => setShowPassword(!showPassword)}
              aria-label={
                showPassword ? "Sembunyikan password" : "Tampilkan password"
              }
              aria-pressed={showPassword}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          )}
        </div>
        {error && (
          <span id={id + "-error"} role="alert" className={styles.errorText}>
            {error}
          </span>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
