"""Tests du baromètre : la somme des contributions doit égaler la variation du score.

Lancement : python -m unittest discover -s tests -v
"""

import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "collect"))
import collect as c  # noqa: E402

DATA = RACINE / "site" / "data.json"
HORIZONS = (1, 3, 12)


def sous_scores_aleatoires(graine, n=40):
    """Sous-scores fictifs entre 0 et 100, mêmes colonnes que le vrai calcul."""
    rng = np.random.default_rng(graine)
    colonnes = [(z, i) for z in c.ZONES for i in c.POIDS_ZONE] + \
               [("socle", i) for i in c.POIDS_SOCLE]
    idx = pd.date_range("2020-01-01", periods=n, freq="MS")
    return pd.DataFrame(rng.uniform(0, 100, (n, len(colonnes))), index=idx,
                        columns=pd.MultiIndex.from_tuples(colonnes))


class TestPoids(unittest.TestCase):
    def test_poids_somment_a_un(self):
        self.assertAlmostEqual(sum(c.POIDS_ZONE.values()) + sum(c.POIDS_SOCLE.values()), 1)
        for poids in c.PONDERATIONS.values():
            self.assertAlmostEqual(sum(poids.values()), 1)

    def test_bases_regime_somment_a_100(self):
        for base in c.BASES.values():
            self.assertEqual(sum(base.values()), 100)


class TestContributionsSynthetiques(unittest.TestCase):
    """Données aléatoires : identité exacte, à la précision machine près."""

    def test_monde(self):
        for graine in range(20):
            ss = sous_scores_aleatoires(graine)
            sz = c.scores_zones(ss)
            for nom, poids in c.PONDERATIONS.items():
                monde = c.score_monde(sz, poids)
                for h in HORIZONS:
                    contrib = c.contributions(ss, h, poids=poids)
                    variation = monde.iloc[-1] - monde.iloc[-1 - h]
                    self.assertAlmostEqual(contrib.sum(), variation, places=9,
                                           msg=f"{nom}, {h} mois, graine {graine}")

    def test_zones(self):
        for graine in range(20):
            ss = sous_scores_aleatoires(graine)
            sz = c.scores_zones(ss)
            for z in c.ZONES:
                for h in HORIZONS:
                    contrib = c.contributions(ss, h, zone=z)
                    variation = sz[z].iloc[-1] - sz[z].iloc[-1 - h]
                    self.assertAlmostEqual(contrib.sum(), variation, places=9)

    def test_mode_niveau(self):
        ss = sous_scores_aleatoires(7)
        sz = c.scores_zones(ss)
        for poids in c.PONDERATIONS.values():
            contrib = c.contributions(ss, 0, poids=poids, niveau=True)
            self.assertAlmostEqual(contrib.sum(), c.score_monde(sz, poids).iloc[-1] - 50, places=9)


class TestAllocation(unittest.TestCase):
    def test_total_100_et_aucune_poche_negative(self):
        for reg in c.BASES:
            for score in (20, 39.9, 40, 59.9, 60, 90, float("nan")):
                for attrait_a in (10, 34.9, 35, 65, 65.1, 90, float("nan")):
                    for attrait_o in (20, 50, 80):
                        a, etapes = c.allocation(reg, score, attrait_a, attrait_o)
                        self.assertEqual(sum(a.values()), 100)
                        self.assertTrue(all(v >= 0 for v in a.values()))
                        self.assertEqual(len(etapes), 3)

    def test_regles(self):
        # Ralentissement 35/50/5/10 ; score < 40 : A -10 vers L ; attrait A < 35, O >= 50 : -10 vers O
        a, _ = c.allocation("Ralentissement", 30, 20, 60)
        self.assertEqual(a, {"A": 15, "O": 60, "R": 5, "L": 20})
        # Expansion 65/25/5/5 ; score >= 60 : +5 (pris sur L) ; attrait A > 65 : +5 (pris sur O)
        a, _ = c.allocation("Expansion", 70, 80, 50)
        self.assertEqual(a, {"A": 75, "O": 20, "R": 5, "L": 0})

    def test_regime_confirme(self):
        brut = pd.Series(["Expansion", "Surchauffe", "Expansion", "Surchauffe", "Surchauffe"])
        self.assertEqual(list(c.regime_confirme(brut)),
                         ["Expansion", "Expansion", "Expansion", "Expansion", "Surchauffe"])


class TestPreferenceGeo(unittest.TestCase):
    """Note v4 : classement des zones par score de climat uniquement."""

    def test_classement_par_score_seul(self):
        idx = pd.date_range("2020-01-01", periods=4, freq="MS")
        # us : score le plus haut mais en forte baisse et en stagflation ;
        # jp : score le plus bas mais en forte hausse et en expansion.
        sz = pd.DataFrame({"us": [90, 80, 70, 60], "ez": [50, 50, 50, 55], "jp": [10, 20, 30, 54]},
                          index=idx)
        regimes = {"us": pd.Series(["Stagflation"] * 4, index=idx),
                   "ez": pd.Series(["Ralentissement"] * 4, index=idx),
                   "jp": pd.Series(["Expansion"] * 4, index=idx)}
        lignes = c.preference_geo(sz, regimes, 3)
        self.assertEqual([l["zone"] for l in lignes], ["us", "ez", "jp"])
        self.assertEqual([l["rang"] for l in lignes], [1, 2, 3])
        self.assertEqual([l["position"] for l in lignes], ["Surpondérer", "Neutre", "Sous-pondérer"])
        self.assertNotIn("points", lignes[0])
        self.assertEqual(lignes[2]["variation_3m"], 44)


@unittest.skipUnless(DATA.exists(), "site/data.json absent : lancer collect.py d'abord")
class TestDataJson(unittest.TestCase):
    """Vérifie les chiffres publiés (arrondis à 4 décimales)."""

    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(DATA.read_text(encoding="utf-8"))

    def verifier(self, bloc, nom):
        for h, v in bloc["variations"].items():
            somme = sum(x["contribution"] for x in v["contributions"])
            self.assertAlmostEqual(somme, v["variation"], delta=0.005, msg=f"{nom} {h}")
        somme = sum(x["contribution"] for x in bloc["niveau"]["contributions"])
        self.assertAlmostEqual(somme, bloc["niveau"]["ecart_a_50"], delta=0.005, msg=f"{nom} niveau")

    def test_monde(self):
        for k, bloc in self.d["monde"].items():
            self.verifier(bloc, f"monde {k}")

    def test_zones(self):
        for z, bloc in self.d["zones"].items():
            self.verifier(bloc, f"zone {z}")

    def test_preference_geo_triee_par_score(self):
        pg = self.d["preference_geographique"]
        scores = [l["score"] for l in pg]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(scores, sorted((self.d["zones"][z]["score"] for z in self.d["zones"]),
                                        reverse=True))
        self.assertNotIn("bonus_regime", self.d["parametres"])

    def test_scores_bornes(self):
        for bloc in list(self.d["monde"].values()) + list(self.d["zones"].values()):
            self.assertTrue(0 <= bloc["score"] <= 100)


if __name__ == "__main__":
    unittest.main()
