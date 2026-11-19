# Projet : Baromètre synthétique mondial (KEDGE, gestion d'actifs)
Référence unique : docs/Barometre_note_de_cadrage_v4.docx. En cas de doute, 
la note fait foi.
Rendu attendu : site Netlify fonctionnel + note PDF de 2 pages max.
## Architecture- collect/ : script Python (pandas, requests, openpyxl/xlrd) -> 
site/data.json- site/ : index.html statique + Chart.js (CDN), lit data.json, aucune clé 
d'API- .github/workflows/daily.yml : cron quotidien + workflow_dispatch, lance le 
script,
commit data.json (permissions: contents: write)- Netlify publie le dossier site/ (pas de commande de build)
## Règles de calcul (note v4)- Zones : États-Unis, zone euro, Japon. Score de zone = 80 % indicateurs de 
zone + 20 % socle mondial.- Poids : PIB 15, CLI OCDE 15, écart inflation à 2 % 20 (absolu, inversé), 
tendance actions 15
(cours / moyenne 12 mois), pente 10a-3m 15 ; socle : VIX, BAA10Y, GPR, 
Brent vs moyenne 12 mois (5 chacun, inversés).- Tout en mensuel (dernière valeur connue du mois).- Normalisation climat : Z-score sur 10 ans glissants, écrêté à ±3, score = 
(z+3)/6*100.- Valorisation : Z-score sur l'historique long. Actions = 1/CAPE - DFII10 ; 
obligations = taux réel 10 ans par zone.- Score mondial : pondération capi 84/9/7 par défaut + option parts égales 
(sélecteur sur le site).- Régimes : croissance = moyenne sous-scores PIB et CLI (seuil 50) ; 
inflation glissement annuel (seuil 2,5 %).
Bases A/O/R/L : Expansion 65/25/5/5, Surchauffe 50/10/30/10, Ralentissement 
35/50/5/10, Stagflation 30/15/30/25.- Allocation : base régime -> climat (<40 : actions -10 vers L ; >=60 : +5) 
> valorisation
(attrait actions <35 : -10 vers O si attrait O >=50 sinon L ; >65 : +5). 
Préférence géographique par classement des zones.- Contributions : poids zone x poids indicateur x variation du sous-score ; 
leur somme doit égaler la variation du score (à tester).- Variations 1, 3, 12 mois ; mode "niveau" (écart à 50) ; phrase automatique 
"porté par A, freiné par B".
- Test historique 2008 / 2020 / 2022 contre le 60/40, présenté comme une 
illustration.
## Robustesse- Si une source échoue, garder la dernière valeur du data.json précédent et 
le signaler.- Afficher la date de la dernière donnée de chaque série.- Le site n'est pas une recommandation d'investissement : afficher les 
limites (Chine exclue,
CAPE US seulement, seuils fixés a priori, flux de capitaux absents).
## Façon de travailler- Avancer par étapes courtes, tester chaque étape avant de passer à la 
suivante.- Signaler clairement toute série introuvable et proposer un remplacement 
plutôt que d'inventer des données.- Code simple, pas de framework, pas de base de données.- Travailler et pousser directement sur la branche main, sans pull request.- L'utilisateur débute : expliquer en une ou deux phrases simples ce qui a 
été fait et ce qu'il doit faire ensuite
