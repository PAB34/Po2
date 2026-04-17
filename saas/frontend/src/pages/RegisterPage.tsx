import { useState, useEffect } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { fetchCities, type City } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

export function RegisterPage() {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [telephone, setTelephone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [cityId, setCityId] = useState("");
  const [cities, setCities] = useState<City[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function loadCities() {
      try {
        const response = await fetchCities();
        setCities(response);
      } catch {
        setCities([]);
      }
    }

    void loadCities();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    setIsSubmitting(true);

    try {
      await register({
        email,
        password,
        nom,
        prenom,
        telephone,
        city_id: cityId ? Number(cityId) : undefined,
      });
      await login({ email, password });
      navigate("/account");
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Inscription impossible.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel">
      <h2>Inscription</h2>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label className="field">
            <span>Prénom</span>
            <input type="text" value={prenom} onChange={(event) => setPrenom(event.target.value)} required />
          </label>
          <label className="field">
            <span>Nom</span>
            <input type="text" value={nom} onChange={(event) => setNom(event.target.value)} required />
          </label>
        </div>
        <label className="field">
          <span>Téléphone</span>
          <input type="tel" value={telephone} onChange={(event) => setTelephone(event.target.value)} />
        </label>
        <label className="field">
          <span>Ville</span>
          <select value={cityId} onChange={(event) => setCityId(event.target.value)}>
            <option value="">Sélectionner une ville</option>
            {cities.map((city) => (
              <option key={city.id} value={city.id}>
                {city.nom_commune}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Email</span>
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <div className="form-grid">
          <label className="field">
            <span>Mot de passe</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
            />
          </label>
          <label className="field">
            <span>Confirmer le mot de passe</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              minLength={8}
            />
          </label>
        </div>
        {error && <p className="error-text">{error}</p>}
        <div className="form-actions">
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Création..." : "Créer mon compte"}
          </button>
        </div>
      </form>
    </section>
  );
}
