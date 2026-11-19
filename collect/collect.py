"""Baromètre synthétique mondial : collecte et calculs (note de cadrage v4).

Étapes :
  1. collecte des séries (fonctions de test_sources.py) ; en cas d'échec d'une
     source, reprise de la dernière version enregistrée dans site/data.json ;
  2. passage en mensuel (dernière valeur connue du mois) ;
  3. normalisation : Z-score sur 10 ans glissants, écrêté à ±3, score 0-100 ;
  4. scores par zone (80 % zone + 20 % socle) et score mondial (capi / égal) ;
  5. régimes croissance / inflation (brut et confirmé après 2 mois) ;
  6. valorisation (Z-score sur l'historique long, fenêtre croissante) ;
  7. variations 1, 3, 12 mois, contributions, mode « niveau », phrase ;
  8. allocation en trois étapes et préférence géographique ;
  9. test historique 2008 / 2020 / 2022 contre le 60/40.

Lancement : python collect/collect.py  ->  site/data.json
"""

import functools
import io
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sources import (  # noqa: E402  fonctions de téléchargement déjà testées
    SHILLER_SECOURS, bce, cli_ocde, cli_zone_euro_composite, dbnomics, eurostat,
    fred, gpr, lien_shiller, pente_japon, pib_japon, taux_long_japon, telecharger)

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "site" / "data.json"
DEBUT = "1985-01-01"  # début du panel mensuel

# --------------------------------------------------------------------------
# Paramètres de la note v4
# --------------------------------------------------------------------------
ZONES = {"us": "États-Unis", "ez": "Zone euro", "jp": "Japon"}

# Poids des indicateurs dans chaque score de zone (somme = 1).
POIDS_ZONE = {"pib": 0.15, "cli": 0.15, "inflation": 0.20, "actions": 0.15, "pente": 0.15}
POIDS_SOCLE = {"vix": 0.05, "credit": 0.05, "gpr": 0.05, "brent": 0.05}
LIBELLES = {"pib": "Croissance du PIB", "cli": "Indicateur avancé OCDE",
            "inflation": "Écart d'inflation à 2 %", "actions": "Tendance actions",
            "pente": "Pente 10 ans - 3 mois", "vix": "VIX", "credit": "Spread de crédit Baa",
            "gpr": "Risque géopolitique", "brent": "Choc pétrolier (Brent)"}

PONDERATIONS = {"capi": {"us": 0.84, "ez": 0.09, "jp": 0.07},
                "egal": {"us": 1 / 3, "ez": 1 / 3, "jp": 1 / 3}}

FENETRE_CLIMAT = 120   # 10 ans glissants
MINI_OBS = 36          # minimum d'observations pour calculer un Z-score
SEUIL_CROISSANCE = 50
SEUIL_INFLATION = 2.5

BASES = {"Expansion": {"A": 65, "O": 25, "R": 5, "L": 5},
         "Surchauffe": {"A": 50, "O": 10, "R": 30, "L": 10},
         "Ralentissement": {"A": 35, "O": 50, "R": 5, "L": 10},
         "Stagflation": {"A": 30, "O": 15, "R": 30, "L": 25}}
# Hypothèse (non précisée par la note) : bonus de régime pour le classement des zones.
BONUS_REGIME = {"Expansion": 5, "Surchauffe": 0, "Ralentissement": 0, "Stagflation": -5}

EPISODES = {"2008": ("2008-01", "2008-12"), "2020": ("2020-01", "2020-12"),
            "2022": ("2022-01", "2022-12")}

LIMITES = [
    "Le baromètre éclaire la décision d'allocation ; ce n'est pas une recommandation d'investissement.",
    "Chine exclue faute de sources gratuites et automatisables (présente via le risque géopolitique).",
    "Valorisation des actions fondée sur le seul CAPE américain (≈ 84 % de la capitalisation des trois zones).",
    "Seuils (40, 60, 35, 65, 2,5 %) et répartitions par régime fixés a priori, non calibrés sur le passé.",
    "Flux de capitaux absents : séries de référence payantes.",
    "Zone euro : indicateur avancé approché par la moyenne pondérée Allemagne, France, Italie, Espagne.",
    "Séries datées par période de référence et non par date de publication : le test historique "
    "suppose les données connues plus tôt qu'en réalité (PIB notamment).",
    "Test historique : actifs américains, prix mensuels moyens (Shiller), obligations et actifs "
    "réels reconstitués à partir des taux ; illustration, pas une preuve.",
]


