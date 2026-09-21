/* Vigie Foncier Sète — carte + filtres (tout se passe dans le navigateur). */
"use strict";

const ORDRE_ZONES = ["UD", "UC", "UV", "3UB", "1UB", "2UB", "UA", "UE", "UP", "AU0", "AUE0", "A", "N"];
const COULEURS_CLASSE = { A: "#1a7f37", B: "#7fb800", C: "#e0a800", D: "#c9c4b8", "-": "#9aa0a6" };
const LIBELLES_CLASSE = { A: "A ≥ 80", B: "B 65-79", C: "C 50-64", D: "D < 50", "-": "non notée" };
const CLE_REGLAGES = "vigie.reglages.v1";
const CLE_ETAT = "vigie.etat.v2";
const LIMITE_LISTE = 300;

const FILTRE_VIDE = {
  secteurs: null,            // null = tous ; sinon liste de codes
  surfMin: null, surfMax: null, libreMin: null, batiMin: null, batiMax: null,
  nu: "tous",
  resMin: null, utilMax: null, scoreMin: null,
  classes: ["A", "B", "C", "D", "-"],
  nc: true,
  priorites: null, habitations: null,
  ref: "",
};

let R;              // matrice de règles (regles.json)
let P = [];         // propriétés des parcelles
let GEO;            // FeatureCollection des parcelles
let carte;
let filtre = structuredClone(FILTRE_VIDE);
let selection = [];
let prereglageActif = null;

const $ = (s) => document.querySelector(s);
const nf = new Intl.NumberFormat("fr-FR");
const m2 = (v) => (v === null || v === undefined ? "—" : `${nf.format(v)} m²`);

function stocker(cle, valeur) { try { localStorage.setItem(cle, JSON.stringify(valeur)); } catch (_) {} }
function relire(cle) { try { return JSON.parse(localStorage.getItem(cle)); } catch (_) { return null; } }

/* ---------- Réglages prédéfinis ---------- */
function secteursDe(...familles) {
  return Object.entries(R.secteurs).filter(([, s]) => familles.includes(s.famille)).map(([c]) => c);
}
function prereglages() {
  return {
    division: {
      libelle: "Division pavillonnaire",
      filtre: { ...FILTRE_VIDE, secteurs: secteursDe("division"), nu: "exclure", surfMin: 350, surfMax: 3000, libreMin: 180, batiMin: 40, batiMax: 300, resMin: 60, nc: false },
    },
    densification: {
      libelle: "Densification promoteur",
      filtre: { ...FILTRE_VIDE, secteurs: secteursDe("densification"), surfMin: 300, resMin: 60, nc: true },
    },
    nus: {
      libelle: "Terrains nus",
      filtre: { ...FILTRE_VIDE, secteurs: secteursDe("division", "densification", "protege"), nu: "seulement", surfMin: 200 },
    },
    grosses: {
      libelle: "Grandes réserves ≥ 150 m²",
      filtre: { ...FILTRE_VIDE, secteurs: secteursDe("division", "densification"), nu: "exclure", resMin: 150, nc: false },
    },
    tout: { libelle: "Tout afficher", filtre: { ...FILTRE_VIDE } },
  };
}

/* ---------- Chargement ---------- */
async function charger() {
  const [regles, parcelles, meta] = await Promise.all([
    fetch("data/regles.json").then((r) => r.json()),
    fetch("data/parcelles.geojson").then((r) => r.json()),
    fetch("data/meta.json").then((r) => r.json()),
  ]);
  R = regles;
  GEO = parcelles;
  GEO.features.forEach((f, i) => { f.id = i; f.properties.i = i; });
  P = GEO.features.map((f) => f.properties);
  P.forEach((p) => { p.lib = `${p.sec} ${p.num}`; });
  construireFiltres();
  construireAide(meta);
  const etat = relire(CLE_ETAT);
  if (etat && etat.filtre) { filtre = { ...structuredClone(FILTRE_VIDE), ...etat.filtre }; prereglageActif = etat.prereglage || null; }
  else appliquerPrereglage("division", false);
  synchroniserControles();
  initCarte();
}

