"""Test des sources du baromètre (note de cadrage v4).

Pour chacune des 19 séries du score de climat, le script télécharge la série
et affiche : série / source / OK-KO / première date / dernière date / fréquence.
Il teste aussi les séries de valorisation.

CLI : la note v4 prévoyait DBnomics, figé à mai 2026 et sans série zone euro.
On interroge donc l'OCDE directement ; la zone euro est approchée par la
moyenne pondérée des CLI Allemagne, France, Italie, Espagne (~75 % du PIB).

Statuts :
  OK      série téléchargée et à jour
  RETARD  série téléchargée mais dernière donnée trop ancienne
  KO      série introuvable ou source en erreur

Lancement : python collect/test_sources.py
Code de sortie 1 si l'une des 19 séries est KO (le workflow apparaît en rouge).
"""

import io
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RACINE = Path(__file__).resolve().parent.parent
SHILLER_SECOURS = RACINE / "data" / "backup" / "ie_data.xls"
ENTETES = {}  # en-tête par défaut : FRED refuse certains User-Agent personnalisés

# Retard maximal toléré (jours) entre la dernière donnée et aujourd'hui.
RETARD_MAX = {"Quotidienne": 15, "Mensuelle": 100, "Trimestrielle": 200}


# --------------------------------------------------------------------------
# Téléchargement
# --------------------------------------------------------------------------
def telecharger(url, essais=3, timeout=90):
    """GET avec quelques nouvelles tentatives (certains sites coupent parfois)."""
    derniere_erreur = None
    for i in range(essais):
        try:
            r = requests.get(url, headers=ENTETES, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            derniere_erreur = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"échec après {essais} essais : {derniere_erreur}")


def vers_dates(periodes):
    """Convertit '2026-10', '2026-Q3' ou '2026-10-31' en dates (début de période)."""
    p = pd.Series(periodes).astype(str)
    trim = p.str.extract(r"^(\d{4})-?Q(\d)$")
    if trim[0].notna().all():
        return pd.to_datetime(dict(year=trim[0].astype(int),
                                   month=(trim[1].astype(int) - 1) * 3 + 1, day=1)).values
    fmt = "%Y-%m" if p.str.len().max() <= 7 else "%Y-%m-%d"
    return pd.to_datetime(p, format=fmt).values


def nettoyer(s):
    """Série numérique triée, sans valeurs manquantes."""
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if s.empty:
        raise RuntimeError("série vide")
    return s


def fred(code):
    r = telecharger(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}")
    d = pd.read_csv(io.StringIO(r.text))
    d.index = pd.to_datetime(d.iloc[:, 0])
    return nettoyer(d[code])


def bce(cle):
    """ECB Data Portal, ex. 'FM/M.U2.EUR.DS.EI.DJES50I.HSTA'."""
    r = telecharger(f"https://data-api.ecb.europa.eu/service/data/{cle}"
                    "?format=csvdata&detail=dataonly")
    d = pd.read_csv(io.StringIO(r.text))
    if d.empty:
        raise RuntimeError("aucune donnée")
    d.index = vers_dates(d["TIME_PERIOD"])
    return nettoyer(d["OBS_VALUE"])


def eurostat(jeu, cle):
    r = telecharger("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/"
                    f"data/{jeu}/{cle}?format=SDMX-CSV")
    d = pd.read_csv(io.StringIO(r.text))
    d.index = vers_dates(d["TIME_PERIOD"])
    return nettoyer(d["OBS_VALUE"])


def ocde(flux, cle):
    """API SDMX de l'OCDE, ex. flux 'OECD.SDD.STES,DSD_STES@DF_CLI,'."""
    r = telecharger(f"https://sdmx.oecd.org/public/rest/data/{flux}/{cle}"
                    "?dimensionAtObservation=AllDimensions&format=csvfile")
    d = pd.read_csv(io.StringIO(r.text))
    if d.empty:
        raise RuntimeError("aucune donnée")
    return d


def ocde_serie(flux, cle):
    d = ocde(flux, cle)
    if d["TIME_PERIOD"].nunique() != len(d):
        raise RuntimeError("clé ambiguë : plusieurs séries renvoyées")
    d.index = vers_dates(d["TIME_PERIOD"])
    return nettoyer(d["OBS_VALUE"])