# --------------------------------------------------------------------------
# 1. Collecte
# --------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def shiller():
    """Fichier de Shiller (en ligne, sinon copie de secours). Renvoie (DataFrame, source)."""
    try:
        contenu = telecharger(lien_shiller(), essais=5).content
        source = "Shiller, shillerdata.com (ie_data.xls)"
    except Exception as e:  # noqa: BLE001
        print(f"  ! Shiller en ligne indisponible ({e}) : copie de secours")
        contenu = SHILLER_SECOURS.read_bytes()
        source = "Shiller, copie de secours data/backup/ie_data.xls"
    d = pd.read_excel(io.BytesIO(contenu), sheet_name="Data", skiprows=7)
    d = d[pd.to_numeric(d["Date"], errors="coerce").notna()].copy()
    annee = d["Date"].astype(float).astype(int)
    mois = ((d["Date"].astype(float) - annee) * 100).round().astype(int)
    d.index = pd.to_datetime(dict(year=annee, month=mois, day=1))
    d = d.rename(columns={"Rate GS10": "GS10"})
    return d[["P", "D", "CAPE", "GS10", "CPI"]].apply(pd.to_numeric, errors="coerce"), source


def col_shiller(col):
    return lambda: shiller()[0][col].dropna()


# clé : (groupe, libellé, source, fonction)
CATALOGUE = {
    # Socle mondial
    "vix": ("Socle", "VIX", "FRED, VIXCLS", lambda: fred("VIXCLS")),
    "baa10y": ("Socle", "Spread Baa - 10 ans", "FRED, BAA10Y", lambda: fred("BAA10Y")),
    "gpr": ("Socle", "Risque géopolitique (GPR)", "Iacoviello, data_gpr_export.xls", gpr),
    "brent": ("Socle", "Brent", "FRED, DCOILBRENTEU", lambda: fred("DCOILBRENTEU")),
    # États-Unis
    "us_pib": ("États-Unis", "PIB réel", "FRED, GDPC1", lambda: fred("GDPC1")),
    "us_cli": ("États-Unis", "CLI OCDE", "OCDE, DF_CLI USA", lambda: cli_ocde("USA")),
    "us_prix": ("États-Unis", "Déflateur PCE", "FRED, PCEPI", lambda: fred("PCEPI")),
    "us_actions": ("États-Unis", "S&P 500", "FRED, SP500", lambda: fred("SP500")),
    "us_pente": ("États-Unis", "Pente 10 ans - 3 mois", "FRED, T10Y3M", lambda: fred("T10Y3M")),
    # Zone euro
    "ez_pib": ("Zone euro", "PIB réel", "Eurostat, namq_10_gdp EA20",
               lambda: eurostat("namq_10_gdp", "Q.CLV10_MEUR.SCA.B1GQ.EA20")),
    "ez_cli": ("Zone euro", "CLI OCDE (DE/FR/IT/ES)", "OCDE, DF_CLI composite 4 pays",
               cli_zone_euro_composite),
    "ez_inflation": ("Zone euro", "IPCH (glissement annuel)", "BCE, HICP.M.U2.N.000000.4D0.ANR",
                     lambda: bce("HICP/M.U2.N.000000.4D0.ANR")),
    "ez_actions": ("Zone euro", "Euro Stoxx 50", "BCE, FM.M.U2.EUR.DS.EI.DJES50I.HSTA",
                   lambda: bce("FM/M.U2.EUR.DS.EI.DJES50I.HSTA")),
    "ez_pente": ("Zone euro", "Pente 10 ans - 3 mois", "BCE, YC...SRS_10Y_3M",
                 lambda: bce("YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SRS_10Y_3M")),
    # Japon
    "jp_pib": ("Japon", "PIB réel", "OCDE, QNA (B1GQ volume)", pib_japon),
    "jp_cli": ("Japon", "CLI OCDE", "OCDE, DF_CLI JPN", lambda: cli_ocde("JPN")),
    "jp_prix": ("Japon", "IPC", "DBnomics, STATJP CPIm 001",
                lambda: dbnomics("STATJP", "CPIm", "001")),
    "jp_actions": ("Japon", "Nikkei 225", "FRED, NIKKEI225", lambda: fred("NIKKEI225")),
    "jp_pente": ("Japon", "Pente 10 ans - 3 mois", "OCDE, FINMARK IRLT - IR3TIB", pente_japon),
    # Valorisation
    "cape": ("Valorisation", "PER de Shiller (CAPE)", "Shiller, ie_data.xls", col_shiller("CAPE")),
    "dfii10": ("Valorisation", "Taux réel 10 ans US (TIPS)", "FRED, DFII10", lambda: fred("DFII10")),
    "ez_10a": ("Valorisation", "Taux 10 ans zone euro (AAA)", "BCE, YC...SR_10Y",
               lambda: bce("YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y")),
    "jp_10a": ("Valorisation", "Taux 10 ans Japon", "OCDE, FINMARK IRLT", taux_long_japon),
    # Test historique et prolongement du S&P 500 avant 2016
    "sp_shiller": ("Test historique", "S&P composite (moyenne mensuelle)", "Shiller, ie_data.xls",
                   col_shiller("P")),
    "div_shiller": ("Test historique", "Dividendes S&P", "Shiller, ie_data.xls", col_shiller("D")),
    "gs10": ("Test historique", "Taux 10 ans US", "Shiller, ie_data.xls (GS10)", col_shiller("GS10")),
    "cpi_us": ("Test historique", "IPC américain", "Shiller, ie_data.xls (CPI)", col_shiller("CPI")),
    "tb3ms": ("Test historique", "Bons du Trésor 3 mois", "FRED, TB3MS", lambda: fred("TB3MS")),
}


