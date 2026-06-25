import type { ReactNode } from "react";
import { Button } from "./Button";

type DrawerProps = { open: boolean; title: string; eyebrow?: string; description?: string; wide?: boolean; children: ReactNode; footer?: ReactNode; onClose: () => void; };

export function Drawer({ open, title, eyebrow, description, wide = false, children, footer, onClose }: DrawerProps) {
  return (
    <>
      <div className={["po2-drawer-backdrop", open ? "po2-drawer-backdrop--open" : ""].join(" ")} onClick={onClose} />
      <aside className={["po2-drawer", open ? "po2-drawer--open" : "", wide ? "po2-drawer--wide" : ""].join(" ")} aria-hidden={!open}>
        <header className="po2-drawer__header"><Button variant="ghost" onClick={onClose} aria-label="Fermer le panneau">×</Button>{eyebrow ? <span className="po2-eyebrow">{eyebrow}</span> : null}<h2>{title}</h2>{description ? <p>{description}</p> : null}</header>
        <div className="po2-drawer__body">{children}</div>
        {footer ? <footer className="po2-drawer__footer">{footer}</footer> : null}
      </aside>
    </>
  );
}
