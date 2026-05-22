from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.city import City
from app.models.cpe import CpeFinanceImportBatch, CpeFinanceInvoice, CpeFinanceLine, CpeSite
from app.models.user import User
from app.services.cpe_finance_imports import create_finance_batch_from_bytes, finance_batch_detail


def _csv_text() -> str:
    return """CODE CONTRAT;LIBELLE CONTRAT;TYPE DE MARCHE;NUMERO DE FACTURE;TYPE DE FACTURE;DEBUT PERIODE DE FACTURATION;FIN PERIODE DE FACTURATION;MARCHE;SERVICE VENDU;POSTE FACTURE;MONTANT HT;CONSOMMATION;LIEU OU DETAIL DE LA PRESTATION;INDEX DEBUT DE RELEVE;INDEX FIN DE RELEVE
C00190116O;SETE LOT 1;MTI;FAC-AC;AC;2026-01-01;2026-03-31;P1;ACOMPTE GAZ;P1;120,50;;REFAC VDS-ENS 02 - ECOLE;;
C00190116O;SETE LOT 1;MTI;FAC-DE;DE;2026-01-01;2026-12-31;P1;DECOMPTE GAZ;CTA;80,00;10;REFAC VDS-CULT 99 - SITE ABSENT;1;11
C00190116O;SETE LOT 1;MTI;FAC-P2;EC;2026-01-01;2026-03-31;P2;MAINTENANCE;P2;40,00;;LIGNE SANS CODE;;
C000OTHER;AUTRE;MC;FAC-R2;EC;2026-01-01;2026-01-31;R2;RESEAU;R2;10,00;;AUTRE SITE;;
"""


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    City.__table__.create(engine)
    User.__table__.create(engine)
    CpeSite.__table__.create(engine)
    CpeFinanceImportBatch.__table__.create(engine)
    CpeFinanceInvoice.__table__.create(engine)
    CpeFinanceLine.__table__.create(engine)
    return Session(engine)


def test_create_finance_batch_persists_filtered_lines_and_p1_summary():
    with _session() as db:
        city = City(nom_commune="Sete")
        user = User(email="cpe@example.test", password_hash="hash", nom="Cpe", prenom="Test", city_id=1)
        db.add_all([city, user])
        db.flush()
        db.add(
            CpeSite(
                city_id=city.id,
                code_site="VDS-ENS 02",
                nom_site="Ecole",
                categorie="ENS",
                nb_mwh_pci=1,
                ecs_ref_m3_an=0,
                pce="PCE-1",
            )
        )
        db.commit()

        batch = create_finance_batch_from_bytes(
            db,
            city.id,
            user.id,
            filename="export_finances.csv",
            content_type="text/csv",
            data=_csv_text().encode("utf-8"),
        )
        detail = finance_batch_detail(batch)

        assert batch.source_row_count == 4
        assert batch.imported_line_count == 3
        assert batch.ignored_line_count == 1
        assert batch.invoice_count == 3
        assert batch.matched_site_line_count == 1
        assert batch.unknown_site_line_count == 1
        assert batch.missing_site_code_line_count == 1
        assert detail.p1.nb_lignes == 2
        assert detail.p1.nb_factures == 2
        assert detail.p1.nb_sites_cpe_rapproches == 1
        assert detail.p1.nb_sites_cpe_avec_pce == 1
        assert [item.code for item in detail.p1.types_facture] == ["AC", "DE"]
