# -*- coding: utf-8 -*-
"""Métriques de texte, formes ISO 5807, géométrie et palette.

Module partagé par tracer.py et verifier.py : le traceur et le lint mesurent
le texte et les formes avec les mêmes fonctions, de sorte qu'un schéma tracé
passe le lint, et qu'une retouche manuelle qui déborde ne le passe pas.

Bibliothèque standard seule. Python 3.9 ou plus.
"""
import json
import math
import os
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
PALETTE_DEFAUT = os.path.join(os.path.dirname(ICI), "assets", "palette.json")

POLICE = ('-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", '
          'Helvetica, Arial, sans-serif')

TAILLE_TEXTE = 13.0
TAILLE_ETIQUETTE = 11.0
TAILLE_TITRE = 15.0
INTERLIGNE = 1.3
MONTANTE = 0.80
DESCENDANTE = 0.22

# Les largeurs sont celles de Helvetica, en millièmes de cadratin. Le rendu
# réel dépend de la police du lecteur : la marge couvre l'écart avec les
# polices de repli de la pile, elle ne le supprime pas.
MARGE_METRIQUE = 1.15
FACTEUR_GRAS = 1.06

MARGE_TRACE = 7.0
MARGE_LINT = 4.0

_ASCII = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333,
    278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278,
    584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278,
    500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944,
    667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556,
    278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500,
    278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]
LARGEURS = {chr(32 + i): w for i, w in enumerate(_ASCII)}
LARGEURS.update({
    "\u00a0": 278, "\u202f": 278, "\u2019": 222, "\u2018": 222,
    "\u201c": 333, "\u201d": 333, "\u00ab": 556, "\u00bb": 556,
    "\u2013": 556, "\u2014": 1000, "\u2026": 1000, "\u0153": 944,
    "\u0152": 1000, "\u00e6": 889, "\u00c6": 1000, "\u00df": 611,
    "\u20ac": 556, "\u00b0": 400, "\u00b7": 278, "\u00d7": 584,
})
LARGEUR_INCONNUE = 1000


def largeur_texte(texte, taille, gras=False):
    """Largeur estimée d'une ligne, marge de sécurité comprise."""
    total = 0
    for c in texte:
        if unicodedata.combining(c):
            continue
        w = LARGEURS.get(c)
        if w is None:
            w = LARGEURS.get(unicodedata.normalize("NFD", c)[0],
                             LARGEUR_INCONNUE)
        total += w
    return (total / 1000.0 * taille * MARGE_METRIQUE
            * (FACTEUR_GRAS if gras else 1.0))


def boite_glyphes(x, ligne_base, largeur, taille, ancre):
    """Rectangle occupé par une ligne de texte : x0, y0, x1, y1."""
    if ancre == "middle":
        x0 = x - largeur / 2
    elif ancre == "end":
        x0 = x - largeur
    else:
        x0 = x
    return (x0, ligne_base - MONTANTE * taille,
            x0 + largeur, ligne_base + DESCENDANTE * taille)


# --- Formes -----------------------------------------------------------------

FORMES = {
    "terminal": {"taille": (170, 44), "nom": "Terminal"},
    "traitement": {"taille": (170, 56), "nom": "Traitement"},
    "decision": {"taille": (180, 84), "nom": "Décision"},
    "entree-sortie": {"taille": (180, 56), "nom": "Entrée/sortie"},
    "processus-predefini": {"taille": (180, 56),
                            "nom": "Processus prédéfini"},
    "connecteur": {"taille": (36, 36), "nom": "Connecteur de page"},
    "renvoi-page": {"taille": (44, 44), "nom": "Renvoi hors page"},
    "annotation": {"taille": (170, 50), "nom": "Annotation"},
    "base-de-donnees": {"taille": (150, 72), "nom": "Fichier ou base"},
    "document": {"taille": (170, 62), "nom": "Document"},
    "documents": {"taille": (178, 70), "nom": "Documents multiples"},
    "operation-manuelle": {"taille": (180, 56), "nom": "Opération manuelle"},
    "saisie-manuelle": {"taille": (180, 60), "nom": "Saisie manuelle"},
    "preparation": {"taille": (180, 52), "nom": "Préparation"},
    "parallele": {"taille": (0, 8), "nom": "Mode parallèle"},
}
FORMES_SANS_TEXTE = {"parallele"}
COTES = {"haut": (0.0, -1.0), "bas": (0.0, 1.0),
         "gauche": (-1.0, 0.0), "droite": (1.0, 0.0)}
