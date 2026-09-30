# Signaux du lint

Chaque correction se fait **dans le modèle**, suivie d'un nouveau tracé. Un SVG ne se corrige pas à la main.

## Erreurs

| Signal | Cause | Correction |
| --- | --- | --- |
| la ligne « … » déborde de la forme | texte modifié dans le SVG, ou `largeur`/`hauteur` imposées trop petites | retracer depuis le modèle ; retirer la taille imposée ou raccourcir le libellé |
| forme hors du cadre du SVG | SVG retouché | retracer |
| {hex} n'est la valeur d'aucun jeton | couleur posée à la main, ou palette d'une autre variante | retracer ; pour un SVG non produit par le traceur, le reprendre en modèle |
| variable CSS, non résolue | `var(--…)` dans le SVG | poser la valeur du jeton ; un SVG servi par img ne lit pas les variables |
| couleur hors palette (ni jeton ni hex) | couleur nommée, `rgb()` | idem |
| ressource externe | police, feuille ou image chargée depuis l'extérieur | la retirer ; elle ne se charge pas dans ce mode |
| jumeau light ou dark absent | un seul fichier de la paire | retracer : le traceur écrit toujours les deux |
| variantes divergentes | les deux fichiers ne portent pas le même contenu | retracer les deux ensemble |
| title, desc, role ou aria-labelledby absent | SVG non produit par le traceur | le reprendre en modèle |
| alt absent ou vide | snippet incomplet | remplir `alt` dans le modèle et recoller le snippet |
| alt identique au titre | `alt` nomme au lieu de décrire | le réécrire, voir [`alt.md`](alt.md) |
| source dark absente, srcset inattendu | snippet modifié à la main | recoller le snippet affiché par le traceur |
| fichier introuvable depuis le Markdown | `--chemin` faux | retracer avec le chemin vu depuis le fichier Markdown |

## Avertissements

| Signal | Cause | Correction |
| --- | --- | --- |
| lien traverse le nœud … | routage par défaut qui coupe un symbole | `sortie`/`entree`, puis `couloir`, puis `via`, voir [`modele.md`](modele.md) |
| étiquette recouvre le nœud … | étiquette trop longue, ou sortie trop proche d'un voisin | raccourcir l'étiquette, ou changer de côté de sortie |
| aucun terminal | début et fin non représentés | ajouter les deux terminaux |
| terminal à la fois entrée et sortie | un terminal au milieu du flux | le remplacer par un traitement, ou scinder |
| décision : moins de deux sorties | losange sans alternative | ajouter l'issue manquante, ou remplacer par un traitement |
| décision : sortie sans étiquette | issue non nommée | ajouter `etiquette` au lien |
| mode parallèle ni fourche ni jointure | traits parallèles mal reliés | une entrée et plusieurs sorties, ou l'inverse |
| sorties multiples hors décision | branchement sans losange | ajouter une décision, ou une fourche parallèle |
| connecteur au libellé long | phrase dans un cercle | une lettre ou un numéro |
| connecteur sans connecteur apparié | la paire n'existe pas sur le schéma | ajouter le second, ou utiliser un renvoi hors page |
| annotation reliée à aucun symbole | `cible` absente | renseigner `cible` |
| nœud isolé | symbole sans lien | le relier, ou le retirer |
| alt de moins de 60 caractères | description probablement absente | vérifier qu'il décrit le flux |

## Informations

| Signal | Sens |
| --- | --- |
| SVG non produit par tracer.py | seules la palette, la parité et l’accessibilité sont vérifiées ; le débordement et les règles ISO ne peuvent pas l'être sans les métadonnées du traceur |
| aucun élément picture | le fichier Markdown n'appelle aucun schéma |

## Limite de la mesure

La largeur du texte est estimée à partir des chasses de Helvetica, avec une marge de 15 %. Elle couvre les polices de la famille Arial et Helvetica. Une police de repli plus large, DejaVu Sans par exemple, peut dépasser l'estimation de quelques pour cent, ce qu'absorbe la marge intérieure des formes. Un schéma qui passe le lint n'a donc pas été vu : il a été mesuré.
