// Éditeur de composition d'une paroi opaque (couches de l'intérieur vers l'extérieur), partagé par
// la bibliothèque de projet et les modèles. Recherche unique pour ajouter une couche.
import { useMemo, useState } from "react";

import { useAuth } from "../../providers/AuthProvider";
import {
  DELTA_U2_LABELS,
  WALL_TYPE_LABELS,
  elementCellLabel,
  elementSignals,
  elementTableLabel,
  materialLabel,
  normalizeSearch,
  wallApi,
  type ElementTable,
  type ElementsEdition,
  type Material,
  type MaterialsEdition,
  type ThicknessResult,
  type WallFacing,
  type WallLayerRequest,
  type WallRequest,
  type WallType,
} from "../library";
import { parseDecimal } from "../scale";

export type LayerKind = "materiau" | "element" | "lambda" | "resistance" | "lame_air" | "lame_air_ventilee";

export type Layer = {
  key: number;
  type: LayerKind;
  family: string;
  materialId: string;
  tableId: string;
  // Case du tableau d'éléments, « ligne:colonne ».
  cell: string;
  variant: string;
  lambda: string;
  thicknessCm: string;
  thicknessMm: string;
  r: string;
  label: string;
  insulation: boolean;
};

export type WallDraft = { wallType: WallType; facing: WallFacing; level: number; deltaU1: string; layers: Layer[] };

export const KIND_LABELS: Record<LayerKind, string> = {
  materiau: "Matériau de la bibliothèque",
  element: "Élément à résistance tabulée",
  lambda: "Matériau à λ connue (fabricant)",
  resistance: "Élément à résistance connue",
  lame_air: "Lame d'air non ventilée",
  lame_air_ventilee: "Lame d'air fortement ventilée",
};

// Couches ajoutées par bouton ; les matériaux et éléments passent par la recherche.
const BUTTON_KINDS: LayerKind[] = ["lambda", "resistance", "lame_air", "lame_air_ventilee", "materiau", "element"];

// Mots du métier absents des libellés officiels.
const SYNONYMS: [RegExp, string][] = [
  [/blocs creux en beton/, "parpaing agglo agglomere"],
  [/plaque.*platre|plaques de platre/, "ba13 ba 13 placo"],
  [/polystyrene expanse/, "pse"],
  [/polystyrene extrude/, "xps"],
  [/polyurethane/, "pu pir"],
  [/laine|laines minerales/, "isolant"],
  [/beton cellulaire/, "siporex ytong"],
];

let nextKey = 1;

const decimalText = (value: number | null | undefined, factor = 1) =>
  value === null || value === undefined ? "" : String(Math.round(value * factor * 1000) / 1000).replace(".", ",");

export function newLayer(type: LayerKind, changes: Partial<Layer> = {}): Layer {
  nextKey += 1;
  return {
    key: nextKey,
    type,
    family: "",
    materialId: "",
    tableId: "",
    cell: "",
    variant: "",
    lambda: "",
    thicknessCm: "",
    thicknessMm: "",
    r: "",
    label: "",
    insulation: false,
    ...changes,
  };
}

function layerFromRequest(layer: WallLayerRequest): Layer {
  switch (layer.type) {
    case "materiau":
      return newLayer("materiau", {
        materialId: layer.materiau_id,
        thicknessCm: decimalText(layer.epaisseur_m, 100),
        insulation: Boolean(layer.isolant),
        label: layer.libelle ?? "",
      });
    case "element":
      return newLayer("element", { tableId: layer.tableau_id, cell: `${layer.ligne}:${layer.colonne}`, variant: layer.variante ?? "" });
    case "lambda":
      return newLayer("lambda", {
        lambda: decimalText(layer.lambda),
        thicknessCm: decimalText(layer.epaisseur_m, 100),
        insulation: Boolean(layer.isolant),
        label: layer.libelle ?? "",
      });
    case "resistance":
      return newLayer("resistance", { r: decimalText(layer.r), label: layer.libelle ?? "" });
    case "lame_air":
      return newLayer("lame_air", { thicknessMm: decimalText(layer.epaisseur_mm) });
    default:
      return newLayer("lame_air_ventilee");
  }
}