/* ---------- Construction du panneau ---------- */
function construireFiltres() {
  const pre = prereglages();
  $("#prereglages").innerHTML = Object.entries(pre)
    .map(([k, v]) => `<button class="puce" data-pre="${k}">${v.libelle}</button>`).join("");
  $("#prereglages").onclick = (e) => { const b = e.target.closest("[data-pre]"); if (b) appliquerPrereglage(b.dataset.pre); };

  // Raccourcis par famille
  $("#raccourcis-familles").innerHTML = Object.entries(R.familles).map(([k, f]) =>
    `<button class="puce" data-fam="${k}" title="Sélectionner / retirer les secteurs de cette famille"><span class="pastille" style="background:${f.couleur}"></span>${f.libelle}</button>`
  ).join("");
  $("#raccourcis-familles").onclick = (e) => {
    const b = e.target.closest("[data-fam]"); if (!b) return;
    const codes = secteursDe(b.dataset.fam);
    const actifs = new Set(filtre.secteurs ?? Object.keys(R.secteurs));
    const tousActifs = codes.every((c) => actifs.has(c));
    if (filtre.secteurs === null) { actifs.clear(); }
    codes.forEach((c) => (tousActifs && filtre.secteurs !== null ? actifs.delete(c) : actifs.add(c)));
    filtre.secteurs = [...actifs];
    modifie();
  };

  // Arbre zone → secteurs, avec le nombre de parcelles (secteur principal)
  const compte = {};
  P.forEach((p) => { compte[p.z] = (compte[p.z] || 0) + 1; });
  const parZone = {};
  Object.entries(R.secteurs).forEach(([code, s]) => { (parZone[s.zone] ||= []).push(code); });
  const zones = ORDRE_ZONES.filter((z) => parZone[z]).concat(Object.keys(parZone).filter((z) => !ORDRE_ZONES.includes(z)));
  $("#arbre-zones").innerHTML = zones.map((z) => {
    const codes = parZone[z].sort((a, b) => a.localeCompare(b, "fr", { numeric: true }));
    const total = codes.reduce((t, c) => t + (compte[c] || 0), 0);
    return `<div class="zone" data-zone="${z}">
      <div class="tete"><span class="chevron">▸</span><input type="checkbox" data-zone-case="${z}"><b>${z}</b><span class="n">${nf.format(total)}</span></div>
      <div class="secteurs">${codes.map((c) => {
        const s = R.secteurs[c];
        const couleur = (R.familles[s.famille] || {}).couleur || "#999";
        const titre = `${R.familles[s.famille]?.libelle || ""} — emprise ${s.emprise.taux != null ? Math.round(s.emprise.taux * 100) + " %" : "non chiffrée"}`;
        return `<label title="${titre}"><input type="checkbox" data-secteur="${c}"><span class="pastille" style="background:${couleur}"></span>${c} <span class="n">${compte[c] || 0}</span></label>`;
      }).join("")}</div></div>`;
  }).join("");
  $("#arbre-zones").onclick = (e) => {
    if (e.target.matches("input")) return;
    const tete = e.target.closest(".tete");
    if (tete) { const z = tete.parentElement; z.classList.toggle("ouverte"); z.querySelector(".chevron").textContent = z.classList.contains("ouverte") ? "▾" : "▸"; }
  };
  $("#arbre-zones").onchange = (e) => {
    const actifs = new Set(filtre.secteurs ?? Object.keys(R.secteurs));
    if (e.target.dataset.secteur) {
      e.target.checked ? actifs.add(e.target.dataset.secteur) : actifs.delete(e.target.dataset.secteur);
    } else if (e.target.dataset.zoneCase) {
      parZone[e.target.dataset.zoneCase].forEach((c) => (e.target.checked ? actifs.add(c) : actifs.delete(c)));
    }
    filtre.secteurs = actifs.size === Object.keys(R.secteurs).length ? null : [...actifs];
    modifie();
  };

  // Lecture Excel : valeurs présentes
  const valeurs = (cle) => [...new Set(Object.values(R.secteurs).map((s) => s[cle]).filter(Boolean))];
  const ordreP = ["Priorité 1", "Priorité 2", "Priorité 3", "À valider", "Hors cible"];
  $("#f-priorite").insertAdjacentHTML("beforeend", valeurs("priorite_zone").sort((a, b) => ordreP.indexOf(a) - ordreP.indexOf(b))
    .map((v) => `<label><input type="checkbox" value="${v}">${v}</label>`).join(""));
  $("#f-habitation").insertAdjacentHTML("beforeend", ["Oui", "Conditionnelle", "Non"].filter((v) => valeurs("habitation").includes(v))
    .map((v) => `<label><input type="checkbox" value="${v}">${v}</label>`).join(""));

  // Champs numériques
  const nums = { "#f-surf-min": "surfMin", "#f-surf-max": "surfMax", "#f-libre-min": "libreMin", "#f-bati-min": "batiMin", "#f-bati-max": "batiMax",
    "#f-res-min": "resMin", "#f-util-max": "utilMax", "#f-score-min": "scoreMin" };
  Object.entries(nums).forEach(([sel, cle]) => {
    $(sel).addEventListener("input", (e) => { filtre[cle] = e.target.value === "" ? null : Number(e.target.value); modifie(false); });
  });
  document.querySelectorAll("input[name=nu]").forEach((r) => r.addEventListener("change", (e) => { filtre.nu = e.target.value; modifie(); }));
  $("#f-classes").addEventListener("change", () => { filtre.classes = cochees("#f-classes"); modifie(); });
  $("#f-nc").addEventListener("change", (e) => { filtre.nc = e.target.checked; modifie(); });
  $("#f-priorite").addEventListener("change", () => { const v = cochees("#f-priorite"); filtre.priorites = v.length ? v : null; modifie(); });
  $("#f-habitation").addEventListener("change", () => { const v = cochees("#f-habitation"); filtre.habitations = v.length ? v : null; modifie(); });
  $("#f-ref").addEventListener("input", (e) => { filtre.ref = e.target.value; modifie(false); });
  $("#reinit").onclick = () => appliquerPrereglage("tout");
  $("#export").onclick = exporterCsv;
  $("#tri").onchange = rendreListe;

  // Mes réglages (navigateur)
  majMesReglages();
  $("#sauver-reglage").onclick = () => {
    const nom = prompt("Nom du réglage :"); if (!nom) return;
    const tous = relire(CLE_REGLAGES) || {}; tous[nom] = structuredClone(filtre); stocker(CLE_REGLAGES, tous); majMesReglages(nom);
  };
  $("#mes-reglages").onchange = (e) => {
    const tous = relire(CLE_REGLAGES) || {}; if (!tous[e.target.value]) return;
    filtre = { ...structuredClone(FILTRE_VIDE), ...structuredClone(tous[e.target.value]) }; prereglageActif = null; modifie();
  };
  $("#suppr-reglage").onclick = () => {
    const nom = $("#mes-reglages").value; if (!nom) return;
    const tous = relire(CLE_REGLAGES) || {}; delete tous[nom]; stocker(CLE_REGLAGES, tous); majMesReglages();
  };

  document.querySelectorAll(".onglets button").forEach((b) => b.onclick = () => {
    document.querySelectorAll(".onglets button, .onglet").forEach((x) => x.classList.remove("actif"));
    b.classList.add("actif"); $(`#onglet-${b.dataset.onglet}`).classList.add("actif");
  });
}