def en_mensuel(s):
    """Dernière valeur connue de chaque mois. Les séries trimestrielles sont
    placées sur le dernier mois du trimestre (donnée complète à cette date)."""
    s = s.sort_index()
    ecart = pd.Series(s.index).diff().dt.days.median()
    m = s.resample("MS").last().dropna()
    if ecart and ecart > 80:  # trimestrielle
        m.index = m.index + pd.offsets.MonthBegin(2)
    return m[m.index >= DEBUT]


def charger_precedent():
    try:
        return json.loads(SORTIE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def serie_depuis_json(bloc):
    idx = pd.date_range(bloc["debut"], periods=len(bloc["valeurs"]), freq="MS")
    return pd.Series(bloc["valeurs"], index=idx, dtype=float).dropna()


def collecter(precedent):
    """Renvoie (dict de séries mensuelles, liste d'état des sources)."""
    brut_prec = precedent.get("brut", {})
    series, etat = {}, []
    for cle, (groupe, libelle, source, fonction) in CATALOGUE.items():
        ligne = {"cle": cle, "groupe": groupe, "serie": libelle, "source": source}
        try:
            s = en_mensuel(fonction())
            if s.empty:
                raise RuntimeError("série vide")
            ligne["statut"] = "OK"
            if cle in ("cape", "sp_shiller", "div_shiller", "gs10", "cpi_us"):
                ligne["source"] = shiller()[1]
                if "secours" in ligne["source"]:
                    ligne["statut"] = "OK (copie de secours)"
        except Exception as e:  # noqa: BLE001
            if cle in brut_prec:
                s = serie_depuis_json(brut_prec[cle])
                ligne["statut"] = "ÉCHEC : dernière valeur du data.json précédent conservée"
            else:
                s = pd.Series(dtype=float)
                ligne["statut"] = "ÉCHEC : aucune valeur disponible"
            ligne["erreur"] = str(e)[:150]
        series[cle] = s
        ligne["derniere_date"] = s.index[-1].strftime("%Y-%m") if len(s) else None
        ligne["derniere_valeur"] = arrondi(s.iloc[-1], 3) if len(s) else None
        print(f"  {ligne['statut'][:6]:<6} {groupe} / {libelle} "
              f"(dernière donnée : {ligne['derniere_date']})")
        etat.append(ligne)
    return series, etat


# --------------------------------------------------------------------------
# 2-3. Panel mensuel, indicateurs bruts, normalisation
# --------------------------------------------------------------------------
def panel_mensuel(series, fin):
    idx = pd.date_range(DEBUT, fin, freq="MS")
    return pd.DataFrame({k: s.reindex(idx).ffill() for k, s in series.items()}, index=idx)


def glissement(s):
    return (s / s.shift(12) - 1) * 100


def tendance(s):
    """Cours rapporté à sa moyenne des 12 derniers mois."""
    return s / s.rolling(12, min_periods=12).mean()


def score_z(x, fenetre=FENETRE_CLIMAT, mini=MINI_OBS):
    """Z-score glissant (fenetre=None : historique complet disponible à chaque date),
    écrêté à ±3 et ramené sur 0-100."""
    r = x.expanding(min_periods=mini) if fenetre is None else x.rolling(fenetre, min_periods=mini)
    z = ((x - r.mean()) / r.std()).clip(-3, 3)
    return (z + 3) / 6 * 100


def indicateurs(p):
    """Valeurs brutes orientées (plus haut = meilleur climat) et inflation des zones."""
    infl = pd.DataFrame({"us": glissement(p["us_prix"]), "ez": p["ez_inflation"],
                         "jp": glissement(p["jp_prix"])})
    # S&P 500 : FRED (cours de clôture) depuis 2016, prolongé par la série de Shiller.
    actions_us = tendance(p["us_actions"]).combine_first(tendance(p["sp_shiller"]))
    brut = {
        ("us", "pib"): glissement(p["us_pib"]), ("ez", "pib"): glissement(p["ez_pib"]),
        ("jp", "pib"): glissement(p["jp_pib"]),
        ("us", "cli"): p["us_cli"], ("ez", "cli"): p["ez_cli"], ("jp", "cli"): p["jp_cli"],
        ("us", "actions"): actions_us, ("ez", "actions"): tendance(p["ez_actions"]),
        ("jp", "actions"): tendance(p["jp_actions"]),
        ("us", "pente"): p["us_pente"], ("ez", "pente"): p["ez_pente"],
        ("jp", "pente"): p["jp_pente"],
        # inversés : un niveau élevé dégrade le climat
        ("socle", "vix"): -p["vix"], ("socle", "credit"): -p["baa10y"],
        ("socle", "gpr"): -p["gpr"], ("socle", "brent"): -tendance(p["brent"]),
    }
    for z in ZONES:
        brut[(z, "inflation")] = -(infl[z] - 2).abs()
    brut = pd.DataFrame(brut)
    return brut, infl


def sous_scores(brut):
    ordre = [(z, i) for z in ZONES for i in POIDS_ZONE] + [("socle", i) for i in POIDS_SOCLE]
    return pd.DataFrame({c: score_z(brut[c]) for c in ordre})


# --------------------------------------------------------------------------
# 4. Scores et contributions (formules linéaires, vérifiées par les tests)
# --------------------------------------------------------------------------
def poids_indicateur(indic):
    return POIDS_ZONE.get(indic, POIDS_SOCLE.get(indic))


def scores_zones(ss):
    """Score de zone = somme pondérée des 5 indicateurs de zone et des 4 du socle."""
    socle = sum(ss[("socle", i)] * w for i, w in POIDS_SOCLE.items())
    return pd.DataFrame({z: sum(ss[(z, i)] * w for i, w in POIDS_ZONE.items()) + socle
                         for z in ZONES})


def score_monde(sz, poids):
    return sum(sz[z] * w for z, w in poids.items())


def poids_effectifs(colonnes, poids=None):
    """Poids de chaque sous-score dans le score mondial (poids=None : score d'une zone).
    Socle : présent dans chaque zone, son poids effectif est w × somme des poids zones."""
    total = 1.0 if poids is None else sum(poids.values())
    return pd.Series({(z, i): poids_indicateur(i) * (total if z == "socle" or poids is None
                                                     else poids[z])
                      for z, i in colonnes})


def contributions(ss, h, poids=None, zone=None, niveau=False):
    """Contributions à la variation sur h mois (ou à l'écart à 50 si niveau=True).
    poids : pondération des zones (score mondial) ; zone : score d'une zone."""
    cols = [c for c in ss.columns if poids is not None or c[0] in (zone, "socle")]
    d = ss[cols].dropna()
    ecart = d.iloc[-1] - 50 if niveau else d.iloc[-1] - d.iloc[-1 - h]
    return ecart * poids_effectifs(cols, poids)


# --------------------------------------------------------------------------
# 5. Régimes
# --------------------------------------------------------------------------
def regime(croissance, inflation):
    def un(g, i):
        if pd.isna(g) or pd.isna(i):
            return None
        forte, elevee = g >= SEUIL_CROISSANCE, i >= SEUIL_INFLATION
        return {(True, False): "Expansion", (True, True): "Surchauffe",
                (False, False): "Ralentissement", (False, True): "Stagflation"}[(forte, elevee)]
    return pd.Series([un(g, i) for g, i in zip(croissance, inflation)], index=croissance.index)


def regime_confirme(brut):
    """Un changement de régime n'est acté qu'après deux mois consécutifs."""
    sortie, courant, precedent = [], None, None
    for r in brut:
        if r is None:
            sortie.append(courant)
            continue
        if courant is None or (r != courant and r == precedent):
            courant = r
        sortie.append(courant)
        precedent = r
    return pd.Series(sortie, index=brut.index)


# --------------------------------------------------------------------------
# 6. Valorisation
# --------------------------------------------------------------------------
def valorisation(p, infl):
    prime = 100 / p["cape"] - p["dfii10"]  # prime de risque de Shiller, en points
    taux_reels = pd.DataFrame({"us": p["dfii10"], "ez": p["ez_10a"] - infl["ez"],
                               "jp": p["jp_10a"] - infl["jp"]})
    attrait_o = taux_reels.apply(lambda c: score_z(c, fenetre=None))
    return prime, score_z(prime, fenetre=None), taux_reels, attrait_o


# --------------------------------------------------------------------------
# 8. Allocation
# --------------------------------------------------------------------------
def deplacer(a, de, vers, points):
    points = min(points, a[de])
    a[de] -= points
    a[vers] += points


def renforcer_actions(a, points):
    """Hypothèse : les points ajoutés aux actions sont pris sur les liquidités,
    puis sur les obligations si les liquidités ne suffisent pas."""
    for source in ("L", "O"):
        pris = min(points, a[source])
        deplacer(a, source, "A", pris)
        points -= pris


def allocation(reg, score, attrait_a, attrait_o):
    a = dict(BASES[reg])
    etapes = [{"etape": "1. Base du régime", "motif": f"Régime mondial : {reg}", **a}]
    if pd.isna(score):
        motif = "Score indisponible : pas d'ajustement"
    elif score < 40:
        deplacer(a, "A", "L", 10)
        motif = f"Score mondial {fr(score, 1)} < 40 : actions -10 vers liquidités"
    elif score >= 60:
        renforcer_actions(a, 5)
        motif = f"Score mondial {fr(score, 1)} ≥ 60 : actions +5"
    else:
        motif = f"Score mondial {fr(score, 1)} entre 40 et 60 : pas d'ajustement"
    etapes.append({"etape": "2. Ajustement par le climat", "motif": motif, **a})
    if pd.isna(attrait_a):
        motif = "Valorisation indisponible : pas de correction"
    elif attrait_a < 35:
        vers = "O" if attrait_o >= 50 else "L"
        deplacer(a, "A", vers, 10)
        motif = (f"Attrait actions {fr(attrait_a, 1)} < 35 : actions -10 vers "
                 + ("obligations (attrait obligations ≥ 50)" if vers == "O"
                    else "liquidités (attrait obligations < 50)"))
    elif attrait_a > 65:
        renforcer_actions(a, 5)
        motif = f"Attrait actions {fr(attrait_a, 1)} > 65 : actions +5"
    else:
        motif = f"Attrait actions {fr(attrait_a, 1)} entre 35 et 65 : pas de correction"
    etapes.append({"etape": "3. Correction par la valorisation", "motif": motif, **a})
    return a, etapes


def preference_geo(sz, regimes_zones, t):
    """Classement : score de climat + variation sur 3 mois + bonus de régime (hypothèse)."""
    lignes = []
    for z in ZONES:
        var3 = sz[z].iloc[t] - sz[z].iloc[t - 3]
        reg = regimes_zones[z].iloc[t]
        pts = sz[z].iloc[t] + var3 + BONUS_REGIME.get(reg, 0)
        lignes.append({"zone": z, "nom": ZONES[z], "score": arrondi(sz[z].iloc[t]),
                       "variation_3m": arrondi(var3), "regime": reg, "points": arrondi(pts)})
    lignes.sort(key=lambda x: -x["points"])
    for rang, l in enumerate(lignes):
        l["rang"] = rang + 1
        l["position"] = ("Surpondérer" if rang == 0 else
                         "Sous-pondérer" if rang == len(lignes) - 1 else "Neutre")
    return lignes


# --------------------------------------------------------------------------
# 9. Test historique
# --------------------------------------------------------------------------
def duree(y):
    """Duration modifiée approchée d'une obligation 10 ans au pair (coupon semestriel)."""
    y = y.clip(lower=0.001)
    return (1 - (1 + y / 2) ** -20) / y


def rendements(p):
    """Rendements mensuels approchés (actifs américains)."""
    prix, div = p["sp_shiller"], p["div_shiller"].ffill()
    y, ry = p["gs10"] / 100, p["dfii10"] / 100
    r = pd.DataFrame(index=p.index)
    r["A"] = (prix + div / 12) / prix.shift() - 1
    r["O"] = y.shift() / 12 - duree(y.shift()) * y.diff()
    inflation_m = p["cpi_us"] / p["cpi_us"].shift() - 1
    tips = ry.shift() / 12 - duree(ry.shift()) * ry.diff() + inflation_m
    r["R"] = 0.5 * tips + 0.5 * (p["brent"] / p["brent"].shift() - 1)
    r["L"] = p["tb3ms"].shift() / 100 / 12
    return r


def test_historique(p, regimes, score, attrait_a, attrait_o):
    r = rendements(p)
    resultats = {}
    for nom, (debut, fin) in EPISODES.items():
        mois = pd.date_range(debut, fin, freq="MS")
        ref = mois[0] - pd.offsets.MonthBegin(1)
        if ref not in score.index or pd.isna(score.get(ref)) or regimes.get(ref) is None:
            resultats[nom] = {"disponible": False, "motif": "scores indisponibles avant l'épisode"}
            continue
        v_b, v_r, lignes = 100.0, 100.0, []
        pic_b, pic_r, dd_b, dd_r = 100.0, 100.0, 0.0, 0.0
        for m in mois:
            prec = m - pd.offsets.MonthBegin(1)  # décision prise fin du mois précédent
            a, _ = allocation(regimes[prec], score[prec], attrait_a[prec], attrait_o[prec])
            rm = r.loc[m]
            if rm[list(a)].isna().any():
                break
            v_b *= 1 + sum(a[k] / 100 * rm[k] for k in a)
            v_r *= 1 + 0.6 * rm["A"] + 0.4 * rm["O"]
            pic_b, pic_r = max(pic_b, v_b), max(pic_r, v_r)
            dd_b, dd_r = min(dd_b, v_b / pic_b - 1), min(dd_r, v_r / pic_r - 1)
            lignes.append({"mois": m.strftime("%Y-%m"), "regime": regimes[prec], **a,
                           "barometre": arrondi(v_b), "ref_60_40": arrondi(v_r)})
        resultats[nom] = {
            "disponible": bool(lignes), "periode": f"{debut} à {lignes[-1]['mois']}" if lignes else None,
            "perf_barometre": arrondi(v_b - 100), "perf_60_40": arrondi(v_r - 100),
            "perte_max_barometre": arrondi(dd_b * 100), "perte_max_60_40": arrondi(dd_r * 100),
            "mois": lignes}
    return resultats


# --------------------------------------------------------------------------
# Utilitaires de sortie
# --------------------------------------------------------------------------
def arrondi(x, n=2):
    if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x):
        return None
    return round(float(x), n)