ETATS = ("neutre", "accent", "succes", "attention", "danger", "fait")

# Constantes de dessin, partagées avec le lint pour reconstruire les zones.
BIAIS_ES = 18.0          # décalage du parallélogramme entrée/sortie
BARRE_PP = 12.0          # barres du processus prédéfini
RETRAIT_OM = 20.0        # retrait bas de l'opération manuelle
PENTE_SM = 0.30          # hauteur relative de la pente de saisie manuelle
POINTE_PREP = 18.0       # pointes de l'hexagone de préparation
ELLIPSE_BD = 10.0        # demi-hauteur des ellipses de la base de données
VAGUE_DOC = 7.0          # amplitude de la vague des documents
DECALAGE_DOCS = 4.0      # décalage entre feuilles des documents multiples
POINTE_RENVOI = 0.60     # hauteur relative du corps du renvoi hors page
CROCHET_ANNOT = 12.0     # retour du crochet d'annotation


def _arc(cx, cy, rx, ry, a0, a1, n):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n),
             cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _bezier(p0, p1, p2, p3, n):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0]
                    + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1]
                    + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def _document(x, y, w, h):
    a = VAGUE_DOC
    pts = [(x, y), (x + w, y), (x + w, y + h - a)]
    pts += _bezier((x + w, y + h - a), (x + w * 0.75, y + h - 3 * a),
                   (x + w * 0.25, y + h + a), (x, y + h - a), 16)[1:]
    return pts


def _rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def contour(forme, x, y, w, h):
    """Contour extérieur de la forme, en polygone. Sert aux points d'attache."""
    cx, cy = x + w / 2, y + h / 2
    if forme == "terminal":
        r = min(h, w) / 2
        return (_arc(x + w - r, cy, r, r, -math.pi / 2, math.pi / 2, 12)
                + _arc(x + r, cy, r, r, math.pi / 2, 3 * math.pi / 2, 12))
    if forme == "decision":
        return [(cx, y), (x + w, cy), (cx, y + h), (x, cy)]
    if forme == "entree-sortie":
        s = BIAIS_ES
        return [(x + s, y), (x + w, y), (x + w - s, y + h), (x, y + h)]
    if forme == "operation-manuelle":
        i = RETRAIT_OM
        return [(x, y), (x + w, y), (x + w - i, y + h), (x + i, y + h)]
    if forme == "saisie-manuelle":
        return [(x, y + PENTE_SM * h), (x + w, y), (x + w, y + h), (x, y + h)]
    if forme == "preparation":
        p = POINTE_PREP
        return [(x + p, y), (x + w - p, y), (x + w, cy),
                (x + w - p, y + h), (x + p, y + h), (x, cy)]
    if forme == "connecteur":
        return _arc(cx, cy, w / 2, h / 2, 0, 2 * math.pi, 24)[:-1]
    if forme == "renvoi-page":
        return [(x, y), (x + w, y), (x + w, y + POINTE_RENVOI * h),
                (cx, y + h), (x, y + POINTE_RENVOI * h)]
    if forme == "base-de-donnees":
        e = ELLIPSE_BD
        return (_arc(cx, y + e, w / 2, e, math.pi, 2 * math.pi, 12)
                + _arc(cx, y + h - e, w / 2, e, 0, math.pi, 12))
    if forme == "document":
        return _document(x, y, w, h)
    if forme == "documents":
        d = DECALAGE_DOCS
        return _document(x, y + 2 * d, w - 2 * d, h - 2 * d)
    return _rect(x, y, w, h)


def zone_texte(forme, x, y, w, h):
    """Polygone dans lequel le texte doit tenir."""
    cx = x + w / 2
    if forme == "processus-predefini":
        return _rect(x + BARRE_PP, y, w - 2 * BARRE_PP, h)
    if forme == "base-de-donnees":
        e = ELLIPSE_BD
        return (_arc(cx, y + e, w / 2, e, math.pi, 0, 12)
                + _arc(cx, y + h - e, w / 2, e, 0, math.pi, 12)[1:-1])
    if forme == "annotation":
        return _rect(x + CROCHET_ANNOT / 2, y, w - CROCHET_ANNOT, h)
    return contour(forme, x, y, w, h)


