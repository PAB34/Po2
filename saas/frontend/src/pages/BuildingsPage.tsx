import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { createBuildingRequest, fetchBuildings, fetchCities, type Building, type CreateBuildingPayload } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

function buildAddressLine(building: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">) {
  if (building.adresse_reconstituee) {
    return building.adresse_reconstituee;
  }

  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${building.nom_commune}` : building.nom_commune;
}

export function BuildingsPage() {
  const queryClient = useQueryClient();
  const { token, user } = useAuth();
  const [nomBatiment, setNomBatiment] = useState("");
  const [cityId, setCityId] = useState(user?.city_id ? String(user.city_id) : "");
  const [numeroVoirie, setNumeroVoirie] = useState("");
  const [natureVoie, setNatureVoie] = useState("");
  const [nomVoie, setNomVoie] = useState("");
  const [prefixe, setPrefixe] = useState("");
  const [section, setSection] = useState("");
  const [numeroPlan, setNumeroPlan] = useState("");
  const [adresseReconstituee, setAdresseReconstituee] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const buildingsQuery = useQuery({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token as string),
    enabled: Boolean(token),
  });

  const citiesQuery = useQuery({
    queryKey: ["cities", "buildings"],
    queryFn: fetchCities,
    enabled: Boolean(token) && !user?.city_id,
  });

  const createBuildingMutation = useMutation({
    mutationFn: (payload: CreateBuildingPayload) => createBuildingRequest(token as string, payload),
    onSuccess: async () => {
      setSuccess("Bâtiment créé avec succès.");
      setError(null);
      setNomBatiment("");
      setNumeroVoirie("");
      setNatureVoie("");
      setNomVoie("");
      setPrefixe("");
      setSection("");
      setNumeroPlan("");
      setAdresseReconstituee("");
      if (!user?.city_id) {
        setCityId("");
      }
      await queryClient.invalidateQueries({ queryKey: ["buildings"] });
    },
    onError: (mutationError: unknown) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "Création du bâtiment impossible.");
    },
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token) {
      setError("Authentification requise.");
      return;
    }

    if (!user?.city_id && !cityId) {
      setError("Veuillez sélectionner une ville.");
      return;
    }

    setError(null);
    setSuccess(null);

    await createBuildingMutation.mutateAsync({
      city_id: user?.city_id ?? Number(cityId),
      nom_batiment: nomBatiment || undefined,
      numero_voirie: numeroVoirie || undefined,
      nature_voie: natureVoie || undefined,
      nom_voie: nomVoie || undefined,
      prefixe: prefixe || undefined,
      section: section || undefined,
      numero_plan: numeroPlan || undefined,
      adresse_reconstituee: adresseReconstituee || undefined,
    });
  }

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Bâtiments</h2>
          <p>Connecte-toi pour consulter et créer des bâtiments.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <h2>Bâtiments</h2>
          <p>Crée un bâtiment, puis enrichis-le ensuite avec ses locaux.</p>
        </div>
        <div className="header-badge">
          <strong>{buildingsQuery.data?.length ?? 0}</strong>
          <span>bâtiment(s)</span>
        </div>
      </div>

      <form className="form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="field">
            <span>Nom du bâtiment</span>
            <input type="text" value={nomBatiment} onChange={(event) => setNomBatiment(event.target.value)} />
          </label>
          {!user?.city_id && (
            <label className="field">
              <span>Ville</span>
              <select value={cityId} onChange={(event) => setCityId(event.target.value)} required>
                <option value="">Sélectionner une ville</option>
                {citiesQuery.data?.map((city) => (
                  <option key={city.id} value={city.id}>
                    {city.nom_commune}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Numéro de voirie</span>
            <input type="text" value={numeroVoirie} onChange={(event) => setNumeroVoirie(event.target.value)} />
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
            <span>Adresse reconstituée</span>
            <input type="text" value={adresseReconstituee} onChange={(event) => setAdresseReconstituee(event.target.value)} />
          </label>
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Préfixe</span>
            <input type="text" value={prefixe} onChange={(event) => setPrefixe(event.target.value)} />
          </label>
          <label className="field">
            <span>Section</span>
            <input type="text" value={section} onChange={(event) => setSection(event.target.value)} />
          </label>
        </div>
        <label className="field">
          <span>Numéro de plan</span>
          <input type="text" value={numeroPlan} onChange={(event) => setNumeroPlan(event.target.value)} />
        </label>
        {citiesQuery.isLoading && !user?.city_id && <p>Chargement des villes...</p>}
        {error && <p className="error-text">{error}</p>}
        {success && <p className="success-text">{success}</p>}
        <div className="form-actions">
          <button type="submit" disabled={createBuildingMutation.isPending}>
            {createBuildingMutation.isPending ? "Création..." : "Créer le bâtiment"}
          </button>
        </div>
      </form>

      <div className="section-block">
        <div className="section-heading">
          <h3>Liste des bâtiments</h3>
          <p>Les bâtiments sont filtrés selon la ville de ton compte quand elle est renseignée.</p>
        </div>
        {buildingsQuery.isLoading && <p>Chargement des bâtiments...</p>}
        {buildingsQuery.error instanceof Error && <p className="error-text">{buildingsQuery.error.message}</p>}
        {!buildingsQuery.isLoading && !buildingsQuery.error && (buildingsQuery.data?.length ?? 0) === 0 && (
          <div className="empty-state">
            <strong>Aucun bâtiment pour le moment.</strong>
            <span>Crée ton premier bâtiment avec le formulaire ci-dessus.</span>
          </div>
        )}
        <div className="resource-list">
          {buildingsQuery.data?.map((building) => (
            <article key={building.id} className="resource-card">
              <div className="resource-card-header">
                <div>
                  <h3>{building.nom_batiment || `Bâtiment #${building.id}`}</h3>
                  <p>{buildAddressLine(building)}</p>
                </div>
                <span className="resource-badge">{building.statut_geocodage}</span>
              </div>
              <dl className="resource-metadata">
                <div>
                  <dt>Commune</dt>
                  <dd>{building.nom_commune}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{building.source_creation}</dd>
                </div>
                <div>
                  <dt>Référence cadastrale</dt>
                  <dd>{[building.prefixe, building.section, building.numero_plan].filter(Boolean).join(" ") || "Non renseignée"}</dd>
                </div>
              </dl>
              <div className="resource-card-actions">
                <Link className="secondary-link" to={`/buildings/${building.id}`}>
                  Ouvrir la fiche
                </Link>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
