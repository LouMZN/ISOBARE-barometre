---
title: "Isobare — notre baromètre synthétique mondial"
subtitle: "KEDGE BS · Gestion d'actifs 2025-2026 · Note explicative, données au 20 novembre 2026"
author: 'Groupe 3 : Kaloufina ASSADILLAH · Lou MAZERAN\-\-MAGNAN · Inès ESPINAT · Faith HERITAGE · Jade MONNET'
lang: fr
---

**Site : [https://isobare.netlify.app](https://isobare.netlify.app)** (mis à jour automatiquement chaque matin).

**L'idée en bref.** Un investisseur doit décider comment répartir son argent entre actions, obligations, actifs réels (matières premières, immobilier) et liquidités. Les informations utiles sont nombreuses et parlent des « langues » différentes : un PIB en %, un indice boursier en points, un prix du pétrole en dollars. Notre baromètre les rassemble en **un seul score de 0 à 100** pour trois zones (États-Unis, zone euro, Japon) : **50 = situation normale**, au-dessus le climat est favorable, en dessous il est défavorable. Le site montre aussi si les marchés sont chers et ce que cela implique pour l'allocation.

## 1. Les indicateurs choisis (attendu 1)

Nous avons retenu **9 indicateurs**, qui couvrent **7 des 8 familles** proposées dans le sujet. Le signe indique si une hausse de l'indicateur améliore (+) ou dégrade (−) le score.

| Famille (poids) | Indicateur | Ce qu'il nous apprend |
|--------------|------------------|----------------------------------------------|
| Croissance (30 %) | PIB réel (+) | L'économie produit-elle plus qu'il y a un an ? C'est la base des bénéfices des entreprises. |
| | Indicateur avancé de l'OCDE, CLI (+) | Le PIB arrive en retard ; le CLI annonce les retournements de l'économie environ 6 à 9 mois à l'avance. |
| Inflation (20 %) | Écart de l'inflation à 2 % (−) | 2 % est l'objectif des banques centrales. Plus on s'en éloigne (vers le haut ou le bas), plus elles risquent d'agir brutalement. |
| Marchés (30 %) | Tendance des actions (+) | Le cours de l'indice (S&P 500, Euro Stoxx 50, Nikkei) comparé à sa moyenne sur 12 mois : les marchés montent-ils ou baissent-ils ? |
| | Pente des taux 10 ans − 3 mois (+) | Quand les taux courts dépassent les taux longs (courbe « inversée »), une récession a souvent suivi. |
| Risque, commun aux 3 zones (20 %) | VIX (−) | La « peur » des investisseurs, mesurée par la volatilité attendue des actions. |
| | Spread de crédit (−) | Le surcoût payé par les entreprises pour emprunter : il monte quand le risque de faillite augmente. |
| | Risque géopolitique, GPR (−) | Les tensions dans le monde (guerres, crises), mesurées à partir de la presse. |
| | Prix du pétrole Brent (−) | Une flambée du pétrole freine la croissance et relance l'inflation. |

En plus du score, nous mesurons la **valorisation** : les actions sont-elles chères (ratio cours / bénéfices de Shiller, dit CAPE) et les obligations rapportent-elles plus que l'inflation (taux réel) ? Nous avons **écarté** les flux de capitaux, car les données sont payantes, et la Chine, faute de données gratuites fiables (elle reste présente à travers le risque géopolitique).

## 2. Les sources de données (attendu 2)

Toutes nos sources sont **publiques et gratuites** : **FRED** (banque de données de la Réserve fédérale de Saint-Louis : VIX, pétrole, S&P 500, taux et données américaines), **BCE** et **Eurostat** (zone euro), **OCDE** (indicateurs avancés, données japonaises), **DBnomics** (prix au Japon), et les fichiers mis en ligne par les chercheurs **Robert Shiller** (CAPE) et **Caldara et Iacoviello** (risque géopolitique). Au total, 28 séries.

## 3. La méthode de collecte (attendu 3)

Nous avons écrit un programme en **Python**. Chaque matin à 6 h (heure UTC), **GitHub Actions** le lance automatiquement : il télécharge les 28 séries, les met toutes au rythme mensuel (dernière valeur connue du mois), calcule les scores et enregistre le résultat dans un fichier (`data.json`). Le site, hébergé sur **Netlify**, lit ce fichier et affiche les graphiques. Si une source ne répond pas, le programme garde la dernière valeur connue et le site le signale. Aucune saisie manuelle n'est nécessaire.

## 4. Rendre les données comparables : normalisation (attendu 4)

**Le problème** : on ne peut pas additionner un VIX à 24,6 et une inflation à 3,3 %. Il faut d'abord tout ramener sur la même échelle.

**Notre solution : le Z-score.** Pour chaque indicateur, nous regardons de combien il s'écarte de sa moyenne des **10 dernières années**, en nombre d'écarts-types (l'écart « habituel »). Nous plafonnons ce résultat entre −3 et +3, puis le convertissons en note sur 100 : **sous-score = (Z + 3) / 6 × 100**.

> **Exemple avec le VIX** : il vaut 24,6 aujourd'hui, contre une moyenne de 18,8 sur 10 ans et un écart-type de 6,9. Il est donc 0,84 écart-type au-dessus de la normale. Comme un VIX élevé est une mauvaise nouvelle, on **inverse** le signe (−0,84), ce qui donne un sous-score de **36/100**.

Nous avons préféré le Z-score à la méthode Min-Max, qui dépend trop des valeurs extrêmes (crise de 2008, Covid en 2020). Deux ajustements complètent la méthode : l'**inversion** pour les indicateurs de risque (VIX, crédit, géopolitique, pétrole) et la **cible** pour l'inflation, où l'on mesure l'écart à 2 % : une inflation trop faible est pénalisée comme une inflation trop forte.

## 5. Le score global et le choix des pondérations (attendu 5)

**Score d'une zone** = moyenne pondérée de ses 9 sous-scores, avec les poids du tableau : **30 % croissance, 20 % inflation, 30 % marchés, 20 % risque**. Nous avons fixé les poids par famille plutôt que par indicateur pour ne pas compter deux fois la même information (le PIB et le CLI racontent en partie la même chose). Croissance et marchés pèsent le plus car ce sont les moteurs directs des bénéfices et des cours.

**Score mondial** = moyenne des trois zones, pondérée par le **poids de chaque zone en Bourse** : États-Unis 84 %, zone euro 9 %, Japon 7 %. C'est ce que vit un investisseur qui détient un portefeuille mondial. Comme le score devient alors très américain, le site propose aussi une version à **parts égales**.

**Du score à l'allocation.** Le baromètre classe la situation dans l'un des quatre « régimes » ci-dessous, selon la croissance (au-dessus ou en dessous de 50) et l'inflation (au-dessus ou en dessous de 2,5 %). Chaque régime a une répartition de départ (en % : actions / obligations / actifs réels / liquidités), ensuite corrigée : on retire 10 points d'actions si le score passe sous 40 ou si les actions sont très chères.

| | Inflation basse (< 2,5 %) | Inflation haute (≥ 2,5 %) |
|---|---|---|
| **Croissance forte (≥ 50)** | Expansion : 65 / 25 / 5 / 5 | Surchauffe : 50 / 10 / 30 / 10 |
| **Croissance faible (< 50)** | Ralentissement : 35 / 50 / 5 / 10 | Stagflation : 30 / 15 / 30 / 25 |

## 6. Analyse et interprétation (attendu 6)

**Quels indicateurs pèsent le plus ?** Avec la pondération boursière, les indicateurs américains représentent **67 %** du score mondial ; l'inflation américaine est à elle seule l'indicateur le plus lourd (16,8 %). Mais ce qui fait **bouger** le score, c'est surtout la **tendance du S&P 500** : sur 3 mois, le score a perdu 4,4 points, dont 2,5 viennent de la baisse relative des actions américaines et 1,1 de la hausse du VIX. À l'inverse, l'indicateur avancé de l'OCDE (+1,8 point sur 12 mois) et la pente des taux américains (+1,4) soutiennent le score.

**Quels signaux aujourd'hui ?**

- **Climat neutre mais en dégradation** : score mondial **51,7/100** (54,3 à parts égales), −4,4 points en 3 mois. Les marchés deviennent plus nerveux alors que l'économie réelle tient encore.
- **Régime de surchauffe** : la croissance reste solide (56,8) mais l'inflation est trop élevée (3,3 % ; 4,0 % en zone euro). Seul le Japon (2,1 %) est en expansion.
- **Actions très chères** : le CAPE américain est à 39,4. Une action « rapporte » environ 2,5 % de bénéfices par an, moins qu'une obligation américaine protégée de l'inflation (2,9 %). Les actions n'offrent donc aucune prime pour leur risque.
- **Ce que suggère le baromètre** : **40 % actions, 20 % obligations, 30 % actifs réels, 10 % liquidités**, contre 60 % actions et 40 % obligations dans un portefeuille classique. Par zone : privilégier le **Japon** (score 61,3), rester neutre sur les États-Unis (51,1), alléger la zone euro (50,5).

**Le baromètre aurait-il aidé dans le passé ?** En 2022, année où actions et obligations ont baissé ensemble, notre règle aurait perdu −9,3 % contre −15,1 % pour un portefeuille 60/40, grâce à sa part d'actifs réels. En 2020, elle aurait moins bien profité du rebond (+12,2 % contre +16,2 %). En 2008, le résultat dépend des réglages : c'est une illustration, pas une preuve.

## Limites

Le baromètre est un **outil pédagogique, pas un conseil en investissement**. La Chine n'est pas couverte ; la valorisation des actions repose sur le seul CAPE américain ; nos seuils (50, 2,5 %, 40…) ont été fixés à l'avance, sans optimisation sur le passé ; les flux de capitaux manquent. Enfin, chaque zone est comparée à **sa propre histoire** : un score élevé veut dire « mieux que d'habitude », pas « mieux que les autres zones ».