def fr(x, n=1):
    """Nombre au format français (virgule décimale, signe moins typographique)."""
    return f"{x:.{n}f}".replace(".", ",").replace("-", "−")


def signe(x, n=1):
    return ("+" if x > 0 else "") + fr(x, n)


def libelle_contrib(cle):
    z, i = cle
    return LIBELLES[i] + ("" if z == "socle" else f" ({ZONES[z]})")


def initiale_minuscule(texte):
    """« Tendance actions (États-Unis) » -> « tendance actions (États-Unis) » ; « VIX » inchangé."""
    return texte if texte[1:2].isupper() else texte[:1].lower() + texte[1:]


def phrase(variation, contrib, h):
    duree_txt = {1: "un mois", 3: "trois mois", 12: "douze mois"}[h]
    c = contrib.sort_values()
    texte = f"Sur {duree_txt}, le score a varié de {signe(variation)} points"
    hausse, baisse = c[c > 0], c[c < 0]
    morceaux = []
    if len(hausse):
        morceaux.append(f"porté par {initiale_minuscule(libelle_contrib(hausse.index[-1]))} "
                        f"({signe(hausse.iloc[-1])})")
    if len(baisse):
        morceaux.append(f"freiné par {initiale_minuscule(libelle_contrib(baisse.index[0]))} "
                        f"({signe(baisse.iloc[0])})")
    return texte + (", " + " et ".join(morceaux) if morceaux else "") + "."