function majMesReglages(choisi = "") {
  const tous = relire(CLE_REGLAGES) || {};
  $("#mes-reglages").innerHTML = `<option value="">Mes réglages…</option>` +
    Object.keys(tous).map((n) => `<option ${n === choisi ? "selected" : ""}>${n}</option>`).join("");
}
function cochees(sel) { return [...document.querySelectorAll(`${sel} input:checked`)].map((i) => i.value); }

function appliquerPrereglage(cle, rafraichir = true) {
  filtre = structuredClone(prereglages()[cle].filtre);
  prereglageActif = cle;
  if (rafraichir) modifie();
}

/* Recopie l'état du filtre dans les contrôles. */
function synchroniserControles() {
  const actifs = new Set(filtre.secteurs ?? Object.keys(R.secteurs));
  document.querySelectorAll("[data-secteur]").forEach((c) => { c.checked = actifs.has(c.dataset.secteur); });
  document.querySelectorAll("[data-zone-case]").forEach((c) => {
    const codes = [...c.closest(".zone").querySelectorAll("[data-secteur]")].map((x) => x.dataset.secteur);
    const n = codes.filter((x) => actifs.has(x)).length;
    c.checked = n === codes.length; c.indeterminate = n > 0 && n < codes.length;
  });
  document.querySelectorAll("[data-fam]").forEach((b) => {
    const codes = secteursDe(b.dataset.fam);
    b.classList.toggle("actif", filtre.secteurs !== null && codes.length > 0 && codes.every((c) => actifs.has(c)));
  });
  document.querySelectorAll("[data-pre]").forEach((b) => b.classList.toggle("actif", b.dataset.pre === prereglageActif));
  $("#resume-zonage").textContent = filtre.secteurs === null ? "tous les secteurs" : `${filtre.secteurs.length} secteur(s)`;
  const vals = { "#f-surf-min": filtre.surfMin, "#f-surf-max": filtre.surfMax, "#f-libre-min": filtre.libreMin, "#f-bati-min": filtre.batiMin, "#f-bati-max": filtre.batiMax,
    "#f-res-min": filtre.resMin, "#f-util-max": filtre.utilMax, "#f-score-min": filtre.scoreMin };
  Object.entries(vals).forEach(([s, v]) => { if (document.activeElement !== $(s)) $(s).value = v ?? ""; });
  document.querySelectorAll("input[name=nu]").forEach((r) => { r.checked = r.value === filtre.nu; });
  document.querySelectorAll("#f-classes input").forEach((c) => { c.checked = filtre.classes.includes(c.value); });
  $("#f-nc").checked = filtre.nc;
  document.querySelectorAll("#f-priorite input").forEach((c) => { c.checked = (filtre.priorites || []).includes(c.value); });
  document.querySelectorAll("#f-habitation input").forEach((c) => { c.checked = (filtre.habitations || []).includes(c.value); });
  if (document.activeElement !== $("#f-ref")) $("#f-ref").value = filtre.ref;
}

