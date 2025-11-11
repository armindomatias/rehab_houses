import React from "react";

const cn = (...args: (string | boolean | undefined)[]): string =>
  args.filter(Boolean).join(" ");

interface CardProps {
  className?: string;
  children: React.ReactNode;
}

export const Card = ({ className = "", children }: CardProps) => (
  <div
    className={cn(
      "rounded-2xl border border-neutral-200 bg-white shadow-sm",
      className
    )}
  >
    {children}
  </div>
);

interface CardHeaderProps {
  title: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const CardHeader = ({ title, icon, action }: CardHeaderProps) => (
  <div className="flex items-center justify-between gap-3 border-b border-neutral-100 p-4">
    <div className="flex items-center gap-2 text-neutral-800">
      {icon}
      <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
    </div>
    {action}
  </div>
);

interface CardBodyProps {
  className?: string;
  children: React.ReactNode;
}

export const CardBody = ({ className = "", children }: CardBodyProps) => (
  <div className={cn("p-4", className)}>{children}</div>
);

