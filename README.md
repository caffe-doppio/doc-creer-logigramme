# doc-creer-logigramme

[![License: MIT](https://shields.io)](LICENSE)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

Skill pour agent de code (Claude, Codex) qui transforme la description d'un processus en **logigramme ISO 5807** prêt pour un README GitHub : deux SVG jumeaux, clair et sombre, aux couleurs de GitHub, et le snippet Markdown qui les appelle avec un vrai texte alternatif.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="exemples/demande-acces-exemple-dark.svg">
  <img alt="Logigramme en neuf étapes. Une demande d'accès arrive par courriel ou formulaire, un dossier est ouvert et horodaté, puis l'identité du demandeur est contrôlée. Si elle n'est pas établie, un justificatif proportionné est demandé et la demande revient au point de réception. Si elle l'est, deux traitements menés en parallèle, l'extraction depuis le registre et l'interrogation des sous-traitants, se rejoignent avant une relecture manuelle qui occulte les données de tiers. La réponse est envoyée avec la copie des données, et la demande est close. Une annotation rappelle le délai d'un mois, prorogeable de deux mois." src="exemples/demande-acces-exemple.svg">
</picture>

*Tracé depuis [`assets/exemple.logigramme.json`](assets/exemple.logigramme.json). Basculez GitHub en thème sombre : l'image change avec lui.*

## Pourquoi ce skill

Un schéma dessiné à la main dans un README vieillit mal : on ne le retouche plus, il ne suit pas le thème sombre, et le lecteur d'écran n'en lit que le titre. Ce skill fait du schéma un **fichier source** :

- le modèle JSON est la source, les SVG en sont tirés par script et ne se retouchent jamais ;
- une paire de SVG, un par thème, dont les couleurs sont prises dans les jetons des feuilles de style GitHub ;
- un texte alternatif qui décrit le flux, rédigé en même temps que le modèle ;
- un lint qui mesure le débordement du texte, les liens qui coupent une forme, la parité des deux variantes et les règles ISO 5807.

> [!TIP]
> Skill peut être utilisé pour convertir une description d'une logique métier, un croquis, un autre schéma ou le code en flowchart **ISO 5807**, en deux schémas couleur, avec alt texte.
> Sur GitHub, une autre forge ou dans un progiciel : des schémas claires et standartisées, on en a besoin partout.

## Installation

Cloner le dépôt dans le dossier de skills de l'agent.

Claude Code, pour tous les projets :

```bash
git clone <url-du-depot> ~/.claude/skills/doc-creer-logigramme
```

Pour un seul projet, cloner dans `.claude/skills/` à la racine du projet. Pour Codex, [`agents/openai.yaml`](agents/openai.yaml) porte le nom d'affichage et autorise l'invocation implicite.

Python 3.9 ou plus, bibliothèque standard seule. Aucune dépendance à installer.

## Utilisation

Demander à l'agent, en langage naturel :

> Fais le logigramme du processus de validation d'une commande décrit dans `docs/commande.md`.

Le skill se déclenche sur *logigramme*, *flowchart*, *ISO 5807*, *schéma de processus*, *diagramme de flux*. Il ne s'applique pas aux diagrammes de séquence, d'états, d'architecture ni aux organigrammes.

L'agent rend un bloc de remise normalisé : fichiers produits, nombre de symboles et de liens, résultat du lint, avertissements maintenus, et **ce que le schéma ne dit pas**, c'est-à-dire les trous de la source.

Les scripts s'emploient aussi sans agent :

```bash
python3 scripts/tracer.py docs/commande.logigramme.json --sortie docs/assets --chemin assets
```

```bash
python3 scripts/verifier.py docs/assets/commande.svg --md docs/commande.md
```

## Comment le skill travaille

Les deux schémas suivants sont la logique de [`SKILL.md`](SKILL.md), tracée par le skill lui-même. Ils sont reliés par un renvoi hors page, comme le skill le propose pour tout processus trop long pour un seul schéma.

### 1. Du processus au modèle

L'agent lit la source sans l'interpréter. Une issue manquante appelle une question, pas une supposition. Du code se lit fichier par fichier : un appel vers une fonction définie ailleurs devient un *processus prédéfini* à son nom, sans exploration du dépôt.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="exemples/lecture-source-dark.svg">
  <img alt="Logigramme en dix symboles, premier de deux. Le processus à schématiser arrive sous forme de description, de schéma existant ou de code. Les étapes, les décisions et leurs issues sont relevées. Si la source est illisible ou incomplète, une question est posée à l'humain et le relevé reprend avec sa réponse. Si elle est complète, le nombre de symboles est évalué : au-delà de vingt-cinq, un découpage en plusieurs schémas est proposé avant d'écrire le modèle. Le modèle JSON et son texte alternatif sont écrits, puis un renvoi hors page mène au second schéma, le tracé et la vérification. Une annotation rappelle qu'aucune donnée personnelle réelle n'entre dans un libellé." src="exemples/lecture-source.svg">
</picture>

### 2. Tracé, vérification et remise

Le traceur refuse plutôt que de tronquer : un texte qui ne tient pas dans sa cellule renvoie au modèle. Le lint signale et ne corrige jamais. Après trois essais sur le même point, l'agent s'arrête et présente les options à l'humain au lieu d'insister.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="exemples/trace-verification-dark.svg">
  <img alt="Logigramme en onze symboles, second de deux. Il part du renvoi hors page venu du premier schéma. Le script tracer.py lit le modèle. S'il rend le code 2, modèle invalide ou texte trop long, le modèle est corrigé et retracé. S'il rend le code 3, SVG déjà présents, l'accord de l'humain est demandé avant de remplacer. S'il rend le code 0, le script verifier.py contrôle la paire de SVG et le snippet. En cas d'erreur, si trois essais ont déjà eu lieu sur le même point, le travail s'arrête et la décision revient à l'humain ; sinon le modèle est corrigé et retracé. Sans erreur, la remise liste les fichiers, le snippet et les avertissements maintenus, et le logigramme est remis." src="exemples/trace-verification.svg">
</picture>

| Code de `tracer.py` | Sens |
| --- | --- |
| 0 | les deux SVG sont écrits, le snippet est sur la sortie standard |
| 2 | modèle invalide ou texte trop long, la liste des corrections est affichée |
| 3 | SVG déjà présents, `--remplacer` requis |

| Niveau du lint | Effet |
| --- | --- |
| `ERREUR` | bloque la remise |
| `AVERTISSEMENT` | se corrige, ou se justifie en une ligne dans la remise |
| `INFO` | ne demande rien |

Chaque signal, sa cause et sa correction : [`references/signaux.md`](references/signaux.md).

## Les quinze formes

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/catalogue-formes-dark.svg">
  <img alt="Planche de quinze symboles de logigramme rangés en trois rangées de cinq. Première rangée : terminal en forme de stade, traitement rectangulaire, décision en losange, entrée ou sortie en parallélogramme, processus prédéfini à doubles bords verticaux. Deuxième rangée : connecteur de page en petit cercle marqué A, renvoi hors page en pentagone marqué B, annotation en crochet ouvert, fichier ou base en cylindre, document à base ondulée. Troisième rangée : documents multiples empilés, opération manuelle en trapèze, saisie manuelle au bord supérieur incliné, préparation en hexagone, mode parallèle en deux traits horizontaux." src="assets/catalogue-formes.svg">
</picture>

Nom de chaque forme dans le modèle et règles d'emploi : [`references/iso-5807.md`](references/iso-5807.md).

## Le modèle

Chaque symbole occupe une cellule d'une grille, repérée par colonne et rang. Le routage des liens est orthogonal et se règle par côté de sortie, couloir ou points de passage.

```json
{
  "id": "validation-commande",
  "titre": "Validation d'une commande",
  "alt": "Logigramme en quatre étapes. Une commande est reçue, puis le stock est contrôlé. S'il est suffisant, la commande est traitée aussitôt ; sinon, le client est d'abord prévenu du délai. Les deux issues mènent à la commande traitée.",
  "noeuds": [
    {"id": "debut", "forme": "terminal", "texte": "Commande reçue", "col": 1, "rang": 0},
    {"id": "stock", "forme": "decision", "texte": "Stock suffisant ?", "col": 1, "rang": 1},
    {"id": "delai", "forme": "traitement", "texte": "Prévenir du délai", "col": 2, "rang": 1, "etat": "attention"},
    {"id": "fin", "forme": "terminal", "texte": "Commande traitée", "col": 1, "rang": 2, "etat": "succes"}
  ],
  "liens": [
    {"de": "debut", "vers": "stock"},
    {"de": "stock", "vers": "fin", "etiquette": "oui"},
    {"de": "stock", "vers": "delai", "etiquette": "non"},
    {"de": "delai", "vers": "fin", "sortie": "bas", "entree": "droite"}
  ]
}
```

Format complet : [`references/modele.md`](references/modele.md). Rédaction du texte alternatif et du snippet : [`references/alt.md`](references/alt.md).

## Palette

[`assets/palette.json`](assets/palette.json) contient les jetons de couleur des thèmes clair et sombre de GitHub (Primer, jetons `--bgColor-*`, `--fgColor-*`, `--borderColor-*`). Le lint refuse toute couleur qui n'est la valeur d'aucun jeton de la variante. Pour la régénérer depuis des feuilles plus récentes :

```bash
python3 scripts/extraire_palette.py --light github-light.css --dark github-dark.css --remplacer
```

## Limites

- Le texte est **mesuré, pas rendu** : ses largeurs sont estimées d'après les chasses de Helvetica, avec 15 % de marge. Un schéma qui passe le lint a été mesuré, pas vu.
- Le basculement clair/sombre suit `prefers-color-scheme`. Son articulation avec le sélecteur de thème manuel de GitHub n'est pas vérifiée.
- Le snippet est du HTML dans du Markdown. Avec markdownlint, autoriser `picture`, `source` et `img` dans la règle `MD033`.

## Contenu du dépôt

| Chemin | Rôle |
| --- | --- |
| `SKILL.md` | instructions lues par l'agent |
| `references/` | format du modèle, formes ISO 5807, texte alternatif, signaux du lint |
| `scripts/tracer.py` | modèle JSON vers deux SVG et un snippet |
| `scripts/verifier.py` | lint des SVG et des snippets Markdown |
| `scripts/commun.py` | mesures de texte, formes et palette partagées par les deux scripts |
| `scripts/extraire_palette.py` | régénération de `assets/palette.json` |
| `assets/` | palette, modèle d'exemple, catalogue des formes |
| `exemples/` | modèles et SVG des schémas de ce README |
| `agents/openai.yaml` | métadonnées d'affichage pour Codex |

## Licence

[MIT](LICENSE).
