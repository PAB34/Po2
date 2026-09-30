// Guide du calage (S2, D173) : dit à quoi servent les points avant de les demander, puis coche les quatre
// clics un à un. Deux repères suffisent : le premier place le calque, le second le tourne et le met à l'échelle.

export type EtapeCalage = { texte: string; etat: "faite" | "en_cours" | "a_venir" };

export function etapesDuCalage(voisin: string, plan: string, couleur: string, clics: number): EtapeCalage[] {
  const textes = [
    `Repère A sur le ${voisin} (calque ${couleur}) : cliquez un point précis que vous retrouverez sur les deux plans.`,
    `Repère A sur le ${plan} (plan noir) : cliquez exactement le même point du bâtiment.`,
    `Repère B sur le ${voisin} (calque ${couleur}) : un autre point, le plus loin possible de A.`,
    `Repère B sur le ${plan} (plan noir) : le même point B. L'outil enregistre alors le calage.`,
  ];
  return textes.map((texte, rang) => ({
    texte,
    etat: rang < clics ? "faite" : rang === clics ? "en_cours" : "a_venir",
  }));
}

export function GuideCalage({
  voisin,
  plan,
  couleur,
  clics,
  busy,
}: {
  voisin: string;
  plan: string;
  couleur: string;
  clics: number;
  busy: boolean;
}) {
  return (
    <>
      <strong>
        Superposer le {voisin} au {plan}
      </strong>
      <p className="th-calage__but">
        Les deux plans ne sont pas placés au même endroit sur leur feuille, ni forcément dans le même sens ou à la
        même taille. Montrez à l'outil <b>deux points du bâtiment</b> qui existent sur les deux plans (un poteau,
        un angle de la cage d'escalier, un croisement d'axes) : pour chacun, où il est sur le {voisin}, puis où il
        est sur le {plan}. L'outil déplace, tourne et met le {voisin} à l'échelle pour que ces deux points
        tombent l'un sur l'autre.
      </p>
      <ol className="th-calage__etapes">
        {etapesDuCalage(voisin, plan, couleur, clics).map((etape) => (
          <li key={etape.texte} className={`th-calage__etape is-${etape.etat}`}>
            {etape.etat === "faite" ? "✓ " : ""}
            {etape.texte}
          </li>
        ))}
      </ol>
      {busy && <span>Enregistrement…</span>}
    </>
  );
}