def dbnomics(fournisseur, jeu, serie):
    r = telecharger(f"https://api.db.nomics.world/v22/series/{fournisseur}/{jeu}/"
                    f"{serie}?observations=1&format=json")
    docs = r.json()["series"]["docs"]
    if not docs:
        raise RuntimeError("série inconnue")
    doc = docs[0]
    s = pd.Series(doc["value"], index=vers_dates(doc["period"]))
    return nettoyer(s.replace("NA", None))


# --------------------------------------------------------------------------
# Séries particulières
# --------------------------------------------------------------------------
def pib_japon():
    """PIB réel du Japon (comptes trimestriels OCDE, volume, monnaie nationale)."""
    return ocde_serie("OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,",
                      "Q.Y.JPN.S1.S1.B1GQ._Z._Z._Z.XDC.LR.LA.T0102")


def pente_japon():
    """Taux long (IRLT) moins taux 3 mois (IR3TIB), OCDE, base FINMARK."""
    d = ocde("OECD.SDD.STES,DSD_STES@DF_FINMARK,", "JPN.M.IR3TIB+IRLT.PA.....")
    d = d.pivot_table(index="TIME_PERIOD", columns="MEASURE", values="OBS_VALUE")
    d.index = vers_dates(d.index)
    return nettoyer(d["IRLT"] - d["IR3TIB"])


def taux_long_japon():
    d = ocde("OECD.SDD.STES,DSD_STES@DF_FINMARK,", "JPN.M.IRLT.PA.....")
    d.index = vers_dates(d["TIME_PERIOD"])
    return nettoyer(d["OBS_VALUE"])


def gpr():
    r = telecharger("https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls")
    d = pd.read_excel(io.BytesIO(r.content))
    d.index = pd.to_datetime(d["month"])
    return nettoyer(d["GPR"])


def cli_ocde(zone):
    """CLI directement à l'OCDE (plus à jour que DBnomics)."""
    return ocde_serie("OECD.SDD.STES,DSD_STES@DF_CLI,", f"{zone}.M.LI...AA...H")


# Poids approximatifs dans le PIB 2024 de la zone euro (estimation, à affiner).
POIDS_CLI_ZE = {"DEU": 0.39, "FRA": 0.27, "ITA": 0.20, "ESP": 0.14}


def cli_zone_euro_composite():
    """Moyenne pondérée des CLI des 4 grands pays de la zone euro (~75 % du PIB)."""
    d = ocde("OECD.SDD.STES,DSD_STES@DF_CLI,",
             "+".join(POIDS_CLI_ZE) + ".M.LI...AA...H")
    d = d.pivot_table(index="TIME_PERIOD", columns="REF_AREA", values="OBS_VALUE")
    d.index = vers_dates(d.index)
    d = d.dropna()
    return nettoyer(sum(d[p] * w for p, w in POIDS_CLI_ZE.items()))


# --- Shiller : lien du site, sinon copie de secours du dépôt --------------
SHILLER_SOURCE_UTILISEE = "?"


def lien_shiller():
    """Le lien du fichier change : on le cherche sur la page d'accueil."""
    page = telecharger("https://shillerdata.com/", essais=5).text
    liens = re.findall(r'(?:https?:)?//[^"\'\s]+/ie_data\.xls[^"\'\s]*', page)
    if not liens:
        raise RuntimeError("lien ie_data.xls absent de shillerdata.com")
    lien = liens[0]
    return "https:" + lien if lien.startswith("//") else lien


def lire_shiller(contenu):
    d = pd.read_excel(io.BytesIO(contenu), sheet_name="Data", skiprows=7)
    d = d[["Date", "CAPE"]].dropna()
    d = d[pd.to_numeric(d["Date"], errors="coerce").notna()]
    annee = d["Date"].astype(float).astype(int)
    mois = ((d["Date"].astype(float) - annee) * 100).round().astype(int)
    d.index = pd.to_datetime(dict(year=annee, month=mois, day=1))
    return nettoyer(d["CAPE"])