export function draftFromComposition(composition: Partial<WallRequest>, fallbackType: WallType, fallbackFacing: WallFacing): WallDraft {
  return {
    wallType: composition.type ?? fallbackType,
    facing: composition.donne_sur ?? fallbackFacing,
    level: composition.niveau_delta_u2 ?? 1,
    deltaU1: decimalText(composition.delta_u1 ?? 0),
    layers: (composition.couches ?? []).map(layerFromRequest),
  };
}

function toRequest(layer: Layer, index: number): WallLayerRequest {
  const label = layer.label.trim() || undefined;
  switch (layer.type) {
    case "materiau": {
      const thickness = parseDecimal(layer.thicknessCm);
      if (!layer.materialId || !thickness) {
        throw new Error(`Couche ${index + 1} : choisissez un matériau et une épaisseur.`);
      }
      return { type: "materiau", materiau_id: layer.materialId, epaisseur_m: thickness / 100, isolant: layer.insulation, libelle: label };
    }
    case "element": {
      if (!layer.tableId || !layer.cell) {
        throw new Error(`Couche ${index + 1} : choisissez un élément du tableau.`);
      }
      const [row, column] = layer.cell.split(":").map(Number);
      return { type: "element", tableau_id: layer.tableId, ligne: row, colonne: column, variante: layer.variant || undefined };
    }
    case "lambda": {
      const thickness = parseDecimal(layer.thicknessCm);
      const lambda = parseDecimal(layer.lambda);
      if (!thickness || !lambda) {
        throw new Error(`Couche ${index + 1} : saisissez λ et l'épaisseur.`);
      }
      return { type: "lambda", lambda, epaisseur_m: thickness / 100, isolant: layer.insulation, libelle: label };
    }
    case "resistance": {
      const r = parseDecimal(layer.r);
      if (!r) {
        throw new Error(`Couche ${index + 1} : saisissez la résistance R.`);
      }
      return { type: "resistance", r, libelle: label };
    }
    case "lame_air": {
      const thickness = parseDecimal(layer.thicknessMm);
      if (!thickness) {
        throw new Error(`Couche ${index + 1} : saisissez l'épaisseur de la lame d'air.`);
      }
      return { type: "lame_air", epaisseur_mm: thickness };
    }
    default:
      return { type: "lame_air_ventilee" };
  }
}

// Lève une erreur lisible si une couche est incomplète.
export function compositionFromDraft(draft: WallDraft): WallRequest {
  return {
    type: draft.wallType,
    donne_sur: draft.facing,
    niveau_delta_u2: draft.level,
    delta_u1: parseDecimal(draft.deltaU1) ?? 0,
    couches: draft.layers.map(toRequest),
  };
}

type SearchOption = { key: string; text: string; label: string; detail: string; make: () => Layer };

function searchOptions(materials: Material[], tables: ElementTable[]): SearchOption[] {
  const withSynonyms = (text: string) => {
    const normalized = normalizeSearch(text);
    return `${normalized} ${SYNONYMS.filter(([pattern]) => pattern.test(normalized)).map(([, words]) => words).join(" ")}`;
  };
  const options: SearchOption[] = materials.map((material) => ({
    key: `m:${material.id}`,
    text: withSynonyms(`${material.section_titre} ${material.libelle} ${material.rho_texte}`),
    label: materialLabel(material),
    detail: `λ ${material.lambda.toLocaleString("fr-FR")} · matériau`,
    make: () => newLayer("materiau", { family: material.famille ?? "", materialId: material.id, insulation: material.famille === "2.6" }),
  }));
  for (const table of tables) {
    table.lignes.forEach((line, row) =>
      line.valeurs.forEach((value, column) => {
        if (value === null) {
          return;
        }
        options.push({
          key: `e:${table.id}:${row}:${column}`,
          text: withSynonyms(`${table.titre} ${line.libelle} ${table.colonnes.length > 1 ? table.colonnes[column] : ""}`),
          label: `${table.titre} — ${elementCellLabel(table, row, column)}`,
          detail: `R ${value.toLocaleString("fr-FR")} · élément tabulé`,
          make: () => newLayer("element", { family: table.famille, tableId: table.id, cell: `${row}:${column}`, insulation: table.isolant }),
        });
      }),
    );
  }
  return options;
}

