#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifie des logigrammes SVG et les snippets Markdown qui les appellent.

Signale, ne corrige jamais : aucun fichier n'est modifié.

Pour chaque schéma, les deux jumeaux nom.svg et nom-dark.svg sont vérifiés
ensemble, quel que soit celui qui est nommé : présence, accessibilité,
appartenance des couleurs à la palette de la variante, parité de contenu.
Pour un SVG produit par tracer.py, s'ajoutent le débordement du texte hors
de sa forme, les liens qui traversent une forme, les règles ISO 5807 et,
si le schéma a des couloirs, l'appartenance des nœuds et la lisibilité des
en-têtes.

Usage :
    python scripts/verifier.py SCHEMA.svg [...] [--md FICHIER.md ...]
        [--palette PALETTE] [--strict]

Codes de sortie : 0 aucun signal bloquant, 1 au moins une erreur (ou un
avertissement avec --strict), 2 usage incorrect.
Bibliothèque standard seule. Python 3.9 ou plus.
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun as c  # noqa: E402

NS = "{http://www.w3.org/2000/svg}"
ATTRS_COULEUR = ("fill", "stroke", "stop-color", "flood-color",
                 "lighting-color", "color")
ATTRS_HORS_PARITE = {"fill", "stroke", "fill-opacity", "stroke-opacity",
                     "stop-color", "stop-opacity", "data-variante"}
DECL_CSS = re.compile(r"(fill|stroke|stop-color|flood-color|color)\s*:\s*"
                      r"([^;}\s]+)")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
MOTS_NEUTRES = {"none", "transparent"}


class Rapport:
    def __init__(self):
        self.signaux = []

    def erreur(self, ou, msg):
        self.signaux.append(("ERREUR", ou, msg))

    def avert(self, ou, msg):
        self.signaux.append(("AVERTISSEMENT", ou, msg))

    def info(self, ou, msg):
        self.signaux.append(("INFO", ou, msg))

    def compte(self, niveau):
        return sum(1 for s in self.signaux if s[0] == niveau)


def local(tag):
    return tag.split("}", 1)[-1] if isinstance(tag, str) else ""


def nombre(el, nom, defaut=None):
    v = el.get(nom)
    if v is None:
        return defaut
    try:
        return float(re.sub(r"px$", "", v.strip()))
    except ValueError:
        return defaut


# --- Couleurs et ressources ---------------------------------------------------

def verifier_couleur(valeur, admises, ou, rap, contexte):
    v = valeur.strip()
    if v.lower() in MOTS_NEUTRES or v.startswith("url(#"):
        return
    if v.startswith("var("):
        rap.erreur(ou, "%s : variable CSS %s, non résolue dans un SVG servi "
                   "par img. Poser la valeur du jeton." % (contexte, v))
        return
    if v.lower() == "currentcolor":
        rap.avert(ou, "%s : currentColor vaut noir hors d'un document HTML"
                  % contexte)
        return
    if not HEX.match(v):
        rap.erreur(ou, "%s : couleur %r hors palette (ni jeton ni hex)"
                   % (contexte, v))
        return
    hexa, _ = c.normaliser_hex(v)
    if hexa not in admises:
        rap.erreur(ou, "%s : %s n'est la valeur d'aucun jeton de la feuille "
                   "de cette variante" % (contexte, hexa))


def verifier_ressources(racine, brut, admises, ou, rap):
    for el in racine.iter():
        tag = local(el.tag)
        for nom in ATTRS_COULEUR:
            if el.get(nom) is not None:
                verifier_couleur(el.get(nom), admises, ou, rap,
                                 "<%s %s>" % (tag, nom))
        style = el.get("style")
        if style:
            for prop, val in DECL_CSS.findall(style):
                verifier_couleur(val, admises, ou, rap,
                                 "<%s style %s>" % (tag, prop))
        if tag == "style" and el.text:
            if "@import" in el.text or "@font-face" in el.text:
                rap.erreur(ou, "<style> charge une ressource externe, "
                           "bloquée dans un SVG servi par img")
            for prop, val in DECL_CSS.findall(el.text):
                verifier_couleur(val, admises, ou, rap, "<style> %s" % prop)
        for nom in ("href", "{http://www.w3.org/1999/xlink}href"):
            ref = el.get(nom)
            if ref and not ref.startswith("#") and not ref.startswith("data:"):
                rap.erreur(ou, "<%s> référence une ressource externe %s, "
                           "non chargée dans un SVG servi par img" % (tag, ref))


# --- Accessibilité ------------------------------------------------------------

