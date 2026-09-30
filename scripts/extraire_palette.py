#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrait les jetons de couleur des feuilles de style GitHub light et dark.

Produit assets/palette.json, lu par tracer.py et verifier.py : les jetons des
rôles employés par le traceur, et l'ensemble des teintes distinctes de chaque
feuille, contre lequel le lint vérifie toute couleur. Seuls les jetons dont la
valeur, une fois les var() résolues, est une couleur hexadécimale comptent. La
première occurrence de chaque jeton fait foi : les feuilles GitHub répètent le
même bloc sous une requête média, avec les mêmes valeurs.

Usage :
    python scripts/extraire_palette.py --light github-light.css \
        --dark github-dark.css [--sortie assets/palette.json] [--remplacer]

Bibliothèque standard seule. Python 3.9 ou plus.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun as c  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE_DEFAUT = os.path.join(os.path.dirname(ICI), "assets", "palette.json")

DECLARATION = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+);")
VARIABLE = re.compile(r"^var\(\s*(--[A-Za-z0-9_-]+)\s*\)$")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def lire_jetons(chemin):
    with open(chemin, encoding="utf-8") as f:
        texte = f.read()
    texte = re.sub(r"/\*.*?\*/", "", texte, flags=re.S)
    brut = {}
    for nom, valeur in DECLARATION.findall(texte):
        if nom not in brut:
            brut[nom] = valeur.strip()

    def resoudre(nom, pile=()):
        valeur = brut.get(nom)
        if valeur is None or nom in pile:
            return None
        m = VARIABLE.match(valeur)
        if m:
            return resoudre(m.group(1), pile + (nom,))
        return valeur

    jetons = {}
    for nom in sorted(brut):
        valeur = resoudre(nom)
        if valeur and HEX.match(valeur):
            jetons[nom] = valeur.lower()
    return jetons


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--light", required=True, help="feuille github-light.css")
    p.add_argument("--dark", required=True, help="feuille github-dark.css")
    p.add_argument("--sortie", default=SORTIE_DEFAUT)
    p.add_argument("--remplacer", action="store_true",
                   help="autorise l'écrasement d'un palette.json existant")
    a = p.parse_args()

    for chemin in (a.light, a.dark):
        if not os.path.isfile(chemin):
            sys.exit("feuille introuvable : %s" % chemin)
    if os.path.exists(a.sortie) and not a.remplacer:
        sys.exit("%s existe déjà. Relancer avec --remplacer pour l'écraser."
                 % a.sortie)

    light, dark = lire_jetons(a.light), lire_jetons(a.dark)
    if not light or not dark:
        sys.exit("aucun jeton de couleur trouvé : vérifier les feuilles.")

    palette = {"format": 2,
               "sources": {"light": os.path.basename(a.light),
                           "dark": os.path.basename(a.dark)},
               "jetons": {}, "teintes": {}}
    for variante, jetons in (("light", light), ("dark", dark)):
        manquants = [j for j in c.ROLES.values() if j not in jetons]
        if manquants:
            sys.exit("jetons de rôle absents de la feuille %s : %s"
                     % (variante, ", ".join(manquants)))
        palette["jetons"][variante] = {j: jetons[j]
                                       for j in sorted(set(c.ROLES.values()))}
        palette["teintes"][variante] = sorted(
            {c.normaliser_hex(v)[0] for v in jetons.values()})
    with open(a.sortie, "w", encoding="utf-8", newline="\n") as f:
        json.dump(palette, f, ensure_ascii=False, separators=(",", ":"),
                  sort_keys=True)
        f.write("\n")
    print("%s : %d et %d jetons lus, %d et %d teintes retenues"
          % (a.sortie, len(light), len(dark),
             len(palette["teintes"]["light"]), len(palette["teintes"]["dark"])))


if __name__ == "__main__":
    main()
