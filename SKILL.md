---
name: doc-creer-logigramme
description: >
  Crée le logigramme ISO 5807 d'un processus métier : deux SVG jumeaux, light
  et dark, aux couleurs des feuilles de style GitHub, et le snippet Markdown
  qui les appelle avec son texte alternatif. Invoquer pour schématiser un
  processus depuis une description, un brouillon, un autre schéma ou du code.
  Mots déclencheurs : logigramme, flowchart, ISO 5807, schéma de processus,
  diagramme de flux, schématiser un processus. Ne pas invoquer pour un
  diagramme de séquence, d'états, d'architecture ou un organigramme
  hiérarchique, ni pour corriger le processus ou le code décrit.
compatibility: >
  Requiert Python 3.9 ou plus, bibliothèque standard seule. Conçu pour Claude
  et Codex.
metadata:
  domaine: "doc"
  version: "0.01.000"
---

# Rôle : créer un logigramme

Ce rôle **traduit un processus en logigramme**. Il produit un modèle JSON, deux SVG jumeaux et un snippet. Il ne modifie ni le processus, ni le code qu'il décrit.

Le modèle JSON est la source. Les SVG en sont tirés par script et ne se retouchent jamais à la main : une retouche diverge du modèle, puis de son jumeau.

## Hors de ce rôle

| Ce qui est constaté | Ce qu'il faut faire |
| --- | --- |
| le processus décrit paraît incohérent ou incomplet | le dire dans la remise, schématiser ce qui est décrit, ne pas le corriger |
| le code lu semble fautif | produire un ticket, `domaine: back` ou `front` |
| un schéma existant du dépôt n'est pas à la palette | produire un ticket, `domaine: doc` |
| le fichier Markdown hôte demande d'autres changements | les signaler, ne toucher qu'au snippet, et seulement si l'insertion est demandée |

Aucune donnée personnelle réelle dans un libellé, un titre ou un texte alternatif, quelle que soit la source. Un nom de client, une adresse ou un identifiant lus dans le code ou dans un brouillon deviennent un rôle générique : « le client », « l'adresse de livraison ».

## Lecture de la source

**Description ou brouillon.** Relever les étapes, les décisions et leurs issues, les entrées et sorties, les stockages, les traitements délégués. Une issue manquante ou une étape implicite appelle une question, pas une supposition.

**Autre schéma** (image, Mermaid, SVG, dessin). Transcrire sans réorganiser le processus. Seule la mise en forme change. Un passage illisible est un point d'arrêt : le nommer et demander.

**Code.** Lire les seuls fichiers désignés. Un appel vers une fonction définie ailleurs devient un `processus-predefini` à son nom, sans ouvrir le fichier qui la contient. Ne pas explorer le dépôt pour compléter le schéma.

Au-delà de vingt-cinq symboles, proposer un découpage en plusieurs logigrammes reliés par des renvois hors page, avant d'écrire le modèle.

## Écriture du modèle

Format : [`references/modele.md`](references/modele.md). Formes et règles d'emploi : [`references/iso-5807.md`](references/iso-5807.md). Point de départ : [`assets/exemple.logigramme.json`](assets/exemple.logigramme.json).

Le modèle se pose à côté des SVG, sous le nom `{id}.logigramme.json`, pour que le schéma puisse être retracé par une autre session.

Règles de libellé :

- un libellé par symbole, court, sans point final ;
- une décision est une question fermée, et chacune de ses sorties porte une étiquette ;
- une espace fine insécable (U+202F) avant `?`, `!`, `:` et `;` ;
- `\n` dans un texte force un retour à la ligne, sinon le traceur coupe lui-même.

Le texte alternatif se rédige à ce moment, pas après : [`references/alt.md`](references/alt.md).

## Tracé des deux variantes

```text
python scripts/tracer.py DOSSIER/ID.logigramme.json --sortie DOSSIER --chemin CHEMIN_VU_DU_MD
```

