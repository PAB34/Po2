import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLElement> & { title?: ReactNode; eyebrow?: ReactNode; action?: ReactNode; };

export function Card({ title, eyebrow, action, className = "", children, ...props }: CardProps) {
  return (
    <section className={["po2-card", className].filter(Boolean).join(" ")} {...props}>
      {title || eyebrow || action ? (
        <header className="po2-card__header">
          <div>{eyebrow ? <span className="po2-eyebrow">{eyebrow}</span> : null}{title ? <h2>{title}</h2> : null}</div>
          {action ? <div className="po2-card__action">{action}</div> : null}
        </header>
      ) : null}
      <div className="po2-card__body">{children}</div>
    </section>
  );
}
