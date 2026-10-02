> Généré le 2026-09-03 par `saas/backend/scripts/sig_agglo_recon.py --sample`.
> **Aucune donnée nominative** : noms de colonnes et comptages uniquement.
> Compte utilisé : privilèges `vitis_user`, `vmap_cadastre_medium_user`, `vmap_user`.

Généré par `scripts/sig_agglo_recon.py` — noms de colonnes et comptages uniquement.

| Couche | Table | Lignes | MAJ | Colonnes |
| --- | --- | ---: | --- | --- |
| Bâtiment en N&B | `agglo_s_cadastre.vmap_fond_cadastral_bati` | 173857 | 2024-09-26 | `id`, `id_com`, `pre`, `section`, `geom`, `dur_lib`, `dur_code`, `tex` |
| Bâtiments en couleur | `agglo_s_cadastre.vmap_fond_cadastral_bati` | 173857 | 2018-10-10 | `id`, `id_com`, `pre`, `section`, `geom`, `dur_lib`, `dur_code`, `tex` |
| Numéro de parcelle (< 1500e) | `agglo_s_cadastre.vmap_fond_cadastral_parcelle_etq_inf_1500e` | 173365 | 2025-02-20 | `id`, `id_com`, `section`, `fon`, `hei`, `tyu`, `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `tpa`, `hta`, `vta`, `texte`, `rotation`, `taille`, `geom`, `pre` |
| Numéro de parcelle (> 1500e) | `agglo_s_cadastre.vmap_fond_cadastral_parcelle_etq_inf_7500e` | 173365 | 2025-02-20 | `gid`, `id_com`, `parcelle`, `section`, `indp_code`, `id_par`, `sup_fiscale`, `geom`, `id_sec`, `commune`, `indp`, `tranches_etiquettes`, `surf_sig_m2` |
| Numéros de parcelle en N&B 1 test paul symbologie | `agglo_s_cadastre.vmap_fond_cadastral_parcelle_etq_inf_7500e` | 173365 |  | `gid`, `id_com`, `parcelle`, `section`, `indp_code`, `id_par`, `sup_fiscale`, `geom`, `id_sec`, `commune`, `indp`, `tranches_etiquettes`, `surf_sig_m2` |
| Parcelle | `agglo_s_cadastre.vmap_fond_cadastral_parcelle` | 173365 | 2025-02-20 | `recherche`, `localisation`, `id_com`, `parcelle`, `section`, `pre`, `coar`, `indp_code`, `id_par`, `lib_sup_fiscale`, `sup_fiscale`, `sup_m2`, `lib_sup_m2`, `jdatat`, `x`, `y`, `feuille`, `geom`, `id_sec`, `commune`, `indp`, `etiquettes_parcelle`, `remonter_tps_multidate`, `remonter_tps_comparer`, `date_rafraichissement_vue` |
| Parcelles (N&B, cartads) | `agglo_cartads.parcelles_cartads` | 173365 | 2024-07-09 | `id_par`, `id_com`, `id_par_ads`, `id_par_cartads`, `supf_cad`, `supf_sig_m2`, `feuille`, `geom` |
| Parcelles en N&B | `agglo_s_cadastre.vmap_fond_cadastral_parcelle` | 173365 | 2024-06-21 | `recherche`, `localisation`, `id_com`, `parcelle`, `section`, `pre`, `coar`, `indp_code`, `id_par`, `lib_sup_fiscale`, `sup_fiscale`, `sup_m2`, `lib_sup_m2`, `jdatat`, `x`, `y`, `feuille`, `geom`, `id_sec`, `commune`, `indp`, `etiquettes_parcelle`, `remonter_tps_multidate`, `remonter_tps_comparer`, `date_rafraichissement_vue` |
| Parcelles en couleur | `agglo_s_cadastre.vmap_fond_cadastral_parcelle` | 173365 | 2024-05-16 | `recherche`, `localisation`, `id_com`, `parcelle`, `section`, `pre`, `coar`, `indp_code`, `id_par`, `lib_sup_fiscale`, `sup_fiscale`, `sup_m2`, `lib_sup_m2`, `jdatat`, `x`, `y`, `feuille`, `geom`, `id_sec`, `commune`, `indp`, `etiquettes_parcelle`, `remonter_tps_multidate`, `remonter_tps_comparer`, `date_rafraichissement_vue` |
| Parcelles étiquettes en N&B | `agglo_s_cadastre.vmap_fond_cadastral_parcelle` | 173365 | 2024-06-03 | `recherche`, `localisation`, `id_com`, `parcelle`, `section`, `pre`, `coar`, `indp_code`, `id_par`, `lib_sup_fiscale`, `sup_fiscale`, `sup_m2`, `lib_sup_m2`, `jdatat`, `x`, `y`, `feuille`, `geom`, `id_sec`, `commune`, `indp`, `etiquettes_parcelle`, `remonter_tps_multidate`, `remonter_tps_comparer`, `date_rafraichissement_vue` |
| Parcelles étiquettes en couleur | `agglo_s_cadastre.vmap_fond_cadastral_parcelle` | 173365 | 2024-06-03 | `recherche`, `localisation`, `id_com`, `parcelle`, `section`, `pre`, `coar`, `indp_code`, `id_par`, `lib_sup_fiscale`, `sup_fiscale`, `sup_m2`, `lib_sup_m2`, `jdatat`, `x`, `y`, `feuille`, `geom`, `id_sec`, `commune`, `indp`, `etiquettes_parcelle`, `remonter_tps_multidate`, `remonter_tps_comparer`, `date_rafraichissement_vue` |
| Bâtiment | `s_cadastre.v_vmap_batiment` | 100722 | 2025-03-07 | `dur_code`, `dur_lib`, `geom`, `id`, `id_com`, `pre`, `section`, `tex` |
| Historique parcelle | `foncier.vmp_cadhist` | 91537 | 2025-02-20 | `an_ajout`, `an_suppr`, `existe_encore`, `geom`, `gid`, `id_par`, `infobulle`, `no_parcelle`, `recherche`, `supf_m2` |
| Unité foncière | `s_cadastre.v_vmap_unite_fonciere` | 63811 | 2025-02-20 | `geom`, `id_com`, `id_dnupro`, `id_uf`, `nb_parcelles`, `superficie` |
| Propriétaire parcelle (nom d'usage) | `agglo_s_cadastre.vmp_uf_proprietaire` | 63809 | 2025-02-20 | `ddenom`, `dlign3`, `dlign4`, `dlign5`, `dlign6`, `dnomlp`, `dnomus`, `dnuper`, `dnupro`, `dprnlp`, `dprnus`, `dqualp`, `etq_proprietaire`, `gdesip`, `geom`, `gid`, `id_com`, `id_dnupro`, `id_uf` |
| Cadastre_div_lineaire | `s_cadastre.v_vmap_objet_lineaire_divers` | 59315 | 2025-02-20 | `geom`, `id`, `id_com`, `pre`, `section`, `sym_code`, `texte` |
| Cadastre_div_points | `s_cadastre.v_vmap_objet_ponctuel_divers` | 53151 | 2025-02-20 | `geom`, `id`, `id_com`, `ori`, `section`, `sym_code`, `texte` |
| Clôture | `s_cadastre.v_vmap_objet_ponctuel_divers` | 53151 | 2025-02-20 | `geom`, `id`, `id_com`, `ori`, `section`, `sym_code`, `texte` |
| Numéro adresse (étiquette) | `s_cadastre.v_vmap_texte_numero_de_voirie` | 37167 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Parcelles susceptibles d'inclure des maisons avec jardin > 50m2 | `dechets.vmp_composteurs_parcelles_maisons_jardins_50m2` | 27859 | 2023-12-15 | `gid`, `id_par`, `nb_maisons`, `surf_parcelle`, `surf_bati_dans_parcelle`, `date_rafraichissement_vue`, `geom` |
| Zone de communication (étiquette) | `s_cadastre.v_vmap_texte_zone_de_communication` | 23590 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Parcelles susceptibles d'inclure des maisons avec jardin > 200m2 | `dechets.vmp_composteurs_parcelles_maisons_jardins_200m2` | 20510 | 2022-01-07 | `gid`, `id_par`, `nb_maisons`, `surf_parcelle`, `surf_bati_dans_parcelle`, `date_rafraichissement_vue`, `geom` |
| Foncier présumé public (DGFP 2025) | `foncier.vmp_foncier_public` | 17040 | 2024-11-25 | `gid`, `id_com`, `id_par`, `id_dnupro`, `nb_proprio`, `ddenom`, `gdesip`, `ccodem`, `l_ccodem`, `ccodro`, `l_ccodro`, `code`, `type`, `assimile_sam`, `surfcad_m2`, `surfsig_m2`, `dtmajic`, `date_rafraichissement_vue`, `geom` |
| Cadastre_div_surfacique | `s_cadastre.v_vmap_objet_surfacique_divers` | 10210 | 2025-02-20 | `geom`, `id`, `id_com`, `section`, `sym_code`, `texte` |
| Objet Surfacique | `s_cadastre.v_vmap_objet_surfacique_divers` | 10210 | 2025-02-20 | `geom`, `id`, `id_com`, `section`, `sym_code`, `texte` |
| Borne de propriété | `s_cadastre.v_vmap_borne_de_limite_de_propriete` | 7941 | 2025-02-20 | `geom`, `id`, `id_com`, `pre`, `section` |
| Ligne de rattachement | `agglo_s_cadastre.vmap_fond_cadastral_parcelle_etq_rattachement` | 6548 | 2025-02-20 | `id_com`, `id`, `sym_code`, `section`, `pre`, `texte`, `geom` |
| Parcelles forestières | `environnement.vmp_onf_parcforet` | 4867 | 2025-02-06 | `geom`, `gid`, `id_foret`, `libelle_foret`, `no_parcelle_foret` |
| Subdivision fiscale | `s_cadastre.v_vmap_subdivision_fiscale` | 3029 | 2025-02-20 | `geom`, `id`, `id_com`, `pre`, `section`, `tex` |
| Ravalement incitatif Loupian - Parcelles éligibles | `logement.operation_facades_parcelles` | 2823 |  | `cdcomm`, `dtmaj`, `geom`, `gid`, `id_par`, `lien_source`, `sources`, `subvention`, `subvention_type` |
| Ravalement incitatif Marseillan - Parcelles éligibles | `logement.operation_facades_parcelles` | 2823 | 2025-04-04 | `cdcomm`, `dtmaj`, `geom`, `gid`, `id_par`, `lien_source`, `sources`, `subvention`, `subvention_type` |
| Ravalement incitatif Mèze - Parcelles éligibles | `logement.operation_facades_parcelles` | 2823 |  | `cdcomm`, `dtmaj`, `geom`, `gid`, `id_par`, `lien_source`, `sources`, `subvention`, `subvention_type` |
| COPROFF - Ref. National des Copropriétés (RNIC) | `logement.vmp_cerema_coproff` | 2773 |  | `adress_ref`, `code_ape`, `com_rl`, `contact_nom`, `contact_renseigne`, `date_immat`, `date_reg`, `dfinmandat`, `dt_maj`, `email_gestionnaire`, `email_syndic`, `geom`, `idcopro`, `idtup`, `mandat`, `nb_adr_com`, `nom_syndic`, `nom_usage`, `num_immat`, `repre_lega`, `siret`, `telephone_fixe`, `telephone_portable`, `telephone_standard`, `typ_syndic` |
| Points canevas | `s_cadastre.v_vmap_point_de_canevas` | 2372 | 2025-02-20 | `can_code`, `geom`, `id`, `id_com`, `map_code`, `ori`, `palt_code`, `ppln_code`, `pre`, `section`, `sym_code` |
| Tronçon cours d'eau (étiquettes) | `s_cadastre.v_vmap_texte_troncon_de_cours_d_eau` | 1409 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Liste parcelles communales 2018 (intérieur espaces naturels) | `environnement.perimetre_competence_espaces_nat_parcellecommunale` | 1313 | 2019-10-09 | `code`, `communeinsee_tex2`, `dateappro`, `datemaj`, `ddenom`, `dtmajic`, `fid`, `geom`, `gid`, `gid_esp_nat`, `id_com`, `id_dnupro`, `id_par`, `nb_proprio`, `num_parcelle`, `rmq`, `statut`, `surfcad_m2`, `surfsig_m2`, `type` |
| Domaine non cadastré (terrestre) | `foncier.vmp_dnc_horseau` | 1125 | 2017-07-13 | `cdcomm`, `dtedigeo`, `dtmaj`, `eau_regime`, `geom`, `gid` |
| Parcelles communales mises à disposition de SAM | `environnement.vmp_perimetre_competence_espaces_nat_pv_mad_parcelles` | 1104 | 2024-10-17 | `cdcomm`, `dtmaj`, `geom`, `gid`, `id_par`, `lib_surface_cadastrale`, `pv_date`, `pv_document`, `st_area`, `surface_cadastrale` |
| Lieu-dit (étiquettes) | `s_cadastre.v_vmap_texte_lieu_dit` | 1074 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Lieu-dit | `s_cadastre.v_vmap_lieu_dit` | 1061 | 2025-02-20 | `geom`, `id`, `id_com`, `oid`, `pre`, `section`, `texte` |
| Sections en N&B | `agglo_s_cadastre.vmap_fond_cadastral_section` | 979 | 2017-08-30 | `id_sec`, `id_com`, `section`, `pre`, `geom`, `commune` |
| Sections en couleur | `agglo_s_cadastre.vmap_fond_cadastral_section` | 979 | 2018-05-11 | `id_sec`, `id_com`, `section`, `pre`, `geom`, `commune` |
| Objet du réseau routier (étiquettes) | `s_cadastre.v_vmap_texte_objet_du_reseau_routier` | 973 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Foncier communal en zone A | `foncier.vmp_foncier_communes_zones_a` | 719 | 2021-01-26 | `gid`, `id_par`, `etq_parcelle`, `libelle`, `surf_parcelle`, `surf_intersection`, `id_dnupro`, `ddenom`, `geom`, `geom_parcelle` |
| Parcelles communales en zone A | `foncier.vmp_foncier_communes_zones_a` | 719 | 2021-01-26 | `gid`, `id_par`, `etq_parcelle`, `libelle`, `surf_parcelle`, `surf_intersection`, `id_dnupro`, `ddenom`, `geom`, `geom_parcelle` |
| Objet ponctuel divers (étiquettes) | `s_cadastre.v_vmap_texte_objet_ponctuel_divers` | 623 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Ensemble immobilier (étiquette) | `s_cadastre.v_vmap_texte_ensemble_immobilier` | 597 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Section | `s_cadastre.v_vmap_section_cadastrale` | 585 | 2025-02-20 | `commune`, `geom`, `id_com`, `id_sec`, `pre`, `section` |
| Objet linéaire divers (étiquettes) | `s_cadastre.v_vmap_texte_objet_lineaire_divers` | 261 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| Domaine non cadastré (surfaces en eau) | `foncier.vmp_dnc_eau` | 251 | 2017-07-13 | `cdcomm`, `dtedigeo`, `dtmaj`, `eau_regime`, `geom`, `gid` |
| Signalement cadastre (polygone) | `agglo_s_cadastre.propriete_cadastrale_signalements_polygone` | 171 | 2024-11-22 | `categorie`, `commune`, `date_millesime_majic`, `document`, `dtmaj`, `geom`, `gid`, `id_com`, `id_par`, `mise_a_jour_majic_ok`, `proprietaire_presume`, `rmq` |
| Foncier agglo en zone A | `foncier.vmp_foncier_agglo_zones_a` | 167 | 2021-02-25 | `gid`, `id_par`, `etq_parcelle`, `libelle`, `surf_parcelle`, `surf_intersection`, `id_dnupro`, `ddenom`, `geom`, `geom_parcelle` |
| Parcelles agglo en zone A | `foncier.vmp_foncier_agglo_zones_a` | 167 | 2021-02-25 | `gid`, `id_par`, `etq_parcelle`, `libelle`, `surf_parcelle`, `surf_intersection`, `id_dnupro`, `ddenom`, `geom`, `geom_parcelle` |
| Signalement cadastre | `agglo_s_cadastre.vmp_propriete_cadastrale_signalements_polygone` | 147 | 2024-11-07 | `categorie`, `document`, `dtmaj`, `geom`, `gid`, `id_par`, `proprietaire_presume`, `rmq` |
| Parcelles confiées à la gestion de SAM | `foncier.vmp_perimetre_competence_foncier_et_espaces_nat` | 123 | 2024-05-17 | `cdcomm`, `date_debut`, `date_deliberation`, `date_fin`, `dtmaj`, `geom`, `gid`, `id_par`, `lien_deliberation`, `lien_document`, `mesures_ge`, `nom`, `rmq_version`, `service_referent`, `statut`, `type_en` |
| Parcelles sans informations foncières | `agglo_s_cadastre.vmp_parcelles_sans_infos_majic` | 85 |  | `annee_majic`, `geom`, `id_par` |
| DPM - Domaine public maritime (DDTM) | `foncier.ddtm_dpm` | 53 | 2024-05-17 | `doc_lien`, `dtmaj`, `geom`, `gid`, `insee_com`, `nom_com`, `observation`, `sources` |
| Limites du DPM (DDTM) | `foncier.ddtm_dpm` | 53 | 2025-03-31 | `doc_lien`, `dtmaj`, `geom`, `gid`, `insee_com`, `nom_com`, `observation`, `sources` |
| Périmètres AOC et IGP viticoles | `economie.vmp_delimitation_parcellaire_aoc_inao` | 44 | 2024-11-08 | `app`, `appellation`, `categorie`, `commune`, `dtmaj`, `geom`, `gid`, `signe`, `type_denom`, `type_prod` |
| Communes en N&B | `agglo_s_cadastre.vmap_fond_cadastral_commune` | 27 | 2017-08-30 | `id_com`, `annee`, `source_code`, `dep_code`, `nom`, `geom` |
| Communes en N&B (sans étiquettes) | `agglo_s_cadastre.vmap_fond_cadastral_commune` | 27 |  | `id_com`, `annee`, `source_code`, `dep_code`, `nom`, `geom` |
| Communes en couleur | `agglo_s_cadastre.vmap_fond_cadastral_commune` | 27 | 2018-05-11 | `id_com`, `annee`, `source_code`, `dep_code`, `nom`, `geom` |
| Périmètre cadastral des communes | `agglo_s_cadastre.vmap_fond_cadastral_commune` | 27 | 2024-03-27 | `id_com`, `annee`, `source_code`, `dep_code`, `nom`, `geom` |
| Objet surfacique divers (étiquettes) | `s_cadastre.v_vmap_texte_objet_surfacique_divers` | 21 | 2025-02-20 | `cef`, `csp`, `di1`, `di2`, `di3`, `di4`, `fon`, `geom`, `hei`, `hta`, `id`, `id_com`, `rotation`, `section`, `taille`, `texte`, `tpa`, `tyu`, `vta` |
| EPF - Périmètres d'intervention | `foncier.vmp_epf_perimetres` | 16 | 2024-05-17 | `avancement`, `axe`, `cdcomm`, `code_convention`, `commune`, `date_avancement`, `dtmaj`, `duree_conv`, `geom`, `gid`, `lib_duree_conv`, `lib_sources_dtmaj`, `lien_convention`, `nom`, `sources`, `type_convention`, `type_filtre`, `type_objet` |
| EPF - Périmètres d'intervention | `foncier.vmp_epf_perimetres` | 16 | 2024-05-17 | `avancement`, `axe`, `cdcomm`, `code_convention`, `commune`, `date_avancement`, `dtmaj`, `duree_conv`, `geom`, `gid`, `lib_duree_conv`, `lib_sources_dtmaj`, `lien_convention`, `nom`, `sources`, `type_convention`, `type_filtre`, `type_objet` |
| Plan initiative copropriétés (PIC) > immeubles | `logement.coproprietes_pic` | 16 | 2025-04-11 | `copropriete`, `date_protocole`, `dtmaj`, `geom`, `lien_protocole`, `no_copro` |
| Commune | `s_cadastre.v_vmap_commune` | 14 | 2025-03-07 | `annee`, `dep_code`, `geom`, `id_com`, `nom`, `source_code` |
| Communes (masque) | `agglo_s_cadastre.v_vmap_commune_renverse` | 13 | 2021-08-03 | `annee`, `dep_code`, `geom`, `id_com`, `nom`, `source_code` |
| Obligation de DP avant division parcellaire | `urbanisme.vmp_obligation_dp_avant_division_parcellaire` | 12 | 2025-07-31 | `date_deliberation`, `geom`, `gid`, `libelle`, `lien_deliberation`, `lien_titre` |
| Baux de location | `foncier.baux_villeveyrac` | 8 | 2019-03-28 | `date_deliberation`, `dtmaj`, `duree_contrat`, `geom`, `gid`, `nom`, `sources`, `type_contrat` |
| Ports départementaux | `foncier.cd34_port` | 6 | 2025-02-04 | `cdcomm`, `dtmaj`, `fiche_info_ports`, `geom`, `gid`, `nom_commun`, `nom_port`, `num_port` |
| Ports départementaux | `foncier.cd34_port` | 6 | 2025-02-04 | `cdcomm`, `dtmaj`, `fiche_info_ports`, `geom`, `gid`, `nom_commun`, `nom_port`, `num_port` |
| Périmètres d'étude réglementaires | `foncier.vmp_perimetres_etudes` | 5 | 2024-05-17 | `dt_approbation`, `etiquette`, `geom`, `gid`, `libelle`, `lien_doc`, `superf_m2` |
| Périmètres d'étude réglementaires | `foncier.vmp_perimetres_etudes` | 5 | 2024-05-21 | `dt_approbation`, `etiquette`, `geom`, `gid`, `libelle`, `lien_doc`, `superf_m2` |
| DPF - Gestionnaire : VNF | `foncier.dpf` | 4 | 2024-05-16 | `dtmaj`, `geom`, `gestionnaire`, `gid`, `lien_doc`, `sources`, `titre_doc` |
| DPF - Gestionnaire : Ville de Sète | `foncier.dpf` | 4 | 2024-05-16 | `dtmaj`, `geom`, `gestionnaire`, `gid`, `lien_doc`, `sources`, `titre_doc` |
| PORT Sète Sud France | `foncier.region_port` | 1 | 2024-05-22 | `dtmaj`, `geom`, `gest`, `gid`, `lien_doc`, `rmq`, `titre_doc` |
| PORT Sète Sud France | `foncier.region_port` | 1 | 2024-05-17 | `dtmaj`, `geom`, `gest`, `gid`, `lien_doc`, `rmq`, `titre_doc` |

**47 couche(s) inaccessibles** (droits ou vue en erreur) :

- ADS dossier - Contour Parcelles (`agglo_cartads.vmp_localisation_dossiers_cartads_dans_vmap_restric_insee`) — ERROR_SERVER_REQUEST_500
- AOC (source chambre d'agriculture) (`environnement.pgmoure_ca_parcellaire_aoc_viticoles`) — ERROR_SERVER_REQUEST_500
- Analyse spatiale SIG - Digital Technologie - avril 2019* (`pluvial.vmp_pluvial_servitude_parcelle`) — ERROR_SERVER_REQUEST_500
- Bail la Rouquette > vocations culturales (`foncier.vmp_bail_agglo_larouquette_usages`) — ERROR_SERVER_REQUEST_500
- Bail la Rouquette > zonage (`foncier.vmp_bail_agglo_larouquette_zonage`) — ERROR_SERVER_REQUEST_500
- Baux SAM (`foncier.baux_agglo`) — ERROR_SERVER_REQUEST_500
- Baux exploitants (`foncier.vmp_bail_agglo_agriculteur`) — ERROR_SERVER_REQUEST_500
- Cadastre 1824 complet (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon a1 La Bourdigue (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon a2 La Peyrade (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon a3 Ile Centre (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon a4 Le Port (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon b1 Centre Ville (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon b3 Chabanettes (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon b3 Pierres blanches-Lazaret (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon b5 Chateau vert-Pont levis (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon b6 Barrou (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon b7 Caraussane (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon c1 Limites communes Etang (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon c2 Villeroy-Listel (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon c3 Croix de Marques (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre Napoleon c4 Castelas (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Cadastre_Napoleon_b2_La_Consigne (`None.None`) — ERROR_GENERIC_CONTROLLER_GET
- Compteurs AEP Montbazin (`aep.compteurs_montbazin`) — ERROR_SERVER_REQUEST_500
- DIA récentes parcelles veille prioritaire (`agglo_cartads.vmp_splbt_dia_opah_veille_prioritaire`) — ERROR_SERVER_REQUEST_500
- Grandes propriétés privées, SCI et exploitants (`environnement.pgmoure_parcelle_proprietaire_prive`) — ERROR_SERVER_REQUEST_500
- Limites du DPM (DDTM) - Frontignan (étude) (`foncier.ddtm_dpm_frontignan`) — ERROR_SERVER_REQUEST_500
- Mesure de compensation existante (nom couche ?) (`environnement.pgmoure_parcelle_montbazin`) — ERROR_SERVER_REQUEST_500
- Nombre de propriétaires - Personne Morale (`s_openmajic.v_om_parcelle_point`) — ERROR_SERVER_REQUEST_500
- OLD - Parcelles impactées et propriétaires (`risques.vmp_debroussaillement_old_mailing`) — ERROR_SERVER_REQUEST_500
- PSE diagnostic (`environnement.pse_parcelles_diagnostic`) — ERROR_SERVER_REQUEST_500
- Parcelle sous commodat (contrat) (`environnement.pgmoure_parcelles_commodat_pizalli_tot`) — ERROR_SERVER_REQUEST_500
- Parcelles RPG BIO 2022 (`temporaire_migration.formation_laurent_tp_integration_rpg_bio_2022`) — ERROR_SERVER_REQUEST_500
- Parcelles des baux dont SAM est bénéficiaire (`foncier.baux_agglo_parcelle`) — ERROR_SERVER_REQUEST_500
- Parcelles en veille prioritaire DIA (`logement.vmp_opah_splbt_parcelles_veille_prioritaire`) — ERROR_SERVER_REQUEST_500
- Personne Morale (`s_openmajic.v_om_parcelle_categorisee`) — ERROR_SERVER_REQUEST_500
- Potentiel mesure compensation propriété privée ou privée/publique (Biotope-LPO) (`environnement.pgmoure_potentiel_mc_propriete_prive_new`) — ERROR_SERVER_REQUEST_500
- Propriétaire exploitant (`environnement.pgmoure_propr_exploitant`) — ERROR_SERVER_REQUEST_500
- Propriété de Lafarge mise à disposition par convention aux chasseurs de Bouzigues - Juillet 2019 (`environnement.pgmoure_chasse_juillet2019`) — ERROR_SERVER_REQUEST_500
- Propriété publique (`environnement.pgmoure_parcelle_propriete_publique`) — ERROR_SERVER_REQUEST_500
- Signalement propriétaire pas à jour (`agglo_s_cadastre.vmp_propriete_cadastrale_signalements`) — ERROR_SERVER_REQUEST_500
- Zone de reconquête agropastorale sur propriété privée (`environnement.pgmoure_potentiel_agro_pastoral_sur_propriete_privee`) — ERROR_SERVER_REQUEST_500
- Zone de reconquête agropastorale sur propriété publique (`environnement.pgmoure_potentiel_agro_pastoral_sur_propriete_publique`) — ERROR_SERVER_REQUEST_500
- parcelle_bati_1945_1985 (`ass_raepa.v_parcelle_annee_construction`) — ERROR_SERVER_REQUEST_500
- parcelle_bati_1985_2000 (`ass_raepa.v_parcelle_annee_construction`) — ERROR_SERVER_REQUEST_500
- parcelle_bati_apres_2000 (`ass_raepa.v_parcelle_annee_construction`) — ERROR_SERVER_REQUEST_500
- parcelle_bati_avant1945 (`ass_raepa.v_parcelle_annee_construction`) — ERROR_SERVER_REQUEST_500
