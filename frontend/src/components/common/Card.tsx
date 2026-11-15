import React from "react";
import { cn } from "../../utils/helpers";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hoverEffect = false,
  ...props
}) => {
  return (
    <div
      className={cn(
        "bg-surface border border-slate-800 rounded-xl p-5 shadow-sm transition-all duration-200",
        hoverEffect && "hover:border-slate-700 hover:shadow-md hover:-translate-y-0.5",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