/* ---------- Filtrage ---------- */
function normRef(t) { return t.toUpperCase().replace(/[^A-Z0-9]/g, ""); }

function passe(p, f, secteurs) {
  if (secteurs && !secteurs.has(p.z)) return false;
  if (f.surfMin != null && p.surf < f.surfMin) return false;
  if (f.surfMax != null && p.surf > f.surfMax) return false;
  if (f.libreMin != null && p.libre < f.libreMin) return false;
  if (f.batiMin != null && p.bati < f.batiMin) return false;
  if (f.batiMax != null && p.bati > f.batiMax) return false;
  if (f.nu === "exclure" && p.nu) return false;
  if (f.nu === "seulement" && !p.nu) return false;
  if (p.res === null) { if (!f.nc) return false; }
  else {
    if (f.resMin != null && p.res < f.resMin) return false;
    if (f.utilMax != null && p.util != null && p.util * 100 > f.utilMax) return false;
  }
  if (f.scoreMin != null && (p.score == null || p.score < f.scoreMin)) return false;
  if (!f.classes.includes(p.cl)) return false;
  const s = R.secteurs[p.z];
  if (f.priorites && !f.priorites.includes(s.priorite_zone)) return false;
  if (f.habitations && !f.habitations.includes(s.habitation)) return false;
  if (f.ref) {
    const q = normRef(f.ref);
    const lib = p.sec + String(p.num);
    if (!(normRef(p.id).includes(q) || lib.includes(q) || (p.sec + String(p.num).padStart(4, "0")).includes(q))) return false;
  }
  return true;
}

let minuterie;
function modifie(resynchro = true) {
  if (resynchro) synchroniserControles();
  else { prereglageActif = null; document.querySelectorAll("[data-pre]").forEach((b) => b.classList.remove("actif")); }
  clearTimeout(minuterie);
  minuterie = setTimeout(appliquer, 120);
}

function appliquer() {
  const secteurs = filtre.secteurs ? new Set(filtre.secteurs) : null;
  selection = P.filter((p) => passe(p, filtre, secteurs));
  if (carte && carte.getLayer("parcelles-fond")) {
    const ids = selection.map((p) => p.i);
    const expr = ["in", ["get", "i"], ["literal", ids]];
    carte.setFilter("parcelles-fond", expr);
    carte.setFilter("parcelles-trait", expr);
  }
  $("#compteur").textContent = nf.format(selection.length);
  $("#compteur-liste").textContent = nf.format(selection.length);
  stocker(CLE_ETAT, { filtre, prereglage: prereglageActif });
  rendreListe();
}