function LayerSearch({ options, onPick }: { options: SearchOption[]; onPick: (layer: Layer) => void }) {
  const [query, setQuery] = useState("");
  const tokens = normalizeSearch(query.trim()).split(/\s+/).filter(Boolean);
  const results = query.trim().length < 2 ? [] : options.filter((option) => tokens.every((token) => option.text.includes(token))).slice(0, 12);
  return (
    <div className="th-search">
      <input
        value={query}
        placeholder="Ajouter une couche : rechercher un matériau ou un élément (ex. parpaing 20, laine de verre, ba13)"
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setQuery("");
          }
        }}
      />
      {results.length > 0 && (
        <ul className="th-search__results">
          {results.map((result) => (
            <li key={result.key}>
              <button
                type="button"
                onClick={() => {
                  onPick(result.make());
                  setQuery("");
                }}
              >
                <span>{result.label}</span>
                <small className="th-muted">{result.detail}</small>
              </button>
            </li>
          ))}
        </ul>
      )}
      {query.trim().length >= 2 && results.length === 0 && <p className="th-muted">Aucun résultat : essayez un autre mot, ou ajoutez une couche « λ connue ».</p>}
    </div>
  );
}

function cellOptions(table: ElementTable): { value: string; label: string }[] {
  const options: { value: string; label: string }[] = [];
  table.lignes.forEach((line, row) =>
    line.valeurs.forEach((value, column) => {
      if (value !== null) {
        const warning = elementSignals(table, row, column).length ? " · à vérifier" : "";
        options.push({ value: `${row}:${column}`, label: `${elementCellLabel(table, row, column)} · R ${value.toLocaleString("fr-FR")}${warning}` });
      }
    }),
  );
  return options;
}

type EditorProps = {
  draft: WallDraft;
  onChange: (draft: WallDraft) => void;
  materials?: MaterialsEdition;
  elements?: ElementsEdition;
};

