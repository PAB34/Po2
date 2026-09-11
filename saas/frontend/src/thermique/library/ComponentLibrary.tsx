// Bibliothèque de composants par catégorie (murs, planchers, menuiseries, ponts thermiques), en
// cartes repliables. Même écran pour la bibliothèque d'un projet et pour « Mes modèles ».
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../providers/AuthProvider";
import {
  componentsApi,
  type ComponentCategory,
  type ComponentPayload,
  type ComponentResult,
  type ComponentStatus,
  type LibraryComponent,
} from "../components";
import { normalizeSearch, type WallRequest } from "../library";
import { useElements } from "../pages/ElementsPanel";
import { useMaterials } from "../pages/MaterialsPanel";
import { KIND_LABELS, WallDraftEditor, compositionFromDraft, draftFromComposition, type LayerKind, type WallDraft } from "./WallEditor";

export type LibraryScope = { kind: "projet"; projectId: number } | { kind: "modeles" };

const MODELS_KEY = ["thermique", "composants", "modeles"];
const decimal2 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });
const decimal3 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

const number = (value: number | null | undefined) => (value === null || value === undefined ? "—" : value.toLocaleString("fr-FR"));
// Accepte 0 et les valeurs négatives (ψ d'un angle sortant, Sw nul) ; vide → null.
const signedDecimal = (value: string) => {
  const cleaned = value.replace(/\s/g, "").replace(",", ".");
  const parsed = cleaned === "" ? Number.NaN : Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
};
const text = (value: unknown) => (typeof value === "number" ? String(value).replace(".", ",") : "");

function resultLabel(result: ComponentResult | null): string {
  if (!result || result.valeur === null) {
    return "à compléter";
  }
  return `${result.grandeur} ${decimal2.format(result.valeur)}`;
}

function thicknessLabel(result: ComponentResult | null): string | null {
  if (!result?.epaisseur_m) {
    return null;
  }
  return `${result.epaisseur_complete ? "" : "≥ "}${decimal2.format(result.epaisseur_m * 100)} cm`;
}

