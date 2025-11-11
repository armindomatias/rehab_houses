import React from "react";
import { Loader2 } from "lucide-react";

const cn = (...args: (string | boolean | undefined)[]): string =>
  args.filter(Boolean).join(" ");

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  variant?: "primary" | "secondary";
}

export const Button = ({
  className = "",
  children,
  loading,
  variant = "primary",
  ...props
}: ButtonProps) => {
  if (variant === "secondary") {
    return (
      <button
        {...props}
        className={cn(
          "inline-flex h-10 items-center justify-center gap-2 rounded-xl border px-4 text-sm font-medium",
          "border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          className
        )}
      >
        {children}
      </button>
    );
  }

  return (
    <button
      {...props}
      className={cn(
        "inline-flex h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold",
        "bg-emerald-600 text-white hover:bg-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-100",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        loading && "opacity-80",
        className
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
};