def liste_contrib(c):
    return [{"zone": z, "indicateur": i, "libelle": libelle_contrib((z, i)),
             "contribution": arrondi(v, 4)} for (z, i), v in c.items()]


def bloc_dynamique(ss, serie_score, poids=None, zone=None):
    d = ss.dropna()
    t = d.index[-1]
    sortie = {"score": arrondi(serie_score[t]), "variations": {}}
    for h in (1, 3, 12):
        var = serie_score[t] - serie_score[d.index[-1 - h]]
        c = contributions(ss, h, poids=poids, zone=zone)
        sortie["variations"][f"{h}m"] = {"variation": arrondi(var, 4), "phrase": phrase(var, c, h),
                                         "contributions": liste_contrib(c)}
    niv = contributions(ss, 0, poids=poids, zone=zone, niveau=True)
    sortie["niveau"] = {"ecart_a_50": arrondi(serie_score[t] - 50, 4),
                        "contributions": liste_contrib(niv)}
    return sortie


def historique(serie, depuis="2007-01-01"):
    s = serie[serie.index >= depuis].dropna()
    return {"dates": [d.strftime("%Y-%m") for d in s.index],
            "valeurs": [v if isinstance(v, str) else arrondi(v) for v in s]}


def brut_pour_json(series):
    out = {}
    for k, s in series.items():
        if len(s):
            idx = pd.date_range(s.index[0], s.index[-1], freq="MS")
            out[k] = {"debut": idx[0].strftime("%Y-%m-%d"),
                      "valeurs": [arrondi(v, 6) for v in s.reindex(idx)]}
    return out


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------
def calculer(series, fin):
    p = panel_mensuel(series, fin)
    brut, infl = indicateurs(p)
    ss = sous_scores(brut)
    complet = ss.dropna()
    ss = ss.loc[:complet.index[-1]]  # dernier mois où tous les sous-scores existent
    sz = scores_zones(ss)
    monde = {k: score_monde(sz, w) for k, w in PONDERATIONS.items()}
    croissance = pd.DataFrame({z: (ss[(z, "pib")] + ss[(z, "cli")]) / 2 for z in ZONES})
    reg_zones = {z: regime(croissance[z], infl[z].reindex(ss.index)) for z in ZONES}
    prime, attrait_a, taux_reels, attrait_o_z = valorisation(p, infl)
    return p, ss, sz, monde, croissance, infl.reindex(ss.index), reg_zones, \
        prime.reindex(ss.index), attrait_a.reindex(ss.index), \
        taux_reels.reindex(ss.index), attrait_o_z.reindex(ss.index)