def cape_shiller():
    global SHILLER_SOURCE_UTILISEE
    try:
        s = lire_shiller(telecharger(lien_shiller(), essais=5).content)
        SHILLER_SOURCE_UTILISEE = "Shiller, shillerdata.com (ie_data.xls)"
        return s
    except Exception as e:
        print(f"  ! Shiller en ligne indisponible ({e}) : copie de secours utilisée")
        SHILLER_SOURCE_UTILISEE = "Shiller, copie de secours data/backup/ie_data.xls"
        return lire_shiller(SHILLER_SECOURS.read_bytes())


# --------------------------------------------------------------------------
# Catalogue : les 19 séries de la note v4, puis compléments
# --------------------------------------------------------------------------
SERIES_19 = [
    # Socle mondial de risque
    ("Socle", "VIX", "FRED, VIXCLS", lambda: fred("VIXCLS")),
    ("Socle", "Spread Baa - 10 ans", "FRED, BAA10Y", lambda: fred("BAA10Y")),
    ("Socle", "Risque géopolitique (GPR)", "Iacoviello, data_gpr_export.xls", gpr),
    ("Socle", "Brent", "FRED, DCOILBRENTEU", lambda: fred("DCOILBRENTEU")),
    # États-Unis
    ("États-Unis", "PIB réel", "FRED, GDPC1", lambda: fred("GDPC1")),
    ("États-Unis", "CLI OCDE", "OCDE, DF_CLI USA", lambda: cli_ocde("USA")),
    ("États-Unis", "Inflation (déflateur PCE)", "FRED, PCEPI", lambda: fred("PCEPI")),
    ("États-Unis", "Actions (S&P 500)", "FRED, SP500", lambda: fred("SP500")),
    ("États-Unis", "Pente 10 ans - 3 mois", "FRED, T10Y3M", lambda: fred("T10Y3M")),
    # Zone euro
    ("Zone euro", "PIB réel", "Eurostat, namq_10_gdp EA20",
     lambda: eurostat("namq_10_gdp", "Q.CLV10_MEUR.SCA.B1GQ.EA20")),
    ("Zone euro", "CLI OCDE (DE/FR/IT/ES)", "OCDE, DF_CLI composite 4 pays",
     cli_zone_euro_composite),
    ("Zone euro", "Inflation (IPCH)", "BCE, HICP.M.U2.N.000000.4D0.ANR",
     lambda: bce("HICP/M.U2.N.000000.4D0.ANR")),
    ("Zone euro", "Actions (Euro Stoxx 50)", "BCE, FM...DJES50I.HSTA",
     lambda: bce("FM/M.U2.EUR.DS.EI.DJES50I.HSTA")),
    ("Zone euro", "Pente 10 ans - 3 mois", "BCE, YC...SRS_10Y_3M",
     lambda: bce("YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SRS_10Y_3M")),
    # Japon
    ("Japon", "PIB réel", "OCDE, QNA (B1GQ volume)", pib_japon),
    ("Japon", "CLI OCDE", "OCDE, DF_CLI JPN", lambda: cli_ocde("JPN")),
    ("Japon", "Inflation (IPC)", "DBnomics, STATJP CPIm 001",
     lambda: dbnomics("STATJP", "CPIm", "001")),
    ("Japon", "Actions (Nikkei 225)", "FRED, NIKKEI225", lambda: fred("NIKKEI225")),
    ("Japon", "Pente 10 ans - 3 mois", "OCDE, FINMARK IRLT - IR3TIB", pente_japon),
]

SERIES_VALORISATION = [
    ("Valorisation", "PER de Shiller (CAPE)", "Shiller, ie_data.xls", cape_shiller),
    ("Valorisation", "Taux réel 10 ans US (TIPS)", "FRED, DFII10", lambda: fred("DFII10")),
    ("Valorisation", "Taux 10 ans zone euro (AAA)", "BCE, YC...SR_10Y",
     lambda: bce("YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y")),
    ("Valorisation", "Taux 10 ans Japon", "OCDE, FINMARK IRLT", taux_long_japon),
]

