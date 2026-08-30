"""desactiver les PRM Sete Agglopole hors perimetre Ville

Revision ID: 0069
Revises: 0068
Create Date: 2026-07-23

Les factures du marche 2024-FCS-03 (groupement de commandes) portent a la fois les
points de livraison de la Ville de Sete et ceux de Sete Agglopole Mediterranee. La
plateforme ne traite que la Ville : ces points doivent sortir de tous les calculs.

Aucun champ des factures ne separe les deux perimetres (meme titulaire de paiement,
meme marche, meme reference client, et 5 regroupements utilises des deux cotes). Le
rattachement repose donc sur une liste nominative, etablie a partir de la nature des
sites (competences intercommunales : assainissement, dechets, lecture publique, gens
du voyage...) et corroboree par le perimetre de consentement ENEDIS, dont les 549 PRM
portent tous le SIRET 21340301700014 (Commune de Sete).

On desactive, on ne supprime pas : les factures restent integralement en base et un
simple passage de `active` a True remet un point dans le perimetre.

Voir docs/refonte-v1/enedis-referentiel-prm-qualite-decisions.md (decision D5).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


# 56 points de livraison Sete Agglopole Mediterranee, releves le 2026-07-23
# (461 473,55 EUR TTC factures sur janvier-juin 2026).
_PRM_AGGLO: tuple[tuple[str, str], ...] = (
    ("30002434075609", "STEP MEZE"),
    ("50047710718488", "CONSERVATOIRE INTERCOMMUNAL"),
    ("30002431730880", "AIRE DES GENS DU VOYAGE MARSEILAN"),
    ("30002434087199", "COMPLEXE OIKOS"),
    ("50056439897755", "THEATRE MOLIERE"),
    ("30002430027319", "PISCINE DI STEFANO"),
    ("50094722258520", "POLE UNIVERSITAIRE MICHELE WEIL"),
    ("50093860610138", "STEP VILLEVEYRAC"),
    ("30002431360760", "MEDIATHEQUE FRANCOIS MITTERAND"),
    ("30002431360547", "MEDIATHEQUE ANDRE MALRAUX"),
    ("30002430890178", "LAGUNAGE VIC LA GARDIOLE"),
    ("30002431622338", "LAGUNAGES ONGLOUS"),
    ("50092764060808", "MEDIATHEQUE INTERCOMMUNALE"),
    ("30002431129242", "STEP MIREVAL"),
    ("30002431618492", "LAGUNAGES PRADELS"),
    ("50076845103701", "AIRE GENS DU VOYAGE FRONTIGNAN"),
    ("30002430481801", "STAND DE TIR"),
    ("30002431532113", "ECOSITE TJ GENERAL"),
    ("50089798460977", "MEDIATHEQUE OLYMPE DE GOUGES"),
    ("50024398628114", "BUREAUX PEPINIERE FLEXYS"),
    ("30002434035999", "STEP MONTBAZIN"),
    ("50030054332888", "PARKING VISITEUR GARE"),
    ("24300578701307", "MUSEE DE L ETANG DE THAU"),
    ("24314905775517", "POLE DECHETS DE MARSEILLAN"),
    ("24364109881940", "BIBLIOTHEQUE MEZE"),
    ("50093421333416", "POLE CYCLE DE LEAU"),
    ("24353545553601", "VILLA GALLO ROMAINE"),
    ("50036539895729", "PEM NORD PARKING"),
    ("50093162999287", "AIRE DES GENS DU VOYAGE MEZE"),
    ("24316931824708", "JARDIN ANTIQUE"),
    ("30002431038901", "PR PLUVIAL FONTREGEIRE"),
    ("30002430016730", "PR PLUVIAL PAIROLET"),
    ("30002431671924", "PR PLUVIAL SESQUIERS"),
    ("24326193770048", "BUREAUX ECOSITE N10"),
    ("50086185443418", "POLE CYCLE DE LEAU"),
    ("24330680082620", "DECHETTERIE FRONTIGNAN"),
    ("24336324150261", "LOGEMENT FONCTION DGS"),
    ("50054793368693", "GARAGE AUTOMOBILE ASSOCIATIF"),
    ("50018605847190", "RACCORDEMENT ABRI CHAUFFEUR"),
    ("24343559996743", "DECHETTERIE SETE"),
    ("24337337003176", "PEM SUD"),
    ("24329232975630", "AMPHI SALLE COURS ARDAM BAT11"),
    ("24338350194790", "ANNEXE MEDIATHEQUE F MITERRAND"),
    ("24351229997798", "OT MEZE AILE OUEST"),
    ("24395658315554", "POMPE GREEN SEA"),
    ("24317366116006", "DECHETTERIE MEZE"),
    ("24300433962951", "ZAE LA PEYRADE PARKING PL"),
    ("24309117128642", "DECHETTERIE BALARUC"),
    ("24317655472589", "DECHETTERIE MARSEILLAN"),
    ("24397250333560", "DECHETTERIE MONTBAZIN"),
    ("24377857990544", "PR PLUVIAL BIR HAKEIM"),
    ("50064914585110", "PLATE FORME DECHETES VERTS"),
    ("24353256046999", "CAPITAINERIE AILE EST"),
    ("50079685290706", "ACCELERATEUR EAUX PLUVIALES"),
    ("24334587405824", "CONTROLE DEBIT"),
    ("24385962226532", "CA DU BASSIN DE THAU"),
)


_NOTE = "Hors perimetre Ville : Sete Agglopole Mediterranee."


def upgrade() -> None:
    conn = op.get_bind()
    for prm, site in _PRM_AGGLO:
        # Cas courant : le point a deja une ligne de matrice, creee depuis les factures.
        res = conn.execute(
            sa.text(
                "UPDATE energy_accounting_site_mappings SET active = false, "
                "notes = COALESCE(NULLIF(notes, ''), :note) "
                "WHERE prm_id = :prm"
            ),
            {"prm": prm, "note": _NOTE},
        )
        if res.rowcount:
            continue
        # Sinon on la cree desactivee, pour que le point soit ecarte des son arrivee.
        # Le city_id est repris des factures qui portent ce PRM : une ligne rattachee a
        # aucune collectivite ne serait pas vue par le filtre de perimetre.
        conn.execute(
            sa.text(
                "INSERT INTO energy_accounting_site_mappings "
                "(city_id, prm_id, site_name, active, notes, created_at, updated_at) "
                "SELECT DISTINCT i.city_id, :prm, :site, false, :note, now(), now() "
                "FROM energy_invoice_sites s "
                "JOIN energy_invoices i ON i.id = s.invoice_id "
                "WHERE s.prm_id = :prm"
            ),
            {"prm": prm, "site": site, "note": _NOTE},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for prm, _site in _PRM_AGGLO:
        conn.execute(
            sa.text("UPDATE energy_accounting_site_mappings SET active = true WHERE prm_id = :prm"),
            {"prm": prm},
        )
