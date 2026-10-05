# Format du modèle

Un fichier JSON en UTF-8, nommé `{id}.logigramme.json`. Exemple complet : [`../assets/exemple.logigramme.json`](../assets/exemple.logigramme.json).

## Racine

| Champ | Obligatoire | Valeur |
| --- | --- | --- |
| `id` | oui | minuscules, chiffres, tirets simples ; donne le nom des fichiers |
| `titre` | oui | titre du schéma, repris dans `title` du SVG |
| `alt` | oui | texte alternatif du snippet, voir [`alt.md`](alt.md) |
| `description` | non | contenu de `desc` dans le SVG ; vaut `alt` par défaut |
| `chemin` | non | chemin des SVG vu depuis le fichier Markdown, `assets` par défaut ; `--chemin` le remplace |
| `grille` | non | `{"colonne": 250, "rangee": 140}`, en pixels, valeurs par défaut |
| `pointes` | non | `toutes` par défaut, ou `iso`, voir [`iso-5807.md`](iso-5807.md) |
| `titre_visible` | non | `true` pour écrire le titre en tête du schéma ; `false` par défaut, le titre de section du Markdown suffit |
| `couloirs` | non | liste ordonnée des couloirs, voir [Couloirs](#couloirs) ; absente, le schéma n'en a pas |
| `noeuds` | oui | liste des symboles |
| `liens` | oui | liste des lignes de flux, éventuellement vide |

## Placement sur la grille

Chaque symbole occupe une cellule, repérée par `col` et `rang`, entiers à partir de 0. Le symbole est centré dans sa cellule. Deux symboles ne partagent pas une cellule.

Le placement est une décision de mise en page, prise dans le modèle :

- le flux principal dans une colonne, souvent `col: 1`, pour laisser une colonne de chaque côté aux branches ;
- une branche de décision à gauche ou à droite, au même rang que le losange ou en dessous ;
- une rangée vide entre deux symboles si un lien doit passer entre eux.

## Nœud

| Champ | Obligatoire | Valeur |
| --- | --- | --- |
| `id` | oui | lettres, chiffres, `_` et `-`, unique |
| `forme` | oui | une des quinze formes de [`iso-5807.md`](iso-5807.md) |
| `texte` | oui, sauf `parallele` | libellé ; `\n` force un retour à la ligne |
| `col`, `rang` | oui | cellule |
| `cols` | `parallele` seul | nombre de colonnes couvertes par les traits, 1 par défaut |
| `cible` | `annotation` seule | `id` du symbole annoté |
| `couloir` | oui si `couloirs` est déclaré | `id` du couloir qui porte le symbole ; interdit sinon |
| `etat` | non | `neutre` par défaut, `accent`, `succes`, `attention`, `danger`, `fait` |
| `largeur`, `hauteur` | non | taille imposée, en pixels ; le traceur n'agrandit plus la forme |

Sans `largeur` ni `hauteur`, le traceur part d'une taille propre à la forme et l'agrandit jusqu'à ce que le texte tienne, dans la limite de la cellule.

## Lien

| Champ | Obligatoire | Valeur |
| --- | --- | --- |
| `de`, `vers` | oui | `id` des deux symboles ; jamais une annotation |
| `etiquette` | non | texte posé au départ du lien ; obligatoire en pratique sur une sortie de décision |
| `sortie`, `entree` | non | `haut`, `bas`, `gauche`, `droite` : côté de départ et côté d'arrivée |
| `via` | non | points de passage, liste de `[col, rang]` ; décimaux admis, `1.5` passe entre deux colonnes |
| `couloir` | non | entier ; décale de 16 pixels par unité un retour qui contourne, pour écarter deux retours parallèles. Sans rapport avec le `couloir` d'un nœud |
| `etat` | non | comme pour un nœud ; colore le trait et sa pointe |

Côtés par défaut :

| Cible | Sortie | Entrée |
| --- | --- | --- |
| rang inférieur | `bas` | `haut` |
| même rang, à droite | `droite` | `gauche` |
| même rang, à gauche | `gauche` | `droite` |
| rang supérieur, retour | `droite` | `droite`, contour par la droite |

Le routage est orthogonal. Quand le lint signale qu'un lien traverse un symbole, trois corrections, dans cet ordre : changer `sortie` ou `entree`, ajouter `couloir`, poser `via`.

## Couloirs

Les couloirs sont verticaux : chacun couvre une ou plusieurs colonnes entières de la grille, sur toute la hauteur du schéma, sous un en-tête qui porte son titre. Règles d'emploi : [`iso-5807.md`](iso-5807.md#couloirs). Exemple : [`../exemples/violation-donnees.logigramme.json`](../exemples/violation-donnees.logigramme.json).

| Champ | Obligatoire | Valeur |
| --- | --- | --- |
| `id` | oui | lettres, chiffres, `_` et `-`, unique parmi les couloirs |
| `titre` | oui | titre de l'en-tête, sur une ligne |
| `cols` | non | nombre de colonnes couvertes, 1 par défaut |

L'ordre de la liste fixe les colonnes : le premier couloir commence à la colonne 0, chaque suivant commence où finit le précédent. `col` reste un numéro de colonne du schéma entier, pas un numéro relatif au couloir.

```json
"couloirs": [
  {"id": "agent", "titre": "Personne qui constate"},
  {"id": "dpo", "titre": "DPO", "cols": 2}
]
```

Ici, `agent` couvre la colonne 0 et `dpo` les colonnes 1 et 2. Un nœud `"couloir": "dpo"` se place en colonne 1 ou 2. Ailleurs, le traceur refuse le modèle.

Un couloir prend une colonne de plus que son flux quand il porte une branche de décision ou une annotation : l'annotation se pose dans le couloir de sa cible.

L'orientation verticale n'est pas un réglage. Le flux principal descend, et une couche ou un acteur peut revenir plus bas dans le processus : un couloir en colonne l'accueille à n'importe quelle hauteur, alors qu'un couloir horizontal obligerait le flux à remonter. Le modèle n'a donc pas de couloirs horizontaux.

Le traceur pose l'en-tête au-dessus de tout le contenu, et allonge les couloirs jusqu'au dernier symbole ou au dernier lien. Un modèle sans `couloirs` se trace à l'identique d'avant leur introduction.
