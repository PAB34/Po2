import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createLocalRequest,
  deleteLocalRequest,
  fetchBuilding,
  fetchBuildingLocals,
  type Building,
  type CreateLocalPayload,
  type Local,
  type UpdateBuildingPayload,
  type UpdateLocalPayload,
  updateBuildingRequest,
  updateLocalRequest,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

function buildAddressLine(
  building: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">,
) {
  if (building.adresse_reconstituee) {
    return building.adresse_reconstituee;
  }

  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${building.nom_commune}` : building.nom_commune;
}

function parseJsonArray(value: string | null): string[] {
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value) as unknown;
    return Array.isArray(parsed) ? parsed.map((item) => String(item)) : [];
  } catch {
    return [];
  }
}

function parseCandidateLabels(value: string | null): string[] {
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map((item) => {
        if (item && typeof item === "object") {
          const candidate = item as { name?: unknown; label?: unknown; source?: unknown };
          const label = String(candidate.name ?? candidate.label ?? "").trim();
          const source = String(candidate.source ?? "").trim();
          if (!label) {
            return "";
          }
          return source ? `${label} (${source})` : label;
        }
        return String(item);
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

export function BuildingDetailPage() {
  const { buildingId } = useParams();
  const parsedBuildingId = Number(buildingId);
  const queryClient = useQueryClient();
  const { token } = useAuth();

  const [nomBatiment, setNomBatiment] = useState("");
  const [numeroVoirie, setNumeroVoirie] = useState("");
  const [indiceRepetition, setIndiceRepetition] = useState("");
  const [natureVoie, setNatureVoie] = useState("");
  const [nomVoie, setNomVoie] = useState("");
  const [prefixe, setPrefixe] = useState("");
  const [section, setSection] = useState("");
  const [numeroPlan, setNumeroPlan] = useState("");
  const [adresseReconstituee, setAdresseReconstituee] = useState("");

  const [nomLocal, setNomLocal] = useState("");
  const [typeLocal, setTypeLocal] = useState("BUREAU");
  const [niveau, setNiveau] = useState("");
  const [surfaceM2, setSurfaceM2] = useState("");
  const [usage, setUsage] = useState("");
  const [statutOccupation, setStatutOccupation] = useState("");
  const [commentaire, setCommentaire] = useState("");

  const [editingLocalId, setEditingLocalId] = useState<number | null>(null);
  const [editingLocalForm, setEditingLocalForm] = useState({
    nom_local: "",
    type_local: "BUREAU",
    niveau: "",
    surface_m2: "",
    usage: "",
    statut_occupation: "",
    commentaire: "",
  });

  const [buildingError, setBuildingError] = useState<string | null>(null);
  const [buildingSuccess, setBuildingSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const buildingQuery = useQuery({
    queryKey: ["building", parsedBuildingId, token],
    queryFn: () => fetchBuilding(token as string, parsedBuildingId),
    enabled: Boolean(token) && Number.isInteger(parsedBuildingId),
  });

  const localsQuery = useQuery({
    queryKey: ["building-locals", parsedBuildingId, token],
    queryFn: () => fetchBuildingLocals(token as string, parsedBuildingId),
    enabled: Boolean(token) && Number.isInteger(parsedBuildingId),
  });

  useEffect(() => {
    if (!buildingQuery.data) {
      return;
    }

    setNomBatiment(buildingQuery.data.nom_batiment ?? "");
    setNumeroVoirie(buildingQuery.data.numero_voirie ?? "");
    setIndiceRepetition(buildingQuery.data.indice_repetition ?? "");
    setNatureVoie(buildingQuery.data.nature_voie ?? "");
    setNomVoie(buildingQuery.data.nom_voie ?? "");
    setPrefixe(buildingQuery.data.prefixe ?? "");
    setSection(buildingQuery.data.section ?? "");
    setNumeroPlan(buildingQuery.data.numero_plan ?? "");
    setAdresseReconstituee(buildingQuery.data.adresse_reconstituee ?? "");
  }, [buildingQuery.data]);

  const updateBuildingMutation = useMutation({
    mutationFn: (payload: UpdateBuildingPayload) => updateBuildingRequest(token as string, parsedBuildingId, payload),
    onSuccess: async () => {
      setBuildingSuccess("Bâtiment mis à jour avec succès.");
      setBuildingError(null);
      await queryClient.invalidateQueries({ queryKey: ["building", parsedBuildingId] });
      await queryClient.invalidateQueries({ queryKey: ["buildings"] });
    },
    onError: (mutationError: unknown) => {
      setBuildingSuccess(null);
      setBuildingError(mutationError instanceof Error ? mutationError.message : "Mise à jour du bâtiment impossible.");
    },
  });

  const createLocalMutation = useMutation({
    mutationFn: (payload: CreateLocalPayload) => createLocalRequest(token as string, parsedBuildingId, payload),
    onSuccess: async () => {
      setSuccess("Local créé avec succès.");
      setError(null);
      setEditingLocalId(null);
      setNomLocal("");
      setTypeLocal("BUREAU");
      setNiveau("");
      setSurfaceM2("");
      setUsage("");
      setStatutOccupation("");
      setCommentaire("");
      await queryClient.invalidateQueries({ queryKey: ["building-locals", parsedBuildingId] });
    },
    onError: (mutationError: unknown) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "Création du local impossible.");
    },
  });

  const updateLocalMutation = useMutation({
    mutationFn: ({ localId, payload }: { localId: number; payload: UpdateLocalPayload }) =>
      updateLocalRequest(token as string, parsedBuildingId, localId, payload),
    onSuccess: async () => {
      setSuccess("Local mis à jour avec succès.");
      setError(null);
      setEditingLocalId(null);
      await queryClient.invalidateQueries({ queryKey: ["building-locals", parsedBuildingId] });
    },
    onError: (mutationError: unknown) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "Mise à jour du local impossible.");
    },
  });

  const deleteLocalMutation = useMutation({
    mutationFn: (localId: number) => deleteLocalRequest(token as string, parsedBuildingId, localId),
    onSuccess: async () => {
      setSuccess("Local supprimé avec succès.");
      setError(null);
      setEditingLocalId(null);
      await queryClient.invalidateQueries({ queryKey: ["building-locals", parsedBuildingId] });
    },
    onError: (mutationError: unknown) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "Suppression du local impossible.");
    },
  });

  function startEditingLocal(local: Local) {
    setEditingLocalId(local.id);
    setEditingLocalForm({
      nom_local: local.nom_local,
      type_local: local.type_local,
      niveau: local.niveau ?? "",
      surface_m2: local.surface_m2 != null ? String(local.surface_m2) : "",
      usage: local.usage ?? "",
      statut_occupation: local.statut_occupation ?? "",
      commentaire: local.commentaire ?? "",
    });
    setError(null);
    setSuccess(null);
  }

  async function handleBuildingSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !Number.isInteger(parsedBuildingId)) {
      setBuildingError("Contexte de bâtiment invalide.");
      return;
    }

    setBuildingError(null);
    setBuildingSuccess(null);

    await updateBuildingMutation.mutateAsync({
      nom_batiment: nomBatiment || undefined,
      numero_voirie: numeroVoirie || undefined,
      indice_repetition: indiceRepetition || undefined,
      nature_voie: natureVoie || undefined,
      nom_voie: nomVoie || undefined,
      prefixe: prefixe || undefined,
      section: section || undefined,
      numero_plan: numeroPlan || undefined,
      adresse_reconstituee: adresseReconstituee || undefined,
    });
  }

  async function handleCreateLocalSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !Number.isInteger(parsedBuildingId)) {
      setError("Contexte de bâtiment invalide.");
      return;
    }

    setError(null);
    setSuccess(null);

    await createLocalMutation.mutateAsync({
      nom_local: nomLocal,
      type_local: typeLocal,
      niveau: niveau || undefined,
      surface_m2: surfaceM2 ? Number(surfaceM2) : undefined,
      usage: usage || undefined,
      statut_occupation: statutOccupation || undefined,
      commentaire: commentaire || undefined,
    });
  }

  async function handleLocalUpdateSubmit(event: FormEvent<HTMLFormElement>, localId: number) {
    event.preventDefault();

    if (!token || !Number.isInteger(parsedBuildingId)) {
      setError("Contexte de bâtiment invalide.");
      return;
    }

    setError(null);
    setSuccess(null);

    await updateLocalMutation.mutateAsync({
      localId,
      payload: {
        nom_local: editingLocalForm.nom_local,
        type_local: editingLocalForm.type_local,
        niveau: editingLocalForm.niveau || undefined,
        surface_m2: editingLocalForm.surface_m2 ? Number(editingLocalForm.surface_m2) : undefined,
        usage: editingLocalForm.usage || undefined,
        statut_occupation: editingLocalForm.statut_occupation || undefined,
        commentaire: editingLocalForm.commentaire || undefined,
      },
    });
  }

  async function handleDeleteLocal(localId: number) {
    if (!token || !Number.isInteger(parsedBuildingId)) {
      setError("Contexte de bâtiment invalide.");
      return;
    }

    setError(null);
    setSuccess(null);
    await deleteLocalMutation.mutateAsync(localId);
  }

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Détail du bâtiment</h2>
          <p>Connecte-toi pour consulter cette fiche.</p>
        </div>
      </section>
    );
  }

  if (!Number.isInteger(parsedBuildingId)) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Détail du bâtiment</h2>
          <p>Identifiant de bâtiment invalide.</p>
        </div>
        <div className="form-actions">
          <Link className="secondary-link" to="/buildings/list">
            Retour à la liste
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Bâtiment</p>
          <h2>{buildingQuery.data?.nom_batiment || `Bâtiment #${parsedBuildingId}`}</h2>
          <p>{buildingQuery.data ? buildAddressLine(buildingQuery.data) : "Chargement de l'adresse..."}</p>
        </div>
        <div className="form-actions">
          <Link className="secondary-link" to="/buildings/list">
            Retour à la liste
          </Link>
        </div>
      </div>

      {buildingQuery.isLoading && <p>Chargement de la fiche bâtiment...</p>}
      {buildingQuery.error instanceof Error && <p className="error-text">{buildingQuery.error.message}</p>}

      {buildingQuery.data && (
        <>
          <div className="detail-grid">
            <div className="detail-card">
              <span>Commune</span>
              <strong>{buildingQuery.data.nom_commune}</strong>
            </div>
            <div className="detail-card">
              <span>Statut géocodage</span>
              <strong>{buildingQuery.data.statut_geocodage}</strong>
            </div>
            <div className="detail-card">
              <span>Référence cadastrale</span>
              <strong>
                {[buildingQuery.data.prefixe, buildingQuery.data.section, buildingQuery.data.numero_plan].filter(Boolean).join(" ") ||
                  "Non renseignée"}
              </strong>
            </div>
          </div>

          <div className="section-block">
            <div className="section-heading">
              <h3>Traçabilité DGFIP</h3>
              <p>Résumé des données cadastrales et MAJIC qui ont servi à créer ce bâtiment.</p>
            </div>
            <div className="detail-grid">
              <div className="detail-card">
                <span>Clé DGFIP</span>
                <strong>{buildingQuery.data.dgfip_unique_key || "Non renseignée"}</strong>
              </div>
              <div className="detail-card">
                <span>Fichier source</span>
                <strong>{buildingQuery.data.dgfip_source_file || "Non renseigné"}</strong>
              </div>
              <div className="detail-card">
                <span>Lignes source</span>
                <strong>{parseJsonArray(buildingQuery.data.dgfip_source_rows_json).join(", ") || "Non renseignées"}</strong>
              </div>
            </div>
            <div className="resource-list">
              <article className="resource-card">
                <div className="resource-card-header">
                  <div>
                    <h3>Indices MAJIC détectés</h3>
                    <p>Valeurs présentes dans le fichier source pour aider à qualifier le bâtiment.</p>
                  </div>
                </div>
                <dl className="resource-metadata">
                  <div>
                    <dt>Bâtiment</dt>
                    <dd>{parseJsonArray(buildingQuery.data.majic_building_values_json).join(", ") || "Aucun"}</dd>
                  </div>
                  <div>
                    <dt>Entrée</dt>
                    <dd>{parseJsonArray(buildingQuery.data.majic_entry_values_json).join(", ") || "Aucune"}</dd>
                  </div>
                  <div>
                    <dt>Niveau / Porte</dt>
                    <dd>
                      {[
                        parseJsonArray(buildingQuery.data.majic_level_values_json).join(", "),
                        parseJsonArray(buildingQuery.data.majic_door_values_json).join(", "),
                      ]
                        .filter(Boolean)
                        .join(" • ") || "Aucun détail complémentaire"}
                    </dd>
                  </div>
                </dl>
              </article>
            </div>
          </div>

          <div className="section-block">
            <div className="section-heading">
              <h3>Rapprochement IGN</h3>
              <p>Données IGN conservées lors de la validation du bâtiment.</p>
            </div>
            <div className="detail-grid">
              <div className="detail-card">
                <span>Couche IGN</span>
                <strong>{buildingQuery.data.ign_layer || "Aucune"}</strong>
              </div>
              <div className="detail-card">
                <span>Nom IGN brut</span>
                <strong>{buildingQuery.data.ign_name || "Aucun"}</strong>
              </div>
              <div className="detail-card">
                <span>Nom IGN proposé</span>
                <strong>{buildingQuery.data.ign_name_proposed || "Aucune proposition"}</strong>
              </div>
            </div>
            <div className="resource-list">
              <article className="resource-card">
                <div className="resource-card-header">
                  <div>
                    <h3>Candidats de toponymie retenus</h3>
                    <p>Liste des noms IGN proposés autour de l’objet sélectionné.</p>
                  </div>
                </div>
                <p>{parseCandidateLabels(buildingQuery.data.ign_toponym_candidates_json).join(" | ") || "Aucun candidat enregistré."}</p>
              </article>
            </div>
          </div>

          <div className="section-block">
            <div className="section-heading">
              <h3>Éditer le bâtiment</h3>
              <p>Met à jour les informations d’adresse et d’identification cadastrale.</p>
            </div>
            <form className="form" onSubmit={handleBuildingSubmit}>
              <div className="form-grid">
                <label className="field">
                  <span>Nom du bâtiment</span>
                  <input type="text" value={nomBatiment} onChange={(event) => setNomBatiment(event.target.value)} />
                </label>
                <label className="field">
                  <span>Numéro de voirie</span>
                  <input type="text" value={numeroVoirie} onChange={(event) => setNumeroVoirie(event.target.value)} />
                </label>
              </div>
              <div className="form-grid">
                <label className="field">
                  <span>Indice de répétition</span>
                  <input type="text" value={indiceRepetition} onChange={(event) => setIndiceRepetition(event.target.value)} />
                </label>
                <label className="field">
                  <span>Nature de voie</span>
                  <input type="text" value={natureVoie} onChange={(event) => setNatureVoie(event.target.value)} />
                </label>
              </div>
              <div className="form-grid">
                <label className="field">
                  <span>Nom de voie</span>
                  <input type="text" value={nomVoie} onChange={(event) => setNomVoie(event.target.value)} />
                </label>
                <label className="field">
                  <span>Préfixe</span>
                  <input type="text" value={prefixe} onChange={(event) => setPrefixe(event.target.value)} />
                </label>
              </div>
              <div className="form-grid">
                <label className="field">
                  <span>Section</span>
                  <input type="text" value={section} onChange={(event) => setSection(event.target.value)} />
                </label>
                <label className="field">
                  <span>Numéro de plan</span>
                  <input type="text" value={numeroPlan} onChange={(event) => setNumeroPlan(event.target.value)} />
                </label>
              </div>
              <div className="form-grid">
                <label className="field">
                  <span>Adresse reconstituée</span>
                  <input type="text" value={adresseReconstituee} onChange={(event) => setAdresseReconstituee(event.target.value)} />
                </label>
              </div>
              {buildingError && <p className="error-text">{buildingError}</p>}
              {buildingSuccess && <p className="success-text">{buildingSuccess}</p>}
              <div className="form-actions">
                <button type="submit" disabled={updateBuildingMutation.isPending}>
                  {updateBuildingMutation.isPending ? "Mise à jour..." : "Enregistrer le bâtiment"}
                </button>
              </div>
            </form>
          </div>
        </>
      )}

      <div className="section-block">
        <div className="section-heading">
          <h3>Ajouter un local</h3>
          <p>Le local principal existe déjà à la création du bâtiment. Tu peux ajouter les suivants ici.</p>
        </div>
        <form className="form" onSubmit={handleCreateLocalSubmit}>
          <div className="form-grid">
            <label className="field">
              <span>Nom du local</span>
              <input type="text" value={nomLocal} onChange={(event) => setNomLocal(event.target.value)} required />
            </label>
            <label className="field">
              <span>Type de local</span>
              <select value={typeLocal} onChange={(event) => setTypeLocal(event.target.value)}>
                <option value="BUREAU">Bureau</option>
                <option value="LOGEMENT">Logement</option>
                <option value="COMMERCE">Commerce</option>
                <option value="TECHNIQUE">Technique</option>
                <option value="ANNEXE">Annexe</option>
              </select>
            </label>
          </div>
          <div className="form-grid">
            <label className="field">
              <span>Niveau</span>
              <input type="text" value={niveau} onChange={(event) => setNiveau(event.target.value)} />
            </label>
            <label className="field">
              <span>Surface (m²)</span>
              <input type="number" min="0" step="0.1" value={surfaceM2} onChange={(event) => setSurfaceM2(event.target.value)} />
            </label>
          </div>
          <div className="form-grid">
            <label className="field">
              <span>Usage</span>
              <input type="text" value={usage} onChange={(event) => setUsage(event.target.value)} />
            </label>
            <label className="field">
              <span>Statut d'occupation</span>
              <input type="text" value={statutOccupation} onChange={(event) => setStatutOccupation(event.target.value)} />
            </label>
          </div>
          <label className="field">
            <span>Commentaire</span>
            <input type="text" value={commentaire} onChange={(event) => setCommentaire(event.target.value)} />
          </label>
          {error && <p className="error-text">{error}</p>}
          {success && <p className="success-text">{success}</p>}
          <div className="form-actions">
            <button type="submit" disabled={createLocalMutation.isPending}>
              {createLocalMutation.isPending ? "Création..." : "Ajouter le local"}
            </button>
          </div>
        </form>
      </div>

      <div className="section-block">
        <div className="section-heading">
          <h3>Locaux</h3>
          <p>Vue courante des locaux rattachés à ce bâtiment.</p>
        </div>
        {localsQuery.isLoading && <p>Chargement des locaux...</p>}
        {localsQuery.error instanceof Error && <p className="error-text">{localsQuery.error.message}</p>}
        {!localsQuery.isLoading && !localsQuery.error && (localsQuery.data?.length ?? 0) === 0 && (
          <div className="empty-state">
            <strong>Aucun local trouvé.</strong>
            <span>Ajoute un local pour commencer à décrire ce bâtiment.</span>
          </div>
        )}
        <div className="resource-list">
          {localsQuery.data?.map((local) => (
            <article key={local.id} className="resource-card">
              <div className="resource-card-header">
                <div>
                  <h3>{local.nom_local}</h3>
                  <p>{local.usage || "Usage non renseigné"}</p>
                </div>
                <span className="resource-badge">{local.type_local}</span>
              </div>
              <dl className="resource-metadata">
                <div>
                  <dt>Niveau</dt>
                  <dd>{local.niveau || "Non renseigné"}</dd>
                </div>
                <div>
                  <dt>Surface</dt>
                  <dd>{local.surface_m2 ? `${local.surface_m2} m²` : "Non renseignée"}</dd>
                </div>
                <div>
                  <dt>Occupation</dt>
                  <dd>{local.statut_occupation || "Non renseignée"}</dd>
                </div>
              </dl>
              {local.commentaire && <p>{local.commentaire}</p>}
              <div className="resource-card-actions">
                <button type="button" className="secondary-button" onClick={() => startEditingLocal(local)}>
                  Modifier
                </button>
                <button type="button" className="danger-button" onClick={() => void handleDeleteLocal(local.id)}>
                  Supprimer
                </button>
              </div>

              {editingLocalId === local.id && (
                <form className="form compact-form" onSubmit={(event) => void handleLocalUpdateSubmit(event, local.id)}>
                  <div className="form-grid">
                    <label className="field">
                      <span>Nom du local</span>
                      <input
                        type="text"
                        value={editingLocalForm.nom_local}
                        onChange={(event) => setEditingLocalForm((current) => ({ ...current, nom_local: event.target.value }))}
                        required
                      />
                    </label>
                    <label className="field">
                      <span>Type de local</span>
                      <select
                        value={editingLocalForm.type_local}
                        onChange={(event) => setEditingLocalForm((current) => ({ ...current, type_local: event.target.value }))}
                      >
                        <option value="PRINCIPAL">Principal</option>
                        <option value="BUREAU">Bureau</option>
                        <option value="LOGEMENT">Logement</option>
                        <option value="COMMERCE">Commerce</option>
                        <option value="TECHNIQUE">Technique</option>
                        <option value="ANNEXE">Annexe</option>
                      </select>
                    </label>
                  </div>
                  <div className="form-grid">
                    <label className="field">
                      <span>Niveau</span>
                      <input
                        type="text"
                        value={editingLocalForm.niveau}
                        onChange={(event) => setEditingLocalForm((current) => ({ ...current, niveau: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>Surface (m²)</span>
                      <input
                        type="number"
                        min="0"
                        step="0.1"
                        value={editingLocalForm.surface_m2}
                        onChange={(event) => setEditingLocalForm((current) => ({ ...current, surface_m2: event.target.value }))}
                      />
                    </label>
                  </div>
                  <div className="form-grid">
                    <label className="field">
                      <span>Usage</span>
                      <input
                        type="text"
                        value={editingLocalForm.usage}
                        onChange={(event) => setEditingLocalForm((current) => ({ ...current, usage: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>Statut d'occupation</span>
                      <input
                        type="text"
                        value={editingLocalForm.statut_occupation}
                        onChange={(event) =>
                          setEditingLocalForm((current) => ({ ...current, statut_occupation: event.target.value }))
                        }
                      />
                    </label>
                  </div>
                  <label className="field">
                    <span>Commentaire</span>
                    <input
                      type="text"
                      value={editingLocalForm.commentaire}
                      onChange={(event) => setEditingLocalForm((current) => ({ ...current, commentaire: event.target.value }))}
                    />
                  </label>
                  <div className="form-actions">
                    <button type="submit" disabled={updateLocalMutation.isPending}>
                      {updateLocalMutation.isPending ? "Enregistrement..." : "Enregistrer"}
                    </button>
                    <button type="button" className="secondary-button" onClick={() => setEditingLocalId(null)}>
                      Annuler
                    </button>
                  </div>
                </form>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}