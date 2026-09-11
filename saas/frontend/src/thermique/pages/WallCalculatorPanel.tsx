import { useMemo, useState } from "react";

import { useAuth } from "../../providers/AuthProvider";
import {
  DELTA_U2_LABELS,
  WALL_TYPE_LABELS,
  elementCellLabel,
  elementSignals,
  elementTableLabel,
  materialLabel,
  wallApi,
  type ElementTable,
  type Material,
  type ThicknessResult,
  type WallFacing,
  type WallLayerRequest,
  type WallRequest,
  type WallResult,
  type WallType,
} from "../library";
import { parseDecimal } from "../scale";
import { useElements } from "./ElementsPanel";
import { useMaterials } from "./MaterialsPanel";

type LayerKind = "materiau" | "element" | "lambda" | "resistance" | "lame_air" | "lame_air_ventilee";

type Layer = {
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

const KIND_LABELS: Record<LayerKind, string> = {
  materiau: "Matériau de la bibliothèque",
  element: "Élément à résistance tabulée (brique, bloc, plancher…)",
  lambda: "Matériau à λ connue (fabricant)",
  resistance: "Élément à résistance connue",
  lame_air: "Lame d'air non ventilée",
  lame_air_ventilee: "Lame d'air fortement ventilée",
};

const decimal3 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const decimal2 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

let nextKey = 1;

function newLayer(type: LayerKind): Layer {
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
  };
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
    case "lambda": {
      const thickness = parseDecimal(layer.thicknessCm);
      const lambda = parseDecimal(layer.lambda);
      if (!thickness || !lambda) {
        throw new Error(`Couche ${index + 1} : saisissez λ et l'épaisseur.`);
      }
      return { type: "lambda", lambda, epaisseur_m: thickness / 100, isolant: layer.insulation, libelle: label };
    }
    case "element": {
      if (!layer.tableId || !layer.cell) {
        throw new Error(`Couche ${index + 1} : choisissez un tableau et une case.`);
      }
      const [row, column] = layer.cell.split(":").map(Number);
      return { type: "element", tableau_id: layer.tableId, ligne: row, colonne: column, variante: layer.variant || undefined };
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

export function WallCalculatorPanel() {
  const { token } = useAuth();
  const { data: library } = useMaterials();
  const { data: elementLibrary } = useElements();
  const elementTables = elementLibrary?.tableaux ?? [];
  const [wallType, setWallType] = useState<WallType>("mur");
  const [facing, setFacing] = useState<WallFacing>("exterieur");
  const [level, setLevel] = useState(1);
  const [deltaU1, setDeltaU1] = useState("0");
  const [layers, setLayers] = useState<Layer[]>([newLayer("materiau")]);
  const [result, setResult] = useState<WallResult | null>(null);
  const [thickness, setThickness] = useState<ThicknessResult | null>(null);
  const [insulationIndex, setInsulationIndex] = useState<number | null>(null);
  const [target, setTarget] = useState("0,20");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const materials = library?.materiaux ?? [];
  const byFamily = useMemo(() => {
    const groups = new Map<string, Material[]>();
    for (const material of materials) {
      const key = material.famille ?? "";
      groups.set(key, [...(groups.get(key) ?? []), material]);
    }
    return groups;
  }, [materials]);

  const update = (key: number, changes: Partial<Layer>) =>
    setLayers((current) => current.map((layer) => (layer.key === key ? { ...layer, ...changes } : layer)));
  const move = (index: number, offset: number) =>
    setLayers((current) => {
      const next = [...current];
      const [layer] = next.splice(index, 1);
      next.splice(index + offset, 0, layer);
      return next;
    });

  const buildRequest = (): WallRequest => ({
    type: wallType,
    donne_sur: facing,
    niveau_delta_u2: level,
    delta_u1: parseDecimal(deltaU1) ?? 0,
    couches: layers.map(toRequest),
  });

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Calcul impossible.");
    } finally {
      setBusy(false);
    }
  }

  const compute = () =>
    run(async () => {
      setThickness(null);
      setResult(await wallApi.compute(token!, buildRequest()));
    });

  const solve = () =>
    run(async () => {
      const goal = parseDecimal(target);
      if (insulationIndex === null || !goal) {
        throw new Error("Choisissez la couche isolante et le U cible.");
      }
      setThickness(await wallApi.thickness(token!, buildRequest(), insulationIndex, goal));
    });

  const sizableLayers = layers
    .map((layer, index) => ({ layer, index }))
    .filter(({ layer }) => layer.type === "materiau" || layer.type === "lambda");

  return (
    <>
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">Bibliothèque de composants</p>
          <h1>Composer une paroi</h1>
          <p className="th-muted">
            Couches de l'intérieur vers l'extérieur. Méthode des règles Th-Bât (parois opaques) : Up = 1 / (Rsi + ΣR + Rse) +
            ΔU1 + ΔU2, arrondi à deux chiffres significatifs.
          </p>
        </div>
      </div>

      <section className="po2-card th-section">
        <div className="po2-card__body th-form">
          <div className="th-inline-form">
            <label className="th-field th-field--grow">
              <span>Type de paroi</span>
              <select value={wallType} onChange={(event) => setWallType(event.target.value as WallType)}>
                {Object.entries(WALL_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="th-field">
              <span>Donne sur</span>
              <select value={facing} onChange={(event) => setFacing(event.target.value as WallFacing)}>
                <option value="exterieur">L'extérieur</option>
                <option value="local_non_chauffe">Un local non chauffé</option>
              </select>
            </label>
            <label className="th-field">
              <span>Correction ΔU2</span>
              <select value={level} onChange={(event) => setLevel(Number(event.target.value))}>
                {Object.entries(DELTA_U2_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="th-field">
              <span>ΔU1 ponts intégrés, W/(m²·K)</span>
              <input className="th-input-xs" inputMode="decimal" value={deltaU1} onChange={(event) => setDeltaU1(event.target.value)} />
            </label>
          </div>

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
                {layers.map((layer, index) => (
                  <tr key={layer.key}>
                    <td>{index + 1}</td>
                    <td>
                      <div className="th-muted" style={{ fontSize: "0.78rem" }}>
                        {KIND_LABELS[layer.type]}
                      </div>
                      {layer.type === "materiau" && (
                        <div className="th-inline">
                          <select value={layer.family} onChange={(event) => update(layer.key, { family: event.target.value, materialId: "" })}>
                            <option value="">Famille…</option>
                            {(library?.familles ?? []).map((item) => (
                              <option key={item.section} value={item.section}>
                                {item.titre}
                              </option>
                            ))}
                          </select>
                          <select
                            value={layer.materialId}
                            disabled={!layer.family}
                            onChange={(event) => update(layer.key, { materialId: event.target.value })}
                            style={{ maxWidth: "26rem" }}
                          >
                            <option value="">Matériau…</option>
                            {(byFamily.get(layer.family) ?? []).map((material) => (
                              <option key={material.id} value={material.id}>
                                {materialLabel(material)} · λ {material.lambda.toLocaleString("fr-FR")}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      {layer.type === "element" && (() => {
                        const table = elementTables.find((item) => item.id === layer.tableId);
                        const [row, column] = layer.cell ? layer.cell.split(":").map(Number) : [-1, -1];
                        const variants = table && row >= 0
                          ? Object.entries(table.variantes).filter(([key]) => (table.lignes[row].variantes[key] ?? [])[column] != null)
                          : [];
                        const signals = table && row >= 0 ? elementSignals(table, row, column) : [];
                        return (
                          <>
                            <div className="th-inline">
                              <select value={layer.family} onChange={(event) => update(layer.key, { family: event.target.value, tableId: "", cell: "", variant: "" })}>
                                <option value="">Famille…</option>
                                {(elementLibrary?.familles ?? []).map((item) => (
                                  <option key={item.id} value={item.id}>
                                    {item.libelle}
                                  </option>
                                ))}
                              </select>
                              <select
                                value={layer.tableId}
                                disabled={!layer.family}
                                onChange={(event) => update(layer.key, { tableId: event.target.value, cell: "", variant: "" })}
                                style={{ maxWidth: "22rem" }}
                              >
                                <option value="">Tableau…</option>
                                {elementTables
                                  .filter((item) => item.famille === layer.family)
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
                                style={{ maxWidth: "26rem" }}
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
                        );
                      })()}
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
                      <button type="button" className="th-link" disabled={index === 0} onClick={() => move(index, -1)}>
                        Monter
                      </button>
                      <button type="button" className="th-link" disabled={index === layers.length - 1} onClick={() => move(index, 1)}>
                        Descendre
                      </button>
                      <button type="button" className="th-link th-link--danger" onClick={() => setLayers((current) => current.filter((item) => item.key !== layer.key))}>
                        Retirer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="th-inline">
            {(Object.keys(KIND_LABELS) as LayerKind[]).map((kind) => (
              <button key={kind} type="button" className="po2-button po2-button--ghost" onClick={() => setLayers((current) => [...current, newLayer(kind)])}>
                + {KIND_LABELS[kind]}
              </button>
            ))}
          </div>
          <div>
            <button type="button" className="po2-button po2-button--primary" disabled={busy || layers.length === 0} onClick={() => void compute()}>
              Calculer Up
            </button>
          </div>
          {error && <p className="th-alert th-alert--error">{error}</p>}
        </div>
      </section>

      {result && (
        <div className="th-columns">
          <section className="po2-card th-section">
            <div className="po2-card__header">
              <div>
                <h2>
                  Up = {decimal2.format(result.up_arrondi)} W/(m²·K)
                </h2>
                <p className="th-muted">{result.libelle_type}</p>
              </div>
            </div>
            <div className="th-table-wrap">
              <table className="th-table">
                <thead>
                  <tr>
                    <th>Couche</th>
                    <th>e</th>
                    <th>λ</th>
                    <th>R m²·K/W</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Résistance superficielle intérieure Rsi</td>
                    <td />
                    <td />
                    <td>{decimal3.format(result.rsi)}</td>
                  </tr>
                  {result.couches.map((layer) => (
                    <tr key={layer.index} className={layer.ignoree ? "th-muted" : undefined}>
                      <td>
                        {layer.libelle || KIND_LABELS[layer.type as LayerKind]}
                        {layer.ignoree && " (ignorée : au-delà d'une lame fortement ventilée)"}
                        {layer.source && (
                          <span className="th-muted">
                            {" "}
                            · {layer.type === "materiau" ? "§" : ""}
                            {layer.source}
                          </span>
                        )}
                      </td>
                      <td>
                        {layer.epaisseur_m !== undefined && `${decimal2.format(layer.epaisseur_m * 100)} cm`}
                        {layer.epaisseur_mm !== undefined && `${decimal2.format(layer.epaisseur_mm)} mm`}
                      </td>
                      <td>{layer.lambda !== undefined && layer.lambda.toLocaleString("fr-FR")}</td>
                      <td>{decimal3.format(layer.r)}</td>
                    </tr>
                  ))}
                  <tr>
                    <td>Résistance superficielle extérieure Rse</td>
                    <td />
                    <td />
                    <td>{decimal3.format(result.rse)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="po2-card__body">
              <p>
                RT = {decimal3.format(result.rt)} m²·K/W · Uc = {decimal3.format(result.uc)} · ΔU1 = {decimal3.format(result.delta_u1)} ·
                ΔU2 = {decimal3.format(result.delta_u2)} · Up = {decimal3.format(result.up)} W/(m²·K)
              </p>
              {result.remarques.map((note) => (
                <p key={note} className="th-muted">
                  {note}
                </p>
              ))}
              <p className="th-muted">{result.source}</p>
            </div>
          </section>

          <section className="po2-card th-section">
            <div className="po2-card__header">
              <div>
                <h2>Épaisseur d'isolant pour un U cible</h2>
                <p className="th-muted">Plus petite épaisseur de la couche choisie donnant Up ≤ U cible, arrondie au centimètre supérieur.</p>
              </div>
            </div>
            <div className="po2-card__body th-form">
              <label className="th-field">
                <span>Couche à dimensionner</span>
                <select value={insulationIndex ?? ""} onChange={(event) => setInsulationIndex(event.target.value === "" ? null : Number(event.target.value))}>
                  <option value="">Choisir…</option>
                  {sizableLayers.map(({ layer, index }) => (
                    <option key={layer.key} value={index}>
                      Couche {index + 1} :{" "}
                      {layer.type === "materiau"
                        ? materialLabel(materials.find((material) => material.id === layer.materialId) ?? ({ libelle: "?", section_titre: "?", rho_texte: "" } as Material))
                        : layer.label || "λ saisie"}
                    </option>
                  ))}
                </select>
              </label>
              <label className="th-field">
                <span>U cible, W/(m²·K)</span>
                <input className="th-input-xs" inputMode="decimal" value={target} onChange={(event) => setTarget(event.target.value)} />
              </label>
              <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => void solve()}>
                Calculer l'épaisseur
              </button>
              {thickness && (
                <div className="th-alert th-alert--ok">
                  Épaisseur minimale : <strong>{decimal2.format(thickness.epaisseur_min_m * 1000)} mm</strong>, soit{" "}
                  <strong>{decimal2.format(thickness.epaisseur_arrondie_m * 100)} cm</strong> au centimètre supérieur, pour un Up de{" "}
                  {decimal2.format(thickness.up_obtenu_arrondi)} W/(m²·K) ({decimal3.format(thickness.up_obtenu)}).
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
