import React from "react";
import { cn } from "../../utils/helpers";
import { ROLE_BADGE_COLORS } from "../../utils/constants";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "role" | "accent" | "highlight" | "outline";
  roleType?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = "default",
  roleType,
  ...props
}) => {
  const base = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide border";

  let variantStyle = "bg-slate-800 text-slate-300 border-slate-700";
  if (variant === "role" && roleType && ROLE_BADGE_COLORS[roleType]) {
    variantStyle = ROLE_BADGE_COLORS[roleType];
  } else if (variant === "accent") {
    variantStyle = "bg-accent/20 text-accent border-accent/30";
  } else if (variant === "highlight") {
    variantStyle = "bg-highlight/20 text-highlight border-highlight/30";
  } else if (variant === "outline") {
    variantStyle = "bg-transparent text-slate-400 border-slate-700";
  }

  return (
    <span className={cn(base, variantStyle, className)} {...props}>
      {children}
    </span>
  );
};

