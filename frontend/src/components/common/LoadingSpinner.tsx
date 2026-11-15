import React from "react";
import { cn } from "../../utils/helpers";

export interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  className,
  label,
}) => {
  const sizeClasses = {
    sm: "w-5 h-5 border-2",
    md: "w-8 h-8 border-3",
    lg: "w-12 h-12 border-4",
  };

  return (
    <div className={cn("flex flex-col items-center justify-center p-6 space-y-3", className)}>
      <div
        className={cn(
          "rounded-full border-slate-700 border-t-accent animate-spin",
          sizeClasses[size]
        )}
      />
      {label && <p className="text-sm text-slate-400 font-medium">{label}</p>}
    </div>
  );
};

