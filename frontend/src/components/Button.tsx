import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", className = "", ...rest }: Props) {
  const base = "rounded-button px-6 py-2 text-sm font-normal transition disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-pricing-blue text-white hover:brightness-105"
      : "border border-steel text-ink hover:border-ink";
  return <button className={`${base} ${styles} ${className}`} {...rest} />;
}
