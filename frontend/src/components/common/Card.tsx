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
        "bg-[#12263A] border border-[#1E3A5F]/70 rounded-[18px] p-6 shadow-xl shadow-black/30 transition-all duration-250 backdrop-blur-sm",
        hoverEffect && "hover:border-[#F4C430]/40 hover:shadow-2xl hover:shadow-[#0B3D91]/20 hover:-translate-y-1",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

