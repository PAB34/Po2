import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { useAuth } from "../providers/AuthProvider";

export function AccountPage() {
  const { changePassword, isLoading, updateProfile, user } = useAuth();
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [telephone, setTelephone] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setNom(user.nom);
      setPrenom(user.prenom);
      setTelephone(user.telephone ?? "");
    }
  }, [user]);

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileMessage(null);
    setProfileError(null);

    try {
      await updateProfile({ nom, prenom, telephone });
      setProfileMessage("Profil mis à jour.");
    } catch (submissionError) {
      setProfileError(submissionError instanceof Error ? submissionError.message : "Mise à jour impossible.");
    }
  }

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordMessage(null);
    setPasswordError(null);

    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setPasswordMessage("Mot de passe mis à jour.");
    } catch (submissionError) {
      setPasswordError(submissionError instanceof Error ? submissionError.message : "Changement impossible.");
    }
  }

  if (isLoading) {
    return (
      <section className="panel">
        <h2>Compte utilisateur</h2>
        <p>Chargement de la session...</p>
      </section>
    );
  }

  if (!user) {
    return (
      <section className="panel">
        <h2>Compte utilisateur</h2>
        <p>Connecte-toi pour accéder à ton profil.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg">
      <div>
        <h2>Compte utilisateur</h2>
        <p>{user.email}</p>
      </div>

      <form className="form" onSubmit={handleProfileSubmit}>
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
        {profileError && <p className="error-text">{profileError}</p>}
        {profileMessage && <p className="success-text">{profileMessage}</p>}
        <div className="form-actions">
          <button type="submit">Enregistrer le profil</button>
        </div>
      </form>

      <form className="form" onSubmit={handlePasswordSubmit}>
        <label className="field">
          <span>Mot de passe actuel</span>
          <input
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            required
            minLength={8}
          />
        </label>
        <label className="field">
          <span>Nouveau mot de passe</span>
          <input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            required
            minLength={8}
          />
        </label>
        {passwordError && <p className="error-text">{passwordError}</p>}
        {passwordMessage && <p className="success-text">{passwordMessage}</p>}
        <div className="form-actions">
          <button type="submit">Changer le mot de passe</button>
        </div>
      </form>
    </section>
  );
}