# --------------------------------------------------------------------------
# Diagnostic et affichage
# --------------------------------------------------------------------------
def frequence(s):
    ecart = pd.Series(s.index).diff().dt.days.median()
    if ecart <= 5:
        return "Quotidienne"
    if ecart <= 35:
        return "Mensuelle"
    if ecart <= 100:
        return "Trimestrielle"
    return f"~{int(ecart)} j"


def format_date(d, freq):
    if freq == "Mensuelle":
        return d.strftime("%Y-%m")
    if freq == "Trimestrielle":
        return f"{d.year}-T{(d.month - 1) // 3 + 1}"
    return d.strftime("%Y-%m-%d")


def fin_de_periode(d, freq):
    """Dernier jour couvert par la donnée (pour mesurer le retard)."""
    if freq == "Mensuelle":
        return d + pd.offsets.MonthEnd(0)
    if freq == "Trimestrielle":
        return d + pd.offsets.QuarterEnd(0)
    return d


def tester(groupe, nom, source, fonction):
    ligne = {"Groupe": groupe, "Série": nom, "Source": source}
    try:
        s = fonction()
        freq = frequence(s)
        retard = (pd.Timestamp(date.today()) - fin_de_periode(s.index[-1], freq)).days
        statut = "OK" if retard <= RETARD_MAX.get(freq, 400) else "RETARD"
        ligne.update({"Statut": statut, "Première date": format_date(s.index[0], freq),
                      "Dernière date": format_date(s.index[-1], freq),
                      "Fréquence": freq, "Nb obs.": len(s),
                      "Dernière valeur": f"{s.iloc[-1]:.2f}", "Remarque": ""})
        if nom.startswith("PER de Shiller"):
            ligne["Source"] = SHILLER_SOURCE_UTILISEE
        if statut == "RETARD":
            ligne["Remarque"] = f"dernière donnée il y a {retard} jours"
    except Exception as e:
        ligne.update({"Statut": "KO", "Première date": "-", "Dernière date": "-",
                      "Fréquence": "-", "Nb obs.": 0, "Dernière valeur": "-",
                      "Remarque": str(e)[:90]})
    print(f"  {ligne['Statut']:<6} {groupe} / {nom}")
    return ligne


COLONNES = ["Groupe", "Série", "Source", "Statut", "Première date",
            "Dernière date", "Fréquence", "Dernière valeur", "Remarque"]


def tableau_markdown(df):
    lignes = ["| " + " | ".join(COLONNES) + " |",
              "|" + "---|" * len(COLONNES)]
    for _, r in df.iterrows():
        lignes.append("| " + " | ".join(str(r[c]) for c in COLONNES) + " |")
    return "\n".join(lignes)


def main():
    print(f"Test des sources du baromètre - {date.today():%d/%m/%Y}\n")
    blocs = [("Les 19 séries du score de climat (note v4)", SERIES_19),
             ("Valorisation (hors score de climat)", SERIES_VALORISATION)]
    resultats = []
    for titre, series in blocs:
        print(f"{titre} :")
        df = pd.DataFrame([tester(*s) for s in series])
        resultats.append((titre, df))
        print()

    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 45)
    rapport = [f"# Test des sources - {date.today():%d/%m/%Y}\n"]
    for titre, df in resultats:
        print(f"=== {titre} ===")
        print(df[COLONNES].to_string(index=False))
        print()
        rapport += [f"## {titre}\n", tableau_markdown(df), ""]

    principal = resultats[0][1]
    bilan = (f"Bilan des 19 séries : {sum(principal.Statut == 'OK')} OK, "
             f"{sum(principal.Statut == 'RETARD')} en retard, "
             f"{sum(principal.Statut == 'KO')} KO.")
    print(bilan)
    rapport.append(f"**{bilan}**\n")

    # Résumé lisible dans l'onglet Actions de GitHub
    resume = os.environ.get("GITHUB_STEP_SUMMARY")
    if resume:
        with open(resume, "a", encoding="utf-8") as f:
            f.write("\n".join(rapport))

    sys.exit(1 if (principal.Statut == "KO").any() else 0)


if __name__ == "__main__":
    main()
