---
title: "Baromètre synthétique mondial"
subtitle: "KEDGE BS – Gestion d'actifs 2025-2026 · Note méthodologique et lecture au 19 novembre 2026"
lang: fr
---

**Site : [https://barometre-kedge-3.netlify.app](https://barometre-kedge-3.netlify.app)** — mise à jour quotidienne automatique ; données de cette note : fichier `data.json` généré le 19/11/2026, mois de calcul novembre 2026, 28 séries sur 28 collectées sans échec.

Le baromètre éclaire l'allocation entre actions (A), obligations d'État (O), actifs réels (R) et liquidités (L), et le choix des zones. Il répond à trois questions : *quel est le climat ?* (score 0-100), *est-il déjà dans les prix ?* (valorisation), *dans quelle direction va-t-on ?* (régime, dynamique, contributions).

## 1. Choix des indicateurs

Neuf indicateurs (19 séries) couvrent sept des huit familles citées par le sujet : PIB, inflation, indices boursiers, volatilité, taux, matières premières, risque/incertitude. Trois zones : États-Unis, zone euro, Japon. La Chine est écartée faute de séries gratuites et automatisables (inflation, courbe et indice boursier), mais reste présente via le risque géopolitique.

| Famille (poids) | Indicateur | Mesure retenue | Poids | Sens |
|--------------|---------------|------------------------------|----:|---|
| Croissance (30 %) | PIB réel | Glissement annuel | 15 % | + |
| | Indicateur avancé OCDE (CLI) | Niveau | 15 % | + |
| Inflation (20 %) | Écart à la cible | − \|inflation − 2 %\| (PCE US, IPCH, IPC Japon) | 20 % | − |
| Marchés (30 %) | Tendance actions | Cours / moyenne 12 mois (S&P 500, Euro Stoxx 50, Nikkei 225) | 15 % | + |
| | Pente de la courbe | Taux 10 ans − taux 3 mois | 15 % | + |
| Risque – socle mondial (20 %) | VIX ; spread Baa − 10 ans US ; risque géopolitique (GPR) ; Brent / moyenne 12 mois | Niveau (Brent : écart à la tendance) | 4 × 5 % | − |

Le socle de risque est commun aux trois zones. Hors score, le **pilier valorisation** mesure l'attrait des actions (prime de risque de Shiller : 1/CAPE − taux réel 10 ans US) et des obligations (taux réel 10 ans par zone).

## 2. Sources de données

Uniquement des sources publiques et gratuites, sans clé d'API exposée :

- **FRED** (Fed de Saint-Louis, CSV) : VIXCLS, BAA10Y, DCOILBRENTEU, GDPC1, PCEPI, SP500, T10Y3M, NIKKEI225, DFII10, TB3MS.
- **BCE – ECB Data Portal** (API SDMX) : IPCH zone euro, Euro Stoxx 50, courbe AAA (pente 10 ans − 3 mois et taux 10 ans). **Eurostat** : PIB EA20 (namq_10_gdp).
- **OCDE** (API SDMX) : CLI (zone euro = composite Allemagne, France, Italie, Espagne), PIB trimestriel Japon, taux long et court japonais. **DBnomics** : IPC Japon (Statistics Japan).
- **Fichiers en ligne** : indice GPR de Caldara et Iacoviello (xls) ; données de R. Shiller (ie_data.xls : CAPE, S&P long, dividendes, taux 10 ans, IPC).

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
