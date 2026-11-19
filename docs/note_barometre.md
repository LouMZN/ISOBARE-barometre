---
title: "Isobare"
subtitle: "KEDGE BS – Gestion d'actifs 2025-2026 · Note méthodologique et lecture au 19 novembre 2026"
lang: fr
---

**Site : [https://barometre-kedge-3.netlify.app](https://barometre-kedge-3.netlify.app)** — mise à jour quotidienne automatique ; données de cette note : fichier `data.json` généré le 19/11/2026, mois de calcul novembre 2026, 28 séries sur 28 collectées sans échec.

Le baromètre éclaire l'allocation entre actions (A), obligations d'État (O), actifs réels (R) et liquidités (L), et le choix des zones. Il répond à trois questions : *quel est le climat ?* (score 0-100), *est-il déjà dans les prix ?* (valorisation), *dans quelle direction va-t-on ?* (régime, dynamique, contributions).

## 1. Choix des indicateurs

Neuf indicateurs (19 séries) couvrent sept des huit familles citées par le sujet : PIB, inflation, indices boursiers, volatilité, taux, matières premières, risque/incertitude. Trois zones : États-Unis, zone euro, Japon. La Chine est écartée faute de séries gratuites et automatisables (inflation, courbe et indice boursier), mais reste présente via le risque géopolitique.

Chaque indicateur répond à une question précise de l'investisseur ; le sens indique si une hausse améliore (+) ou dégrade (−) le score.

| Indicateur (poids, sens) | Série et mesure | Pourquoi cet indicateur |
|------------------|------------------------|------------------------------------------|
| **Croissance (30 %)** | | |
| PIB réel (15 %, +) | GDPC1, PIB EA20, PIB Japon ; glissement annuel | Mesure directe de l'activité, socle des bénéfices des entreprises. Publié par trimestre et avec retard, d'où l'indicateur suivant. |
| Indicateur avancé OCDE – CLI (15 %, +) | CLI OCDE par zone ; niveau | Anticipe de 6 à 9 mois les retournements du cycle et compense le retard du PIB ; méthode identique pour les trois zones. |
| **Inflation (20 %)** | | |
| Écart d'inflation à 2 % (20 %, −) | Déflateur PCE (US), IPCH (zone euro), IPC (Japon) ; − \|glissement annuel − 2 %\| | La cible de 2 % guide les banques centrales : au-dessus, resserrement monétaire ; en dessous, demande faible. Chaque zone est mesurée sur l'indice que cible sa banque centrale. |
| **Marchés financiers (30 %)** | | |
| Tendance actions (15 %, +) | S&P 500, Euro Stoxx 50, Nikkei 225 ; cours / moyenne 12 mois | Résume les anticipations de bénéfices des investisseurs ; le ratio, sans unité, rend comparables des indices de niveaux très différents. |
| Pente 10 ans − 3 mois (15 %, +) | T10Y3M (US), courbe AAA BCE, taux OCDE (Japon) | Meilleur indicateur avancé reconnu des récessions : une courbe inversée les a précédées. Seule mesure de la courbe homogène entre les trois zones. |
| **Risque – socle mondial (20 %)** | | |
| VIX (5 %, −) | VIXCLS ; niveau | Volatilité implicite à 30 jours du S&P 500 : thermomètre mondial de l'aversion au risque. |
| Spread de crédit (5 %, −) | BAA10Y : Moody's Baa − 10 ans US | Prix du risque de défaut et coût de financement des entreprises. Préféré au spread haut rendement, dont l'historique gratuit est tronqué à 3 ans. |
| Risque géopolitique (5 %, −) | GPR de Caldara et Iacoviello ; niveau | Seule mesure chiffrée, gratuite et mensuelle des tensions géopolitiques ; intègre la Chine, absente des zones. |
| Choc pétrolier (5 %, −) | Brent ; cours / moyenne 12 mois | Choc d'offre qui freine la croissance et relance l'inflation ; l'écart à la tendance isole le choc, que le niveau en dollars ne mesure pas. |
| **Valorisation (hors score, corrige l'allocation)** | | |
| Attrait des actions | 1/CAPE de Shiller − taux réel 10 ans US (DFII10) | Rendement des bénéfices lissé sur 10 ans comparé au placement réel sans risque : plus le CAPE est élevé, plus les rendements futurs tendent à être faibles. |
| Attrait des obligations | Taux réel 10 ans : TIPS (US), taux nominal − inflation (zone euro, Japon) | Rémunération réelle offerte par les obligations d'État, seule mesure comparable entre zones. |

**Écartés** : flux de capitaux (séries de référence payantes) ; taux directeurs et change, affichés en contexte car leur effet sur le climat est ambigu ; Chine (pas de séries gratuites d'inflation, de courbe et d'indice boursier).

## 2. Sources de données

Uniquement des sources publiques et gratuites, sans clé d'API exposée : **FRED** (Fed de Saint-Louis, fichiers CSV : VIX, spread Baa, Brent, PIB et PCE US, S&P 500, pente US, Nikkei 225, taux réel US, bons à 3 mois) ; **BCE – ECB Data Portal** (API SDMX : IPCH, Euro Stoxx 50, courbe AAA) ; **Eurostat** (PIB EA20) ; **OCDE** (API SDMX : CLI, PIB et taux japonais) ; **DBnomics** (IPC Japon) ; fichiers en ligne de **Caldara et Iacoviello** (GPR) et de **R. Shiller** (CAPE, S&P long, dividendes, taux 10 ans, IPC).

## 3. Méthode de collecte

Script **Python** (pandas, requests, xlrd/openpyxl) exécuté chaque jour à 6 h UTC par **GitHub Actions**, puis publication automatique sur **Netlify** (page statique + Chart.js). Chaque exécution : (1) télécharge les 28 séries ; (2) les ramène en mensuel (dernière valeur connue du mois) ; (3) calcule scores, régimes, valorisation, contributions, allocation et test historique ; (4) vérifie par test unitaire que la somme des contributions égale la variation du score ; (5) enregistre `data.json`. **Robustesse** : si une source échoue, la dernière valeur connue est conservée et l'échec est signalé sur le site ; la date de la dernière donnée de chaque série est affichée (aujourd'hui de 09/2026 pour les PIB du T3 à 11/2026 pour les marchés).

## 4. Normalisation et pondération

- **Z-score sur 10 ans glissants** (120 mois, 36 au minimum), **écrêté à ±3** et converti en sous-score : **(z + 3) / 6 × 100**. 50 = moyenne décennale de la zone. La fenêtre de 10 ans est imposée par la série la plus courte et suit les changements de régime de taux ; chaque zone est comparée à sa propre histoire.
- **Inversion pour le risque** : VIX, spread, GPR et Brent entrent avec un signe négatif. **Cible** : l'inflation est mesurée par son écart absolu à 2 %, une inflation trop basse étant aussi pénalisée qu'une inflation trop forte.
- **Valorisation** : Z-score sur l'historique long disponible (fenêtre croissante, depuis 2003), car les cycles de valorisation durent plusieurs décennies.
- **Pondérations 30 / 20 / 30 / 20** par famille (grille du cours). Raisonner par famille neutralise la double comptabilisation d'indicateurs corrélés (PIB et CLI ; VIX et spread). L'inflation, seul indicateur de sa famille, pèse 20 %.

## 5. Construction du score global

- **Score de zone** = 80 % indicateurs de zone + 20 % socle mondial : Σ poids × sous-score.
- **Score mondial** = moyenne des zones pondérée par la **capitalisation boursière** (États-Unis 84 %, zone euro 9 %, Japon 7 %, poids MSCI ACWI renormalisés) : c'est la lecture d'un investisseur. Le site propose aussi des **parts égales** (lecture économique), car la pondération capi fait du score mondial un score quasi américain.
- **Régime** : croissance = moyenne des sous-scores PIB et CLI (seuil 50) ; inflation en glissement annuel (seuil 2,5 %) → expansion, surchauffe, ralentissement ou stagflation (logique All Weather), avec une base A/O/R/L par régime (65/25/5/5 ; 50/10/30/10 ; 35/50/5/10 ; 30/15/30/25).
- **Allocation en trois étapes** : base du régime → climat (score < 40 : actions −10 vers L ; ≥ 60 : +5) → valorisation (attrait actions < 35 : −10 vers O si attrait O ≥ 50, sinon L ; > 65 : +5). Préférence géographique par classement des scores de zone.
- **Dynamique** : variations à 1, 3 et 12 mois ; contribution = poids de zone × poids de l'indicateur × variation du sous-score, dont la somme égale exactement la variation du score.

## 6. Analyse et interprétation

**Quels indicateurs pèsent le plus ?** *Par construction*, en pondération capi, les cinq indicateurs américains représentent 67 % du score mondial (inflation US 16,8 %, chacun des quatre autres 12,6 %), le socle 20 % (5 % par indicateur), la zone euro 7,2 % et le Japon 5,6 %. *En pratique*, ce qui fait bouger le score est plus concentré :

| Horizon | Δ score | Principaux soutiens | Principaux freins |
|-----------|----:|--------------------------|--------------------------|
| Niveau (écart à 50) | +1,5 | CLI US (+2,2), spread de crédit (+1,0), pente US (+0,8) | Tendance actions US (−1,6), VIX (−0,7), GPR (−0,6) |
| 3 mois | −4,6 | Brent (+0,4), inflation US (+0,4) | Tendance actions US (−2,5), VIX (−1,1), GPR (−0,4) |
| 12 mois | −4,2 | CLI US (+1,8), pente US (+1,4) | Tendance actions US (−3,3), inflation US (−1,1), VIX (−1,0) |

La **tendance du S&P 500** est le premier moteur du score sur toutes les périodes : forte sensibilité, combinée au poids américain. Le **sentiment de marché** (VIX, actions) se dégrade alors que les **fondamentaux** (CLI, pente, crédit) restent porteurs.

**Quels signaux aujourd'hui ?**

- **Climat neutre en dégradation** : score mondial **51,5/100** (53,1 à parts égales), −4,6 points sur 3 mois. Il reste dans la zone sans ajustement (40-60).
- **Régime de surchauffe**, confirmé : croissance 56,8 > 50 et inflation 3,2 % > 2,5 % (États-Unis 3,3 %, zone euro 4,0 %). Le Japon (inflation 1,2 %) est seul en expansion.
- **Actions très chères** : CAPE 39,4, prime de risque **−0,35 point** (rendement des bénéfices 2,5 % < taux réel 2,9 %), attrait **9,6/100**. Obligations attractives (attrait 75,8, taux réel US 2,9 %).
- **Lecture d'allocation : A 40 / O 20 / R 30 / L 10** (base surchauffe 50/10/30/10, puis −10 points d'actions vers les obligations pour cause de valorisation), contre 60/40 en référence. **Géographie** : surpondérer le Japon (57,7), neutre États-Unis (51,1), sous-pondérer la zone euro (50,5).

**Test historique** (illustration, non preuve ; actifs américains) : en 2022, −9,3 % contre −15,1 % pour le 60/40 (perte maximale −10,8 % contre −18,8 %), grâce à des obligations limitées à 10-25 % et à 30 % d'actifs réels (surchauffe puis stagflation) ; en 2008, −17,2 % contre −19,6 % ; en 2020, +12,2 % contre +16,2 % : la règle protège dans les baisses mais rate une partie des rebonds rapides.

## 7. Limites

Le site n'est **pas une recommandation d'investissement**. Chine exclue (présente via le GPR) ; valorisation des actions fondée sur le seul **CAPE américain** (≈ 84 % de la capitalisation des trois zones) ; **seuils** (40, 60, 35, 65, 2,5 %) et répartitions par régime **fixés a priori**, non calibrés pour éviter le sur-ajustement ; **flux de capitaux absents** (séries payantes) ; CLI zone euro approché par quatre pays ; séries datées par période de référence et non de publication, ce qui flatte le test historique (PIB notamment) ; normalisation par zone : un score élevé signifie « bon au regard de son passé », pas « meilleur que les autres ».