def centre_reference(forme, x, y, w, h):
    """Centre visuel : celui de la feuille de devant pour les documents."""
    if forme == "documents":
        d = DECALAGE_DOCS
        return x + (w - 2 * d) / 2, y + 2 * d + (h - 2 * d) / 2
    return x + w / 2, y + h / 2


# --- Géométrie ----------------------------------------------------------------

def boite_polygone(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def etendue(poly, yy):
    """Intervalle horizontal du polygone à l'ordonnée yy, ou None."""
    xs = []
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if min(y1, y2) <= yy <= max(y1, y2):
            if y1 == y2:
                xs += [x1, x2]
            else:
                xs.append(x1 + (yy - y1) * (x2 - x1) / (y2 - y1))
    if len(xs) < 2:
        return None
    return min(xs), max(xs)


def dedans(poly, px, py):
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < xi:
                inside = not inside
    return inside


def distance_segment(px, py, a, b):
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy)
                     / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def point_interieur(poly, px, py, marge):
    if not dedans(poly, px, py):
        return False
    n = len(poly)
    return all(distance_segment(px, py, poly[i], poly[(i + 1) % n]) >= marge
               for i in range(n))


def boite_dans_zone(poly, boite, marge):
    x0, y0, x1, y1 = boite
    return all(point_interieur(poly, px, py, marge)
               for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def rayon_bord(poly, cx, cy, dx, dy):
    """Premier point du contour atteint depuis (cx, cy) dans la direction."""
    meilleur = None
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - cx) * ey - (y1 - cy) * ex) / den
        u = ((x1 - cx) * dy - (y1 - cy) * dx) / den
        if t > 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            if meilleur is None or t < meilleur:
                meilleur = t
    if meilleur is None:
        return cx, cy
    return cx + meilleur * dx, cy + meilleur * dy


def segment_coupe_boite(a, b, boite):
    """Vrai si le segment orthogonal ou quelconque traverse le rectangle."""
    x0, y0, x1, y1 = boite
    (ax, ay), (bx, by) = a, b
    t0, t1 = 0.0, 1.0
    dx, dy = bx - ax, by - ay
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
    return True


def boites_se_chevauchent(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


# --- Palette ------------------------------------------------------------------

ROLES = {
    "fond": "--bgColor-default",
    "forme-fond": "--bgColor-muted",
    "forme-trait": "--borderColor-emphasis",
    "texte": "--fgColor-default",
    "texte-discret": "--fgColor-muted",
    "lien": "--fgColor-muted",
}
for _etat, _suffixe in (("accent", "accent"), ("succes", "success"),
                        ("attention", "attention"), ("danger", "danger"),
                        ("fait", "done")):
    ROLES[_etat + "-trait"] = "--borderColor-%s-emphasis" % _suffixe
    ROLES[_etat + "-fond"] = "--bgColor-%s-muted" % _suffixe
    ROLES[_etat + "-lien"] = "--fgColor-%s" % _suffixe


def charger_palette(chemin=None):
    chemin = chemin or PALETTE_DEFAUT
    with open(chemin, encoding="utf-8") as f:
        palette = json.load(f)
    if palette.get("format") != 2 or "teintes" not in palette:
        raise ValueError("palette.json : format inattendu")
    return palette


def normaliser_hex(valeur):
    """'#abc' ou '#aabbccdd' vers ('#aabbcc', opacité)."""
    v = valeur.strip().lower().lstrip("#")
    if len(v) in (3, 4):
        v = "".join(c * 2 for c in v)
    alpha = 1.0
    if len(v) == 8:
        alpha = round(int(v[6:8], 16) / 255.0, 3)
        v = v[:6]
    return "#" + v, alpha


def couleurs_variante(palette, variante):
    """Rôle -> (hex6, opacité) pour la variante demandée."""
    jetons = palette["jetons"][variante]
    sortie = {}
    for role, jeton in ROLES.items():
        if jeton not in jetons:
            raise ValueError("jeton absent de la palette %s : %s"
                             % (variante, jeton))
        sortie[role] = normaliser_hex(jetons[jeton])
    return sortie


def teintes_admises(palette, variante):
    return set(palette["teintes"][variante])