Le traceur écrit `ID.svg` et `ID-dark.svg`, puis affiche le snippet sur la sortie standard.

| Code | Sens | Suite |
| --- | --- | --- |
| 0 | tracé | vérification |
| 2 | modèle invalide, ou texte trop long pour sa cellule | corriger le modèle d'après la liste affichée |
| 3 | SVG déjà présents | voir ci-dessous |

Texte trop long : raccourcir le libellé d'abord, agrandir `grille` ensuite. Un libellé qui ne tient pas dans 250 pixels est presque toujours une phrase à scinder en deux étapes.

`--remplacer` n'est permis que sur des fichiers produits par la session en cours, ou après accord explicite de l'humain.

## Vérification

```text
python scripts/verifier.py DOSSIER/ID.svg --md FICHIER.md
```

Un seul des deux jumeaux suffit : le lint vérifie la paire. Il signale, il ne corrige jamais.

- `ERREUR` bloque la remise. Corriger dans le modèle, retracer, revérifier.
- `AVERTISSEMENT` se corrige, ou se justifie en une ligne dans la remise.
- `INFO` ne demande rien.

Chaque signal, sa cause et sa correction : [`references/signaux.md`](references/signaux.md).

Si un outil de rendu est disponible, regarder les deux variantes. Sinon, le dire dans la remise : le lint mesure le texte par estimation, il ne voit pas le rendu.

## Remise

Toujours ce format.

```markdown
## Logigramme — {titre}

- fichiers : {modèle}, {svg light}, {svg dark}
- symboles : {n}, liens : {n}
- vérification : {n} erreur, {n} avertissements
- rendu vu : {oui, avec quel outil | non}

### Snippet
{le snippet affiché par tracer.py, dans un bloc html}

### Avertissements maintenus
- {signal} : {pourquoi il reste}

### Ce que le schéma ne dit pas
- {étapes absentes de la source, questions restées ouvertes}
```

## Quand la décision revient à l'humain

Ne pas demander « que faut-il faire ». Présenter :

- option A : ce qu'elle donne, ce qu'elle coûte, ce qu'elle ferme pour la suite
- option B : idem
- ce que ce rôle recommande, et sur quel fait il s'appuie
- ce qui serait irréversible dans l'une et dans l'autre

Puis s'arrêter.

Cas typiques : deux lectures possibles d'une issue de décision ; un découpage en plusieurs schémas ; l'écrasement d'un SVG existant.

## Quand s'arrêter d'essayer

S'arrêter dès que l'une de ces quatre est vraie :

- le lint ne signale plus aucune erreur ;
- trois essais ont eu lieu sur le même point ;
- ce qui reste à traiter n'a pas diminué entre deux essais ;
- la décision suivante revient à l'humain.

Si Python est absent ou si un script échoue hors d'un modèle invalide, s'arrêter et le dire. Ne pas écrire de SVG à la main, ne pas réécrire un script : un moyen non prévu est un point d'arrêt même quand il fonctionne.

## Les tickets

Un constat hors périmètre produit un ticket, et **ce rôle ne le traite pas**. Trois tickets au maximum par session.

```markdown
## Ticket — {titre en une ligne}

- constaté par : doc-creer-logigramme, le {date}, sur la branche {nom}
- domaine : {git | ci | db | front | back | sec | ops | doc}
- phase : {plan | code | build | test | intégration | déploiement | opération | monitoring}
- rôle à appeler : {$nom-du-role, ou « aucun rôle existant »}

### Constaté
- {le fait, avec le fichier qui l'établit}

### Ce que ça empêche
- {une ligne}

### Pourquoi ce rôle ne l'a pas traité
- {hors périmètre : lequel}

### Pour la session qui le reprendra
- premier geste : {une phrase}
- ne pas commencer par : {le geste tentant et faux}
```

Le ticket est remis dans la réponse. Il ne s'écrit pas dans le dépôt.
