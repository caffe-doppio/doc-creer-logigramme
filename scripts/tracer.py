#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Trace un logigramme ISO 5807 depuis un modèle JSON.

Produit deux fichiers jumeaux, <id>.svg et <id>-dark.svg, et écrit sur la
sortie standard le snippet Markdown qui les appelle. Le texte est coupé et
les formes agrandies dans la limite de leur cellule ; au-delà, le traceur
refuse et dit quel nœud raccourcir. Il ne tronque jamais un texte.

Usage :
    python scripts/tracer.py MODELE.json --sortie DOSSIER
        [--chemin CHEMIN_DANS_LE_MD] [--palette PALETTE] [--remplacer]

Codes de sortie : 0 tracé, 2 modèle invalide, 3 fichier existant.
Bibliothèque standard seule. Python 3.9 ou plus.
"""
import argparse
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun as c  # noqa: E402

GRILLE_DEFAUT = (250, 140)
MARGE = 32.0
TALON = 18.0
DEPORT_COULOIR = 26.0
PAS_COULOIR = 16.0
ENTETE = 46.0
ENTETE_COULOIR = 30.0
ID_FICHIER = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID_NOEUD = re.compile(r"^[A-Za-z0-9_-]+$")


class ModeleInvalide(Exception):
    pass


def fmt(v):
    s = "%.1f" % v
    return s[:-2] if s.endswith(".0") else s


def echapper(texte):
    return (texte.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# --- Validation du modèle -----------------------------------------------------

def valider(m):
    err = []

    def exiger(cond, msg):
        if not cond:
            err.append(msg)

    def nombre_positif(v):
        return (isinstance(v, (int, float)) and not isinstance(v, bool)
                and v > 0)

    if not isinstance(m, dict):
        raise ModeleInvalide(["le modèle doit être un objet JSON"])
    grille = m.get("grille", {})
    exiger(isinstance(grille, dict) and all(
        nombre_positif(grille[k]) for k in ("colonne", "rangee")
        if k in grille), "grille : colonne et rangee, nombres positifs")
    exiger(isinstance(m.get("id"), str) and ID_FICHIER.match(m["id"] or ""),
           "id : obligatoire, minuscules, chiffres et tirets simples")
    for champ in ("titre", "alt"):
        exiger(isinstance(m.get(champ), str) and m[champ].strip(),
               "%s : obligatoire et non vide" % champ)
    exiger(isinstance(m.get("noeuds"), list) and m["noeuds"],
           "noeuds : liste non vide obligatoire")
    exiger(isinstance(m.get("liens", []), list), "liens : doit être une liste")
    exiger(m.get("pointes", "toutes") in ("toutes", "iso"),
           "pointes : 'toutes' ou 'iso'")
    if not isinstance(m.get("noeuds"), list):
        raise ModeleInvalide(err)
    if not isinstance(m.get("liens", []), list):
        m = dict(m, liens=[])

    couloirs = m.get("couloirs")
    plages = {}
    if couloirs is not None:
        if not isinstance(couloirs, list) or not couloirs:
            err.append("couloirs : liste non vide, ou champ absent")
            couloirs = []
        debut = 0
        for i, k in enumerate(couloirs):
            ref = "couloirs[%d]" % i
            if not isinstance(k, dict) or not isinstance(k.get("id"), str) \
                    or not ID_NOEUD.match(k["id"]):
                err.append("%s : id obligatoire (lettres, chiffres, _ et -)"
                           % ref)
                continue
            ref = "couloir %s" % k["id"]
            if k["id"] in plages:
                err.append("%s : id en double" % ref)
            titre = k.get("titre")
            if not isinstance(titre, str) or not titre.strip() \
                    or "\n" in titre:
                err.append("%s : titre obligatoire, sur une ligne" % ref)
            n_cols = k.get("cols", 1)
            if not isinstance(n_cols, int) or isinstance(n_cols, bool) \
                    or n_cols < 1:
                err.append("%s : cols entier au moins égal à 1" % ref)
                n_cols = 1
            plages[k["id"]] = (debut, debut + n_cols - 1)
            debut += n_cols

    ids, cellules = {}, {}
    for i, n in enumerate(m["noeuds"]):
        ref = "noeuds[%d]" % i
        if not isinstance(n, dict):
            err.append("%s : un nœud est un objet JSON" % ref)
            continue
        nid = n.get("id")
        if not isinstance(nid, str) or not ID_NOEUD.match(nid):
            err.append("%s : id obligatoire (lettres, chiffres, _ et -)" % ref)
            continue
        ref = "nœud %s" % nid
        if nid in ids:
            err.append("%s : id en double" % ref)
        ids[nid] = n
        forme = n.get("forme")
        if forme not in c.FORMES:
            err.append("%s : forme inconnue %r, voir references/iso-5807.md"
                       % (ref, forme))
            continue
        if forme not in c.FORMES_SANS_TEXTE:
            if not isinstance(n.get("texte"), str) or not n["texte"].strip():
                err.append("%s : texte obligatoire" % ref)
        if n.get("etat", "neutre") not in c.ETATS:
            err.append("%s : état inconnu %r" % (ref, n.get("etat")))
        for dim in ("largeur", "hauteur"):
            if dim in n and not nombre_positif(n[dim]):
                err.append("%s : %s, nombre positif en pixels" % (ref, dim))
        col, rang = n.get("col"), n.get("rang")
        if not (isinstance(col, int) and isinstance(rang, int)
                and col >= 0 and rang >= 0):
            err.append("%s : col et rang entiers positifs obligatoires" % ref)
            continue
        largeur = n.get("cols", 1) if forme == "parallele" else 1
        if forme == "parallele" and (not isinstance(largeur, int)
                                     or largeur < 1):
            err.append("%s : cols entier au moins égal à 1" % ref)
            largeur = 1
        if couloirs is not None or "couloir" in n:
            k = n.get("couloir")
            if couloirs is None:
                err.append("%s : couloir %r, mais le modèle ne déclare aucun "
                           "couloir" % (ref, k))
            elif not isinstance(k, str) or k not in plages:
                err.append("%s : couloir obligatoire, id d'un couloir déclaré "
                           "(%r reçu ; l'entier de décalage est le couloir "
                           "d'un lien)" % (ref, k))
            elif not (plages[k][0] <= col
                      and col + largeur - 1 <= plages[k][1]):
                err.append("%s : colonne %d hors du couloir %s, qui couvre "
                           "les colonnes %d à %d"
                           % (ref, col, k, plages[k][0], plages[k][1]))
        for k in range(largeur):
            cle = (col + k, rang)
            if cle in cellules:
                err.append("%s : cellule (%d, %d) déjà occupée par %s"
                           % (ref, cle[0], cle[1], cellules[cle]))
            cellules[cle] = nid
        if forme == "annotation" and not n.get("cible"):
            err.append("%s : une annotation porte une cible" % ref)

    for n in ids.values():
        if n.get("forme") == "annotation" and n.get("cible") not in ids:
            if n.get("cible"):
                err.append("nœud %s : cible inconnue %r"
                           % (n.get("id"), n.get("cible")))

    for i, l in enumerate(m.get("liens", [])):
        ref = "liens[%d]" % i
        if not isinstance(l, dict):
            err.append("%s : un lien est un objet JSON" % ref)
            continue
        if l.get("de") is not None and l.get("de") == l.get("vers"):
            err.append("%s : de et vers identiques ; un lien relie deux "
                       "symboles distincts" % ref)
        for bout in ("de", "vers"):
            if l.get(bout) not in ids:
                err.append("%s : %s inconnu %r" % (ref, bout, l.get(bout)))
            elif ids[l[bout]].get("forme") == "annotation":
                err.append("%s : une annotation se relie par sa cible, "
                           "pas par un lien" % ref)
        for cote in ("sortie", "entree"):
            if cote in l and l[cote] not in c.COTES:
                err.append("%s : %s doit valoir haut, bas, gauche ou droite"
                           % (ref, cote))
        if l.get("etat", "neutre") not in c.ETATS:
            err.append("%s : état inconnu %r" % (ref, l.get("etat")))
        via = l.get("via", [])
        if not isinstance(via, list) or not all(
                isinstance(p, list) and len(p) == 2
                and all(isinstance(v, (int, float)) for v in p) for p in via):
            err.append("%s : via est une liste de [col, rang]" % ref)
        if not isinstance(l.get("couloir", 0), int):
            err.append("%s : couloir doit être un entier" % ref)
    if err:
        raise ModeleInvalide(err)
    return ids


# --- Mise en page ---------------------------------------------------------------

class Noeud:
    def __init__(self, d, cw, rh):
        self.d = d
        self.id = d["id"]
        self.forme = d["forme"]
        self.texte = d.get("texte", "")
        self.etat = d.get("etat", "neutre")
        self.ccx = d["col"] * cw + cw / 2
        self.ccy = d["rang"] * rh + rh / 2
        self.lignes = []
        self.ancre = "middle"
        self.cote = None
        if self.forme == "parallele":
            n = d.get("cols", 1)
            ext = min(90.0, cw / 2 - 12)
            self.x = self.ccx - ext
            self.w = (n - 1) * cw + 2 * ext
            self.h = c.FORMES["parallele"]["taille"][1]
            self.y = self.ccy - self.h / 2
        else:
            w, h = c.FORMES[self.forme]["taille"]
            self.w = float(d.get("largeur", w))
            self.h = float(d.get("hauteur", h))
            self.placer()

    def placer(self):
        if self.forme == "documents":
            dd = c.DECALAGE_DOCS
            self.x = self.ccx - (self.w - 2 * dd) / 2
            self.y = self.ccy - (self.h - 2 * dd) / 2 - 2 * dd
        else:
            self.x = self.ccx - self.w / 2
            self.y = self.ccy - self.h / 2

    def boite(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def decaler(self, dx, dy):
        self.x += dx
        self.y += dy
        self.ccx += dx
        self.ccy += dy
        self.lignes = [(t, x + dx, y + dy) for t, x, y in self.lignes]


def largeur_disponible(zone, cx, haut, bas, marge):
    demi = None
    for yy in (haut, (haut + bas) / 2, bas):
        e = c.etendue(zone, yy)
        if e is None:
            return 0.0
        d = min(cx - e[0], e[1] - cx)
        demi = d if demi is None else min(demi, d)
    while demi > 0:
        if c.boite_dans_zone(zone, (cx - demi, haut, cx + demi, bas), marge):
            return 2 * demi
        demi -= 1.0
    return 0.0


def couper(texte, largeurs, taille, gras):
    lignes, i = [], 0
    for paragraphe in texte.split("\n"):
        mots = [m for m in re.split(r"[ \t\r]+", paragraphe) if m]
        if not mots:
            continue
        courant = ""
        for mot in mots:
            if i >= len(largeurs):
                return None
            essai = mot if not courant else courant + " " + mot
            if c.largeur_texte(essai, taille, gras) <= largeurs[i]:
                courant = essai
                continue
            if not courant:
                return "largeur"
            lignes.append(courant)
            i += 1
            if i >= len(largeurs):
                return None
            if c.largeur_texte(mot, taille, gras) > largeurs[i]:
                return "largeur"
            courant = mot
        if i >= len(largeurs):
            return None
        lignes.append(courant)
        i += 1
    return lignes


def disposer(noeud, taille=c.TAILLE_TEXTE):
    """Coupe le texte dans la forme. Renvoie None, 'largeur' ou 'hauteur'."""
    f = noeud.forme
    gras = f == "connecteur" or f == "renvoi-page"
    zone = c.zone_texte(f, noeud.x, noeud.y, noeud.w, noeud.h)
    x0, y0, x1, y1 = c.boite_polygone(zone)
    if f == "documents" or f == "document":
        cx, cy = c.centre_reference(f, noeud.x, noeud.y, noeud.w, noeud.h)
        cy -= c.VAGUE_DOC / 2
    elif f == "renvoi-page":
        cx, cy = (x0 + x1) / 2, noeud.y + noeud.h * c.POINTE_RENVOI / 2 + 2
    else:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    lh = taille * c.INTERLIGNE
    haut_glyphe = (c.MONTANTE + c.DESCENDANTE) * taille
    for n in range(1, 13):
        largeurs, bases = [], []
        for i in range(n):
            haut_ligne = cy - n * lh / 2 + i * lh
            base = haut_ligne + (lh - haut_glyphe) / 2 + c.MONTANTE * taille
            haut, bas = base - c.MONTANTE * taille, base + c.DESCENDANTE * taille
            if f == "annotation":
                ok = y0 + c.MARGE_TRACE <= haut and bas <= y1 - c.MARGE_TRACE
                disp = (x1 - x0 - 2 * c.MARGE_TRACE) if ok else 0.0
            else:
                disp = largeur_disponible(zone, cx, haut, bas, c.MARGE_TRACE)
            if disp <= 0:
                return "hauteur"
            largeurs.append(disp)
            bases.append(base)
        res = couper(noeud.texte, largeurs, taille, gras)
        if res == "largeur":
            return "largeur"
        if isinstance(res, list):
            if f == "annotation":
                noeud.ancre = "start"
                xt = x0 + c.MARGE_TRACE
            else:
                xt = cx
            noeud.lignes = [(t, xt, bases[i]) for i, t in enumerate(res)]
            return None
    return "hauteur"


def dimensionner(noeud, cw, rh):
    if noeud.forme in c.FORMES_SANS_TEXTE:
        return
    fixe = "largeur" in noeud.d or "hauteur" in noeud.d
    for _ in range(80):
        cause = disposer(noeud)
        if cause is None:
            return
        if fixe:
            break
        if noeud.forme in ("connecteur", "renvoi-page"):
            noeud.w += 4
            noeud.h += 4
        elif noeud.forme == "decision":
            noeud.w += 14
            noeud.h += 6
        elif cause == "largeur":
            noeud.w += 12
        else:
            noeud.h += 8
        noeud.placer()
        if noeud.w > cw - 16 or noeud.h > rh - 2 * TALON - 8:
            break
    raise ModeleInvalide([
        "nœud %s : texte trop long pour sa cellule (%s). Raccourcir le texte, "
        "ou augmenter grille.colonne (%d) ou grille.rangee (%d)."
        % (noeud.id, noeud.texte[:40], cw, rh)])


# --- Liens -------------------------------------------------------------------

def port(noeud, cote, autre_x=None):
    dx, dy = c.COTES[cote]
    if noeud.forme == "parallele":
        if cote in ("haut", "bas"):
            x = noeud.ccx if autre_x is None else autre_x
            x = max(noeud.x + 10, min(noeud.x + noeud.w - 10, x))
            return (x, noeud.y if cote == "haut" else noeud.y + noeud.h)
        return (noeud.x if cote == "gauche" else noeud.x + noeud.w,
                noeud.y + noeud.h / 2)
    poly = c.contour(noeud.forme, noeud.x, noeud.y, noeud.w, noeud.h)
    cx, cy = c.centre_reference(noeud.forme, noeud.x, noeud.y,
                                noeud.w, noeud.h)
    return c.rayon_bord(poly, cx, cy, dx, dy)


def cotes_par_defaut(a, b, lien, rang):
    dr = rang[b.id] - rang[a.id]
    dc = b.ccx - a.ccx
    sortie, entree = lien.get("sortie"), lien.get("entree")
    if sortie is None:
        if dr > 0:
            sortie = "bas"
        elif dr < 0:
            sortie = "droite"
        else:
            sortie = "droite" if dc >= 0 else "gauche"
    if entree is None:
        if dr > 0:
            entree = "haut"
        elif dr < 0:
            entree = sortie if sortie in ("gauche", "droite") else "droite"
        else:
            entree = "gauche" if dc >= 0 else "droite"
    return sortie, entree


def simplifier(pts):
    propres = []
    for p in pts:
        p = (round(p[0], 1), round(p[1], 1))
        if not propres or p != propres[-1]:
            propres.append(p)
    i = 1
    while i < len(propres) - 1:
        (ax, ay), (bx, by), (cx_, cy_) = propres[i - 1], propres[i], propres[i + 1]
        if (ax == bx == cx_) or (ay == by == cy_):
            propres.pop(i)
        else:
            i += 1
    return propres


def router(a, b, lien, rang, grille_px):
    s1, s2 = cotes_par_defaut(a, b, lien, rang)
    p = port(a, s1, b.ccx)
    q = port(b, s2, a.ccx)
    d1, d2 = c.COTES[s1], c.COTES[s2]
    p1 = (p[0] + d1[0] * TALON, p[1] + d1[1] * TALON)
    q1 = (q[0] + d2[0] * TALON, q[1] + d2[1] * TALON)
    couloir = lien.get("couloir", 0) * PAS_COULOIR
    pts = [p, p1]

    if lien.get("via"):
        vertical = d1[0] == 0
        cour = p1
        for col, rg in lien["via"]:
            w = grille_px(col, rg)
            if cour[0] != w[0] and cour[1] != w[1]:
                coin = (cour[0], w[1]) if vertical else (w[0], cour[1])
                pts.append(coin)
                vertical = not vertical
            else:
                vertical = cour[0] == w[0]
            pts.append(w)
            cour = w
        if cour[0] != q1[0] and cour[1] != q1[1]:
            pts.append((cour[0], q1[1]) if vertical else (q1[0], cour[1]))
    elif s1 == s2:
        if s1 in ("droite", "gauche"):
            ext = max if s1 == "droite" else min
            signe = 1 if s1 == "droite" else -1
            x = ext(p1[0], q1[0]) + signe * couloir
            pts += [(x, p1[1]), (x, q1[1])]
        else:
            ext = max if s1 == "bas" else min
            signe = 1 if s1 == "bas" else -1
            y = ext(p1[1], q1[1]) + signe * couloir
            pts += [(p1[0], y), (q1[0], y)]
    elif (d1[0] == 0) == (d2[0] == 0):
        avance = ((q1[0] - p1[0]) * d1[0] + (q1[1] - p1[1]) * d1[1] > 0
                  and (p1[0] - q1[0]) * d2[0] + (p1[1] - q1[1]) * d2[1] > 0)
        if d1[0] == 0:
            if avance or p1[0] == q1[0]:
                ym = (p1[1] + q1[1]) / 2
                pts += [(p1[0], ym), (q1[0], ym)]
            else:
                x = (max(a.x + a.w, b.x + b.w) + DEPORT_COULOIR + couloir)
                pts += [(x, p1[1]), (x, q1[1])]
        else:
            if avance or p1[1] == q1[1]:
                xm = (p1[0] + q1[0]) / 2
                pts += [(xm, p1[1]), (xm, q1[1])]
            else:
                y = (max(a.y + a.h, b.y + b.h) + DEPORT_COULOIR + couloir)
                pts += [(p1[0], y), (q1[0], y)]
    else:
        if d1[0] == 0:
            coin, repli = (p1[0], q1[1]), (q1[0], p1[1])
        else:
            coin, repli = (q1[0], p1[1]), (p1[0], q1[1])
        ok = ((coin[0] - p1[0]) * d1[0] + (coin[1] - p1[1]) * d1[1] >= 0
              and (coin[0] - q1[0]) * d2[0] + (coin[1] - q1[1]) * d2[1] >= 0)
        pts.append(coin if ok else repli)
    pts += [q1, q]
    return simplifier(pts), s1


def placer_etiquette(pts, texte):
    taille = c.TAILLE_ETIQUETTE
    w = c.largeur_texte(texte, taille)
    (x0, y0), (x1, y1) = pts[0], pts[1]
    if x0 == x1:
        sens = 1 if y1 > y0 else -1
        base = y0 + sens * 14 + (taille * 0.35 if sens > 0 else 0)
        return (x0 + 6, base, "start", w)
    if x1 > x0:
        return (x0 + 6, y0 - 5, "start", w)
    return (x0 - 6, y0 - 5, "end", w)


# --- Émission SVG -------------------------------------------------------------

def attrs_couleur(nom, valeur):
    hexa, alpha = valeur
    s = '%s="%s"' % (nom, hexa)
    if alpha < 1.0:
        s += ' %s-opacity="%s"' % (nom, "%.3g" % alpha)
    return s


def chemin_polygone(pts):
    return "M " + " L ".join("%s %s" % (fmt(x), fmt(y)) for x, y in pts) + " Z"


def dessiner_forme(n, pal):
    x, y, w, h = n.x, n.y, n.w, n.h
    etat = n.etat
    trait = pal["forme-trait" if etat == "neutre" else etat + "-trait"]
    fond = pal["forme-fond" if etat == "neutre" else etat + "-fond"]
    style = "%s %s stroke-width=\"1.5\"" % (attrs_couleur("fill", fond),
                                            attrs_couleur("stroke", trait))
    sans_fond = attrs_couleur("stroke", trait) + ' fill="none" stroke-width="1.5"'
    f = n.forme
    out = []
    if f == "terminal":
        r = min(w, h) / 2
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>'
                   % (fmt(x), fmt(y), fmt(w), fmt(h), fmt(r), style))
    elif f in ("traitement",):
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="2" %s/>'
                   % (fmt(x), fmt(y), fmt(w), fmt(h), style))
    elif f == "processus-predefini":
        b = c.BARRE_PP
        out.append('<rect x="%s" y="%s" width="%s" height="%s" %s/>'
                   % (fmt(x), fmt(y), fmt(w), fmt(h), style))
        out.append('<path d="M %s %s L %s %s M %s %s L %s %s" %s/>'
                   % (fmt(x + b), fmt(y), fmt(x + b), fmt(y + h),
                      fmt(x + w - b), fmt(y), fmt(x + w - b), fmt(y + h),
                      sans_fond))
    elif f == "connecteur":
        out.append('<circle cx="%s" cy="%s" r="%s" %s/>'
                   % (fmt(x + w / 2), fmt(y + h / 2), fmt(w / 2), style))
    elif f == "base-de-donnees":
        e = c.ELLIPSE_BD
        rx = w / 2
        out.append('<path d="M %s %s A %s %s 0 0 1 %s %s L %s %s A %s %s 0 0 1 '
                   '%s %s Z" %s/>'
                   % (fmt(x), fmt(y + e), fmt(rx), fmt(e), fmt(x + w),
                      fmt(y + e), fmt(x + w), fmt(y + h - e), fmt(rx), fmt(e),
                      fmt(x), fmt(y + h - e), style))
        out.append('<path d="M %s %s A %s %s 0 0 0 %s %s" %s/>'
                   % (fmt(x), fmt(y + e), fmt(rx), fmt(e), fmt(x + w),
                      fmt(y + e), sans_fond))
    elif f in ("document", "documents"):
        a = c.VAGUE_DOC

        def doc(xx, yy, ww, hh):
            return ('<path d="M %s %s L %s %s L %s %s C %s %s %s %s %s %s Z" '
                    '%s/>' % (fmt(xx), fmt(yy), fmt(xx + ww), fmt(yy),
                              fmt(xx + ww), fmt(yy + hh - a),
                              fmt(xx + ww * 0.75), fmt(yy + hh - 3 * a),
                              fmt(xx + ww * 0.25), fmt(yy + hh + a),
                              fmt(xx), fmt(yy + hh - a), style))
        if f == "document":
            out.append(doc(x, y, w, h))
        else:
            d = c.DECALAGE_DOCS
            for k in (2, 1, 0):
                out.append(doc(x + k * d, y + (2 - k) * d, w - 2 * d,
                               h - 2 * d))
    elif f == "annotation":
        k = c.CROCHET_ANNOT
        if n.cote == "droite":
            d = "M %s %s L %s %s L %s %s L %s %s" % (
                fmt(x + w - k), fmt(y), fmt(x + w), fmt(y), fmt(x + w),
                fmt(y + h), fmt(x + w - k), fmt(y + h))
        else:
            d = "M %s %s L %s %s L %s %s L %s %s" % (
                fmt(x + k), fmt(y), fmt(x), fmt(y), fmt(x), fmt(y + h),
                fmt(x + k), fmt(y + h))
        out.append('<path d="%s" %s/>' % (d, sans_fond))
    elif f == "parallele":
        out.append('<path d="M %s %s L %s %s M %s %s L %s %s" %s/>'
                   % (fmt(x), fmt(y), fmt(x + w), fmt(y), fmt(x), fmt(y + h),
                      fmt(x + w), fmt(y + h), sans_fond))
    else:
        out.append('<path d="%s" %s/>'
                   % (chemin_polygone(c.contour(f, x, y, w, h)), style))
    return out


def dessiner_couloir(k, pal):
    trait = attrs_couleur("stroke", pal["forme-trait"])
    base = (k["y"] + ENTETE_COULOIR / 2
            + (c.MONTANTE - c.DESCENDANTE) / 2 * c.TAILLE_TEXTE)
    return [
        '<g class="couloir" data-id="%s" data-x="%s" data-y="%s" data-w="%s" '
        'data-h="%s" data-entete="%s">'
        % (echapper(k["id"]), fmt(k["x"]), fmt(k["y"]), fmt(k["w"]),
           fmt(k["h"]), fmt(ENTETE_COULOIR)),
        '<rect x="%s" y="%s" width="%s" height="%s" fill="none" %s '
        'stroke-width="1"/>' % (fmt(k["x"]), fmt(k["y"]), fmt(k["w"]),
                                fmt(k["h"]), trait),
        '<rect x="%s" y="%s" width="%s" height="%s" %s %s stroke-width="1"/>'
        % (fmt(k["x"]), fmt(k["y"]), fmt(k["w"]), fmt(ENTETE_COULOIR),
           attrs_couleur("fill", pal["forme-fond"]), trait),
        '<text class="titre-couloir" x="%s" y="%s" font-family="%s" '
        'font-size="%s" font-weight="600" text-anchor="middle" %s>%s</text>'
        % (fmt(k["x"] + k["w"] / 2), fmt(base), echapper(c.POLICE),
           fmt(c.TAILLE_TEXTE), attrs_couleur("fill", pal["texte"]),
           echapper(k["titre"])),
        '</g>']


def emettre(modele, noeuds, liens, annots, largeur, hauteur, pal, variante,
            couloirs=()):
    titre = modele["titre"].strip()
    desc = (modele.get("description") or modele["alt"]).strip()
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" '
         'width="%s" height="%s" role="img" '
         'aria-labelledby="titre description" data-logigramme="1" '
         'data-variante="%s">' % (fmt(largeur), fmt(hauteur), fmt(largeur),
                                  fmt(hauteur), variante),
         '<title id="titre">%s</title>' % echapper(titre),
         '<desc id="description">%s</desc>' % echapper(desc),
         '<defs>']
    etats = sorted({l["etat"] for l in liens})
    for e in etats:
        coul = pal["lien" if e == "neutre" else e + "-lien"]
        L.append('<marker id="m-%s" viewBox="0 0 10 10" refX="9" refY="5" '
                 'markerUnits="userSpaceOnUse" markerWidth="9" '
                 'markerHeight="9" orient="auto-start-reverse">'
                 '<path d="M 0 0 L 10 5 L 0 10 z" %s/></marker>'
                 % (e, attrs_couleur("fill", coul)))
    L.append('</defs>')
    L.append('<rect width="%s" height="%s" %s/>'
             % (fmt(largeur), fmt(hauteur), attrs_couleur("fill", pal["fond"])))
    police = echapper(c.POLICE)
    if modele.get("titre_visible"):
        L.append('<text class="titre" x="%s" y="%s" font-family="%s" '
                 'font-size="%s" font-weight="600" %s>%s</text>'
                 % (fmt(MARGE), fmt(MARGE + c.TAILLE_TITRE * c.MONTANTE),
                    police, fmt(c.TAILLE_TITRE),
                    attrs_couleur("fill", pal["texte"]), echapper(titre)))
    for k in couloirs:
        L += dessiner_couloir(k, pal)

    for a in annots:
        coul = pal["texte-discret"]
        L.append('<g class="lien annotation" data-de="%s" data-vers="%s">'
                 '<path d="M %s %s L %s %s" %s fill="none" stroke-width="1.2" '
                 'stroke-dasharray="4 3"/></g>'
                 % (a["de"], a["vers"], fmt(a["pts"][0][0]),
                    fmt(a["pts"][0][1]), fmt(a["pts"][1][0]),
                    fmt(a["pts"][1][1]), attrs_couleur("stroke", coul)))

    for l in liens:
        coul = pal["lien" if l["etat"] == "neutre" else l["etat"] + "-lien"]
        d = "M " + " L ".join("%s %s" % (fmt(x), fmt(y)) for x, y in l["pts"])
        marque = ' marker-end="url(#m-%s)"' % l["etat"] if l["pointe"] else ""
        L.append('<g class="lien" data-de="%s" data-vers="%s">'
                 % (echapper(l["de"]), echapper(l["vers"])))
        L.append('<path d="%s" %s fill="none" stroke-width="1.5"%s/>'
                 % (d, attrs_couleur("stroke", coul), marque))
        if l.get("etiquette"):
            ex, ey, ancre, ew = l["etiq_pos"]
            x0, y0, x1, y1 = c.boite_glyphes(ex, ey, ew, c.TAILLE_ETIQUETTE,
                                             ancre)
            L.append('<rect x="%s" y="%s" width="%s" height="%s" %s/>'
                     % (fmt(x0 - 2), fmt(y0 - 1), fmt(x1 - x0 + 4),
                        fmt(y1 - y0 + 2), attrs_couleur("fill", pal["fond"])))
            L.append('<text class="etiquette" x="%s" y="%s" font-family="%s" '
                     'font-size="%s" text-anchor="%s" %s>%s</text>'
                     % (fmt(ex), fmt(ey), police, fmt(c.TAILLE_ETIQUETTE),
                        ancre, attrs_couleur("fill", pal["texte-discret"]),
                        echapper(l["etiquette"])))
        L.append('</g>')

    for n in noeuds:
        attrs = ('class="noeud" data-id="%s" data-forme="%s" data-x="%s" '
                 'data-y="%s" data-w="%s" data-h="%s"'
                 % (echapper(n.id), n.forme, fmt(n.x), fmt(n.y), fmt(n.w),
                    fmt(n.h)))
        if n.cote:
            attrs += ' data-cote="%s"' % n.cote
        if "couloir" in n.d:
            attrs += ' data-couloir="%s"' % echapper(n.d["couloir"])
        L.append('<g %s>' % attrs)
        L += dessiner_forme(n, pal)
        if n.lignes:
            gras = n.forme in ("connecteur", "renvoi-page")
            coul = pal["texte-discret" if n.forme == "annotation" else "texte"]
            L.append('<text font-family="%s" font-size="%s" text-anchor="%s"%s '
                     '%s>' % (police, fmt(c.TAILLE_TEXTE), n.ancre,
                              ' font-weight="600"' if gras else "",
                              attrs_couleur("fill", coul)))
            for t, x, y in n.lignes:
                L.append('<tspan x="%s" y="%s">%s</tspan>'
                         % (fmt(x), fmt(y), echapper(t)))
            L.append('</text>')
        L.append('</g>')
    L.append('</svg>')
    return "\n".join(L) + "\n"


def snippet(modele, chemin):
    base = chemin.rstrip("/") + "/" if chemin else ""
    alt = " ".join(modele["alt"].split()).replace('"', "&quot;")
    return ('<picture>\n'
            '  <source media="(prefers-color-scheme: dark)" '
            'srcset="%s%s-dark.svg">\n'
            '  <img alt="%s" src="%s%s.svg">\n'
            '</picture>\n' % (base, modele["id"], alt, base, modele["id"]))


# --- Programme -----------------------------------------------------------------

def tracer(modele, palette):
    valider(modele)
    grille = modele.get("grille", {})
    cw = float(grille.get("colonne", GRILLE_DEFAUT[0]))
    rh = float(grille.get("rangee", GRILLE_DEFAUT[1]))
    noeuds = [Noeud(d, cw, rh) for d in modele["noeuds"]]
    par_id = {n.id: n for n in noeuds}
    rang = {d["id"]: d["rang"] for d in modele["noeuds"]}
    erreurs = []
    for n in noeuds:
        try:
            dimensionner(n, cw, rh)
        except ModeleInvalide as e:
            erreurs += e.args[0]
    if erreurs:
        raise ModeleInvalide(erreurs)

    def grille_px(col, rg):
        return (col * cw + cw / 2, rg * rh + rh / 2)

    pointes_iso = modele.get("pointes", "toutes") == "iso"
    liens = []
    for l in modele.get("liens", []):
        a, b = par_id[l["de"]], par_id[l["vers"]]
        pts, s1 = router(a, b, l, rang, grille_px)
        dx = pts[-1][0] - pts[-2][0]
        dy = pts[-1][1] - pts[-2][1]
        standard = (dx == 0 and dy > 0) or (dy == 0 and dx > 0)
        entree = {"de": a.id, "vers": b.id, "pts": pts,
                  "etat": l.get("etat", "neutre"),
                  "pointe": not (pointes_iso and standard),
                  "etiquette": (l.get("etiquette") or "").strip()}
        if entree["etiquette"]:
            entree["etiq_pos"] = placer_etiquette(pts, entree["etiquette"])
        liens.append(entree)

    annots = []
    for n in noeuds:
        if n.forme != "annotation":
            continue
        cible = par_id[n.d["cible"]]
        if cible.ccx > n.ccx:
            n.cote = "droite"
            debut = (n.x + n.w, n.y + n.h / 2)
            fin = port(cible, "gauche")
        else:
            n.cote = "gauche"
            debut = (n.x, n.y + n.h / 2)
            fin = port(cible, "droite")
        annots.append({"de": n.id, "vers": cible.id, "pts": [debut, fin]})

    xs, ys = [], []
    for n in noeuds:
        xs += [n.x, n.x + n.w]
        ys += [n.y, n.y + n.h]
    for l in liens:
        for x, y in l["pts"]:
            xs += [x - 6, x + 6]
            ys += [y - 6, y + 6]
        if l["etiquette"]:
            ex, ey, ancre, ew = l["etiq_pos"]
            b = c.boite_glyphes(ex, ey, ew, c.TAILLE_ETIQUETTE, ancre)
            xs += [b[0] - 2, b[2] + 2]
            ys += [b[1] - 1, b[3] + 1]
    couloirs, debut = [], 0
    for k in modele.get("couloirs", []):
        n_cols = k.get("cols", 1)
        couloirs.append({"id": k["id"], "titre": k["titre"].strip(),
                         "x": debut * cw, "w": n_cols * cw})
        debut += n_cols
        if c.largeur_texte(couloirs[-1]["titre"], c.TAILLE_TEXTE, True) \
                > n_cols * cw - 2 * c.MARGE_TRACE:
            erreurs.append("couloir %s : titre trop long pour sa largeur. Le "
                           "raccourcir, ou augmenter cols ou grille.colonne."
                           % k["id"])
    if erreurs:
        raise ModeleInvalide(erreurs)
    if couloirs:
        # L'en-tête se pose au-dessus de tout le contenu : aucun lien ni
        # symbole ne peut le recouvrir.
        haut = min(ys + [0.0]) - ENTETE_COULOIR
        bas = max(ys + [(max(rang.values()) + 1) * rh])
        for k in couloirs:
            k["y"], k["h"] = haut, bas - haut
            xs += [k["x"], k["x"] + k["w"]]
            ys += [k["y"], k["y"] + k["h"]]
    entete = ENTETE if modele.get("titre_visible") else 0.0
    dx = MARGE - min(xs)
    dy = MARGE + entete - min(ys)
    largeur = math.ceil(max(xs) - min(xs) + 2 * MARGE)
    hauteur = math.ceil(max(ys) - min(ys) + 2 * MARGE + entete)
    if modele.get("titre_visible"):
        largeur = max(largeur, math.ceil(
            2 * MARGE + c.largeur_texte(modele["titre"], c.TAILLE_TITRE,
                                        True)))
    for n in noeuds:
        n.decaler(dx, dy)
    for k in couloirs:
        k["x"] += dx
        k["y"] += dy
    for l in liens + annots:
        l["pts"] = [(x + dx, y + dy) for x, y in l["pts"]]
        if l.get("etiq_pos"):
            ex, ey, ancre, ew = l["etiq_pos"]
            l["etiq_pos"] = (ex + dx, ey + dy, ancre, ew)

    sorties = {}
    for variante in ("light", "dark"):
        pal = c.couleurs_variante(palette, variante)
        sorties[variante] = emettre(modele, noeuds, liens, annots, largeur,
                                    hauteur, pal, variante, couloirs)
    return sorties


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("modele", help="fichier JSON du logigramme")
    p.add_argument("--sortie", required=True,
                   help="dossier où écrire les deux SVG")
    p.add_argument("--chemin", default=None,
                   help="chemin des SVG vu depuis le fichier Markdown "
                        "(défaut : champ chemin du modèle, sinon assets)")
    p.add_argument("--palette", default=None)
    p.add_argument("--remplacer", action="store_true",
                   help="autorise l'écrasement de SVG existants")
    a = p.parse_args()

    try:
        with open(a.modele, encoding="utf-8") as f:
            modele = json.load(f)
    except (OSError, ValueError) as e:
        print("modèle illisible : %s" % e, file=sys.stderr)
        return 2
    try:
        palette = c.charger_palette(a.palette)
        sorties = tracer(modele, palette)
    except ModeleInvalide as e:
        print("modèle invalide :", file=sys.stderr)
        for ligne in e.args[0]:
            print("  - " + ligne, file=sys.stderr)
        return 2
    except (OSError, ValueError) as e:
        print("erreur : %s" % e, file=sys.stderr)
        return 2

    if not os.path.isdir(a.sortie):
        print("dossier de sortie absent : %s" % a.sortie, file=sys.stderr)
        return 2
    cibles = {"light": os.path.join(a.sortie, modele["id"] + ".svg"),
              "dark": os.path.join(a.sortie, modele["id"] + "-dark.svg")}
    existants = [f for f in cibles.values() if os.path.exists(f)]
    if existants and not a.remplacer:
        for f in existants:
            print("existe déjà : %s" % f, file=sys.stderr)
        print("Relancer avec --remplacer si l'écrasement est voulu.",
              file=sys.stderr)
        return 3
    for variante, chemin in cibles.items():
        with open(chemin, "w", encoding="utf-8", newline="\n") as f:
            f.write(sorties[variante])
        print("écrit : %s" % chemin, file=sys.stderr)
    chemin_md = a.chemin if a.chemin is not None else modele.get("chemin",
                                                                  "assets")
    sys.stdout.write(snippet(modele, chemin_md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
