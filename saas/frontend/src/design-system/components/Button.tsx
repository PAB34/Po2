import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; icon?: ReactNode; };

export function Button({ variant = "primary", icon, className = "", children, ...props }: ButtonProps) {
  return (
    <button type="button" className={["po2-button", "po2-button--" + variant, className].filter(Boolean).join(" ")} {...props}>
      {icon ? <span className="po2-button__icon">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
}
