---
title: "Isobare — baromètre synthétique mondial"
subtitle: "KEDGE BS · Gestion d'actifs 2025-2026 · Note méthodologique et lecture au 20 novembre 2026"
lang: fr
---

**Site : [https://isobare.netlify.app](https://isobare.netlify.app)** — mis à jour chaque jour automatiquement. Données de cette note : `data.json` généré le 20/11/2026 (6 h 56 UTC), mois de calcul novembre 2026, 28 séries sur 28 collectées sans échec ; dernières observations de 09/2026 (PIB du T3) à 11/2026 (marchés).

Le baromètre éclaire l'allocation entre actions (A), obligations d'État (O), actifs réels (R) et liquidités (L) sur trois zones : États-Unis, zone euro, Japon. Il répond à trois questions : *quel est le climat ?* (score 0-100), *est-il déjà dans les prix ?* (valorisation), *dans quelle direction va-t-on ?* (régime, variations, contributions).

## 1. Choix des indicateurs (attendu 1)

Neuf indicateurs, soit 19 séries, couvrent **sept des huit familles** du sujet (PIB, inflation, indices boursiers, volatilité, taux, matières premières, risque/incertitude). Sens : une hausse améliore (+) ou dégrade (−) le score.

| Indicateur (poids, sens) | Série et source | Pourquoi cet indicateur |
|------------------|--------------------------|----------------------------------------|
| **Croissance (30 %)** | | |
| PIB réel, glissement annuel (15 %, +) | GDPC1 (FRED) ; EA20 (Eurostat) ; Japon (OCDE) | Mesure directe de l'activité, socle des bénéfices. Trimestriel et publié avec retard, d'où l'indicateur suivant. |
| Indicateur avancé CLI (15 %, +) | CLI de l'OCDE par zone (API SDMX) | Anticipe de 6 à 9 mois les retournements ; méthode identique pour les trois zones. |
| **Inflation (20 %)** | | |
| Écart d'inflation à 2 % (20 %, −) | PCE (FRED) ; IPCH (BCE) ; IPC (DBnomics) | Cible des banques centrales : au-dessus, resserrement ; en dessous, demande faible. Chaque zone est mesurée sur l'indice que cible sa banque centrale. |
| **Marchés financiers (30 %)** | | |
| Tendance actions (15 %, +) | S&P 500, Nikkei 225 (FRED) ; Euro Stoxx 50 (BCE) | Anticipations de bénéfices ; le ratio cours / moyenne 12 mois rend comparables des indices de niveaux différents. |
| Pente 10 ans − 3 mois (15 %, +) | T10Y3M (FRED) ; courbe AAA (BCE) ; taux OCDE (Japon) | Indicateur avancé de récession le plus reconnu : une courbe inversée les a précédées. |
| **Risque — socle mondial (20 %)** | | |
| VIX (5 %, −) | VIXCLS (FRED) | Volatilité implicite à 30 jours : thermomètre mondial de l'aversion au risque. |
| Spread de crédit (5 %, −) | BAA10Y (FRED) | Prix du risque de défaut ; préféré au spread haut rendement, dont l'historique gratuit est tronqué. |
| Risque géopolitique (5 %, −) | Indice GPR (Caldara et Iacoviello) | Seule mesure chiffrée, gratuite et mensuelle des tensions ; intègre la Chine, absente des zones. |
| Choc pétrolier (5 %, −) | Brent, cours / moyenne 12 mois (FRED) | Choc d'offre qui freine la croissance et relance l'inflation ; l'écart à la tendance isole le choc. |
| **Valorisation (hors score, corrige l'allocation)** | | |
| Attrait actions / obligations | CAPE (Shiller) ; taux réels 10 ans (FRED, BCE, OCDE) | 1/CAPE − taux réel US : rendement des bénéfices face au placement réel sans risque. Taux réel 10 ans par zone pour les obligations. |

**Écartés** : flux de capitaux (séries de référence payantes) ; taux directeurs et change (effet ambigu, affichés en contexte) ; Chine (pas de séries gratuites d'inflation, de courbe et d'indice boursier).

## 2. Sources de données (attendu 2)

Sources **publiques, gratuites, sans clé d'API** : bases publiques par fichiers CSV (**FRED**, Fed de Saint-Louis) ; API SDMX institutionnelles (**BCE** – ECB Data Portal, **OCDE**, **Eurostat**) ; agrégateur **DBnomics** ; fichiers Excel des chercheurs (**R. Shiller** : CAPE et séries longues du test historique ; **Caldara et Iacoviello** : GPR). Le site affiche, pour chacune des 28 séries, sa source, son statut et la date de sa dernière donnée.

## 3. Méthode de collecte (attendu 3)

Script **Python** (pandas, requests, xlrd/openpyxl) lancé chaque jour à 6 h UTC par **GitHub Actions**, puis publication automatique sur **Netlify** (page statique, graphiques Chart.js). Chaque exécution : (1) télécharge les séries ; (2) les ramène en mensuel (dernière valeur connue du mois) ; (3) calcule scores, régimes, valorisation, contributions, allocation et test historique ; (4) contrôle par test automatisé que la somme des contributions égale la variation du score ; (5) enregistre `data.json`. **Robustesse** : si une source échoue, la dernière valeur connue est conservée et l'échec est signalé sur le site.

## 4. Normalisation et pondération (attendu 4)

- **Z-score sur 10 ans glissants** (120 mois, 36 au minimum), **écrêté à ±3**, converti en sous-score **(z + 3) / 6 × 100** : 50 = moyenne décennale de la zone. Préféré au Min-Max, sensible aux extrêmes (2008, 2020) ; la fenêtre de 10 ans, imposée par la série la plus courte, suit les changements de régime de taux.
- **Inversion pour le risque** : VIX, spread, GPR et Brent entrent avec un signe négatif. **Cible** : l'inflation est mesurée par son écart absolu à 2 % ; une inflation trop basse est pénalisée comme une inflation trop forte.
- **Valorisation** : Z-score sur l'historique long (fenêtre croissante depuis 2003), les cycles de valorisation durant plusieurs décennies.

## 5. Construction du score global et choix des pondérations (attendu 5)

- **Score de zone** = Σ poids × sous-score, soit 80 % d'indicateurs de zone et 20 % de socle mondial. Les poids **30 / 20 / 30 / 20** sont fixés par famille : raisonner par famille neutralise la double comptabilisation d'indicateurs corrélés (PIB et CLI ; VIX et spread) ; l'inflation, seule de sa famille, pèse 20 %.
- **Score mondial** = moyenne des zones pondérée par la **capitalisation** (États-Unis 84 %, zone euro 9 %, Japon 7 %, parts MSCI ACWI renormalisées) : la lecture d'un investisseur. Le site propose aussi des **parts égales** (lecture économique), la pondération capi faisant du score mondial un score quasi américain.
- **Régime** : croissance = moyenne des sous-scores PIB et CLI (seuil 50) ; inflation en glissement annuel (seuil 2,5 %). Quatre régimes, chacun avec une base A/O/R/L : expansion 65/25/5/5, surchauffe 50/10/30/10, ralentissement 35/50/5/10, stagflation 30/15/30/25.
- **Allocation en trois étapes** : base du régime → climat (score < 40 : actions −10 vers L ; ≥ 60 : +5) → valorisation (attrait actions < 35 : −10 vers O si attrait O ≥ 50, sinon vers L ; > 65 : +5). Préférence géographique par classement des scores de zone.
- **Dynamique** : variations à 1, 3 et 12 mois ; contribution = poids de zone × poids de l'indicateur × variation du sous-score, dont la somme égale exactement la variation du score.

## 6. Analyse et interprétation (attendu 6)

**Quels indicateurs pèsent le plus ?** *Par construction*, en pondération capi, les cinq indicateurs américains font 67 % du score mondial (inflation US 16,8 %, chacun des quatre autres 12,6 %), le socle 20 %, la zone euro 7,2 % et le Japon 5,6 %. *En pratique*, ce qui fait bouger le score est plus concentré (contributions en points de score) :

| Horizon | Δ score | Principaux soutiens | Principaux freins |
|-----------|----:|--------------------------|--------------------------|
| Niveau (écart à 50) | +1,7 | CLI US (+2,2), spread de crédit (+1,0), pente US (+0,7) | Tendance actions US (−1,6), VIX (−0,7), GPR (−0,6) |
| 1 mois | −0,5 | Brent (+1,3), inflation US (+0,4) | Tendance actions US (−1,3), VIX (−0,6) |
| 3 mois | −4,4 | Brent (+0,4), inflation US (+0,4) | Tendance actions US (−2,5), VIX (−1,1), GPR (−0,4) |
| 12 mois | −3,9 | CLI US (+1,8), pente US (+1,4), crédit (+0,4) | Tendance actions US (−3,3), inflation US (−1,1), VIX (−1,0) |

La **tendance du S&P 500** est le premier moteur sur tous les horizons (forte variabilité et poids américain). Le **sentiment de marché** (actions, VIX) se dégrade alors que les **fondamentaux** (CLI, pente, crédit) restent porteurs.

**Quels signaux aujourd'hui ?**

- **Climat neutre, en dégradation** : score mondial **51,7/100** (54,3 à parts égales), −4,4 points sur 3 mois, dans la zone sans ajustement (40-60). VIX à 24,6.
- **Surchauffe**, confirmée sur deux mois : croissance 56,8 > 50, inflation 3,3 % > 2,5 % (États-Unis 3,3 %, zone euro 4,0 %). Le Japon (2,1 %) est seul en expansion.
- **Actions très chères** : CAPE 39,4 ; rendement des bénéfices 2,5 % < taux réel 2,9 %, soit une prime de **−0,34 point** ; attrait **9,7/100**. Obligations attractives (attrait 75,0 ; taux réel US 2,9 %).
- **Lecture d'allocation : A 40 / O 20 / R 30 / L 10** (base surchauffe 50/10/30/10, puis −10 points d'actions vers les obligations pour cause de valorisation), contre 60/40 en référence. **Géographie** : surpondérer le Japon (61,3, porté par une inflation proche de 2 % et une courbe pentue), neutre États-Unis (51,1), sous-pondérer la zone euro (50,5).

**Test historique** (illustration, non preuve ; actifs américains) : en 2022, −9,3 % contre −15,1 % pour le 60/40 (perte maximale −10,8 % contre −18,8 %), grâce à des obligations limitées et 30 % d'actifs réels ; en 2020, +12,2 % contre +16,2 % : la règle amortit les baisses mais rate une partie des rebonds rapides. En 2008, −17,2 % contre −19,6 %, mais ce gain s'inverse dans les trois autres variantes (parts égales ou régime confirmé : −21,1 % à −26,9 %) : seul 2022 est robuste.

## Limites

Le site n'est **pas une recommandation d'investissement**. Chine exclue (présente via le GPR) ; valorisation des actions fondée sur le seul **CAPE américain** ; **seuils** (40, 60, 35, 65, 2,5 %) et bases par régime **fixés a priori**, non calibrés, pour éviter le sur-ajustement ; **flux de capitaux absents** ; CLI zone euro approché par quatre pays ; séries datées par période de référence et non de publication, ce qui flatte le test historique (PIB notamment) ; normalisation par zone : un score élevé signifie « bon au regard de son passé », pas « meilleur que les autres zones ».