/* ---------- Liste ---------- */
function couleurClasse(cl) { return COULEURS_CLASSE[cl] || "#999"; }
function rendreListe() {
  const cle = $("#tri").value;
  const tri = [...selection].sort((a, b) => (b[cle] ?? -1e9) - (a[cle] ?? -1e9) || (b.res ?? -1e9) - (a.res ?? -1e9));
  $("#liste").innerHTML = tri.slice(0, LIMITE_LISTE).map((p) => `
    <li data-i="${p.i}">
      <span class="badge" style="background:${couleurClasse(p.cl)}">${p.score ?? "—"}</span>
      <span><span class="ref">${p.lib}</span> · ${p.z}${Object.keys(p.zs).length > 1 ? "+" : ""}
        <div class="det">${m2(p.surf)} · bâti ${m2(p.bati)} · réserve ${m2(p.res)}${p.nu ? " · terrain nu" : ""}</div></span>
    </li>`).join("");
  $("#note-liste").textContent = selection.length > LIMITE_LISTE
    ? `${LIMITE_LISTE} premières sur ${nf.format(selection.length)} — affinez les filtres ou exportez en CSV.` : "";
}
$("#liste").addEventListener("click", (e) => {
  const li = e.target.closest("li[data-i]"); if (li) ouvrirFiche(Number(li.dataset.i), true);
});

/* ---------- Carte ---------- */
function tuilesIGN(couche, format, style = "normal") {
  return `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${couche}&STYLE=${style}&TILEMATRIXSET=PM&FORMAT=${format}&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}`;
}

function expressionCouleur() {
  const mode = $("#couleur").value;
  if (mode === "famille") {
    return ["match", ["get", "fam"], ...Object.entries(R.familles).flatMap(([k, f]) => [k, f.couleur]), "#999"];
  }
  if (mode === "res") {
    return ["case", ["==", ["get", "res"], null], "#9aa0a6",
      ["interpolate", ["linear"], ["get", "res"], 0, "#f1e8d6", 60, "#f0c05a", 150, "#e07b39", 300, "#b3261e", 800, "#6d0f0a"]];
  }
  return ["match", ["get", "cl"], ...Object.entries(COULEURS_CLASSE).flat(), "#999"];
}

function rendreLegende() {
  const mode = $("#couleur").value;
  let items;
  if (mode === "famille") items = Object.values(R.familles).map((f) => [f.couleur, f.libelle]);
  else if (mode === "res") items = [["#f1e8d6", "0"], ["#f0c05a", "60 m²"], ["#e07b39", "150 m²"], ["#b3261e", "300 m²"], ["#6d0f0a", "800 m² +"], ["#9aa0a6", "non calculable"]];
  else items = Object.entries(COULEURS_CLASSE).map(([k, c]) => [c, LIBELLES_CLASSE[k]]);
  $("#legende").innerHTML = items.map(([c, l]) => `<span><span class="pastille" style="background:${c}"></span>${l}</span>`).join("");
}

