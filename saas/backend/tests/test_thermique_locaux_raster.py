"""Locaux : contours recalés sur les murs, espaces libres, nature des pièces (D24 à D27)."""
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box

from app.services import thermique_locaux as locaux

PX_PAR_M = 118.11  # 300 dpi au 1/100
L, H = 1800, 1000


def _norm(x, y):
    return [x * 1000 / L, y * 1000 / H]


def _plan():
    """Deux bureaux de 4 x 5 m, un couloir de 1,4 m au sud ; murs de 20 cm ; un meuble collé au mur."""
    page = Image.new("L", (L, H), 255)
    d = ImageDraw.Draw(page)
    m = round(0.2 * PX_PAR_M)
    x0, y0 = 100, 100
    w, h, c = round(4 * PX_PAR_M), round(5 * PX_PAR_M), round(1.4 * PX_PAR_M)
    d.rectangle((x0 - m, y0 - m, x0 + 2 * w + m, y0), fill=0)  # façade nord
    d.rectangle((x0 - m, y0 - m, x0, y0 + h + c + m), fill=0)  # pignon ouest
    d.rectangle((x0 + 2 * w, y0 - m, x0 + 2 * w + m, y0 + h + c + m), fill=0)  # pignon est
    d.rectangle((x0 - m, y0 + h + c, x0 + 2 * w + m, y0 + h + c + m), fill=0)  # façade sud
    d.rectangle((x0 + w - m // 2, y0, x0 + w + m // 2, y0 + h), fill=0)  # refend entre bureaux
    d.rectangle((x0, y0 + h, x0 + 2 * w, y0 + h + m // 2), fill=0)  # cloison sur couloir
    d.rectangle((x0 + 60, y0, x0 + 200, y0 + 70), outline=0, width=2)  # bureau collé au mur nord
    batiment = box(x0 - m, y0 - m, x0 + 2 * w + m, y0 + h + c + m)
    # contours de l'agent : 40 cm trop courts de chaque côté
    marge = round(0.4 * PX_PAR_M)
    pieces = []
    for rang, gauche in enumerate((x0, x0 + w)):
        pieces.append({"id": f"piece-00{rang + 1}", "category": "piece", "subtype": f"Bureau {rang + 1}",
                       "points": [_norm(gauche + marge, y0 + marge), _norm(gauche + w - marge, y0 + marge),
                                  _norm(gauche + w - marge, y0 + h - marge), _norm(gauche + marge, y0 + h - marge)]})
    return page, {"objects": pieces}, batiment, (x0, y0, w, h, c)


def test_les_contours_sont_recales_sur_les_murs_et_le_couloir_devient_candidat():
    page, analyse, batiment, (x0, y0, w, h, c) = _plan()

    resultat = locaux.recaler_pieces(page, analyse, PX_PAR_M, batiment)

    b1 = resultat["pieces"][0]
    assert b1["recale"]
    # surface réelle du bureau entre murs : ~3,9 x 5 m (meuble compris, encoche refermée)
    assert 18.0 <= b1["surface_m2"] <= 20.5
    forme = Polygon([(x * L / 1000, y * H / 1000) for x, y in b1["points"]])
    assert forme.bounds[1] <= y0 + 3 and forme.bounds[0] <= x0 + 3  # jusqu'aux murs nord et ouest
    # le couloir, que l'agent n'a pas vu, reste libre et devient un local candidat
    assert resultat["candidats"] and 9 <= resultat["candidats"][0]["surface_m2"] <= 12.5


def test_integration_des_locaux_nature_et_espace_libre_nomme():
    page, analyse, batiment, _ = _plan()
    recalage = locaux.recaler_pieces(page, analyse, PX_PAR_M, batiment)
    analyse = locaux.appliquer(analyse, recalage)
    reponse = {"pieces": [{"id": "piece-001", "local": "chauffe", "indice": ""},
                          {"id": "piece-002", "local": "gaine_technique", "indice": "gaine verticale"}],
               "candidats": [{"id": "C1", "decision": "local", "nom": "circulation", "local": "circulation", "indice": "couloir"}],
               "observations": []}

    finale = locaux.integrer_locaux(analyse, recalage, reponse)

    pieces = [o for o in finale["objects"] if o["category"] == "piece"]
    assert [p["local"] for p in pieces] == ["chauffe", "gaine_technique", "circulation"]
    assert pieces[2]["contour"] == "espace_libre_mesure" and pieces[2]["review_required"]
    assert pieces[0]["contour"] == "recale_sur_murs" and "points_contour_agent" in pieces[0]


def test_un_contour_aberrant_garde_celui_de_l_agent():
    page = Image.new("L", (L, H), 255)  # aucun mur : la croissance est bornée mais la surface explose
    analyse = {"objects": [{"id": "piece-001", "category": "piece", "subtype": "Petit local",
                            "points": [_norm(500, 500), _norm(560, 500), _norm(560, 560), _norm(500, 560)]}]}
    resultat = locaux.recaler_pieces(page, analyse, PX_PAR_M)
    assert not resultat["pieces"][0]["recale"] and resultat["pieces"][0]["motif"]
