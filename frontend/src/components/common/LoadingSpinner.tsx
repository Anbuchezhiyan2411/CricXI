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
    sm: "w-6 h-6 border-2",
    md: "w-10 h-10 border-[3px]",
    lg: "w-16 h-16 border-4",
  };

  return (
    <div className={cn("flex flex-col items-center justify-center p-8 space-y-4 select-none", className)}>
      <div className="relative flex items-center justify-center">
        {/* Ambient Glow */}
        <div className="absolute w-14 h-14 rounded-full bg-[#0B3D91]/30 blur-xl animate-pulse" />
        
        {/* Outer Ring */}
        <div
          className={cn(
            "rounded-full border-[#1E3A5F] border-t-[#F4C430] border-r-[#138A36] animate-spin shadow-lg shadow-[#0B3D91]/20",
            sizeClasses[size]
          )}
        />
        {/* Central Core Ball */}
        <div className="absolute w-3 h-3 rounded-full bg-gradient-to-tr from-[#E53935] to-[#F4C430] shadow-sm animate-ping opacity-75" />
      </div>
      {label && (
        <p className="text-xs sm:text-sm text-[#C7D2E2] font-display font-bold uppercase tracking-wider animate-pulse">
          {label}
        </p>
      )}
    </div>
  );
};