function initCarte() {
  carte = new maplibregl.Map({
    container: "carte",
    style: {
      version: 8,
      glyphs: "https://data.geopf.fr/annexes/ressources/vectorTiles/fonts/{fontstack}/{range}.pbf",
      sources: {
        plan: { type: "raster", tiles: [tuilesIGN("GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", "image/png")], tileSize: 256, maxzoom: 19, attribution: "© IGN" },
        ortho: { type: "raster", tiles: [tuilesIGN("ORTHOIMAGERY.ORTHOPHOTOS", "image/jpeg")], tileSize: 256, maxzoom: 20, attribution: "© IGN" },
      },
      layers: [
        { id: "plan", type: "raster", source: "plan" },
        { id: "ortho", type: "raster", source: "ortho", layout: { visibility: "none" } },
      ],
    },
    center: [3.675, 43.395],
    zoom: 13,
    maxZoom: 20,
  });
  carte.addControl(new maplibregl.NavigationControl(), "top-right");
  carte.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");

  carte.on("load", async () => {
    carte.addSource("parcelles", { type: "geojson", data: GEO, promoteId: "i" });
    carte.addLayer({ id: "parcelles-fond", type: "fill", source: "parcelles",
      paint: { "fill-color": expressionCouleur(), "fill-opacity": ["case", ["boolean", ["feature-state", "choisie"], false], 0.85, 0.55] } });
    carte.addLayer({ id: "parcelles-trait", type: "line", source: "parcelles",
      paint: { "line-color": ["case", ["boolean", ["feature-state", "choisie"], false], "#0b3d91", "#3a3a3a"],
        "line-width": ["interpolate", ["linear"], ["zoom"],
          13, ["case", ["boolean", ["feature-state", "choisie"], false], 3, 0.2],
          17, ["case", ["boolean", ["feature-state", "choisie"], false], 3, 0.9]] } });
    appliquer();
    rendreLegende();

    // Couches d'appoint chargées ensuite (ne bloquent pas l'affichage)
    const [bati, zonage] = await Promise.all([
      fetch("data/batiments.geojson").then((r) => r.json()),
      fetch("data/zonage.geojson").then((r) => r.json()),
    ]);
    carte.addSource("bati", { type: "geojson", data: bati });
    carte.addLayer({ id: "bati", type: "fill", source: "bati", minzoom: 14,
      paint: { "fill-color": "#3b3b3b", "fill-opacity": 0.55 } }, "parcelles-trait");
    carte.addSource("zonage", { type: "geojson", data: zonage });
    carte.addLayer({ id: "zonage", type: "line", source: "zonage",
      paint: { "line-color": "#7a1fa2", "line-width": ["interpolate", ["linear"], ["zoom"], 12, 0.8, 17, 2], "line-dasharray": [3, 2] } });
    carte.addLayer({ id: "zonage-etiq", type: "symbol", source: "zonage", minzoom: 14,
      layout: { "text-field": ["get", "z"], "text-font": ["Source Sans Pro Bold"], "text-size": 12 },
      paint: { "text-color": "#7a1fa2", "text-halo-color": "#fff", "text-halo-width": 1.5 } });
    majCouches();
  });

  carte.on("click", "parcelles-fond", (e) => ouvrirFiche(e.features[0].properties.i, false));
  carte.on("mouseenter", "parcelles-fond", () => { carte.getCanvas().style.cursor = "pointer"; });
  carte.on("mouseleave", "parcelles-fond", () => { carte.getCanvas().style.cursor = ""; });

  $("#couleur").onchange = () => { carte.setPaintProperty("parcelles-fond", "fill-color", expressionCouleur()); rendreLegende(); };
  $("#fond").onchange = majCouches;
  $("#voir-zonage").onchange = majCouches;
  $("#voir-bati").onchange = majCouches;
}

function majCouches() {
  const vis = (id, oui) => carte.getLayer(id) && carte.setLayoutProperty(id, "visibility", oui ? "visible" : "none");
  vis("plan", $("#fond").value === "plan");
  vis("ortho", $("#fond").value === "ortho");
  vis("zonage", $("#voir-zonage").checked);
  vis("zonage-etiq", $("#voir-zonage").checked);
  vis("bati", $("#voir-bati").checked);
}

/* ---------- Fiche parcelle ---------- */
let choisie = null;
function emprise(bbox, geom) {
  const pts = geom.type === "Polygon" ? geom.coordinates.flat() : geom.coordinates.flat(2);
  pts.forEach(([x, y]) => { bbox[0] = Math.min(bbox[0], x); bbox[1] = Math.min(bbox[1], y); bbox[2] = Math.max(bbox[2], x); bbox[3] = Math.max(bbox[3], y); });
  return bbox;
}