def verifier_accessibilite(racine, ou, rap):
    if local(racine.tag) != "svg":
        rap.erreur(ou, "l'élément racine n'est pas svg")
        return None
    for nom in ("viewBox", "width", "height"):
        if not racine.get(nom):
            rap.erreur(ou, "attribut %s absent de la racine" % nom)
    if racine.get("role") != "img":
        rap.erreur(ou, 'role="img" absent de la racine')
    titre = racine.find(NS + "title")
    desc = racine.find(NS + "desc")
    if titre is None or not (titre.text or "").strip():
        rap.erreur(ou, "title absent ou vide")
    if desc is None or not (desc.text or "").strip():
        rap.erreur(ou, "desc absent ou vide")
    ids = (racine.get("aria-labelledby") or "").split()
    for el, nom in ((titre, "title"), (desc, "desc")):
        if el is not None and el.get("id") not in ids:
            rap.erreur(ou, "%s non référencé par aria-labelledby" % nom)
    return (titre.text or "").strip() if titre is not None else None


# --- Parité -------------------------------------------------------------------

def empreinte(racine):
    lignes = []
    for el in racine.iter():
        attrs = sorted((k, v) for k, v in el.attrib.items()
                       if k not in ATTRS_HORS_PARITE)
        texte = (el.text or "").strip()
        if local(el.tag) == "style":
            texte = DECL_CSS.sub(lambda m: m.group(1) + ":*", texte)
        style = [(k, DECL_CSS.sub(lambda m: m.group(1) + ":*", v))
                 if k == "style" else (k, v) for k, v in attrs]
        lignes.append((local(el.tag), tuple(style), texte))
    return lignes


def verifier_parite(r_light, r_dark, ou, rap):
    a, b = empreinte(r_light), empreinte(r_dark)
    if len(a) != len(b):
        rap.erreur(ou, "les deux variantes n'ont pas le même nombre "
                   "d'éléments (%d contre %d)" % (len(a), len(b)))
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            rap.erreur(ou, "variantes divergentes à l'élément %d : <%s> "
                       "light, <%s> dark. Seules les couleurs peuvent "
                       "différer." % (i, x[0], y[0]))
            return


# --- Géométrie et règles ISO, SVG produits par tracer.py ----------------------

def chemin_points(d):
    jetons = re.findall(r"[MLml]|-?\d+(?:\.\d+)?", d or "")
    segments, courant, cmd, nums = [], [], None, []
    for j in jetons:
        if j in "MLml":
            cmd = j
            continue
        nums.append(float(j))
        if len(nums) == 2:
            if cmd in ("M", "m") and courant:
                segments.append(courant)
                courant = []
            courant.append(tuple(nums))
            nums = []
    if courant:
        segments.append(courant)
    return segments


