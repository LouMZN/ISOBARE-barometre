# Format de `site/data.json`

Contrat entre le script de collecte (`collect/collect.py`) et la page
(`site/index.html`). **Le script fait foi** : ce document décrit le fichier tel
qu'il le produit. La page ne fait aucun calcul de score ; elle affiche ce que le
script a calculé selon la note de cadrage v4. Seules mises en forme côté page :
valeurs brutes affichées (glissement annuel, tendance sur 12 mois) recalculées à
partir du bloc `brut`, et contrôle « somme des contributions = variation ».

## Conventions

- Mois au format `"AAAA-MM"`. Mois de référence : `mois_de_calcul`.
- Codes de zone : `us`, `ez`, `jp`.
- Codes d'indicateur de zone : `pib`, `cli`, `inflation`, `actions`, `pente`.
- Codes du socle de risque : `vix`, `credit`, `gpr`, `brent`.
- Régimes : `"Expansion"`, `"Surchauffe"`, `"Ralentissement"`, `"Stagflation"`.
- Pondérations du score mondial : `capi` (84 / 9 / 7) et `egal` (1/3 chacune).
- Allocation : objet `{"A": actions, "O": obligations d'État, "R": actifs réels,
  "L": liquidités}` en points de pourcentage entiers, total 100.
- Deux règles de régime coexistent : `brut` (régime du mois, règle de la note)
  et `confirme` (changement acté après deux mois consécutifs, piste de la note).
  La page affiche `brut` par défaut.
- Séries historiques : objet `{"dates": [...], "valeurs": [...]}` depuis 2007.

## Structure

```jsonc
{
  "genere_le": "2026-11-19T16:29:49Z",       // horodatage UTC de la collecte
  "mois_de_calcul": "2026-11",                // dernier mois où tous les sous-scores existent

  "parametres": {
    "ponderations": {"capi": {"us": 0.84, "ez": 0.09, "jp": 0.07}, "egal": {...}},
    "poids_zone":  {"pib": 0.15, "cli": 0.15, "inflation": 0.20, "actions": 0.15, "pente": 0.15},
    "poids_socle": {"vix": 0.05, "credit": 0.05, "gpr": 0.05, "brent": 0.05},
    "bases_regime": {"Expansion": {"A": 65, "O": 25, "R": 5, "L": 5}, ...},
    "seuil_croissance": 50, "seuil_inflation": 2.5, "fenetre_climat_mois": 120
  },
  "libelles": {"zones": {"us": "États-Unis", ...}, "indicateurs": {"pib": "Croissance du PIB", ...}},

  "sources": [
    {"cle": "us_pib", "groupe": "États-Unis", "serie": "PIB réel", "source": "FRED, GDPC1",
     "statut": "OK",                  // "OK" | "OK (copie de secours)" | "ÉCHEC : ..."
     "derniere_date": "2026-09",      // mois de la dernière observation (PIB : dernier mois du trimestre)
     "derniere_valeur": 24611.077,
     "erreur": "..."}                 // présent seulement en cas d'échec
  ],
  "sources_en_echec": [],             // libellés des séries en échec

  "zones": {
    "us": {
      "nom": "États-Unis",
      "score": 51.11,
      "variations": {
        "1m":  {"variation": -0.53, "phrase": "Sur un mois, ...",
                "contributions": [{"zone": "us", "indicateur": "pib",
                                   "libelle": "Croissance du PIB (États-Unis)", "contribution": -0.0022}, ...]},
        "3m":  {...}, "12m": {...}
      },
      "niveau": {"ecart_a_50": 1.11, "contributions": [...]},
      "sous_scores": {"pib": 46.99, "cli": 67.44, "inflation": 50.07, "actions": 36.91, "pente": 56.36,
                      "vix": 36.06, "credit": 69.52, "gpr": 38.41, "brent": 54.82},
      "croissance": 57.22,            // moyenne des sous-scores pib et cli
      "inflation": 3.29,              // glissement annuel, en %
      "regime": "Surchauffe", "regime_confirme": "Surchauffe",
      "trajectoire_6m": [{"mois": "2026-05", "croissance": 57.49, "inflation": 3.82}, ...],  // 7 points
      "historique": {"dates": [...], "valeurs": [...]}   // score mensuel
    },
    "ez": {...}, "jp": {...}
  },

  "monde": {
    "capi": {
      "score", "variations", "niveau", "croissance", "inflation",
      "regime", "regime_confirme", "trajectoire_6m", "historique",   // comme pour une zone
      "historique_regime": {"dates": [...], "valeurs": ["Expansion", ...]},
      "historique_regime_confirme": {...},
      "allocation": {
        "brut": {"finale": {"A": 40, "O": 20, "R": 30, "L": 10},
                 "etapes": [{"etape": "1. Base du régime", "motif": "Régime mondial : Surchauffe",
                             "A": 50, "O": 10, "R": 30, "L": 10}, ...]},   // 3 étapes
        "confirme": {...}
      },
      "test_historique": {
        "brut": {
          "2008": {"disponible": true, "periode": "2008-01 à 2008-12",
                   "perf_barometre": -17.24, "perf_60_40": -19.63,          // en %
                   "perte_max_barometre": -22.28, "perte_max_60_40": -22.44,  // en %
                   "mois": [{"mois": "2008-01", "regime": "Surchauffe", "A": 50, "O": 10, "R": 30, "L": 10,
                             "barometre": 97.34, "ref_60_40": 97.33}, ...]},  // base 100 avant le 1er mois
          "2020": {...}, "2022": {...}
        },
        "confirme": {...}
      }
    },
    "egal": {...}                     // même structure, pondération égale
  },

  "valorisation": {
    "prime_de_risque_actions": -0.35, // 100 / CAPE − DFII10, en points
    "attrait_actions": 9.57,          // 0-100, Z-score sur l'historique long
    "cape": 39.37,
    "taux_reels_10a": {"us": 2.89, "ez": -0.59, "jp": 1.61},
    "attrait_obligations_zones": {"us": 80.62, "ez": 46.65, "jp": 54.97},
    "attrait_obligations": {"capi": 75.77, "egal": 60.75},
    "historique_attrait_actions": {"dates": [...], "valeurs": [...]}
  },

  "preference_geographique": [       // trié par score de climat décroissant (note v4)
    {"zone": "jp", "nom": "Japon", "score": 57.7,
     "variation_3m": -10.96, "regime": "Expansion",   // pour information, sans effet sur le rang
     "rang": 1, "position": "Surpondérer"}, ...       // 1er : Surpondérer, dernier : Sous-pondérer
  ],

  "limites": ["...", ...],

  "brut": {                           // séries mensuelles brutes, une valeur par mois depuis "debut"
    "vix": {"debut": "1990-01-01", "valeurs": [25.36, ...]}, ...
  }
}
```

## Règles à respecter côté collecte

- Si une source échoue : reprendre la série du `brut` précédent, mettre
  `statut: "ÉCHEC : dernière valeur du data.json précédent conservée"` et
  renseigner `erreur`. La page affiche alors un bandeau d'alerte.
- La somme des contributions doit égaler la variation du score (ou l'écart à 50
  en mode niveau) : la page le vérifie et affiche un avertissement si l'écart
  dépasse 0,05 point.