function ComponentDetail({ component, category }: { component: LibraryComponent; category: ComponentCategory }) {
  const result = component.resultat;
  const detail = result?.detail;
  return (
    <div>
      {category.nature === "paroi" && detail && (
        <>
          <p className="th-muted">{detail.libelle_type}</p>
          <div className="th-table-wrap" style={{ padding: 0 }}>
            <table className="th-table">
              <thead>
                <tr>
                  <th>Couche (intérieur → extérieur)</th>
                  <th>e</th>
                  <th>λ</th>
                  <th>R m²·K/W</th>
                </tr>
              </thead>
              <tbody>
                <tr className="th-muted">
                  <td>Résistance superficielle intérieure Rsi</td>
                  <td />
                  <td />
                  <td>{decimal3.format(detail.rsi)}</td>
                </tr>
                {detail.couches.map((layer) => (
                  <tr key={layer.index} className={layer.ignoree ? "th-muted" : undefined}>
                    <td>
                      {layer.libelle || KIND_LABELS[layer.type as LayerKind]}
                      {layer.ignoree && " (ignorée : au-delà d'une lame fortement ventilée)"}
                      {layer.source && (
                        <small className="th-muted">
                          {" "}
                          · {layer.type === "materiau" ? "§" : ""}
                          {layer.source}
                        </small>
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
                <tr className="th-muted">
                  <td>Résistance superficielle extérieure Rse</td>
                  <td />
                  <td />
                  <td>{decimal3.format(detail.rse)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>
            RT = {decimal3.format(detail.rt)} m²·K/W · Uc = {decimal3.format(detail.uc)} · ΔU1 = {decimal3.format(detail.delta_u1)} · ΔU2 ={" "}
            {decimal3.format(detail.delta_u2)} · <strong>Up = {decimal3.format(detail.up)} W/(m²·K)</strong>
          </p>
          {detail.remarques.map((note) => (
            <p key={note} className="th-muted">
              {note}
            </p>
          ))}
        </>
      )}
      {category.nature === "paroi" && !detail && <p className="th-muted">Aucune couche : « Modifier » pour composer la paroi.</p>}
      {category.nature === "menuiserie" && (
        <p>
          Uw {number(result?.valeur)} W/(m²·K) · Sw {number(result?.sw)} · TLw {number(result?.tlw)}
        </p>
      )}
      {category.nature === "pont" && <p>ψ {number(result?.valeur)} W/(m·K)</p>}
      {component.notes && <p className="th-comp__notes">{component.notes}</p>}
      {component.referentiel && (
        <p className="th-muted" style={{ fontSize: "0.78rem" }}>
          Calculé avec le référentiel Th-Bât : matériaux {component.referentiel.materiaux}, éléments tabulés {component.referentiel.elements}.
        </p>
      )}
    </div>
  );
}

type EditorProps = {
  component: LibraryComponent;
  category: ComponentCategory;
  statuses: Record<ComponentStatus, string>;
  onCancel: () => void;
  onSave: (payload: ComponentPayload) => Promise<void>;
};

function ComponentEditor({ component, category, statuses, onCancel, onSave }: EditorProps) {
  const { token } = useAuth();
  const { data: materials } = useMaterials();
  const { data: elements } = useElements();
  const composition = component.composition;
  const [code, setCode] = useState(component.code);
  const [name, setName] = useState(component.nom);
  const [status, setStatus] = useState<ComponentStatus>(component.statut);
  const [notes, setNotes] = useState(component.notes ?? "");
  const [draft, setDraft] = useState<WallDraft>(() =>
    draftFromComposition(composition as Partial<WallRequest>, category.paroi ?? "mur", category.donne_sur ?? "exterieur"),
  );
  const [values, setValues] = useState(() => ({
    uw: text(composition.uw),
    sw: text(composition.sw),
    tlw: text(composition.tlw),
    psi: text(composition.psi),
  }));
  const [preview, setPreview] = useState<ComponentResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const buildComposition = (): Record<string, unknown> => {
    if (category.nature === "paroi") {
      return compositionFromDraft(draft) as unknown as Record<string, unknown>;
    }
    if (category.nature === "menuiserie") {
      return { uw: signedDecimal(values.uw), sw: signedDecimal(values.sw), tlw: signedDecimal(values.tlw) };
    }
    return { psi: signedDecimal(values.psi) };
  };

  async function act(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Action impossible.");
    } finally {
      setBusy(false);
    }
  }

  const valueField = (key: keyof typeof values, label: string) => (
    <label className="th-field">
      <span>{label}</span>
      <input className="th-input-xs" inputMode="decimal" value={values[key]} onChange={(event) => setValues({ ...values, [key]: event.target.value })} />
    </label>
  );

  return (
    <div className="th-form">
      <div className="th-inline-form">
        <label className="th-field">
          <span>Code</span>
          <input className="th-input-sm" value={code} maxLength={20} onChange={(event) => setCode(event.target.value)} />
        </label>
        <label className="th-field th-field--grow">
          <span>Nom</span>
          <input value={name} maxLength={200} placeholder={`Ex. ${category.sous_categories[0]}`} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="th-field">
          <span>Statut</span>
          <select value={status} onChange={(event) => setStatus(event.target.value as ComponentStatus)}>
            {Object.entries(statuses).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {category.nature === "paroi" && <WallDraftEditor draft={draft} onChange={setDraft} materials={materials} elements={elements} />}
      {category.nature === "menuiserie" && (
        <>
          <div className="th-inline-form">
            {valueField("uw", "Uw, W/(m²·K)")}
            {valueField("sw", "Sw (0 à 1)")}
            {valueField("tlw", "TLw (0 à 1)")}
          </div>
          <p className="th-muted">Valeurs saisies. La composition détaillée (menuiserie, vitrage, fermeture, valeurs Th-Bât) arrive au lot suivant.</p>
        </>
      )}
      {category.nature === "pont" && (
        <>
          <div className="th-inline-form">{valueField("psi", "ψ, W/(m·K)")}</div>
          <p className="th-muted">Valeur saisie. Les ψ tabulés des fascicules Th-Bât arrivent avec le lot ponts thermiques.</p>
        </>
      )}

      <label className="th-field">
        <span>Notes (hypothèses, référence CCTP, fabricant…)</span>
        <textarea rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} />
      </label>
      <div className="th-inline" style={{ flexWrap: "wrap" }}>
        <button
          type="button"
          className="po2-button po2-button--primary"
          disabled={busy}
          onClick={() =>
            void act(() => onSave({ code: code.trim(), nom: name.trim(), statut: status, notes: notes.trim() || null, composition: buildComposition() }))
          }
        >
          Enregistrer
        </button>
        <button
          type="button"
          className="po2-button po2-button--ghost"
          disabled={busy}
          onClick={() => void act(async () => setPreview(await componentsApi.evaluate(token!, component.categorie, buildComposition())))}
        >
          Calculer sans enregistrer
        </button>
        <button type="button" className="th-link" onClick={onCancel}>
          Annuler
        </button>
        {preview && (
          <strong>
            {resultLabel(preview)} {preview.valeur !== null && preview.unite}
            {preview.resume && <span className="th-muted"> · {preview.resume}</span>}
          </strong>
        )}
      </div>
      {error && <p className="th-alert th-alert--error">{error}</p>}
    </div>
  );
}

type CardProps = {
  component: LibraryComponent;
  category: ComponentCategory;
  statuses: Record<ComponentStatus, string>;
  isOpen: boolean;
  isEditing: boolean;
  busy: boolean;
  canSaveAsModel: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onCancel: () => void;
  onSave: (payload: ComponentPayload) => Promise<void>;
  onDuplicate: () => void;
  onSaveAsModel: () => void;
  onDelete: () => void;
};

function ComponentCard(props: CardProps) {
  const { component, category, statuses, isOpen, isEditing, busy } = props;
  const thickness = thicknessLabel(component.resultat);
  return (
    <article className={isOpen ? "th-comp is-open" : "th-comp"}>
      <button type="button" className="th-comp__row" onClick={props.onToggle} aria-expanded={isOpen}>
        <span className="th-comp__chevron" aria-hidden>
          {isOpen ? "▾" : "▸"}
        </span>
        <strong className="th-comp__code">{component.code}</strong>
        <span className="th-comp__name">{component.nom}</span>
        <span className="th-comp__summary">{component.resultat?.resume}</span>
        {thickness && <span className="th-comp__thickness">{thickness}</span>}
        <span className={component.resultat?.valeur == null ? "th-comp__value is-empty" : "th-comp__value"}>{resultLabel(component.resultat)}</span>
        <span className={`th-badge th-badge--${component.statut}`}>{statuses[component.statut]}</span>
      </button>
      {isOpen && (
        <div className="th-comp__body">
          {isEditing ? (
            <ComponentEditor component={component} category={category} statuses={statuses} onCancel={props.onCancel} onSave={props.onSave} />
          ) : (
            <>
              <ComponentDetail component={component} category={category} />
              <div className="th-inline th-comp__actions">
                <button type="button" className="po2-button po2-button--primary" onClick={props.onEdit}>
                  Modifier
                </button>
                <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={props.onDuplicate}>
                  Dupliquer
                </button>
                {props.canSaveAsModel && (
                  <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={props.onSaveAsModel}>
                    Enregistrer comme modèle
                  </button>
                )}
                <button type="button" className="th-link th-link--danger" disabled={busy} onClick={props.onDelete}>
                  Supprimer
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </article>
  );
}

export function ComponentLibrary({ scope }: { scope: LibraryScope }) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const listKey = scope.kind === "projet" ? ["thermique", "composants", "projet", scope.projectId] : MODELS_KEY;
  const categoriesQuery = useQuery({
    queryKey: ["thermique", "composants", "categories"],
    queryFn: () => componentsApi.categories(token!),
    enabled: Boolean(token),
    staleTime: Infinity,
  });
  const listQuery = useQuery({
    queryKey: listKey,
    queryFn: () => (scope.kind === "projet" ? componentsApi.listProject(token!, scope.projectId) : componentsApi.listModels(token!)),
    enabled: Boolean(token),
  });
  const modelsQuery = useQuery({
    queryKey: MODELS_KEY,
    queryFn: () => componentsApi.listModels(token!),
    enabled: Boolean(token) && scope.kind === "projet",
  });
  const [filter, setFilter] = useState("tout");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<Set<number>>(() => new Set());
  const [editing, setEditing] = useState<number | null>(null);
  const [picker, setPicker] = useState<string | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  if (categoriesQuery.isLoading || listQuery.isLoading) {
    return <p className="th-muted">Chargement de la bibliothèque…</p>;
  }
  if (!categoriesQuery.data || !listQuery.data) {
    return <p className="th-alert th-alert--error">{(categoriesQuery.error ?? listQuery.error)?.message ?? "Bibliothèque indisponible."}</p>;
  }

  const { categories, statuts } = categoriesQuery.data;
  const components = listQuery.data;
  const query = normalizeSearch(search.trim());
  const visible = components.filter(
    (component) => !query || normalizeSearch(`${component.code} ${component.nom} ${component.resultat?.resume ?? ""} ${component.notes ?? ""}`).includes(query),
  );
  const shown = categories.filter((category) => filter === "tout" || category.id === filter);
  const refresh = () => queryClient.invalidateQueries({ queryKey: listKey });

  const toggle = (id: number) => {
    const next = new Set(open);
    if (next.has(id)) {
      next.delete(id);
      if (editing === id) {
        setEditing(null);
      }
    } else {
      next.add(id);
    }
    setOpen(next);
  };
  const openAndEdit = (id: number) => {
    setOpen((current) => new Set(current).add(id));
    setEditing(id);
  };

  async function run(action: () => Promise<string | void>) {
    setBusy(true);
    setMessage(null);
    try {
      const done = await action();
      if (done) {
        setMessage({ ok: true, text: done });
      }
    } catch (failure) {
      setMessage({ ok: false, text: failure instanceof Error ? failure.message : "Action impossible." });
    } finally {
      setBusy(false);
    }
  }

  const create = (category: ComponentCategory) =>
    run(async () => {
      const created =
        scope.kind === "projet"
          ? await componentsApi.createInProject(token!, scope.projectId, { categorie: category.id })
          : await componentsApi.createModel(token!, { categorie: category.id });
      await refresh();
      openAndEdit(created.id);
    });
  const importModel = (model: LibraryComponent) =>
    run(async () => {
      if (scope.kind !== "projet") {
        return;
      }
      const created = await componentsApi.importModel(token!, scope.projectId, model.id);
      await refresh();
      setPicker(null);
      setOpen((current) => new Set(current).add(created.id));
      return `Modèle importé dans le projet : ${created.code} · ${created.nom}.`;
    });
  const duplicate = (component: LibraryComponent) =>
    run(async () => {
      const created = await componentsApi.duplicate(token!, component.id);
      await refresh();
      openAndEdit(created.id);
      return `Copie créée : ${created.code}.`;
    });
  const saveAsModel = (component: LibraryComponent) =>
    run(async () => {
      const created = await componentsApi.saveAsModel(token!, component.id);
      await queryClient.invalidateQueries({ queryKey: MODELS_KEY });
      return `« ${component.nom} » est enregistré dans Mes modèles (${created.code}).`;
    });
  const remove = (component: LibraryComponent) => {
    if (!window.confirm(`Supprimer ${component.code} « ${component.nom} » ?`)) {
      return;
    }
    void run(async () => {
      await componentsApi.remove(token!, component.id);
      await refresh();
    });
  };
  const save = async (component: LibraryComponent, payload: ComponentPayload) => {
    const updated = await componentsApi.update(token!, component.id, payload);
    queryClient.setQueryData<LibraryComponent[]>(listKey, (current) => current?.map((item) => (item.id === updated.id ? updated : item)));
    setEditing(null);
  };

  return (
    <div className="th-lib">
      <nav className="th-lib__nav" aria-label="Catégories">
        <button type="button" className={filter === "tout" ? "is-active" : undefined} onClick={() => setFilter("tout")}>
          Toutes les catégories <span className="th-count">{components.length}</span>
        </button>
        {categories.map((category) => (
          <button key={category.id} type="button" className={filter === category.id ? "is-active" : undefined} onClick={() => setFilter(category.id)}>
            {category.libelle} <span className="th-count">{components.filter((component) => component.categorie === category.id).length}</span>
          </button>
        ))}
      </nav>

      <div className="th-lib__main">
        <div className="th-lib__toolbar">
          <input value={search} placeholder="Rechercher un composant (code, nom, couche…)" onChange={(event) => setSearch(event.target.value)} />
          <button type="button" className="po2-button po2-button--ghost" onClick={() => setOpen(new Set(visible.map((component) => component.id)))}>
            Tout déplier
          </button>
          <button
            type="button"
            className="po2-button po2-button--ghost"
            onClick={() => {
              setOpen(new Set());
              setEditing(null);
            }}
          >
            Tout replier
          </button>
        </div>
        {message && <p className={message.ok ? "th-alert th-alert--ok" : "th-alert th-alert--error"}>{message.text}</p>}

        {shown.map((category) => {
          const items = visible.filter((component) => component.categorie === category.id);
          const models = (modelsQuery.data ?? []).filter((model) => model.categorie === category.id);
          return (
            <section key={category.id} className="th-lib__section">
              <header className="th-lib__section-head">
                <h2>
                  {category.libelle} <span className="th-count">{items.length}</span>
                </h2>
                <div className="th-actions">
                  {scope.kind === "projet" && (
                    <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => setPicker(picker === category.id ? null : category.id)}>
                      Depuis mes modèles ({models.length})
                    </button>
                  )}
                  <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => void create(category)}>
                    + {category.nouveau}
                  </button>
                </div>
              </header>
              {picker === category.id && (
                <div className="th-lib__picker">
                  {models.length === 0 ? (
                    <p className="th-muted">
                      Aucun modèle dans cette catégorie. Sur la carte d'un composant, « Enregistrer comme modèle » l'ajoute à Mes modèles.
                    </p>
                  ) : (
                    models.map((model) => (
                      <button key={model.id} type="button" className="th-lib__pick" disabled={busy} onClick={() => void importModel(model)}>
                        <strong>{model.code}</strong> {model.nom} <span className="th-muted">{model.resultat?.resume}</span> <span>{resultLabel(model.resultat)}</span>
                      </button>
                    ))
                  )}
                </div>
              )}
              {items.length === 0 ? (
                <p className="th-muted th-lib__empty">Aucun composant dans cette catégorie pour l'instant.</p>
              ) : (
                items.map((component) => (
                  <ComponentCard
                    key={component.id}
                    component={component}
                    category={category}
                    statuses={statuts}
                    isOpen={open.has(component.id)}
                    isEditing={editing === component.id}
                    busy={busy}
                    canSaveAsModel={scope.kind === "projet"}
                    onToggle={() => toggle(component.id)}
                    onEdit={() => setEditing(component.id)}
                    onCancel={() => setEditing(null)}
                    onSave={(payload) => save(component, payload)}
                    onDuplicate={() => void duplicate(component)}
                    onSaveAsModel={() => void saveAsModel(component)}
                    onDelete={() => remove(component)}
                  />
                ))
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
