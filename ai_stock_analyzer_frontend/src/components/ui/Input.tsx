import React, { InputHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';
import styles from './input.module.css';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, ...props }, ref) => {
    return (
      <div className={styles.wrapper}>
        {label && (
          <label className={styles.label}>
            {label}
          </label>
        )}
        <div className={styles.relative}>
          {icon && (
            <div className={styles.icon}>
              {icon}
            </div>
          )}
          <input
            ref={ref}
            className={clsx(
              styles.input,
              icon && styles.withIcon,
              error && styles.errorInput,
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <span className={styles.errorText}>{error}</span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
