import { useEffect, useLayoutEffect, useRef, useState } from "react";

export type PlanAction = { cle: string; label: string; faire: () => void; disabled?: boolean; title?: string };

/**
 * Menu du clic droit sur le plan.
 *
 * Il ne propose que des gestes applicables là où le curseur est tombé : ajouter un point sur un côté,
 * retirer celui qu'on vise, redresser un côté. Hors édition, il ouvre le local ou lance sa reprise.
 */
export function PlanMenu({
  x,
  y,
  actions,
  onClose,
}: {
  x: number;
  y: number;
  actions: PlanAction[];
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x, y });

  useLayoutEffect(() => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    const marge = 8;
    setPosition({
      x: Math.max(marge, Math.min(x, window.innerWidth - rect.width - marge)),
      y: Math.max(marge, Math.min(y, window.innerHeight - rect.height - marge)),
    });
  }, [actions.length, x, y]);

  useEffect(() => {
    const fermer = (event: Event) => {
      if (!ref.current?.contains(event.target as Node)) {
        onClose();
      }
    };
    const auClavier = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    // Capture des deux côtés : le menu se ferme avant que le plan ne traite le clic ou la touche
    // suivante. En bouillonnement, Échap n'arrivait pas jusqu'ici et le menu restait ouvert.
    window.addEventListener("pointerdown", fermer, true);
    window.addEventListener("keydown", auClavier, true);
    return () => {
      window.removeEventListener("pointerdown", fermer, true);
      window.removeEventListener("keydown", auClavier, true);
    };
  }, [onClose]);

  if (actions.length === 0) {
    return null;
  }
  return (
    <div
      ref={ref}
      className="th-plan-menu"
      role="menu"
      aria-label="Actions sur le plan"
      style={{ left: `${position.x}px`, top: `${position.y}px` }}
      onContextMenu={(event) => event.preventDefault()}
    >
      {actions.map((action, index) => (
        <button
          key={action.cle}
          type="button"
          role="menuitem"
          autoFocus={index === 0}
          disabled={action.disabled}
          title={action.title}
          onClick={() => {
            action.faire();
            onClose();
          }}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
