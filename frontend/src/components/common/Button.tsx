import React from "react";
import { cn } from "../../utils/helpers";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost" | "success" | "gold";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled,
  ...props
}) => {
  const baseStyles = "inline-flex items-center justify-center font-bold uppercase tracking-wider rounded-[14px] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer select-none";

  const variants = {
    primary: "bg-gradient-to-r from-[#0B3D91] via-[#1755BA] to-[#0B3D91] hover:from-[#1755BA] hover:to-[#0B3D91] text-white border border-[#1E3A5F] shadow-lg shadow-[#0B3D91]/35 hover:scale-[1.03] active:scale-[0.98] focus:ring-[#0B3D91]",
    secondary: "bg-[#12263A] hover:bg-[#1E3A5F] text-[#C7D2E2] hover:text-white border border-[#1E3A5F] hover:border-[#F4C430]/40 shadow-sm focus:ring-[#1E3A5F]",
    outline: "border-2 border-[#F4C430] text-[#F4C430] hover:bg-[#F4C430]/10 hover:shadow-md hover:shadow-[#F4C430]/20 focus:ring-[#F4C430]",
    success: "bg-gradient-to-r from-[#138A36] to-[#0F6F2B] hover:from-[#17A340] hover:to-[#138A36] text-white shadow-lg shadow-[#138A36]/30 hover:scale-[1.03] active:scale-[0.98] focus:ring-[#138A36]",
    gold: "bg-gradient-to-r from-[#F4C430] to-[#D4A516] hover:from-[#FDE047] hover:to-[#F4C430] text-[#081826] font-black shadow-lg shadow-[#F4C430]/30 hover:scale-[1.03] active:scale-[0.98] focus:ring-[#F4C430]",
    danger: "bg-gradient-to-r from-[#E53935] to-[#C62828] hover:from-[#EF5350] hover:to-[#E53935] text-white shadow-lg shadow-[#E53935]/30 hover:scale-[1.03] active:scale-[0.98] focus:ring-[#E53935]",
    ghost: "text-[#C7D2E2] hover:text-white hover:bg-[#12263A]/80 border border-transparent hover:border-[#1E3A5F] focus:ring-[#1E3A5F]",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-[11px]",
    md: "px-5 py-2.5 text-xs",
    lg: "px-7 py-3.5 text-sm",
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v8H4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
};