def verifier_geometrie(racine, ou, rap):
    vb = [float(v) for v in (racine.get("viewBox") or "0 0 0 0").split()]
    cadre = (vb[0], vb[1], vb[0] + vb[2], vb[1] + vb[3])
    noeuds, liens, couloirs = {}, [], {}

    for g in racine.iter(NS + "g"):
        classes = (g.get("class") or "").split()
        if "couloir" in classes:
            kid = g.get("data-id")
            dims = [nombre(g, a) for a in ("data-x", "data-y", "data-w",
                                           "data-h", "data-entete")]
            if None in dims:
                rap.erreur(ou, "couloir %s : data-x, data-y, data-w, data-h "
                           "ou data-entete manquant" % kid)
                continue
            x, y, w, h, e = dims
            titre = g.find(NS + "text")
            contenu = "".join(titre.itertext()).strip() \
                if titre is not None else ""
            boite = None
            if contenu:
                taille = nombre(titre, "font-size", c.TAILLE_TEXTE)
                boite = c.boite_glyphes(
                    nombre(titre, "x", 0.0), nombre(titre, "y", 0.0),
                    c.largeur_texte(contenu, taille,
                                    titre.get("font-weight") in
                                    ("600", "700", "bold")),
                    taille, titre.get("text-anchor", "start"))
            couloirs[kid] = {"boite": (x, y, x + w, y + h), "corps": y + e,
                             "titre": contenu, "boite_titre": boite}
            if boite is None:
                rap.erreur(ou, "couloir %s : en-tête sans titre" % kid)
            elif not c.boite_dans_zone(c._rect(x, y, w, e), boite,
                                       c.MARGE_LINT):
                rap.erreur(ou, "couloir %s : le titre « %s » déborde de son "
                           "en-tête" % (kid, contenu))
        elif "noeud" in classes:
            nid, forme = g.get("data-id"), g.get("data-forme")
            if forme not in c.FORMES:
                rap.erreur(ou, "nœud %s : forme %r hors vocabulaire ISO 5807 "
                           "du skill" % (nid, forme))
                continue
            x, y = nombre(g, "data-x"), nombre(g, "data-y")
            w, h = nombre(g, "data-w"), nombre(g, "data-h")
            if None in (x, y, w, h):
                rap.erreur(ou, "nœud %s : data-x, data-y, data-w ou data-h "
                           "manquant" % nid)
                continue
            noeuds[nid] = {"forme": forme, "boite": (x, y, x + w, y + h),
                           "texte": "", "couloir": g.get("data-couloir")}
            if (x < cadre[0] or y < cadre[1] or x + w > cadre[2]
                    or y + h > cadre[3]):
                rap.erreur(ou, "nœud %s : forme hors du cadre du SVG" % nid)
            zone = c.zone_texte(forme, x, y, w, h)
            for texte in g.iter(NS + "text"):
                taille = nombre(texte, "font-size", c.TAILLE_TEXTE)
                ancre = texte.get("text-anchor", "start")
                gras = texte.get("font-weight") in ("600", "700", "bold")
                tspans = list(texte.iter(NS + "tspan")) or [texte]
                for t in tspans:
                    contenu = "".join(t.itertext()).strip() if t is texte \
                        else (t.text or "").strip()
                    if not contenu:
                        continue
                    noeuds[nid]["texte"] += " " + contenu
                    tx = nombre(t, "x", nombre(texte, "x", 0.0))
                    ty = nombre(t, "y", nombre(texte, "y", 0.0))
                    boite = c.boite_glyphes(
                        tx, ty, c.largeur_texte(contenu, taille, gras),
                        taille, ancre)
                    if not c.boite_dans_zone(zone, boite, c.MARGE_LINT):
                        rap.erreur(ou, "nœud %s : la ligne « %s » déborde de "
                                   "la forme %s" % (nid, contenu, forme))
        elif "lien" in classes:
            pts = []
            for p in g.iter(NS + "path"):
                pts += chemin_points(p.get("d"))
            etiquettes = []
            for t in g.iter(NS + "text"):
                contenu = "".join(t.itertext()).strip()
                taille = nombre(t, "font-size", c.TAILLE_ETIQUETTE)
                b = c.boite_glyphes(nombre(t, "x", 0.0), nombre(t, "y", 0.0),
                                    c.largeur_texte(contenu, taille), taille,
                                    t.get("text-anchor", "start"))
                etiquettes.append((contenu, b))
            liens.append({"de": g.get("data-de"), "vers": g.get("data-vers"),
                          "annotation": "annotation" in classes,
                          "segments": pts, "etiquettes": etiquettes})

    for l in liens:
        for bout in ("de", "vers"):
            if l[bout] not in noeuds:
                rap.erreur(ou, "lien %s → %s : extrémité %s inconnue"
                           % (l["de"], l["vers"], l[bout]))
        for seg in l["segments"]:
            for a, b in zip(seg, seg[1:]):
                for nid, n in noeuds.items():
                    if nid in (l["de"], l["vers"]):
                        continue
                    x0, y0, x1, y1 = n["boite"]
                    if c.segment_coupe_boite(a, b, (x0 + 1, y0 + 1,
                                                    x1 - 1, y1 - 1)):
                        rap.avert(ou, "lien %s → %s : traverse le nœud %s. "
                                  "Ajouter via ou couloir dans le modèle."
                                  % (l["de"], l["vers"], nid))
                        break
        for contenu, b in l["etiquettes"]:
            for nid, n in noeuds.items():
                if c.boites_se_chevauchent(b, n["boite"]):
                    rap.avert(ou, "étiquette « %s » du lien %s → %s : "
                              "recouvre le nœud %s" % (contenu, l["de"],
                                                       l["vers"], nid))
            if (b[0] < cadre[0] or b[1] < cadre[1] or b[2] > cadre[2]
                    or b[3] > cadre[3]):
                rap.erreur(ou, "étiquette « %s » hors du cadre" % contenu)

    if couloirs:
        verifier_couloirs(couloirs, noeuds, liens, ou, rap)
    verifier_iso(noeuds, [l for l in liens if not l["annotation"]],
                 [l for l in liens if l["annotation"]], ou, rap)