export function WallDraftEditor({ draft, onChange, materials, elements }: EditorProps) {
  const { token } = useAuth();
  const materialList = materials?.materiaux ?? [];
  const tables = elements?.tableaux ?? [];
  const options = useMemo(() => searchOptions(materialList, tables), [materialList, tables]);
  const byFamily = useMemo(() => {
    const groups = new Map<string, Material[]>();
    for (const material of materialList) {
      groups.set(material.famille ?? "", [...(groups.get(material.famille ?? "") ?? []), material]);
    }
    return groups;
  }, [materialList]);
  const [insulationIndex, setInsulationIndex] = useState<number | null>(null);
  const [target, setTarget] = useState("0,20");
  const [thickness, setThickness] = useState<ThicknessResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (changes: Partial<WallDraft>) => onChange({ ...draft, ...changes });
  const setLayers = (layers: Layer[]) => set({ layers });
  const update = (key: number, changes: Partial<Layer>) => setLayers(draft.layers.map((layer) => (layer.key === key ? { ...layer, ...changes } : layer)));
  const move = (index: number, offset: number) => {
    const next = [...draft.layers];
    const [layer] = next.splice(index, 1);
    next.splice(index + offset, 0, layer);
    setLayers(next);
  };
  const materialOf = (layer: Layer) => materialList.find((material) => material.id === layer.materialId);
  const sizable = draft.layers.map((layer, index) => ({ layer, index })).filter(({ layer }) => layer.type === "materiau" || layer.type === "lambda");

  async function solve() {
    setError(null);
    setThickness(null);
    try {
      const goal = parseDecimal(target);
      if (insulationIndex === null || !goal) {
        throw new Error("Choisissez la couche isolante et le U cible.");
      }
      setThickness(await wallApi.thickness(token!, compositionFromDraft(draft), insulationIndex, goal));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Calcul impossible.");
    }
  }

  return (
    <div className="th-form">
      <div className="th-inline-form">
        <label className="th-field th-field--grow">
          <span>Type de paroi</span>
          <select value={draft.wallType} onChange={(event) => set({ wallType: event.target.value as WallType })}>
            {Object.entries(WALL_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="th-field">
          <span>Donne sur</span>
          <select value={draft.facing} onChange={(event) => set({ facing: event.target.value as WallFacing })}>
            <option value="exterieur">L'extérieur</option>
            <option value="local_non_chauffe">Un local non chauffé ou un autre local</option>
          </select>
        </label>
        <label className="th-field">
          <span>Correction ΔU2</span>
          <select value={draft.level} onChange={(event) => set({ level: Number(event.target.value) })}>
            {Object.entries(DELTA_U2_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="th-field">
          <span>ΔU1 ponts intégrés, W/(m²·K)</span>
          <input className="th-input-xs" inputMode="decimal" value={draft.deltaU1} onChange={(event) => set({ deltaU1: event.target.value })} />
        </label>
      </div>

      <LayerSearch options={options} onPick={(layer) => setLayers([...draft.layers, layer])} />

      {draft.layers.length > 0 && (
        <div className="th-table-wrap" style={{ padding: 0 }}>
          <table className="th-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Couche (intérieur → extérieur)</th>
                <th>Épaisseur</th>
                <th>Isolant</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {draft.layers.map((layer, index) => {
                const family = layer.family || materialOf(layer)?.famille || tables.find((table) => table.id === layer.tableId)?.famille || "";
                const table = tables.find((item) => item.id === layer.tableId);
                const [row, column] = layer.cell ? layer.cell.split(":").map(Number) : [-1, -1];
                const variants =
                  table && row >= 0 ? Object.entries(table.variantes).filter(([key]) => (table.lignes[row]?.variantes[key] ?? [])[column] != null) : [];
                const signals = table && row >= 0 ? elementSignals(table, row, column) : [];
                return (
                  <tr key={layer.key}>
                    <td>{index + 1}</td>
                    <td>
                      <div className="th-muted" style={{ fontSize: "0.78rem" }}>
                        {KIND_LABELS[layer.type]}
                      </div>
                      {layer.type === "materiau" && (
                        <div className="th-inline">
                          <select value={family} onChange={(event) => update(layer.key, { family: event.target.value, materialId: "" })}>
                            <option value="">Famille…</option>
                            {(materials?.familles ?? []).map((item) => (
                              <option key={item.section} value={item.section}>
                                {item.titre}
                              </option>
                            ))}
                          </select>
                          <select
                            value={layer.materialId}
                            disabled={!family}
                            onChange={(event) => update(layer.key, { materialId: event.target.value })}
                            style={{ maxWidth: "24rem" }}
                          >
                            <option value="">Matériau…</option>
                            {(byFamily.get(family) ?? []).map((material) => (
                              <option key={material.id} value={material.id}>
                                {materialLabel(material)} · λ {material.lambda.toLocaleString("fr-FR")}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      {layer.type === "element" && (
                        <>
                          <div className="th-inline">
                            <select value={family} onChange={(event) => update(layer.key, { family: event.target.value, tableId: "", cell: "", variant: "" })}>
                              <option value="">Famille…</option>
                              {(elements?.familles ?? []).map((item) => (
                                <option key={item.id} value={item.id}>
                                  {item.libelle}
                                </option>
                              ))}
                            </select>
                            <select
                              value={layer.tableId}
                              disabled={!family}
                              onChange={(event) => update(layer.key, { tableId: event.target.value, cell: "", variant: "" })}
                              style={{ maxWidth: "20rem" }}
                            >
                              <option value="">Tableau…</option>
                              {tables
                                .filter((item) => item.famille === family)
                                .map((item) => (
                                  <option key={item.id} value={item.id}>
                                    {elementTableLabel(item)}
                                  </option>
                                ))}
                            </select>
                            <select
                              value={layer.cell}
                              disabled={!table}
                              onChange={(event) => update(layer.key, { cell: event.target.value, variant: "" })}
                              style={{ maxWidth: "24rem" }}
                            >
                              <option value="">Élément…</option>
                              {table &&
                                cellOptions(table).map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                            </select>
                            {variants.length > 0 && (
                              <select value={layer.variant} onChange={(event) => update(layer.key, { variant: event.target.value })} aria-label="Variante">
                                <option value="">Valeur du tableau</option>
                                {variants.map(([key, label]) => (
                                  <option key={key} value={key}>
                                    {label}
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>
                          {signals.map((message) => (
                            <p key={message} className="th-alert th-alert--error" style={{ margin: "0.25rem 0 0" }}>
                              {message}
                            </p>
                          ))}
                        </>
                      )}
                      {layer.type === "lambda" && (
                        <div className="th-inline">
                          <input placeholder="Nom (ex. PSE graphité)" value={layer.label} onChange={(event) => update(layer.key, { label: event.target.value })} />
                          <label className="th-inline">
                            λ
                            <input className="th-input-xs" inputMode="decimal" value={layer.lambda} onChange={(event) => update(layer.key, { lambda: event.target.value })} />
                          </label>
                        </div>
                      )}
                      {layer.type === "resistance" && (
                        <div className="th-inline">
                          <input placeholder="Nom (ex. bloc béton 20 cm)" value={layer.label} onChange={(event) => update(layer.key, { label: event.target.value })} />
                          <label className="th-inline">
                            R
                            <input className="th-input-xs" inputMode="decimal" value={layer.r} onChange={(event) => update(layer.key, { r: event.target.value })} />
                          </label>
                        </div>
                      )}
                    </td>
                    <td>
                      {(layer.type === "materiau" || layer.type === "lambda") && (
                        <label className="th-inline">
                          <input className="th-input-xs" inputMode="decimal" value={layer.thicknessCm} onChange={(event) => update(layer.key, { thicknessCm: event.target.value })} />
                          cm
                        </label>
                      )}
                      {layer.type === "lame_air" && (
                        <label className="th-inline">
                          <input className="th-input-xs" inputMode="decimal" value={layer.thicknessMm} onChange={(event) => update(layer.key, { thicknessMm: event.target.value })} />
                          mm
                        </label>
                      )}
                    </td>
                    <td>
                      {(layer.type === "materiau" || layer.type === "lambda") && (
                        <input type="checkbox" checked={layer.insulation} onChange={(event) => update(layer.key, { insulation: event.target.checked })} aria-label="Couche isolante" />
                      )}
                    </td>
                    <td className="th-inline">
                      <button type="button" className="th-link" disabled={index === 0} onClick={() => move(index, -1)} aria-label="Monter">
                        ↑
                      </button>
                      <button type="button" className="th-link" disabled={index === draft.layers.length - 1} onClick={() => move(index, 1)} aria-label="Descendre">
                        ↓
                      </button>
                      <button type="button" className="th-link th-link--danger" onClick={() => setLayers(draft.layers.filter((item) => item.key !== layer.key))}>
                        Retirer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="th-inline" style={{ flexWrap: "wrap" }}>
        <span className="th-muted">Ou ajouter :</span>
        {BUTTON_KINDS.map((kind) => (
          <button key={kind} type="button" className="po2-button po2-button--ghost" onClick={() => setLayers([...draft.layers, newLayer(kind)])}>
            + {KIND_LABELS[kind]}
          </button>
        ))}
      </div>

      {sizable.length > 0 && (
        <div className="th-inline-form th-solver">
          <label className="th-field">
            <span>Épaisseur d'isolant pour un U cible : couche</span>
            <select value={insulationIndex ?? ""} onChange={(event) => setInsulationIndex(event.target.value === "" ? null : Number(event.target.value))}>
              <option value="">Choisir…</option>
              {sizable.map(({ layer, index }) => (
                <option key={layer.key} value={index}>
                  Couche {index + 1} : {layer.type === "materiau" ? (materialOf(layer)?.libelle ?? "?") : layer.label || "λ saisie"}
                </option>
              ))}
            </select>
          </label>
          <label className="th-field">
            <span>U cible, W/(m²·K)</span>
            <input className="th-input-xs" inputMode="decimal" value={target} onChange={(event) => setTarget(event.target.value)} />
          </label>
          <button type="button" className="po2-button po2-button--ghost" onClick={() => void solve()}>
            Calculer l'épaisseur
          </button>
          {thickness && insulationIndex !== null && (
            <span className="th-inline">
              <strong>{(thickness.epaisseur_arrondie_m * 100).toLocaleString("fr-FR")} cm</strong>
              <span className="th-muted">(Up {thickness.up_obtenu_arrondi.toLocaleString("fr-FR")})</span>
              <button
                type="button"
                className="po2-button po2-button--secondary"
                onClick={() => {
                  update(draft.layers[insulationIndex].key, { thicknessCm: decimalText(thickness.epaisseur_arrondie_m, 100), insulation: true });
                  setThickness(null);
                }}
              >
                Appliquer
              </button>
            </span>
          )}
        </div>
      )}
      {error && <p className="th-alert th-alert--error">{error}</p>}
    </div>
  );
}