function ouvrirFiche(i, zoomer) {
  const f = GEO.features[i]; const p = f.properties; const s = R.secteurs[p.z];
  if (choisie !== null) carte.setFeatureState({ source: "parcelles", id: choisie }, { choisie: false });
  choisie = i; carte.setFeatureState({ source: "parcelles", id: i }, { choisie: true });
  const bb = emprise([180, 90, -180, -90], f.geometry);
  const [lon, lat] = [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2];
  if (zoomer) carte.fitBounds([[bb[0], bb[1]], [bb[2], bb[3]]], { padding: 120, maxZoom: 19, duration: 600 });

  const fam = R.familles[s.famille];
  const taux = s.emprise.taux != null ? `${Math.round(s.emprise.taux * 100)} %` : "non chiffrée";
  const secteurs = Object.entries(p.zs).map(([c, a]) => `${c} (${nf.format(a)} m²)`).join(", ");
  const alertes = [];
  if (p.fam === "protege") alertes.push("Secteur « v » : espace vert protégé, droits fortement minorés.");
  if (!s.emprise.calculable) alertes.push(`Règle d'emprise non calculable : ${s.emprise.texte}`);
  if (p.partiel) alertes.push("Une partie de la parcelle est dans un secteur à règle non chiffrée : réserve calculée sur le reste.");
  if (Object.keys(p.zs).length > 1) alertes.push(`Parcelle à cheval sur plusieurs secteurs : ${secteurs}. Emprise pondérée par surface.`);
  if (s.emprise.confiance && s.emprise.confiance !== "explicite") alertes.push(`Taux à confirmer (${s.emprise.confiance.replaceAll("_", " ")}).`);
  if (p.cont && Math.abs(p.surf - p.cont) / p.cont > 0.05) alertes.push(`Surface géométrique (${m2(p.surf)}) ≠ contenance cadastrale (${m2(p.cont)}).`);

  $("#fiche").hidden = false;
  $("#fiche").innerHTML = `
    <button class="fermer" title="Fermer">×</button>
    <h3>Parcelle ${p.lib}</h3>
    <div class="det">${p.id}</div>
    <span class="score" style="background:${couleurClasse(p.cl)}">${p.score != null ? `Score ${p.score}/100 · classe ${p.cl}` : "Non notée"}</span>
    ${p.score != null ? `<p class="det">Score provisoire (avant analyse géométrique) — points forts : ${p.motif}.</p>` : ""}
    <table>
      <tr><td>Secteur PLU</td><td>${p.z} <span class="pastille" style="background:${fam?.couleur}"></span></td></tr>
      <tr><td>Famille</td><td>${fam?.libelle ?? "—"}</td></tr>
      <tr><td>Surface parcelle</td><td>${m2(p.surf)}</td></tr>
      <tr><td>Bâti existant (${p.nbat} bât.)</td><td>${m2(p.bati)}${p.leger ? ` <span class="det">dont ${m2(p.leger)} léger</span>` : ""}</td></tr>
      <tr><td>Terrain libre</td><td>${m2(p.libre)}</td></tr>
      <tr><td>Emprise max PLU (${taux})</td><td>${m2(p.emax)}</td></tr>
      <tr><td>Réserve d'emprise</td><td>${m2(p.res)}</td></tr>
      <tr><td>Emprise déjà utilisée</td><td>${p.util != null ? Math.round(p.util * 100) + " %" : "—"}</td></tr>
    </table>
    ${alertes.map((a) => `<div class="alerte">${a}</div>`).join("")}
    <h4>Règlement (${s.zone})</h4>
    <p><b>Emprise :</b> ${s.emprise.texte || taux} <span class="det">(p. ${s.emprise.pages ?? "?"})</span></p>
    ${s.piscine ? `<p class="det">${s.piscine}</p>` : ""}
    ${s.hauteur ? `<p><b>Hauteur :</b> ${s.hauteur}</p>` : ""}
    <h4>Lecture du classement</h4>
    <p><b>${s.priorite_zone ?? "—"}</b> · habitation : ${s.habitation ?? "—"} · score de zone ${s.score_zone ?? "—"}/100</p>
    <p><b>Profil :</b> ${s.profil ?? "—"}</p>
    <p><b>Contraintes :</b> ${s.contraintes ?? "—"}</p>
    ${s.controle ? `<p><b>Contrôle :</b> ${s.controle}</p>` : ""}
    <p class="det">Pages du règlement : ${s.pages ?? "—"}</p>
    <h4>Vérifier</h4>
    <div class="liens">
      <a target="_blank" rel="noopener" href="https://www.geoportail.gouv.fr/carte?c=${lon},${lat}&z=19&l0=ORTHOIMAGERY.ORTHOPHOTOS::GEOPORTAIL:OGC:WMTS(1)&l1=CADASTRALPARCELS.PARCELLAIRE_EXPRESS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes">Géoportail</a>
      <a target="_blank" rel="noopener" href="https://www.geoportail-urbanisme.gouv.fr/map/#tile=1&lon=${lon}&lat=${lat}&zoom=18">Géoportail de l'urbanisme</a>
      <a target="_blank" rel="noopener" href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lon}">Street View</a>
      <a target="_blank" rel="noopener" href="https://explore.data.gouv.fr/fr/immobilier?onglet=carte&filtre=tous&lat=${lat}&lng=${lon}&zoom=18">Ventes DVF</a>
    </div>`;
  $("#fiche .fermer").onclick = fermerFiche;
}
function fermerFiche() {
  $("#fiche").hidden = true;
  if (choisie !== null) carte.setFeatureState({ source: "parcelles", id: choisie }, { choisie: false });
  choisie = null;
}