def verifier_couloirs(couloirs, noeuds, liens, ou, rap):
    peuples = set()
    for nid, n in noeuds.items():
        kid = n["couloir"]
        if kid is None:
            rap.erreur(ou, "nœud %s : sans couloir, alors que le schéma en "
                       "déclare" % nid)
            continue
        if kid not in couloirs:
            rap.erreur(ou, "nœud %s : couloir %s non déclaré" % (nid, kid))
            continue
        peuples.add(kid)
        x0, y0, x1, y1 = n["boite"]
        k = couloirs[kid]
        if (x0 < k["boite"][0] - 0.5 or x1 > k["boite"][2] + 0.5
                or y0 < k["corps"] - 0.5 or y1 > k["boite"][3] + 0.5):
            rap.erreur(ou, "nœud %s : hors de son couloir %s" % (nid, kid))
    for kid, k in couloirs.items():
        if kid not in peuples:
            rap.avert(ou, "couloir %s : déclaré sans nœud" % kid)
        b = k["boite_titre"]
        if b is None:
            continue
        for nid, n in noeuds.items():
            if c.boites_se_chevauchent(b, n["boite"]):
                rap.erreur(ou, "couloir %s : le nœud %s recouvre le titre de "
                           "l'en-tête" % (kid, nid))
        for l in liens:
            coupe = any(c.segment_coupe_boite(a, z, b)
                        for seg in l["segments"] for a, z in zip(seg, seg[1:]))
            if coupe or any(c.boites_se_chevauchent(b, eb)
                            for _, eb in l["etiquettes"]):
                rap.erreur(ou, "couloir %s : le lien %s → %s recouvre le titre "
                           "de l'en-tête" % (kid, l["de"], l["vers"]))


def verifier_iso(noeuds, liens, annots, ou, rap):
    sorties = {n: [] for n in noeuds}
    entrees = {n: [] for n in noeuds}
    for l in liens:
        if l["de"] in sorties:
            sorties[l["de"]].append(l)
        if l["vers"] in entrees:
            entrees[l["vers"]].append(l)
    annotes = {l["de"] for l in annots}

    if not any(n["forme"] == "terminal" for n in noeuds.values()):
        rap.avert(ou, "aucun terminal : début et fin du processus absents")
    for nid, n in noeuds.items():
        f, s, e = n["forme"], sorties[nid], entrees[nid]
        if f == "annotation":
            if nid not in annotes:
                rap.avert(ou, "annotation %s : reliée à aucun symbole" % nid)
            continue
        if not s and not e:
            rap.avert(ou, "nœud %s : isolé, aucun lien" % nid)
        if f == "terminal" and s and e:
            rap.avert(ou, "terminal %s : à la fois entrée et sortie de flux ; "
                      "un terminal ouvre ou ferme" % nid)
        if f == "decision":
            if len(s) < 2:
                rap.avert(ou, "décision %s : %d sortie, au moins deux "
                          "attendues" % (nid, len(s)))
            if any(not l["etiquettes"] for l in s):
                rap.avert(ou, "décision %s : sortie sans étiquette ; nommer "
                          "chaque issue (oui, non...)" % nid)
        elif f == "parallele":
            if not ((len(e) == 1 and len(s) >= 2)
                    or (len(e) >= 2 and len(s) == 1)):
                rap.avert(ou, "mode parallèle %s : ni fourche (1 entrée, 2 "
                          "sorties ou plus) ni jointure (l'inverse)" % nid)
        elif len(s) > 1 and f not in ("connecteur", "renvoi-page"):
            rap.avert(ou, "nœud %s : %d sorties hors décision ; un "
                      "branchement passe par un losange" % (nid, len(s)))
        if f == "connecteur" and len(n["texte"].strip()) > 3:
            rap.avert(ou, "connecteur %s : libellé long, une lettre ou un "
                      "numéro attendu" % nid)
    paires = {}
    for nid, n in noeuds.items():
        if n["forme"] == "connecteur":
            paires.setdefault(n["texte"].strip(), []).append(nid)
    for lib, ids in paires.items():
        if len(ids) < 2:
            rap.avert(ou, "connecteur « %s » : sans connecteur apparié"
                      % lib)


# --- Snippets Markdown --------------------------------------------------------

PICTURE = re.compile(r"<picture>(.*?)</picture>", re.S | re.I)
SOURCE = re.compile(r"<source\b([^>]*)>", re.I)
IMG = re.compile(r"<img\b([^>]*)>", re.I)
ATTR = re.compile(r'([a-zA-Z-]+)\s*=\s*"([^"]*)"')


