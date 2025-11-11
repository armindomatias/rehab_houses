import React from "react";

const cn = (...args: (string | boolean | undefined)[]): string =>
  args.filter(Boolean).join(" ");

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = ({ className = "", ...props }: InputProps) => (
  <input
    {...props}
    className={cn(
      "h-12 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm",
      "placeholder:text-neutral-400 focus:border-emerald-500 focus:outline-none focus:ring-4 focus:ring-emerald-100",
      "disabled:opacity-50 disabled:cursor-not-allowed",
      className
    )}
  />
);