/* ---------- Export ---------- */
function exporterCsv() {
  const cols = [["id", "identifiant"], ["lib", "parcelle"], ["z", "secteur"], ["fam", "famille"], ["surf", "surface_m2"], ["bati", "bati_m2"],
    ["libre", "terrain_libre_m2"], ["emax", "emprise_max_m2"], ["res", "reserve_emprise_m2"], ["util", "emprise_utilisee"],
    ["nu", "terrain_nu"], ["score", "score"], ["cl", "classe"], ["motif", "motif"]];
  const esc = (v) => (v == null ? "" : /[;"\n]/.test(String(v)) ? `"${String(v).replaceAll('"', '""')}"` : String(v).replace(".", ","));
  const lignes = [cols.map((c) => c[1]).join(";"), ...selection.map((p) => cols.map(([k]) => esc(p[k])).join(";"))];
  const blob = new Blob(["﻿" + lignes.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = `vigie-foncier-sete-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
  URL.revokeObjectURL(a.href);
}

/* ---------- Méthode ---------- */
function construireAide(meta) {
  const nc = Object.entries(R.secteurs).filter(([, s]) => !s.emprise.calculable).map(([c]) => c).join(", ");
  $("#aide").innerHTML = `
    <h3>Ce que calcule l'outil</h3>
    <ul>
      <li><b>Emprise max</b> = surface de la parcelle × taux d'emprise du secteur (article 9 du règlement). Parcelle à cheval : somme pondérée par surface.</li>
      <li><b>Réserve d'emprise</b> = emprise max − bâti cadastral existant (bâti léger compris).</li>
      <li><b>Terrain libre</b> = surface − bâti.</li>
      <li><b>Score provisoire</b> /100 : réserve (40), terrain libre (25), surface (15), emprise peu utilisée (10), priorité de zone de l'Excel (10) ; −30 en secteur « v ». Classes A ≥ 80, B ≥ 65, C ≥ 50.</li>
    </ul>
    <h3>Familles d'opération</h3>
    <ul>${Object.values(R.familles).map((f) => `<li><span class="pastille" style="background:${f.couleur}"></span> ${f.libelle}${f.score ? "" : " — non notée"}</li>`).join("")}</ul>
    <h3>Sources</h3>
    <p>Règlement : ${R.source.document} (XML, fait foi pour les taux) ; lecture qualitative : classement Excel. Cadastre Etalab et zonage du Géoportail de l'urbanisme, données du ${meta.genere_le} (${nf.format(meta.parcelles)} parcelles).</p>
    <h3>Limites</h3>
    <ul>
      <li>Outil de présélection : <b>aucune garantie de constructibilité</b>. Contrôler PLU graphique, PPRI, SPR, servitudes, accès.</li>
      <li>Le PLU raisonne en unité foncière (parcelles contiguës d'un même propriétaire) ; l'outil raisonne à la parcelle.</li>
      <li>Pas encore pris en compte : forme de la parcelle, accès, retraits (étape É4) ; PPRI, SPR, EVP (étape É5).</li>
      <li>Règles non calculables : ${nc}.</li>
    </ul>`;
}

charger().catch((e) => { document.body.insertAdjacentHTML("beforeend", `<p style="position:fixed;top:40%;left:40%;background:#fff;padding:16px">Erreur de chargement : ${e.message}</p>`); });
