# Format de `site/data.json`

Contrat entre le script de collecte (`collect/`) et la page (`site/index.html`).
La page ne fait aucun calcul de score : elle affiche ce que le script a calculé
selon la note de cadrage v4. Seules exceptions, de simple arithmétique sur les
données fournies : les **contributions** (poids × variation des sous-scores),
les **variations** 1 / 3 / 12 mois et le **classement** des zones par score.

## Conventions

- Toutes les séries temporelles sont des tableaux de même longueur que `dates`
  (un élément par mois, du plus ancien au plus récent). Valeur absente : `null`.
- `dates` : mois au format `"AAAA-MM"`. Le mois de référence affiché est le
  dernier mois où `monde.cap.score` n'est pas `null`. L'historique doit couvrir
  au moins 2016 à aujourd'hui (et commencer vers 2006 pour la fenêtre de 10 ans).
- Codes de zone : `us`, `ea`, `jp`.
- Codes d'indicateur de zone : `gdp` (PIB), `cli` (indicateur avancé OCDE),
  `infl` (inflation), `eq` (tendance actions), `slope` (pente 10 ans − 3 mois).
- Codes du socle de risque : `vix`, `baa`, `gpr`, `oil`.
- Codes de régime : `expansion`, `surchauffe`, `ralentissement`, `stagflation`.
- Répartitions d'allocation : tableau `[actions, obligations d'État, actifs réels, liquidités]`
  en points de pourcentage entiers, total 100.

## Structure

```jsonc
{
  "version": 1,
  "genere_le": "2026-11-19T06:12:00Z",   // horodatage UTC de la collecte
  "simule": false,                        // true uniquement pour un jeu de test (bandeau rouge sur le site)
  "dates": ["2006-01", "...", "2026-10"],

  "poids": {
    "zones": {"us": 0.84, "ea": 0.09, "jp": 0.07},   // pondération capitalisation
    "maj_capi": "2026-08",                            // date des fiches MSCI utilisées
    "indicateurs": {"gdp": 0.15, "cli": 0.15, "infl": 0.20, "eq": 0.15, "slope": 0.15},
    "risque": {"vix": 0.05, "baa": 0.05, "gpr": 0.05, "oil": 0.05}
  },

  "zones": {
    "us": {
      "score": [],                 // score de climat de la zone, 0-100
      "croissance": [],            // moyenne des sous-scores gdp et cli
      "sous_scores": {"gdp": [], "cli": [], "infl": [], "eq": [], "slope": []},   // 0-100
      "brut": {
        "gdp": [],    // glissement annuel du PIB réel, en %
        "cli": [],    // indice CLI (100 = tendance)
        "infl": [],   // inflation sur un an, en % (sert aussi à l'axe du quadrant)
        "eq": [],     // cours / moyenne 12 mois − 1, en fraction (0.054 = +5,4 %)
        "slope": []   // taux 10 ans − taux 3 mois, en points de %
      },
      "taux_reel": [],             // taux réel 10 ans, en %
      "attrait_oblig": [],         // 0-100, Z-score sur l'historique long
      "regime": []                 // code de régime de la zone
    },
    "ea": {}, "jp": {}
  },

  "risque": {
    "score": [],                                         // moyenne des 4 sous-scores
    "sous_scores": {"vix": [], "baa": [], "gpr": [], "oil": []},   // 0-100, inversés
    "brut": {
      "vix": [],   // points
      "baa": [],   // points de %
      "gpr": [],   // indice
      "oil": []    // Brent / moyenne 12 mois − 1, en fraction
    }
  },

  "valorisation": {
    "cape": [],              // PER de Shiller
    "taux_reel_us": [],      // DFII10, en %
    "prime": [],             // 100 / CAPE − taux réel US, en points de %
    "attrait_actions": []    // 0-100, Z-score sur l'historique long
  },

  "monde": {
    "cap": {                          // pondération par capitalisation
      "score": [], "croissance": [], "inflation": [], "attrait_oblig": [], "regime": [],
      "allocation": {
        "etapes": [
          {"etape": "regime", "regime": "ralentissement", "repartition": [35, 50, 5, 10]},
          {"etape": "climat", "valeur": 47.2, "regle": "neutre", "repartition": [35, 50, 5, 10]},
          //   regle : "degrade" (< 40) | "neutre" | "favorable" (>= 60)
          {"etape": "valorisation", "valeur": 22.4, "regle": "cheres", "vers": "oblig",
           "repartition": [25, 60, 5, 10]}
          //   regle : "cheres" (< 35) | "normale" | "bon_marche" (> 65)
          //   vers  : "oblig" | "liquidites" | null
        ],
        "finale": [25, 60, 5, 10]
      }
    },
    "egal": {}                        // même structure, pondération égale (1/3 chacune)
  },

  "series": [
    {
      "id": "us_gdp",
      "groupe": "us",              // us | ea | jp | socle | valorisation
      "indicateur": "gdp",         // code d'indicateur, ou cape / tips / taux10 pour la valorisation
      "libelle": "PIB réel",
      "source": "FRED",
      "code": "GDPC1",
      "frequence": "trimestrielle",   // quotidienne | mensuelle | trimestrielle
      "derniere_date": "2026-07-01",  // date de la dernière observation de la source
      "statut": "ok",                 // ok | retard | secours
      "message": ""                   // ex. « source indisponible, valeur du 18/11 conservée »
    }
  ],

  "alertes": []                     // messages libres affichés en tête de page
}
```

## Règles à respecter côté collecte

- Si une source échoue : reprendre la série du `data.json` précédent, mettre
  `statut: "secours"` et expliquer dans `message`.
- La somme des contributions doit égaler la variation du score : la page le
  vérifie et affiche un avertissement si l'écart dépasse 0,05 point.
  Cela suppose `score zone = Σ poids indicateur × sous-score + Σ poids risque × sous-score risque`
  et `score monde = Σ poids zone × score zone`.