def verifier_md(chemin, rap):
    ou = chemin
    try:
        with open(chemin, encoding="utf-8") as f:
            texte = f.read()
    except OSError as e:
        rap.erreur(ou, "illisible : %s" % e)
        return
    dossier = os.path.dirname(os.path.abspath(chemin))
    blocs = PICTURE.findall(texte)
    if not blocs:
        rap.info(ou, "aucun élément picture")
    for bloc in blocs:
        img = IMG.search(bloc)
        src = SOURCE.search(bloc)
        if not img:
            rap.erreur(ou, "picture sans img")
            continue
        ai = dict(ATTR.findall(img.group(1)))
        fichier = ai.get("src", "")
        lieu = "%s [%s]" % (ou, fichier or "?")
        alt = " ".join(ai.get("alt", "").split())
        if not alt:
            rap.erreur(lieu, "alt absent ou vide")
        elif len(alt) < 60:
            rap.avert(lieu, "alt de %d caractères : décrit-il ce que le "
                      "schéma montre ?" % len(alt))
        if not src:
            rap.erreur(lieu, "source dark absente")
        else:
            asrc = dict(ATTR.findall(src.group(1)))
            if "prefers-color-scheme: dark" not in asrc.get("media", ""):
                rap.erreur(lieu, "source sans media prefers-color-scheme: "
                           "dark")
            attendu = re.sub(r"\.svg$", "-dark.svg", fichier)
            if asrc.get("srcset") != attendu:
                rap.erreur(lieu, "srcset %r, jumeau attendu %r"
                           % (asrc.get("srcset"), attendu))
        cible = os.path.join(dossier, fichier)
        if fichier.startswith(("http:", "https:")):
            continue
        if not os.path.isfile(cible):
            rap.erreur(lieu, "fichier introuvable depuis le Markdown")
            continue
        try:
            titre = ET.parse(cible).getroot().find(NS + "title")
        except ET.ParseError:
            continue
        if titre is not None and alt and \
                " ".join((titre.text or "").split()).lower() == alt.lower():
            rap.erreur(lieu, "alt identique au titre : il doit décrire le "
                       "contenu, pas le nommer")


# --- Programme -----------------------------------------------------------------

def jumeaux(chemin):
    if chemin.endswith("-dark.svg"):
        return chemin[:-9] + ".svg", chemin
    return chemin[:-4] + ".svg" if chemin.endswith(".svg") else chemin, \
        chemin[:-4] + "-dark.svg"


def verifier_paire(light, dark, palette, rap):
    racines = {}
    for variante, chemin in (("light", light), ("dark", dark)):
        if not os.path.isfile(chemin):
            rap.erreur(chemin, "jumeau %s absent" % variante)
            continue
        with open(chemin, encoding="utf-8") as f:
            brut = f.read()
        try:
            racine = ET.fromstring(brut)
        except ET.ParseError as e:
            rap.erreur(chemin, "XML invalide : %s" % e)
            continue
        racines[variante] = racine
        verifier_accessibilite(racine, chemin, rap)
        verifier_ressources(racine, brut, c.teintes_admises(palette, variante),
                            chemin, rap)
        if racine.get("data-logigramme"):
            verifier_geometrie(racine, chemin, rap)
        else:
            rap.info(chemin, "SVG non produit par tracer.py : débordement "
                     "et règles ISO non vérifiés")
    if len(racines) == 2:
        verifier_parite(racines["light"], racines["dark"],
                        "%s / %s" % (os.path.basename(light),
                                     os.path.basename(dark)), rap)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("svg", nargs="*", help="un fichier de chaque paire suffit")
    p.add_argument("--md", nargs="*", default=[],
                   help="fichiers Markdown dont les picture sont à vérifier")
    p.add_argument("--palette", default=None)
    p.add_argument("--strict", action="store_true",
                   help="les avertissements font échouer")
    a = p.parse_args()
    if not a.svg and not a.md:
        p.print_usage(sys.stderr)
        return 2
    palette = c.charger_palette(a.palette)
    rap = Rapport()
    vues = []
    for chemin in a.svg:
        paire = jumeaux(chemin)
        if paire not in vues:
            vues.append(paire)
            verifier_paire(paire[0], paire[1], palette, rap)
    for chemin in a.md:
        verifier_md(chemin, rap)

    vus = {}
    for signal in rap.signaux:
        vus[signal] = vus.get(signal, 0) + 1
    for (niveau, ou, msg), n in vus.items():
        print("%-13s %s : %s%s" % (niveau, ou, msg,
                                   " (x%d)" % n if n > 1 else ""))
    ne, na = rap.compte("ERREUR"), rap.compte("AVERTISSEMENT")
    print("%d erreur(s), %d avertissement(s)" % (ne, na))
    return 1 if ne or (a.strict and na) else 0


if __name__ == "__main__":
    sys.exit(main())