def main():
    print(f"Baromètre - collecte du {date.today():%d/%m/%Y}\n")
    precedent = charger_precedent()
    series, etat = collecter(precedent)
    (p, ss, sz, monde, croissance, infl, reg_zones, prime, attrait_a,
     taux_reels, attrait_o_z) = calculer(series, pd.Timestamp(date.today()).to_period("M").start_time)
    t = ss.index[-1]

    sortie = {
        "genere_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mois_de_calcul": t.strftime("%Y-%m"),
        "parametres": {"ponderations": PONDERATIONS, "poids_zone": POIDS_ZONE,
                       "poids_socle": POIDS_SOCLE, "bases_regime": BASES,
                       "seuil_croissance": SEUIL_CROISSANCE, "seuil_inflation": SEUIL_INFLATION,
                       "fenetre_climat_mois": FENETRE_CLIMAT, "bonus_regime": BONUS_REGIME},
        "libelles": {"zones": ZONES, "indicateurs": LIBELLES},
        "sources": etat,
        "sources_en_echec": [e["serie"] for e in etat if e["statut"].startswith("ÉCHEC")],
        "zones": {}, "monde": {}, "valorisation": {}, "limites": LIMITES,
    }

    # Zones
    for z in ZONES:
        sortie["zones"][z] = {
            "nom": ZONES[z],
            **bloc_dynamique(ss, sz[z], zone=z),
            "sous_scores": {i: arrondi(ss[(c, i)][t]) for c, i in ss.columns if c in (z, "socle")},
            "croissance": arrondi(croissance[z][t]), "inflation": arrondi(infl[z][t]),
            "regime": reg_zones[z][t], "regime_confirme": regime_confirme(reg_zones[z])[t],
            "trajectoire_6m": [{"mois": d.strftime("%Y-%m"), "croissance": arrondi(croissance[z][d]),
                                "inflation": arrondi(infl[z][d])} for d in ss.index[-7:]],
            "historique": historique(sz[z]),
        }

    # Valorisation (attrait obligations agrégé selon chaque pondération)
    attrait_o = {k: sum(attrait_o_z[z] * w for z, w in poids.items())
                 for k, poids in PONDERATIONS.items()}
    sortie["valorisation"] = {
        "prime_de_risque_actions": arrondi(prime[t]), "attrait_actions": arrondi(attrait_a[t]),
        "cape": arrondi(p["cape"].dropna().iloc[-1]),
        "taux_reels_10a": {z: arrondi(taux_reels[z][t]) for z in ZONES},
        "attrait_obligations_zones": {z: arrondi(attrait_o_z[z][t]) for z in ZONES},
        "attrait_obligations": {k: arrondi(v[t]) for k, v in attrait_o.items()},
        "historique_attrait_actions": historique(attrait_a),
    }

    # Monde, pour chaque pondération
    for k, poids in PONDERATIONS.items():
        g = sum(croissance[z] * w for z, w in poids.items())
        i = sum(infl[z] * w for z, w in poids.items())
        reg = regime(g, i)
        reg_c = regime_confirme(reg)
        bloc = bloc_dynamique(ss, monde[k], poids=poids)
        bloc.update({
            "croissance": arrondi(g[t]), "inflation": arrondi(i[t]),
            "regime": reg[t], "regime_confirme": reg_c[t],
            "trajectoire_6m": [{"mois": d.strftime("%Y-%m"), "croissance": arrondi(g[d]),
                                "inflation": arrondi(i[d])} for d in ss.index[-7:]],
            "historique": historique(monde[k]),
            "historique_regime": historique(reg), "historique_regime_confirme": historique(reg_c),
            "allocation": {}, "test_historique": {},
        })
        for mode, r in (("brut", reg), ("confirme", reg_c)):
            final, etapes = allocation(r[t], monde[k][t], attrait_a[t], attrait_o[k][t])
            bloc["allocation"][mode] = {"finale": final, "etapes": etapes}
            bloc["test_historique"][mode] = test_historique(p, r, monde[k], attrait_a, attrait_o[k])
        sortie["monde"][k] = bloc

    sortie["preference_geographique"] = preference_geo(sz, reg_zones, ss.index.get_loc(t))
    sortie["brut"] = brut_pour_json(series)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(sortie, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
                      encoding="utf-8")

    m = sortie["monde"]["capi"]
    print(f"\nMois de calcul : {sortie['mois_de_calcul']}")
    print(f"Score mondial (capi) : {m['score']}  |  parts égales : {sortie['monde']['egal']['score']}")
    for z in ZONES:
        print(f"  {ZONES[z]:<11}: {sortie['zones'][z]['score']}  régime {sortie['zones'][z]['regime']}")
    print(f"Régime mondial : {m['regime']} (confirmé : {m['regime_confirme']})")
    print(m["variations"]["3m"]["phrase"])
    print(f"Attrait actions : {sortie['valorisation']['attrait_actions']}  |  "
          f"obligations : {sortie['valorisation']['attrait_obligations']['capi']}")
    print(f"Allocation : {m['allocation']['brut']['finale']}")
    if sortie["sources_en_echec"]:
        print(f"Sources en échec : {', '.join(sortie['sources_en_echec'])}")
    print(f"\nÉcrit : {SORTIE.relative_to(RACINE)} ({SORTIE.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
