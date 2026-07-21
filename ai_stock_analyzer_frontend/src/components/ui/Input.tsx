import React, { InputHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, ...props }, ref) => {
    return (
      <div className="flex flex-col space-y-1.5 w-full">
        {label && (
          <label className="text-sm font-medium text-slate-300">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            className={clsx(
              'flex h-10 w-full rounded-md border border-[rgba(255,255,255,0.08)] bg-[#0a0b10] px-3 py-2 text-sm text-white placeholder:text-slate-500',
              'focus:outline-none focus:ring-1 focus:ring-[#3b82f6] focus:border-[#3b82f6]',
              'transition-colors duration-200',
              'disabled:cursor-not-allowed disabled:opacity-50',
              icon && 'pl-10',
              error && 'border-[#f43f5e] focus:ring-[#f43f5e] focus:border-[#f43f5e]',
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <span className="text-xs text-[#f43f5e]">{error}</span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
