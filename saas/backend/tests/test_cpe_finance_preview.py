from app.services.cpe_finance_preview import preview_finance_export


def test_preview_finance_export_summarizes_cpe_markets_and_site_codes():
    csv_text = """CODE CONTRAT;LIBELLÉ CONTRAT;TYPE DE MARCHÉ;NUMÉRO DE FACTURE;TYPE DE FACTURE;DÉBUT PÉRIODE DE FACTURATION;FIN PÉRIODE DE FACTURATION;MARCHÉ;MONTANT HT;CONSOMMATION;LIEU OU DÉTAIL DE LA PRESTATION;INDEX DÉBUT DE RELÈVE;INDEX FIN DE RELÈVE
C00190116O;SETE LOT 1;MTI;FAC-1;EC;2026-01-01;2026-03-31;P1;120,50;;REFAC VDS-ENS 02 - ECOLE;;
C00190116O;SETE LOT 1;MTI;FAC-1;EC;2026-01-01;2026-03-31;P2;80,00;;CCAS 08 - MULTI ACCUEIL;;
C000OTHER;RESEAU;MC;FAC-2;EC;2026-01-01;2026-01-31;R2;40,00;12;AUTRE SITE;1;13
"""

    preview = preview_finance_export(csv_text.encode("utf-8"), filename="finances.csv")

    assert preview.filename == "finances.csv"
    assert preview.nb_lignes == 3
    assert preview.nb_factures == 2
    assert preview.nb_contrats == 2
    assert preview.montant_ht == 240.5
    assert preview.nb_lignes_p1_p2_p3 == 2
    assert preview.nb_lignes_code_site_cpe == 2
    assert preview.nb_sites_cpe_distincts == 2
    assert preview.nb_lignes_consommation == 1
    assert preview.nb_lignes_index_releve == 1
    assert [item.code for item in preview.marches] == ["P1", "P2", "R2"]
    assert preview.sites_cpe_detectes == ["CCAS 08", "VDS-ENS 02"]
    assert preview.contrats[0].code_contrat == "C00190116O"
    assert preview.contrats[0].nb_sites_cpe_distincts == 2
    assert any("hors P1/P2/P3" in warning for warning in preview.alertes)


def test_preview_finance_export_rejects_missing_required_columns():
    csv_text = "CODE CONTRAT;MONTANT HT\nC001;10,00\n"

    try:
        preview_finance_export(csv_text)
    except ValueError as exc:
        assert "NUMERO DE FACTURE" in str(exc)
        assert "MARCHE" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete DALKIA export")
