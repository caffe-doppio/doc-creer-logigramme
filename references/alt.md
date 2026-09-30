# Texte alternatif et snippet

## Le texte alternatif

Il s'adresse à qui ne voit pas l'image. Il décrit **ce que le schéma montre**, pas ce qu'il s'intitule. Un `alt` qui répète le titre de la section n'apporte rien : le lint le refuse.

Il suit le flux, dans l'ordre de lecture :

1. la nature et la taille du schéma : « Logigramme en neuf étapes. » ;
2. le point de départ ;
3. chaque décision, avec ses issues et où elles mènent ;
4. les branches parallèles, et où elles se rejoignent ;
5. le point d'arrivée ;
6. les annotations, en une phrase.

Il reste en prose, sans liste ni mise en forme. Au-dessous de soixante caractères, le lint demande s'il décrit vraiment le contenu. Il n'a pas de plafond : un schéma de vingt étapes appelle un texte long, et c'est normal.

Le champ `description` du modèle alimente `desc`, lu par qui ouvre le SVG directement. Il vaut `alt` par défaut, ce qui convient presque toujours.

## Le snippet

Affiché par `tracer.py`, à coller tel quel :

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/nom-dark.svg">
  <img alt="Description du contenu du schéma." src="assets/nom.svg">
</picture>
```

Le chemin est celui des SVG vus depuis le fichier Markdown qui les appelle, pas depuis la racine du dépôt. Il vient de `--chemin`, ou du champ `chemin` du modèle.

Le basculement suit la préférence de couleur que le navigateur transmet à la page. Son articulation avec le sélecteur de thème de GitHub n'est pas vérifiée par ce rôle.

## Markdownlint

Le snippet est du HTML dans du Markdown, ce que la règle `MD033` interdit par défaut. Le `.markdownlint.json` du dépôt autorise nommément les trois éléments, et rien de plus large :

```json
{
  "MD033": { "allowed_elements": ["picture", "source", "img"] }
}
```

Si le dépôt n'a pas cette exception, ne pas la créer : le signaler dans la remise.

## Contraintes d'un SVG servi par img

GitHub affiche le SVG comme une image. Dans ce mode, le SVG ne résout pas les variables CSS, ne charge aucune police ni ressource externe, et ne voit pas le thème de la page. D'où les règles que le traceur applique et que le lint vérifie :

- couleurs en valeurs hexadécimales, prises dans les jetons de la feuille de la variante ;
- pile de polices système, sans police embarquée ;
- deux fichiers, un par thème, de contenu identique.
