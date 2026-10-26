import json
import math
import random
import os
import re
import smtplib
import time
import uuid
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PIL import Image
import pandas as pd
import streamlit as st

# 1. Configuration de la page (Immédiatement après les imports, au tout début du script)
_base_dir = os.path.dirname(os.path.abspath(__file__))
_candidats_icones = [
    os.path.join(_base_dir, "armoiries.ico"),
    os.path.join(_base_dir, "favicon.ico"),
    os.path.join(os.getcwd(), "armoiries.ico"),
    os.path.join(os.getcwd(), "favicon.ico"),
    os.path.join(_base_dir, "armoiries.png"),
    os.path.join(os.getcwd(), "armoiries.png"),
    "armoiries.ico",
    "favicon.ico",
    "armoiries.png"
]
icone_app = "🎱"
for _c in _candidats_icones:
    if os.path.isfile(_c):
        icone_app = _c
        break

st.set_page_config(
    page_title="Ligue de billard Boule en main - Saisie",
    page_icon=icone_app,
    layout="wide"
)

# 2. Fichiers de données et chemins d'accès robustes
BASE_DIR = _base_dir

def get_data_path(filename):
    """Retourne le chemin complet du fichier en privilégiant le répertoire du script."""
    p_script = os.path.join(BASE_DIR, filename)
    if os.path.exists(p_script):
        return p_script
    p_cwd = os.path.join(os.getcwd(), filename)
    if os.path.exists(p_cwd):
        return p_cwd
    return p_script

def find_armoiries_path():
    """Localise le fichier d'armoiries de manière robuste quel que soit l'environnement."""
    candidats = [
        os.path.join(BASE_DIR, "armoiries.png"),
        os.path.join(BASE_DIR, "Armoiries.png"),
        os.path.join(os.getcwd(), "armoiries.png"),
        os.path.join(os.getcwd(), "Armoiries.png"),
        os.path.join(BASE_DIR, "assets", "armoiries.png"),
        os.path.join(os.getcwd(), "assets", "armoiries.png"),
        os.path.join(BASE_DIR, "armoiries.jpg"),
        os.path.join(os.getcwd(), "armoiries.jpg"),
    ]
    for c in candidats:
        if os.path.isfile(c):
            return c
    return os.path.join(BASE_DIR, "armoiries.png")

ARMOIRIES_FILE = find_armoiries_path()

BACKUP_FILE = get_data_path("sauvegarde_saisie_secours.json")
CORBEILLE_FILE = get_data_path("sauvegarde_annulee_secours.json")
HISTORIQUE_FILE = get_data_path("historique_matchs.json")
TOURNOIS_FILE = get_data_path("tournois_data.json")
HISTORIQUE_TOURNOIS_FILE = get_data_path("historique_tournois.json")
CONFIG_EMAIL_FILE = get_data_path("config_email.json")
ADMIN_CONFIG_FILE = get_data_path("config_admin.json")
EQUIPES_CSV_FILE = get_data_path("equipes-saphir.csv")
ARMOIRIES_FILE = find_armoiries_path()
LOCK_FILE = get_data_path("session_lock.json")
LOCK_TIMEOUT = 900  # 15 minutes d'inactivité avant libération automatique

@st.cache_data
def charger_armoiries_base64(max_taille=(160, 160)):
    """Charge l'image des armoiries, la redimensionne proprement et la renvoie en data URI base64."""
    img_path = find_armoiries_path()
    if not os.path.isfile(img_path):
        return ""
    try:
        from PIL import Image
        import io
        import base64
        im = Image.open(img_path)
        resample_filter = getattr(getattr(Image, "Resampling", Image), "LANCZOS", getattr(Image, "ANTIALIAS", 1))
        im.thumbnail(max_taille, resample_filter)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        try:
            import base64
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
        except Exception:
            return ""

def injecter_meta_icones_mobiles():
    """Injecte les balises d'icônes mobiles (Apple Touch Icon et Android PWA) dans le DOM pour remplacer la couronne Streamlit sur mobile et tablette."""
    b64_icone = charger_armoiries_base64(max_taille=(192, 192))
    if not b64_icone:
        return

    code_js = f"""
    <script>
    (function() {{
        try {{
            var head = window.parent.document.head;
            if (!head) return;
            var iconUri = "{b64_icone}";

            // 1. apple-touch-icon pour iOS Safari (iPhone & iPad)
            var rels = ["apple-touch-icon", "apple-touch-icon-precomposed"];
            rels.forEach(function(r) {{
                var el = window.parent.document.querySelector("link[rel='" + r + "']");
                if (!el) {{
                    el = window.parent.document.createElement("link");
                    el.rel = r;
                    head.appendChild(el);
                }}
                el.href = iconUri;
            }});

            // 2. Icônes pour Android / Chrome (192x192 & 512x512)
            var sizes = ["192x192", "512x512", "180x180", "32x32"];
            sizes.forEach(function(s) {{
                var el = window.parent.document.querySelector("link[rel='icon'][sizes='" + s + "']");
                if (!el) {{
                    el = window.parent.document.createElement("link");
                    el.rel = "icon";
                    el.sizes = s;
                    head.appendChild(el);
                }}
                el.href = iconUri;
            }});

            // 3. Titre mobile et capacité plein écran
            var metaApp = window.parent.document.querySelector("meta[name='apple-mobile-web-app-title']");
            if (!metaApp) {{
                metaApp = window.parent.document.createElement("meta");
                metaApp.name = "apple-mobile-web-app-title";
                head.appendChild(metaApp);
            }}
            metaApp.content = "Billard Saphir";

            var metaCap = window.parent.document.querySelector("meta[name='apple-mobile-web-app-capable']");
            if (!metaCap) {{
                metaCap = window.parent.document.createElement("meta");
                metaCap.name = "apple-mobile-web-app-capable";
                head.appendChild(metaCap);
            }}
            metaCap.content = "yes";

            // 4. Manifeste PWA
            var linkMan = window.parent.document.querySelector("link[rel='manifest']");
            if (!linkMan) {{
                linkMan = window.parent.document.createElement("link");
                linkMan.rel = "manifest";
                linkMan.href = "/app/static/manifest.json";
                head.appendChild(linkMan);
            }}
        }} catch(e) {{}}
    }})();
    </script>
    """
    st.components.v1.html(code_js, height=0)

def injecter_script_remonter_haut_de_page():
    """Désactivé : ne force plus la remontée automatique en haut de page."""
    pass

def injecter_theme_css_saphir():
    """Injecte le thème visuel global 'Ligue Saphir' (onglets, cartes de métriques, boutons tactiles et bandeaux)."""
    st.markdown(
        """
        <style>
        /* Onglets principaux et secondaires plus lisibles et ergonomiques sur tablette/PC */
        div[data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #f0f4f8;
            padding: 6px 8px;
            border-radius: 10px;
            border: 1px solid #d9e2ec;
        }
        button[data-baseweb="tab"] {
            border-radius: 8px !important;
            padding: 8px 16px !important;
            font-weight: 600 !important;
            color: #334e68 !important;
            transition: all 0.2s ease-in-out !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0b3c5d 0%, #16527a 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 2px 6px rgba(11, 60, 93, 0.28) !important;
            border-bottom: 3px solid #f59e0b !important;
        }
        button[data-baseweb="tab"]:hover:not([aria-selected="true"]) {
            background-color: #e1e8f0 !important;
            color: #0b3c5d !important;
        }

        /* Cartes de métriques (KPI) */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #0b3c5d;
            border-radius: 10px;
            padding: 10px 14px;
            box-shadow: 0 2px 5px rgba(15, 23, 42, 0.05);
        }

        /* Expanders des manches plus nets */
        div[data-testid="stExpander"] {
            border-radius: 10px !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            margin-bottom: 8px;
        }

        /* Boutons ergonomiques pour écrans tactiles */
        div.stButton > button {
            min-height: 40px;
            border-radius: 8px;
            font-weight: 600;
            transition: transform 0.1s ease, box-shadow 0.15s ease;
        }
        div.stButton > button:active {
            transform: scale(0.99);
        }

        /* Bandeau Podium Top 3 */
        .saphir-podium-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin: 10px 0 18px 0;
        }
        .saphir-podium-card {
            border-radius: 10px;
            padding: 12px 14px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        }
        .saphir-podium-1 {
            background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
            border: 2px solid #f59e0b;
        }
        .saphir-podium-2 {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            border: 2px solid #94a3b8;
        }
        .saphir-podium-3 {
            background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
            border: 2px solid #d97706;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def charger_mot_de_passe_admin():
    """Charge le mot de passe d'administration (défaut: saphir2026)."""
    if os.path.exists(ADMIN_CONFIG_FILE):
        try:
            with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return str(data.get("mot_de_passe", "saphir2026")).strip()
        except Exception:
            return "saphir2026"
    return "saphir2026"

def verifier_mot_de_passe_admin(saisie):
    """Vérifie si le mot de passe saisi est valide (tolérance aux espaces et casse)."""
    if not saisie or not isinstance(saisie, str):
        return False
    s_clean = saisie.strip()
    # Le mot de passe par défaut 'saphir2026' est TOUJOURS garanti et accepté
    if s_clean.lower() == "saphir2026":
        return True
    mdp_actuel = charger_mot_de_passe_admin()
    if s_clean == mdp_actuel or s_clean.lower() == mdp_actuel.lower():
        return True
    return False

def sauvegarder_mot_de_passe_admin(nouveau_mdp):
    """Enregistre le nouveau mot de passe administrateur."""
    try:
        with open(ADMIN_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"mot_de_passe": nouveau_mdp}, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def charger_equipes_csv():
    """Charge la liste des équipes et joueurs depuis le fichier CSV."""
    equipes = {}
    if os.path.exists(EQUIPES_CSV_FILE):
        try:
            with open(EQUIPES_CSV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = [p.strip() for p in line.strip().split(",") if p.strip()]
                    if len(parts) >= 2:
                        nom_eq = parts[0]
                        joueurs = parts[1:]
                        while len(joueurs) < 3:
                            joueurs.append(f"Joueur {len(joueurs)+1}")
                        equipes[nom_eq] = joueurs[:3]
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier {EQUIPES_CSV_FILE} : {e}")
    return equipes

def sauvegarder_equipes_csv(equipes_df_ou_dict):
    """Sauvegarde les équipes et leurs 3 joueurs dans le fichier equipes-saphir.csv.
    Format par ligne : Equipe,Joueur 1,Joueur 2,Joueur 3
    """
    try:
        lignes = []
        if isinstance(equipes_df_ou_dict, pd.DataFrame):
            for _, row in equipes_df_ou_dict.iterrows():
                eq = str(row.get("Equipe", "")).strip()
                if not eq:
                    continue
                j1 = str(row.get("Joueur 1", "")).strip()
                j2 = str(row.get("Joueur 2", "")).strip()
                j3 = str(row.get("Joueur 3", "")).strip()
                lignes.append(f"{eq},{j1},{j2},{j3}\n")
        elif isinstance(equipes_df_ou_dict, dict):
            for eq, joueurs in equipes_df_ou_dict.items():
                eq_clean = str(eq).strip()
                if not eq_clean:
                    continue
                j1 = str(joueurs[0]).strip() if len(joueurs) > 0 else ""
                j2 = str(joueurs[1]).strip() if len(joueurs) > 1 else ""
                j3 = str(joueurs[2]).strip() if len(joueurs) > 2 else ""
                lignes.append(f"{eq_clean},{j1},{j2},{j3}\n")
        elif isinstance(equipes_df_ou_dict, list):
            for row in equipes_df_ou_dict:
                if isinstance(row, dict):
                    eq = str(row.get("Equipe", "")).strip()
                    if not eq:
                        continue
                    j1 = str(row.get("Joueur 1", "")).strip()
                    j2 = str(row.get("Joueur 2", "")).strip()
                    j3 = str(row.get("Joueur 3", "")).strip()
                    lignes.append(f"{eq},{j1},{j2},{j3}\n")
                elif isinstance(row, (list, tuple)) and len(row) >= 4:
                    eq = str(row[0]).strip()
                    if not eq:
                        continue
                    lignes.append(f"{eq},{str(row[1]).strip()},{str(row[2]).strip()},{str(row[3]).strip()}\n")

        # Sauvegarde d'une copie de secours .bak
        if os.path.exists(EQUIPES_CSV_FILE):
            try:
                import shutil
                shutil.copyfile(EQUIPES_CSV_FILE, EQUIPES_CSV_FILE + ".bak")
            except Exception:
                pass

        with open(EQUIPES_CSV_FILE, "w", encoding="utf-8") as f:
            f.writelines(lignes)

        return True, f"{len(lignes)} équipe(s) enregistrée(s) avec succès dans equipes-saphir.csv."
    except Exception as e:
        return False, f"Erreur lors de la sauvegarde du fichier equipes-saphir.csv : {e}"

def charger_sauvegarde():
    """Lit le fichier de sauvegarde de secours sans jamais lever d'erreur."""
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            return {}
    return {}

def sauvegarder_donnees(data):
    """Écrit atomiquement la sauvegarde pour éviter les corruptions et horodate les modifications."""
    try:
        data["derniere_mise_a_jour"] = datetime.now().strftime("%H:%M:%S")
        data["ts_modif"] = time.time()
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde automatique : {e}")

def charger_config_email():
    """Charge la configuration SMTP au démarrage de l'application."""
    defaut = {
        "destinataires": "",
        "smtp_serveur": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_expediteur": "",
        "smtp_mdp": "",
        "smtp_ssl": False
    }
    if os.path.exists(CONFIG_EMAIL_FILE):
        try:
            with open(CONFIG_EMAIL_FILE, "r", encoding="utf-8") as f:
                donnees = json.load(f)
                defaut.update(donnees)
                return defaut
        except Exception:
            return defaut
    return defaut

def sauvegarder_config_email(cfg):
    try:
        with open(CONFIG_EMAIL_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

# ==============================================================================
# GESTION DU VERROU DE SESSION EXCLUSIF (UN SEUL MARQUEUR À LA FOIS)
# ==============================================================================
def gerer_verrou_session(my_session_id, veut_etre_editeur=True):
    """Vérifie si la session actuelle détient le verrou d'édition ou l'acquiert."""
    maintenant = time.time()
    lock_existant = {}
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                lock_existant = json.load(f)
        except Exception:
            lock_existant = {}

    detenteur = lock_existant.get("session_id")
    dernier_acces = lock_existant.get("dernier_acces", 0)
    expire = (maintenant - dernier_acces) > LOCK_TIMEOUT

    # Si l'utilisateur est volontairement en mode lecture / consultation
    if not veut_etre_editeur:
        if detenteur and not expire and detenteur != my_session_id:
            temps_restant = int(LOCK_TIMEOUT - (maintenant - dernier_acces))
            return False, max(0, temps_restant), True
        return False, 0, False

    if not detenteur or expire or detenteur == my_session_id:
        nouveau_lock = {
            "session_id": my_session_id,
            "dernier_acces": maintenant,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            with open(LOCK_FILE, "w", encoding="utf-8") as f:
                json.dump(nouveau_lock, f, indent=4)
        except Exception:
            pass
        return True, 0, False
    else:
        temps_restant = int(LOCK_TIMEOUT - (maintenant - dernier_acces))
        return False, max(0, temps_restant), True

def liberer_verrou(my_session_id):
    """Libère le verrou de session si détenu par cette session."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("session_id") == my_session_id:
                os.remove(LOCK_FILE)
        except Exception:
            pass

def forcer_prise_de_main(my_session_id):
    """Force l'acquisition du verrou (si l'utilisateur précédent a quitté sans libérer)."""
    nouveau_lock = {
        "session_id": my_session_id,
        "dernier_acces": time.time(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(nouveau_lock, f, indent=4)
    except Exception:
        pass

def calculer_score_absent(moyenne_val):
    """
    Calcule le score de manche d'un joueur absent :
    moyenne * 24 / 3, arrondi à l'entier le plus proche, plafonné à 7 maximum.
    Prend en compte la saisie sous forme ratio (ex: 0.650) ou pourcentage (ex: 65).
    """
    if moyenne_val is None:
        return 0
    try:
        val = float(moyenne_val)
    except (ValueError, TypeError):
        return 0
    ratio = val / 100.0 if val > 1.0 else val
    pts = int(round((ratio * 24.0) / 3.0))
    return min(7, max(0, pts))

def restaurer_session(data):
    """Restaure l'intégralité de la session (équipes, sélections, présences, scores défaut et points) dans st.session_state."""
    if not data or not isinstance(data, dict):
        return False

    def safe_set(key, val):
        try:
            st.session_state[key] = val
        except Exception:
            pass

    # 1. Équipes
    if "choix_rec" in data:
        safe_set("sel_equipe_rec", data["choix_rec"])
    elif "receveur" in data:
        safe_set("sel_equipe_rec", data["receveur"])

    if "choix_vis" in data:
        safe_set("sel_equipe_vis", data["choix_vis"])
    elif "visiteur" in data:
        safe_set("sel_equipe_vis", data["visiteur"])

    if "input_custom_rec" in data:
        safe_set("input_custom_rec", data["input_custom_rec"])
    if "input_custom_vis" in data:
        safe_set("input_custom_vis", data["input_custom_vis"])

    # 2. Sélections Joueurs
    for k in ["sel_j1_rec", "sel_j2_rec", "sel_j1_vis", "sel_j2_vis"]:
        if k in data:
            safe_set(k, data[k])

    # 3. Données des joueurs (présence, score absent, nom remplaçant)
    joueurs = data.get("joueurs", {})
    for p_id in ["j1_rec", "j2_rec", "j3_rec", "j1_vis", "j2_vis", "j3_vis"]:
        if p_id in joueurs:
            p_data = joueurs[p_id]
            pres = p_data.get("present", True)
            pts = int(p_data.get("pts_absent", 0))
            moy = float(p_data.get("moyenne", 0.625))
            nom = p_data.get("nom", "")

            safe_set(f"pres_{p_id}", pres)
            safe_set(f"pts_{p_id}", pts)
            safe_set(f"moy_{p_id}", moy)
            safe_set(f"prev_state_{p_id}", pres)
            safe_set(f"prev_pts_{p_id}", pts)
            safe_set(f"cust_{p_id}", nom)

    # 4. Scores des 9 manches
    matchs = data.get("matchs", {})
    for num in range(1, 10):
        m = matchs.get(str(num), {})
        if "score_a" in m:
            safe_set(f"s_a_{num}", int(m["score_a"]))
        if "score_b" in m:
            safe_set(f"s_b_{num}", int(m["score_b"]))

    return True

# ==============================================================================
# FEUILLE DE STYLE OFFICIELLE D'IMPRESSION (CALIBRÉE POUR UNE SEULE PAGE A4)
# ==============================================================================
STYLE_PRINT_A4 = """
@page {
    size: A4 portrait;
    margin: 6mm 8mm;
}
@media print {
    *, *:before, *:after {
        box-sizing: border-box !important;
    }
    html, body {
        width: 100% !important;
        height: auto !important;
        margin: 0 !important;
        padding: 0 !important;
        background: #ffffff !important;
        font-family: Arial, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 10.5pt !important;
        line-height: 1.25 !important;
        color: #111111 !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    .no-print {
        display: none !important;
    }
    /* Empêche toute rupture de page involontaire */
    .fiche-a4, table, tr, td, th, div, p {
        page-break-inside: avoid !important;
        break-inside: avoid !important;
    }
    .fiche-a4 {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        page-break-after: avoid !important;
        page-break-before: avoid !important;
        break-after: avoid !important;
    }
    .header-table {
        width: 100% !important;
        border-bottom: 2px solid #0b3c5d !important;
        padding-bottom: 3px !important;
        margin-bottom: 5px !important;
        border-collapse: collapse !important;
    }
    .header-logo-td {
        width: 48px !important;
        padding-right: 8px !important;
        vertical-align: middle !important;
    }
    .header-logo-img {
        height: 44px !important;
        width: 44px !important;
        object-fit: contain !important;
    }
    .header-title-h2 {
        color: #0b3c5d !important;
        margin: 0 !important;
        font-size: 15px !important;
        line-height: 1.2 !important;
    }
    .header-title-sub {
        color: #555 !important;
        font-size: 11px !important;
        font-weight: bold !important;
        margin-top: 1px !important;
    }
    .date-para {
        margin: 3px 0 5px 0 !important;
        font-size: 10.5px !important;
        line-height: 1.2 !important;
    }
    .rectif-box {
        background-color: #fff3cd !important;
        color: #856404 !important;
        border: 1px solid #ffeeba !important;
        border-left: 4px solid #ffc107 !important;
        padding: 3px 6px !important;
        border-radius: 4px !important;
        margin-bottom: 4px !important;
        font-size: 9.5px !important;
        line-height: 1.2 !important;
    }
    .result-container {
        background-color: #f4f6f9 !important;
        padding: 6px 10px !important;
        border-radius: 4px !important;
        margin-bottom: 6px !important;
    }
    .result-h3 {
        margin: 0 0 2px 0 !important;
        color: #1e3d59 !important;
        font-size: 12px !important;
    }
    .result-scores {
        font-size: 13px !important;
        margin: 2px 0 !important;
        line-height: 1.2 !important;
    }
    .result-scores-pts {
        font-size: 16px !important;
        color: #0d47a1 !important;
        font-weight: bold !important;
    }
    .result-winner {
        font-weight: bold !important;
        color: #2e7d32 !important;
        font-size: 12px !important;
        margin: 2px 0 3px 0 !important;
    }
    .absents-box {
        font-size: 9.5px !important;
        padding: 3px 6px !important;
        margin: 3px 0 !important;
    }
    .joueurs-flex {
        display: flex !important;
        gap: 8px !important;
        margin-top: 4px !important;
    }
    .joueur-card {
        flex: 1 !important;
        background: #ffffff !important;
        padding: 4px 6px !important;
        border-radius: 4px !important;
        border: 1px solid #ddd !important;
    }
    .joueur-card h4 {
        margin: 0 0 2px 0 !important;
        color: #0b3c5d !important;
        font-size: 10.5px !important;
    }
    .joueur-card ul {
        margin: 0 !important;
        padding-left: 14px !important;
        font-size: 10px !important;
        line-height: 1.2 !important;
    }
    .approb-container {
        margin-top: 4px !important;
        padding: 4px 6px !important;
        background-color: #f1f8e9 !important;
        border: 1px solid #c8e6c9 !important;
        border-left: 3px solid #2e7d32 !important;
        border-radius: 4px !important;
    }
    .approb-h4 {
        margin: 0 0 2px 0 !important;
        color: #1b5e20 !important;
        font-size: 10px !important;
    }
    .approb-txt {
        font-size: 9.5px !important;
        color: #333 !important;
        line-height: 1.2 !important;
    }
    .manches-table {
        width: 100% !important;
        border-collapse: collapse !important;
        font-size: 10.5px !important;
        line-height: 1.15 !important;
        margin-top: 4px !important;
    }
    .manches-table th {
        background-color: #0b3c5d !important;
        color: #ffffff !important;
        padding: 3.5px 5px !important;
        font-size: 10.5px !important;
        font-weight: bold !important;
        text-align: center !important;
    }
    .manches-table td {
        padding: 2.8px 5px !important;
        font-size: 10px !important;
        border-bottom: 1px solid #e0e0e0 !important;
        text-align: center !important;
    }
    .footer-note {
        font-size: 8px !important;
        color: #777 !important;
        margin-top: 4px !important;
        text-align: center !important;
    }
}
"""

def generer_resume_match(receveur, visiteur, matchs, total_rec, total_vis, pts_joueurs, dict_joueurs, date_str, absents_info=None, rectif_bandeau="", approbateur_rec="", approbateur_vis=""):
    """Génère le résumé en texte brut et en HTML avec les totaux par équipe et par joueur (formaté pour impression A4)."""
    lignes_texte = [
        f"Ligue de billard Boule en main - Résultats officiels",
        f"Date : {date_str}",
        f"Rencontre : {receveur} vs {visiteur}",
        f"Score final : {receveur} ({total_rec} pts) - {visiteur} ({total_vis} pts)"
    ]

    if absents_info:
        lignes_texte.append(f"Joueurs absents : {', '.join(absents_info)}")

    if approbateur_rec or approbateur_vis:
        lignes_texte.extend([
            f"Approbation {receveur} : {approbateur_rec or 'Non renseigné'}",
            f"Approbation {visiteur} : {approbateur_vis or 'Non renseigné'}"
        ])

    def _recup_nom(d, key, fallback=""):
        if isinstance(d, dict) and key in d:
            val = d[key]
            if isinstance(val, dict):
                return val.get("nom", fallback)
            return str(val)
        return fallback

    def _recup_pts(d, key):
        if isinstance(d, dict) and key in d:
            return d[key]
        return 0

    j1_r = _recup_nom(dict_joueurs, "j1_rec", "Joueur 1")
    j2_r = _recup_nom(dict_joueurs, "j2_rec", "Joueur 2")
    j3_r = _recup_nom(dict_joueurs, "j3_rec", "Joueur 3")
    j1_v = _recup_nom(dict_joueurs, "j1_vis", "Joueur 1")
    j2_v = _recup_nom(dict_joueurs, "j2_vis", "Joueur 2")
    j3_v = _recup_nom(dict_joueurs, "j3_vis", "Joueur 3")

    p1_r = _recup_pts(pts_joueurs, "j1_rec")
    p2_r = _recup_pts(pts_joueurs, "j2_rec")
    p3_r = _recup_pts(pts_joueurs, "j3_rec")
    p1_v = _recup_pts(pts_joueurs, "j1_vis")
    p2_v = _recup_pts(pts_joueurs, "j2_vis")
    p3_v = _recup_pts(pts_joueurs, "j3_vis")

    lignes_texte.extend([
        f"\nPoints individuels {receveur} :",
        f"  - {j1_r} : {p1_r} pts",
        f"  - {j2_r} : {p2_r} pts",
        f"  - {j3_r} : {p3_r} pts",
        f"\nPoints individuels {visiteur} :",
        f"  - {j1_v} : {p1_v} pts",
        f"  - {j2_v} : {p2_v} pts",
        f"  - {j3_v} : {p3_v} pts",
        "\nDétail des 9 manches :"
    ])

    lignes_html = []
    for num in range(1, 10):
        m = matchs.get(str(num), {})
        sa = m.get("score_a", 0)
        sb = m.get("score_b", 0)

        ja_raw = m.get("joueur_a", "")
        jb_raw = m.get("joueur_b", "")

        if isinstance(ja_raw, str) and ja_raw in dict_joueurs:
            ja = dict_joueurs[ja_raw].get("nom", ja_raw)
            ja_abs = not dict_joueurs[ja_raw].get("present", True)
        else:
            ja = str(ja_raw)
            ja_abs = bool(m.get("joueur_a_absent", False))

        if isinstance(jb_raw, str) and jb_raw in dict_joueurs:
            jb = dict_joueurs[jb_raw].get("nom", jb_raw)
            jb_abs = not dict_joueurs[jb_raw].get("present", True)
        else:
            jb = str(jb_raw)
            jb_abs = bool(m.get("joueur_b_absent", False))

        label_a = f"{ja} (Absent : {sa} pts)" if ja_abs else ja
        label_b = f"{jb} (Absent : {sb} pts)" if jb_abs else jb

        lignes_texte.append(f"Manche {num} : {label_a} ({sa}) vs ({sb}) {label_b}")

        bg_color = "#f9fbfd" if num % 2 == 1 else "#ffffff"
        sa_fmt = f"<strong>{sa}</strong>" if sa == 8 else f"{sa}"
        sb_fmt = f"<strong>{sb}</strong>" if sb == 8 else f"{sb}"
        lignes_html.append(f"""
        <tr style="background-color: {bg_color}; border-bottom: 1px solid #e0e0e0; text-align: center;">
            <td style="padding: 5px 6px; font-weight: bold;">Manche {num}</td>
            <td style="padding: 5px 6px; text-align: left;">{label_a}</td>
            <td style="padding: 5px 6px; font-weight: bold; font-size: 13px;">{sa_fmt}</td>
            <td style="padding: 5px 6px; font-weight: bold; font-size: 13px;">{sb_fmt}</td>
            <td style="padding: 5px 6px; text-align: left;">{label_b}</td>
        </tr>
        """)

    texte = "\n".join(lignes_texte)

    absents_html_bloc = ""
    if absents_info:
        absents_html_bloc = f"<div class='absents-box' style='color: #d32f2f; margin: 4px 0;'><strong>Joueur(s) absent(s) :</strong> {', '.join(absents_info)}</div>"

    approbateurs_html_bloc = ""
    if approbateur_rec or approbateur_vis:
        approbateurs_html_bloc = f"""
            <div class="approb-container" style="margin-top: 10px; padding: 8px 12px; background-color: #f1f8e9; border: 1px solid #c8e6c9; border-left: 4px solid #2e7d32; border-radius: 6px;">
                <h4 class="approb-h4" style="margin: 0 0 4px 0; color: #1b5e20; font-size: 13px;">✍️ Approbations officielles de la feuille de match :</h4>
                <div class="approb-txt" style="font-size: 12px; color: #333;">
                    • Représentant <strong>{receveur}</strong> : <u>{approbateur_rec or 'Non renseigné'}</u><br>
                    • Représentant <strong>{visiteur}</strong> : <u>{approbateur_vis or 'Non renseigné'}</u>
                </div>
            </div>
        """

    logo_b64 = charger_armoiries_base64()
    src_val = logo_b64 if logo_b64 else "cid:armoiries_logo"
    arm_existe = bool(logo_b64 or os.path.isfile(find_armoiries_path()))
    logo_td = f'<td class="header-logo-td" style="width: 65px; vertical-align: middle; padding-right: 12px;"><img class="header-logo-img" src="{src_val}" alt="Armoiries" style="height: 60px; width: 60px; object-fit: contain; border-radius: 4px;"></td>' if arm_existe else ''

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Feuille de match officielle - Ligue de billard Boule en main</title>
    <style>
        {STYLE_PRINT_A4}
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.5;
            color: #222;
            margin: 0;
            padding: 10px;
        }}
        .fiche-a4 {{
            max-width: 850px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="fiche-a4">
        <div class="no-print" style="text-align: right; margin-bottom: 10px;">
            <button onclick="window.print()" style="background-color: #0b3c5d; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer;">
                🖨️ Imprimer cette feuille (A4)
            </button>
        </div>
        <table class="header-table" style="width: 100%; border-bottom: 2px solid #0b3c5d; padding-bottom: 6px; margin-bottom: 10px; border-collapse: collapse;">
            <tr>
                {logo_td}
                <td class="header-title" style="vertical-align: middle;">
                    <h2 class="header-title-h2" style="color: #0b3c5d; margin: 0; font-size: 19px;">🎱 Ligue de billard Boule en main</h2>
                    <div class="header-title-sub" style="color: #555; font-size: 13px; font-weight: bold; margin-top: 2px;">Feuille de match officielle</div>
                </td>
            </tr>
        </table>
        <p class="date-para" style="margin: 4px 0 8px 0; font-size: 13px;"><strong>Date :</strong> {date_str}</p>
        {rectif_bandeau}
        <div class="result-container" style="background-color: #f4f6f9; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px;">
            <h3 class="result-h3" style="margin: 0; color: #1e3d59; font-size: 15px;">Résultat final du match :</h3>
            <p class="result-scores" style="font-size: 16px; margin: 6px 0;">
                <strong>{receveur}</strong> : <span class="result-scores-pts" style="font-size: 20px; color: #0d47a1;">{total_rec}</span> pts &nbsp;|&nbsp;
                <strong>{visiteur}</strong> : <span class="result-scores-pts" style="font-size: 20px; color: #0d47a1;">{total_vis}</span> pts
            </p>
            <p class="result-winner" style="font-weight: bold; color: #2e7d32; font-size: 14px; margin: 4px 0;">
                Vainqueur : {receveur if total_rec > total_vis else (visiteur if total_vis > total_rec else "Égalité")}
            </p>
            {absents_html_bloc}
            
            <div class="joueurs-flex" style="margin-top: 10px; display: flex; gap: 14px;">
                <div class="joueur-card" style="flex: 1; background: white; padding: 8px 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 6px 0; color: #0b3c5d; font-size: 13px;">Points individuels — {receveur} :</h4>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                        <li><strong>{j1_r}</strong> : {p1_r} pts</li>
                        <li><strong>{j2_r}</strong> : {p2_r} pts</li>
                        <li><strong>{j3_r}</strong> : {p3_r} pts</li>
                    </ul>
                </div>
                <div class="joueur-card" style="flex: 1; background: white; padding: 8px 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 6px 0; color: #0b3c5d; font-size: 13px;">Points individuels — {visiteur} :</h4>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                        <li><strong>{j1_v}</strong> : {p1_v} pts</li>
                        <li><strong>{j2_v}</strong> : {p2_v} pts</li>
                        <li><strong>{j3_v}</strong> : {p3_v} pts</li>
                    </ul>
                </div>
            </div>
            {approbateurs_html_bloc}
        </div>
        <table class="manches-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background-color: #0b3c5d; color: white;">
                    <th style="padding: 7px 6px;">Manche</th>
                    <th style="padding: 7px 6px; text-align: left;">Joueur ({receveur})</th>
                    <th style="padding: 7px 6px;">Pts</th>
                    <th style="padding: 7px 6px;">Pts</th>
                    <th style="padding: 7px 6px; text-align: left;">Joueur ({visiteur})</th>
                </tr>
            </thead>
            <tbody>
                {''.join(lignes_html)}
            </tbody>
        </table>
        <p class="footer-note" style="font-size: 11px; color: #777; margin-top: 12px; text-align: center;">
            Feuille générée automatiquement via l'application officielle de saisie - Ligue de billard Boule en main.
        </p>
    </div>
</body>
</html>
"""
    return texte, html

def charger_historique_matchs():
    """Charge la liste des matchs archivés depuis le fichier d'historique."""
    if os.path.exists(HISTORIQUE_FILE):
        try:
            with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
    return []

def verifier_match_deja_valide(equipe_rec, equipe_vis, matchs_actuels, historique):
    """Vérifie si le match actuellement affiché a déjà été validé et archivé."""
    if st.session_state.get("match_en_cours_deja_valide", False):
        return True, "session_actuelle"

    if not historique or not matchs_actuels:
        return False, None

    tot_rec = sum(m.get("score_a", 0) for m in matchs_actuels.values())
    tot_vis = sum(m.get("score_b", 0) for m in matchs_actuels.values())

    # Si aucun score n'est encore saisi (0 - 0), le match n'est pas déjà validé
    if tot_rec == 0 and tot_vis == 0:
        return False, None

    for m_hist in historique:
        h_rec = m_hist.get("receveur", m_hist.get("equipe_receveur"))
        h_vis = m_hist.get("visiteur", m_hist.get("equipe_visiteur"))
        if h_rec == equipe_rec and h_vis == equipe_vis:
            m_h = m_hist.get("matchs", {})
            correspondance = True
            for num in range(1, 10):
                s_num = str(num)
                try:
                    sc_a_h = int(m_h.get(s_num, {}).get("score_a", -1))
                    sc_b_h = int(m_h.get(s_num, {}).get("score_b", -1))
                    sc_a_act = int(matchs_actuels.get(s_num, {}).get("score_a", -2))
                    sc_b_act = int(matchs_actuels.get(s_num, {}).get("score_b", -2))
                except (ValueError, TypeError):
                    correspondance = False
                    break
                if sc_a_h != sc_a_act or sc_b_h != sc_b_act:
                    correspondance = False
                    break
            if correspondance:
                d_m = m_hist.get("date_enregistrement", m_hist.get("date", "Date inconnue"))
                return True, d_m

    return False, None

def obtenir_html_match(m):
    """Renvoie le HTML officiel du match ou le reconstitue fidèlement à partir des données archivées, calibré pour une page A4."""
    rectif_bandeau = ""
    if m.get("date_rectification"):
        d_rect = m.get("date_rectification")
        m_rect = m.get("motif_rectification", "Correction administrative")
        rectif_bandeau = f"""
        <div class="rectif-box" style="background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-left: 5px solid #ffc107; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; font-size: 12px;">
            <strong>⚠️ FEUILLE OFFICIELLE RECTIFIÉE</strong> le {d_rect}<br>
            <em>Motif officiel : {m_rect}</em>
        </div>
        """

    app_r = m.get("approbateur_receveur", "")
    app_v = m.get("approbateur_visiteur", "")
    nom_rec_disp = m.get("receveur", m.get("equipe_receveur", "Receveur"))
    nom_vis_disp = m.get("visiteur", m.get("equipe_visiteur", "Visiteur"))
    approbateurs_bloc = ""
    if app_r or app_v:
        approbateurs_bloc = f"""
        <div class="approb-container" style="margin-top: 10px; padding: 8px 12px; background-color: #f1f8e9; border: 1px solid #c8e6c9; border-left: 4px solid #2e7d32; border-radius: 6px;">
            <h4 class="approb-h4" style="margin: 0 0 4px 0; color: #1b5e20; font-size: 13px;">✍️ Approbations officielles de la feuille de match :</h4>
            <div class="approb-txt" style="font-size: 12px; color: #333;">
                • Représentant <strong>{nom_rec_disp}</strong> : <u>{app_r or 'Non renseigné'}</u><br>
                • Représentant <strong>{nom_vis_disp}</strong> : <u>{app_v or 'Non renseigné'}</u>
            </div>
        </div>
        """

    if m.get("html_officiel"):
        html_existant = m["html_officiel"]
        # Injection du style d'impression A4 pour forcer une seule page
        if "<style>" in html_existant and "</style>" in html_existant:
            html_existant = re.sub(r"<style>.*?</style>", f"<style>\n{STYLE_PRINT_A4}\n</style>", html_existant, flags=re.DOTALL)
        elif "</head>" in html_existant:
            html_existant = html_existant.replace("</head>", f"<style>\n{STYLE_PRINT_A4}\n</style>\n</head>")

        if "Armoiries" not in html_existant and "armoiries" not in html_existant:
            logo_b64 = charger_armoiries_base64()
            if logo_b64:
                logo_td = f'<td class="header-logo-td" style="width: 65px; vertical-align: middle; padding-right: 12px;"><img class="header-logo-img" src="{logo_b64}" alt="Armoiries" style="height: 60px; width: 60px; object-fit: contain; border-radius: 4px;"></td>'
                html_existant = html_existant.replace(
                    '<td style="vertical-align: middle;">',
                    f'{logo_td}\n                <td class="header-title" style="vertical-align: middle;">'
                )
        if m.get("date_rectification") and "FEUILLE OFFICIELLE RECTIFIÉE" not in html_existant:
            html_existant = html_existant.replace('<div style="background-color: #f4f6f9;', f'{rectif_bandeau}\n        <div style="background-color: #f4f6f9;')
        if (app_r or app_v) and "Approbations officielles" not in html_existant:
            html_existant = html_existant.replace(
                '<table style="width: 100%; border-collapse: collapse; font-size: 14px;">',
                f'{approbateurs_bloc}\n        <table class="manches-table" style="width: 100%; border-collapse: collapse; font-size: 14px;">'
            )
        return html_existant
    
    rec = m.get("receveur", "Receveur")
    vis = m.get("visiteur", "Visiteur")
    date_str = m.get("date_enregistrement", m.get("date", "Date inconnue"))
    tot_rec = m.get("total_receveur", 0)
    tot_vis = m.get("total_visiteur", 0)
    matchs = m.get("matchs", {})
    
    pts_rec_j = {}
    pts_vis_j = {}
    lignes_html = []
    
    for num in range(1, 10):
        m_info = matchs.get(str(num), {})
        sa = m_info.get("score_a", 0)
        sb = m_info.get("score_b", 0)
        ja = m_info.get("joueur_a", f"Joueur ({rec})")
        jb = m_info.get("joueur_b", f"Joueur ({vis})")
        ja_abs = m_info.get("joueur_a_absent", False)
        jb_abs = m_info.get("joueur_b_absent", False)
        
        label_a = f"{ja} (Absent : {sa} pts)" if ja_abs else ja
        label_b = f"{jb} (Absent : {sb} pts)" if jb_abs else jb
        
        pts_rec_j[ja] = pts_rec_j.get(ja, 0) + sa
        pts_vis_j[jb] = pts_vis_j.get(jb, 0) + sb
        
        bg_color = "#f9fbfd" if num % 2 == 1 else "#ffffff"
        sa_fmt = f"<strong>{sa}</strong>" if sa == 8 else f"{sa}"
        sb_fmt = f"<strong>{sb}</strong>" if sb == 8 else f"{sb}"
        
        lignes_html.append(f"""
            <tr style="background-color: {bg_color}; border-bottom: 1px solid #ddd; text-align: center;">
                <td style="padding: 5px 6px;"><strong>Manche {num}</strong></td>
                <td style="padding: 5px 6px; text-align: left;">{label_a}</td>
                <td style="padding: 5px 6px; font-weight: bold; font-size: 13px;">{sa_fmt}</td>
                <td style="padding: 5px 6px; font-weight: bold; font-size: 13px;">{sb_fmt}</td>
                <td style="padding: 5px 6px; text-align: left;">{label_b}</td>
            </tr>
        """)

    li_rec = "".join([f"<li><strong>{nom}</strong> : {pts} pts</li>" for nom, pts in pts_rec_j.items()])
    li_vis = "".join([f"<li><strong>{nom}</strong> : {pts} pts</li>" for nom, pts in pts_vis_j.items()])
    vainqueur = rec if tot_rec > tot_vis else (vis if tot_vis > tot_rec else "Égalité")

    logo_b64 = charger_armoiries_base64()
    src_val = logo_b64 if logo_b64 else "cid:armoiries_logo"
    arm_existe = bool(logo_b64 or os.path.isfile(find_armoiries_path()))
    logo_td = f'<td class="header-logo-td" style="width: 65px; vertical-align: middle; padding-right: 12px;"><img class="header-logo-img" src="{src_val}" alt="Armoiries" style="height: 60px; width: 60px; object-fit: contain; border-radius: 4px;"></td>' if arm_existe else ''

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Feuille de match officielle - Ligue de billard Boule en main</title>
    <style>
        {STYLE_PRINT_A4}
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.5;
            color: #222;
            margin: 0;
            padding: 10px;
        }}
        .fiche-a4 {{
            max-width: 850px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="fiche-a4">
        <div class="no-print" style="text-align: right; margin-bottom: 10px;">
            <button onclick="window.print()" style="background-color: #0b3c5d; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer;">
                🖨️ Imprimer cette feuille (A4)
            </button>
        </div>
        <table class="header-table" style="width: 100%; border-bottom: 2px solid #0b3c5d; padding-bottom: 6px; margin-bottom: 10px; border-collapse: collapse;">
            <tr>
                {logo_td}
                <td class="header-title" style="vertical-align: middle;">
                    <h2 class="header-title-h2" style="color: #0b3c5d; margin: 0; font-size: 19px;">🎱 Ligue de billard Boule en main</h2>
                    <div class="header-title-sub" style="color: #555; font-size: 13px; font-weight: bold; margin-top: 2px;">Feuille de match officielle</div>
                </td>
            </tr>
        </table>
        <p class="date-para" style="margin: 4px 0 8px 0; font-size: 13px;"><strong>Date :</strong> {date_str}</p>
        {rectif_bandeau}
        <div class="result-container" style="background-color: #f4f6f9; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px;">
            <h3 class="result-h3" style="margin: 0; color: #1e3d59; font-size: 15px;">Résultat final du match :</h3>
            <p class="result-scores" style="font-size: 16px; margin: 6px 0;">
                <strong>{rec}</strong> : <span class="result-scores-pts" style="font-size: 20px; color: #0d47a1;">{tot_rec}</span> pts &nbsp;|&nbsp;
                <strong>{vis}</strong> : <span class="result-scores-pts" style="font-size: 20px; color: #0d47a1;">{tot_vis}</span> pts
            </p>
            <p class="result-winner" style="font-weight: bold; color: #2e7d32; font-size: 14px; margin: 4px 0;">
                Vainqueur : {vainqueur}
            </p>
            <div class="joueurs-flex" style="margin-top: 10px; display: flex; gap: 14px;">
                <div class="joueur-card" style="flex: 1; background: white; padding: 8px 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 6px 0; color: #0b3c5d; font-size: 13px;">Points individuels — {rec} :</h4>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">{li_rec}</ul>
                </div>
                <div class="joueur-card" style="flex: 1; background: white; padding: 8px 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 6px 0; color: #0b3c5d; font-size: 13px;">Points individuels — {vis} :</h4>
                    <ul style="margin: 0; padding-left: 18px; font-size: 13px;">{li_vis}</ul>
                </div>
            </div>
            {approbateurs_bloc}
        </div>
        <table class="manches-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background-color: #0b3c5d; color: white;">
                    <th style="padding: 7px 6px;">Manche</th>
                    <th style="padding: 7px 6px; text-align: left;">Joueur ({rec})</th>
                    <th style="padding: 7px 6px;">Pts</th>
                    <th style="padding: 7px 6px;">Pts</th>
                    <th style="padding: 7px 6px; text-align: left;">Joueur ({vis})</th>
                </tr>
            </thead>
            <tbody>
                {''.join(lignes_html)}
            </tbody>
        </table>
        <p class="footer-note" style="font-size: 11px; color: #777; margin-top: 12px; text-align: center;">
            Feuille générée automatiquement via l'application officielle de saisie - Ligue de billard Boule en main.
        </p>
    </div>
</body>
</html>
"""
    return html

def generer_rapport_historique_convivial(historique):
    """Génère un bilan officiel complet et convivial de tous les matchs archivés (texte et HTML)."""
    date_gen = datetime.now().strftime("%d/%m/%Y à %H:%M")
    nb_total = len(historique)

    stats_equipes = {}
    total_pts_ligue = 0
    matchs_traites = []

    for idx, m in enumerate(historique):
        rec = m.get("receveur", m.get("equipe_receveur", "Receveur"))
        vis = m.get("visiteur", m.get("equipe_visiteur", "Visiteur"))
        d_m = m.get("date_enregistrement", m.get("date", "Date inconnue"))
        m_dict = m.get("matchs", {})

        tr = m.get("total_receveur")
        if tr is None:
            tr = sum(m_dict.get(str(i), {}).get("score_a", 0) for i in range(1, 10))
        tv = m.get("total_visiteur")
        if tv is None:
            tv = sum(m_dict.get(str(i), {}).get("score_b", 0) for i in range(1, 10))

        try:
            tr = int(tr)
        except (ValueError, TypeError):
            tr = 0
        try:
            tv = int(tv)
        except (ValueError, TypeError):
            tv = 0

        total_pts_ligue += (tr + tv)

        app_r = m.get("approbateur_receveur", "")
        app_v = m.get("approbateur_visiteur", "")
        est_rect = bool(m.get("date_rectification"))
        d_rect = m.get("date_rectification", "")

        for eq in [rec, vis]:
            if eq not in stats_equipes:
                stats_equipes[eq] = {"pj": 0, "v": 0, "d": 0, "n": 0, "pour": 0, "contre": 0}

        stats_equipes[rec]["pj"] += 1
        stats_equipes[vis]["pj"] += 1
        stats_equipes[rec]["pour"] += tr
        stats_equipes[rec]["contre"] += tv
        stats_equipes[vis]["pour"] += tv
        stats_equipes[vis]["contre"] += tr

        if tr > tv:
            stats_equipes[rec]["v"] += 1
            stats_equipes[vis]["d"] += 1
            vainqueur = rec
        elif tv > tr:
            stats_equipes[vis]["v"] += 1
            stats_equipes[rec]["d"] += 1
            vainqueur = vis
        else:
            stats_equipes[rec]["n"] += 1
            stats_equipes[vis]["n"] += 1
            vainqueur = "Égalité"

        matchs_traites.append({
            "idx": idx + 1,
            "date": d_m,
            "receveur": rec,
            "visiteur": vis,
            "tr": tr,
            "tv": tv,
            "vainqueur": vainqueur,
            "app_r": app_r,
            "app_v": app_v,
            "rectifie": est_rect,
            "d_rect": d_rect,
            "matchs": m_dict
        })

    # Classement général trié
    classement = sorted(
        stats_equipes.items(),
        key=lambda item: (item[1]["v"], item[1]["pour"] - item[1]["contre"], item[1]["pour"]),
        reverse=True
    )

    # 1. Version TEXTE BRUT
    lignes_texte = [
        "============================================================",
        "🎱 LIGUE DE BILLARD BOULE EN MAIN",
        "BILAN OFFICIEL ET HISTORIQUE COMPLET DES MATCHS",
        f"Généré le : {date_gen}",
        f"Total de rencontres jouées : {nb_total}",
        f"Total de points cumulés : {total_pts_ligue} pts",
        "============================================================\n",
        "🏆 CLASSEMENT GÉNÉRAL DES ÉQUIPES :",
        "-" * 60,
        f"{'Rang':<5} {'Équipe':<20} {'PJ':<4} {'V':<4} {'D':<4} {'N':<4} {'BP':<6} {'BC':<6} {'Diff':<6}",
        "-" * 60
    ]

    for rang, (eq, st_e) in enumerate(classement, start=1):
        diff = st_e["pour"] - st_e["contre"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        lignes_texte.append(
            f"{rang:<5} {eq:<20} {st_e['pj']:<4} {st_e['v']:<4} {st_e['d']:<4} {st_e['n']:<4} {st_e['pour']:<6} {st_e['contre']:<6} {diff_str:<6}"
        )

    lignes_texte.extend([
        "-" * 60,
        "\n📋 HISTORIQUE CHRONOLOGIQUE DES RENCONTRES :",
        "-" * 60
    ])

    for m_item in matchs_traites:
        app_txt = ""
        if m_item["app_r"] or m_item["app_v"]:
            app_txt = f" | Approuvé par : {m_item['app_r'] or 'N/D'} & {m_item['app_v'] or 'N/D'}"
        rect_txt = " [Rectifié]" if m_item["rectifie"] else ""
        lignes_texte.append(
            f"Match #{m_item['idx']} ({m_item['date']}){rect_txt} : {m_item['receveur']} ({m_item['tr']} pts) vs {m_item['visiteur']} ({m_item['tv']} pts) -> Vainqueur : {m_item['vainqueur']}{app_txt}"
        )

    lignes_texte.append("\n" + "=" * 60)
    texte_brut = "\n".join(lignes_texte)

    # 2. Version HTML (Mise en page conviviale, responsive et moderne)
    logo_b64 = charger_armoiries_base64()
    src_val = logo_b64 if logo_b64 else "cid:armoiries_logo"
    arm_existe = bool(logo_b64 or os.path.isfile(find_armoiries_path()))
    logo_td = f'<td style="width: 75px; vertical-align: middle; padding-right: 14px;"><img src="{src_val}" alt="Armoiries" style="height: 70px; width: 70px; object-fit: contain; border-radius: 6px;"></td>' if arm_existe else ''

    # Lignes du tableau de classement
    lignes_classement_html = []
    medailles = {1: "🥇", 2: "🥈", 3: "🥉"}
    for rang, (eq, st_e) in enumerate(classement, start=1):
        diff = st_e["pour"] - st_e["contre"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        diff_color = "#2e7d32" if diff > 0 else ("#c62828" if diff < 0 else "#555")
        badge_rang = medailles.get(rang, f"<strong>#{rang}</strong>")
        bg_row = "#f9fbfd" if rang % 2 == 1 else "#ffffff"

        lignes_classement_html.append(f"""
        <tr style="background-color: {bg_row}; border-bottom: 1px solid #e0e0e0; text-align: center;">
            <td style="padding: 9px; font-size: 15px;">{badge_rang}</td>
            <td style="padding: 9px; text-align: left; font-weight: bold; color: #0b3c5d;">{eq}</td>
            <td style="padding: 9px;">{st_e['pj']}</td>
            <td style="padding: 9px; font-weight: bold; color: #2e7d32;">{st_e['v']}</td>
            <td style="padding: 9px; color: #c62828;">{st_e['d']}</td>
            <td style="padding: 9px; color: #666;">{st_e['n']}</td>
            <td style="padding: 9px; font-weight: bold; color: #0d47a1;">{st_e['pour']}</td>
            <td style="padding: 9px; color: #555;">{st_e['contre']}</td>
            <td style="padding: 9px; font-weight: bold; color: {diff_color};">{diff_str}</td>
        </tr>
        """)

    # Lignes de l'historique des matchs
    lignes_matchs_html = []
    for m_item in matchs_traites:
        vainq_badge = f"<span style='background-color: #e8f5e9; color: #2e7d32; font-weight: bold; padding: 3px 8px; border-radius: 12px; font-size: 12px;'>🏆 {m_item['vainqueur']}</span>" if m_item['vainqueur'] != "Égalité" else "<span style='background-color: #fff3e0; color: #e65100; font-weight: bold; padding: 3px 8px; border-radius: 12px; font-size: 12px;'>⚖️ Match nul</span>"
        rect_badge = f"<span style='background-color: #fff3cd; color: #856404; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px;'>⚠️ Rectifié</span>" if m_item['rectifie'] else ""

        app_html = ""
        if m_item['app_r'] or m_item['app_v']:
            app_html = f"<div style='font-size: 11px; color: #555; margin-top: 3px;'>✍️ Approuvé par : <strong>{m_item['app_r'] or 'N/D'}</strong> & <strong>{m_item['app_v'] or 'N/D'}</strong></div>"

        # Mini résumé des 9 manches
        mini_manches_tds = []
        for i_m in range(1, 10):
            m_sc = m_item["matchs"].get(str(i_m), {})
            s_a = m_sc.get("score_a", 0)
            s_b = m_sc.get("score_b", 0)
            mini_manches_tds.append(f"<span style='font-size: 10px; background: #eef2f5; padding: 2px 4px; border-radius: 3px; margin: 1px; display: inline-block;'>M{i_m}: <strong>{s_a}-{s_b}</strong></span>")

        mini_bloc = f"<div style='margin-top: 4px;'>{' '.join(mini_manches_tds)}</div>" if m_item["matchs"] else ""

        lignes_matchs_html.append(f"""
        <tr style="border-bottom: 1px solid #e0e0e0; vertical-align: middle;">
            <td style="padding: 10px; font-weight: bold; text-align: center; color: #0b3c5d;">#{m_item['idx']}</td>
            <td style="padding: 10px; font-size: 12px; color: #555; text-align: center;">{m_item['date']}{rect_badge}</td>
            <td style="padding: 10px; text-align: right; font-weight: bold;">
                {m_item['receveur']} <span style="font-size: 16px; color: #0d47a1; margin-left: 6px;">{m_item['tr']}</span>
            </td>
            <td style="padding: 10px; text-align: center; font-weight: bold; color: #999;">vs</td>
            <td style="padding: 10px; text-align: left; font-weight: bold;">
                <span style="font-size: 16px; color: #0d47a1; margin-right: 6px;">{m_item['tv']}</span> {m_item['visiteur']}
            </td>
            <td style="padding: 10px; text-align: center;">{vainq_badge}</td>
            <td style="padding: 10px; font-size: 12px;">{app_html}{mini_bloc}</td>
        </tr>
        """)

    html_complet = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Bilan officiel de la saison - Ligue de billard Boule en main</title>
        <style>
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ margin: 8mm; font-size: 11pt; }}
            }}
        </style>
    </head>
    <body style="font-family: Arial, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; line-height: 1.6; color: #222; margin: 0; padding: 15px; background-color: #fdfdfd;">
        <div style="max-width: 950px; margin: 0 auto; background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <!-- EN-TETE OFFICIEL -->
            <table style="width: 100%; border-bottom: 3px solid #0b3c5d; padding-bottom: 12px; margin-bottom: 18px; border-collapse: collapse;">
                <tr>
                    {logo_td}
                    <td style="vertical-align: middle;">
                        <h2 style="color: #0b3c5d; margin: 0; font-size: 22px;">🎱 Ligue de billard Boule en main</h2>
                        <div style="color: #444; font-size: 15px; font-weight: bold; margin-top: 3px;">
                            Bilan officiel & Historique complet des rencontres
                        </div>
                        <div style="color: #777; font-size: 12px; margin-top: 2px;">
                            Document officiel généré le {date_gen}
                        </div>
                    </td>
                </tr>
            </table>

            <!-- CARTES STATISTIQUES EN TETE -->
            <div style="display: flex; gap: 12px; margin-bottom: 22px;">
                <div style="flex: 1; background: #e8f0fe; border-left: 4px solid #1a73e8; border-radius: 6px; padding: 10px 14px; text-align: center;">
                    <div style="font-size: 12px; color: #1a73e8; font-weight: bold; text-transform: uppercase;">Rencontres archivées</div>
                    <div style="font-size: 24px; font-weight: bold; color: #0b3c5d;">{nb_total}</div>
                </div>
                <div style="flex: 1; background: #e8f5e9; border-left: 4px solid #2e7d32; border-radius: 6px; padding: 10px 14px; text-align: center;">
                    <div style="font-size: 12px; color: #2e7d32; font-weight: bold; text-transform: uppercase;">Équipes actives</div>
                    <div style="font-size: 24px; font-weight: bold; color: #1b5e20;">{len(stats_equipes)}</div>
                </div>
                <div style="flex: 1; background: #f3e5f5; border-left: 4px solid #7b1fa2; border-radius: 6px; padding: 10px 14px; text-align: center;">
                    <div style="font-size: 12px; color: #7b1fa2; font-weight: bold; text-transform: uppercase;">Points disputés</div>
                    <div style="font-size: 24px; font-weight: bold; color: #4a148c;">{total_pts_ligue}</div>
                </div>
            </div>

            <!-- SECTION 1 : CLASSEMENT GENERAL -->
            <h3 style="color: #0b3c5d; margin: 18px 0 10px 0; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; font-size: 17px;">
                🏆 Classement général des équipes
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 25px;">
                <thead>
                    <tr style="background-color: #0b3c5d; color: white;">
                        <th style="padding: 8px;">Rang</th>
                        <th style="padding: 8px; text-align: left;">Équipe</th>
                        <th style="padding: 8px;">PJ</th>
                        <th style="padding: 8px;">V</th>
                        <th style="padding: 8px;">D</th>
                        <th style="padding: 8px;">N</th>
                        <th style="padding: 8px;">Pts Pour</th>
                        <th style="padding: 8px;">Pts Contre</th>
                        <th style="padding: 8px;">Diff</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(lignes_classement_html)}
                </tbody>
            </table>

            <!-- SECTION 2 : HISTORIQUE COMPLET DES MATCHS -->
            <h3 style="color: #0b3c5d; margin: 25px 0 10px 0; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; font-size: 17px;">
                📋 Détail chronologique de toutes les rencontres
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #0b3c5d; color: white; text-align: center;">
                        <th style="padding: 8px; width: 45px;">#</th>
                        <th style="padding: 8px; width: 140px;">Date</th>
                        <th style="padding: 8px; text-align: right;">Receveur</th>
                        <th style="padding: 8px; width: 30px;"></th>
                        <th style="padding: 8px; text-align: left;">Visiteur</th>
                        <th style="padding: 8px; width: 130px;">Vainqueur</th>
                        <th style="padding: 8px;">Détails & Approbations</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(lignes_matchs_html)}
                </tbody>
            </table>

            <!-- PIED DE PAGE -->
            <div style="margin-top: 30px; padding-top: 12px; border-top: 1px solid #ddd; text-align: center; font-size: 12px; color: #777;">
                Feuille de synthèse officielle — Ligue de billard Boule en main.<br>
                Ce document récapitule l'intégralité des résultats archivés et validés par les marqueurs et capitaines officiels.
            </div>
        </div>
    </body>
    </html>
    """

    return texte_brut, html_complet

def envoyer_courriel(destinataires_str, sujet, texte_brut, html_contenu, config, pieces_jointes=None):
    """Envoie un courriel automatique via SMTP avec intégration universelle de l'image armoiries (CID inline) et pièces jointes."""
    destinataires = [d.strip() for d in destinataires_str.split(",") if d.strip()]
    if not destinataires:
        return False, "Aucune adresse de destinataire valide spécifiée."

    serveur_smtp = config.get("smtp_serveur", "").strip()
    port = int(config.get("smtp_port", 587))
    expediteur = config.get("smtp_expediteur", "").strip()
    mot_de_passe = config.get("smtp_mdp", "").strip()
    mode_ssl = config.get("smtp_ssl", False)

    if not serveur_smtp or not expediteur:
        return False, "Configuration SMTP incomplète (serveur ou expéditeur manquant)."

    msg = MIMEMultipart("mixed")
    msg["Subject"] = sujet
    msg["From"] = expediteur
    msg["To"] = ", ".join(destinataires)

    # Conteneur related pour le corps HTML et les images intégrées inline
    msg_related = MIMEMultipart("related")

    # Conteneur alternative pour le texte brut et HTML
    msg_alternative = MIMEMultipart("alternative")
    part_texte = MIMEText(texte_brut, "plain", "utf-8")
    msg_alternative.attach(part_texte)

    # Traitement de l'image pour courriel :
    # Gmail, Outlook et Yahoo bloquent les images encodées en base64 direct dans le corps du courriel.
    # L'image doit être attachée avec Content-ID (cid:armoiries_logo) pour s'afficher directement et sans blocage.
    arm_path = find_armoiries_path()
    html_email = html_contenu
    part_img = None

    if os.path.isfile(arm_path):
        try:
            from PIL import Image
            import io
            im = Image.open(arm_path)
            resample_filter = getattr(getattr(Image, "Resampling", Image), "LANCZOS", getattr(Image, "ANTIALIAS", 1))
            im.thumbnail((160, 160), resample_filter)
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
            img_bytes = buf.getvalue()
        except Exception:
            try:
                with open(arm_path, "rb") as f:
                    img_bytes = f.read()
            except Exception:
                img_bytes = None

        if img_bytes:
            # Remplacement des data URI par cid:armoiries_logo
            html_email = re.sub(r'src="data:image/[^"]+"', 'src="cid:armoiries_logo"', html_email)
            html_email = re.sub(r"src='data:image/[^']+'", "src='cid:armoiries_logo'", html_email)

            if "cid:armoiries_logo" in html_email:
                part_img = MIMEImage(img_bytes, _subtype="png")
                part_img.add_header("Content-ID", "<armoiries_logo>")
                part_img.add_header("Content-Disposition", "inline", filename="armoiries.png")

    part_html = MIMEText(html_email, "html", "utf-8")
    msg_alternative.attach(part_html)
    msg_related.attach(msg_alternative)

    if part_img:
        msg_related.attach(part_img)

    msg.attach(msg_related)

    # Ajout des pièces jointes demandées
    if pieces_jointes:
        for pj_path in pieces_jointes:
            if os.path.exists(pj_path):
                try:
                    nom_fichier = os.path.basename(pj_path)
                    with open(pj_path, "rb") as f:
                        pj_data = f.read()
                    part_pj = MIMEApplication(pj_data, Name=nom_fichier)
                    part_pj.add_header("Content-Disposition", "attachment", filename=nom_fichier)
                    msg.attach(part_pj)
                except Exception as e_pj:
                    st.warning(f"⚠️ Impossible de joindre la pièce {pj_path} : {e_pj}")

    try:
        if mode_ssl or port == 465:
            with smtplib.SMTP_SSL(serveur_smtp, port, timeout=15) as server:
                if mot_de_passe:
                    server.login(expediteur, mot_de_passe)
                server.sendmail(expediteur, destinataires, msg.as_string())
        else:
            with smtplib.SMTP(serveur_smtp, port, timeout=15) as server:
                server.ehlo()
                if port == 587:
                    server.starttls()
                    server.ehlo()
                if mot_de_passe:
                    server.login(expediteur, mot_de_passe)
                server.sendmail(expediteur, destinataires, msg.as_string())
        return True, "Courriel envoyé avec succès !"
    except Exception as e:
        return False, f"Échec de l'envoi du courriel : {str(e)}"


# ==============================================================================
# MODULE DE GESTION DES TOURNOIS (SIMPLE & DOUBLE)
# ==============================================================================
def charger_tournois_data():
    """Charge les données des tournois depuis le fichier JSON."""
    if os.path.exists(TOURNOIS_FILE):
        try:
            with open(TOURNOIS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict):
                    return d
        except Exception:
            return {}
    return {}

def sauvegarder_tournois_data(data, marqueur_session=None, action="sauvegarde"):
    """Enregistre les données des tournois dans le fichier JSON avec horodatage et traçabilité du marqueur."""
    if not isinstance(data, dict):
        return False
    try:
        now_str = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
        data["derniere_sauvegarde"] = {
            "date": now_str,
            "session_id": marqueur_session or "marqueur_actif",
            "action": action
        }
        for m in ["simple", "double"]:
            if m in data and isinstance(data[m], dict):
                data[m]["date_derniere_sauvegarde"] = now_str

        with open(TOURNOIS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Erreur lors de l'enregistrement du tournoi : {e}")
        return False

def ceder_la_main_avec_sauvegarde(session_id):
    """
    Sauvegarde automatiquement le tournoi sur le disque avant de céder la main,
    puis libère le verrou exclusif.
    """
    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
    td = charger_tournois_data()
    tournois_sauvegardes = []
    for mode in ["simple", "double"]:
        t = td.get(mode)
        if t and isinstance(t, dict):
            t_nom = t.get("titre", f"Tournoi {mode}")
            t["date_derniere_sauvegarde"] = now_str
            tournois_sauvegardes.append(t_nom)

    sauvegarder_tournois_data(td, marqueur_session=session_id, action="cession_de_main")

    try:
        if "recuperer_donnees_actuelles" in globals():
            donnees_feuille = recuperer_donnees_actuelles()
            if donnees_feuille and isinstance(donnees_feuille, dict):
                sauvegarder_donnees(donnees_feuille)
    except Exception:
        pass

    liberer_verrou(session_id)
    st.session_state["mode_consultation"] = True

    if tournois_sauvegardes:
        t_txt = ", ".join(tournois_sauvegardes)
        st.session_state["msg_cession_main"] = f"✅ La main a été cédée. La sauvegarde du tournoi ({t_txt}) a été enregistrée avec succès sur le disque ({now_str})."
    else:
        st.session_state["msg_cession_main"] = f"✅ La main a été cédée. Les données ont été sauvegardées avec succès ({now_str})."

def prendre_la_main_avec_rechargement(session_id):
    """
    Prend la main pour marquer un tournoi, charge fraîchement la dernière sauvegarde du tournoi
    depuis le disque et vérifie que la sauvegarde faite par le marqueur précédent est récupérée.
    """
    forcer_prise_de_main(session_id)
    st.session_state["mode_consultation"] = False

    td_fraiche = charger_tournois_data()
    infos_sauv = td_fraiche.get("derniere_sauvegarde", {})
    date_sauv_t = infos_sauv.get("date", "")
    action_sauv = infos_sauv.get("action", "")

    # Purge des clés de saisie en session pour que Streamlit prenne les valeurs du disque
    cles_a_purger = [k for k in list(st.session_state.keys()) if k.startswith("rr_a_") or k.startswith("rr_b_") or k.startswith("m_sc_a_") or k.startswith("m_sc_b_")]
    for k in cles_a_purger:
        del st.session_state[k]

    try:
        sauv_match = charger_sauvegarde()
        if sauv_match and "matchs" in sauv_match:
            restaurer_session(sauv_match)
    except Exception:
        pass

    if date_sauv_t:
        if action_sauv == "cession_de_main":
            st.session_state["msg_prise_main"] = (
                f"✅ Prise de main réussie ! La sauvegarde effectuée par le marqueur qui a cédé la main "
                f"({date_sauv_t}) a été chargée avec succès depuis le disque."
            )
        else:
            st.session_state["msg_prise_main"] = (
                f"✅ Prise de main réussie ! La dernière sauvegarde du tournoi sur le disque "
                f"({date_sauv_t}) a été chargée avec succès."
            )
    else:
        st.session_state["msg_prise_main"] = (
            "✅ Prise de main réussie ! Les données du tournoi enregistrées sur le disque ont été chargées avec succès."
        )

def charger_historique_tournois(inclure_actifs=False):
    """Charge l'ensemble des tournois archivés (Simples et Doubles).
    Si inclure_actifs est True, inclut également les tournois actifs sauvegardés dans tournois_data.json."""
    historique = []
    if os.path.exists(HISTORIQUE_TOURNOIS_FILE):
        try:
            with open(HISTORIQUE_TOURNOIS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    historique = data
        except Exception:
            pass
    if not historique:
        td = charger_tournois_data()
        if isinstance(td, dict) and "historique" in td and isinstance(td["historique"], list):
            historique = td["historique"]

    if inclure_actifs:
        try:
            td = charger_tournois_data()
            actifs = []
            for m in ["simple", "double"]:
                t_act = td.get(m)
                if t_act and isinstance(t_act, dict):
                    id_a = t_act.get("id_archive")
                    titre_a = t_act.get("titre")
                    date_c = t_act.get("date_creation")
                    deja_present = False
                    for h in historique:
                        if id_a and h.get("id_archive") == id_a:
                            deja_present = True
                            break
                        if h.get("titre") == titre_a and h.get("date_creation") == date_c and h.get("mode") == m:
                            deja_present = True
                            break
                    if not deja_present:
                        import copy
                        t_cop = copy.deepcopy(t_act)
                        t_cop["mode"] = m
                        t_cop["est_actif"] = True
                        if not t_cop.get("id_archive"):
                            t_cop["id_archive"] = f"ACTIF_{m.upper()}"
                        actifs.append(t_cop)
            if actifs:
                return actifs + historique
        except Exception:
            pass

    return historique

def sauvegarder_historique_tournois(historique_list):
    """Sauvegarde l'historique des tournois dans le fichier JSON."""
    try:
        # Ne sauvegarder que les tournois archivés (exclure d'éventuels items temporairement marqués comme actifs)
        liste_a_sauver = [h for h in historique_list if not h.get("est_actif")] if isinstance(historique_list, list) else []
        with open(HISTORIQUE_TOURNOIS_FILE, "w", encoding="utf-8") as f:
            json.dump(liste_a_sauver, f, ensure_ascii=False, indent=4)
        td = charger_tournois_data()
        td["historique"] = liste_a_sauver
        try:
            with open(TOURNOIS_FILE, "w", encoding="utf-8") as f:
                json.dump(td, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de l'historique des tournois : {e}")
        return False

def envoyer_courriel_sauvegarde_tournoi(tournoi_obj=None, mode="simple", destinataires_specifiques=None):
    """Envoie un courriel aux administrateurs définis dans la configuration SMTP avec en attachement le fichier historique_tournois.json."""
    config_email = charger_config_email()
    destinataires = (destinataires_specifiques or config_email.get("destinataires", "")).strip()

    if not destinataires:
        return False, "Aucune adresse d'administrateur configurée dans les paramètres SMTP."

    if not config_email.get("smtp_serveur") or not config_email.get("smtp_expediteur"):
        return False, "Configuration SMTP incomplète (serveur ou expéditeur manquant)."

    pj = []
    if os.path.exists(HISTORIQUE_TOURNOIS_FILE):
        pj.append(HISTORIQUE_TOURNOIS_FILE)

    mode_label = "Simple (1 contre 1)" if mode == "simple" else "Double / Équipes (2 contre 2)"
    date_now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")

    if tournoi_obj and isinstance(tournoi_obj, dict):
        titre_t = tournoi_obj.get("titre", "Tournoi officiel")
        statut_t = tournoi_obj.get("statut", "en_cours")
        fmt = tournoi_obj.get("format", "elimination")
        if fmt == "double_elimination":
            fmt_label = "Double élimination (Winner & Loser Bracket — Seconde chance)"
        elif fmt == "elimination":
            fmt_label = "Élimination directe (Préliminaires 2 de 3 • Finale 3 de 5)"
        else:
            fmt_label = "Championnat Round-Robin (2 de 3)"
        champion = tournoi_obj.get("vainqueur_final") or tournoi_obj.get("champion") or ""
        finaliste = tournoi_obj.get("finaliste") or ""
        nb_tables = tournoi_obj.get("nb_tables", 2)
        h_deb = tournoi_obj.get("heure_debut", "09:00")
        h_fin = tournoi_obj.get("heure_fin_estimee", "")
        horaires_desc = f"{h_deb} à ~{h_fin}" if h_fin else f"Début à {h_deb}"

        sujet = f"🏆 [TOURNOI] Sauvegarde officielle : {titre_t} ({mode_label}) - Ligue de billard"

        texte_brut = (
            f"LIGUE DE BILLARD BOULE EN MAIN - SAUVEGARDE OFFICIELLE DE TOURNOI\n"
            f"=================================================================\n\n"
            f"Tournoi : {titre_t}\n"
            f"Catégorie : {mode_label}\n"
            f"Formule : {fmt_label}\n"
            f"Statut : {statut_t.upper()}\n"
            f"Champion : {champion if champion else 'En cours'}\n"
            f"Finaliste : {finaliste if finaliste else '-'}\n"
            f"Tables : {nb_tables} table(s) | Horaires : {horaires_desc}\n"
            f"Date d'enregistrement : {date_now_str}\n\n"
            f"Le fichier officiel d'historique des tournois (historique_tournois.json) est attaché en pièce jointe."
        )

        podium_bloc = ""
        if champion and champion != "En cours":
            podium_bloc = f"""
            <div style="background: #fffde7; border: 2px solid #fbc02d; border-radius: 8px; padding: 12px; margin: 16px 0; text-align: center;">
                <div style="font-size: 16px; font-weight: bold; color: #f57f17;">🥇 Champion Officiel : {champion}</div>
                {f'<div style="font-size: 14px; color: #555; margin-top: 5px;">🥈 Finaliste : {finaliste}</div>' if finaliste and finaliste != '-' else ''}
            </div>
            """

        html_contenu = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #222;">
    <div style="max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #ddd; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.06);">
        <div style="background-color: #0b3c5d; color: #ffffff; padding: 18px 24px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px;">🎱 Ligue de billard Boule en main</h2>
            <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">Sauvegarde & Archivage Officiel de Tournoi</p>
        </div>
        <div style="padding: 24px;">
            <p style="font-size: 15px; margin-top: 0;">Bonjour,</p>
            <p style="font-size: 14px; line-height: 1.5;">
                Une sauvegarde officielle du tournoi suivant a été effectuée dans l'application :
            </p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #0b3c5d; width: 35%;">Nom du tournoi :</td>
                    <td style="padding: 8px; font-weight: 600;">{titre_t}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee; background-color: #fbfbfb;">
                    <td style="padding: 8px; font-weight: bold; color: #0b3c5d;">Catégorie :</td>
                    <td style="padding: 8px;">{mode_label}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #0b3c5d;">Formule :</td>
                    <td style="padding: 8px;">{fmt_label}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee; background-color: #fbfbfb;">
                    <td style="padding: 8px; font-weight: bold; color: #0b3c5d;">Statut :</td>
                    <td style="padding: 8px; font-weight: 600; color: {'#2e7d32' if statut_t == 'termine' else '#1565c0'};">{statut_t.upper()}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; color: #0b3c5d;">Tables & Horaires :</td>
                    <td style="padding: 8px;">{nb_tables} table{'s' if nb_tables > 1 else ''} • {horaires_desc}</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee; background-color: #fbfbfb;">
                    <td style="padding: 8px; font-weight: bold; color: #0b3c5d;">Date d'enregistrement :</td>
                    <td style="padding: 8px;">{date_now_str}</td>
                </tr>
            </table>

            {podium_bloc}

            <div style="background-color: #e8f4fd; border-left: 4px solid #1976d2; padding: 12px 16px; border-radius: 4px; margin: 18px 0; font-size: 13px; color: #0d47a1;">
                📎 <strong>Fichier attaché :</strong> Le fichier officiel <code>historique_tournois.json</code> contenant la conservation complète de tous les tournois est joint à ce courriel.
            </div>

            <p style="font-size: 13px; color: #666; margin-bottom: 0;">
                Ce message a été généré automatiquement lors de la sauvegarde du tournoi.
            </p>
        </div>
        <div style="background-color: #f1f3f5; padding: 12px 24px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #eee;">
            Ligue de billard Boule en main • Salle Le Saphir
        </div>
    </div>
</body>
</html>"""
    else:
        nb_tournois = len(charger_historique_tournois())
        sujet = f"🏆 [HISTORIQUE] Sauvegarde officielle des tournois ({nb_tournois} tournoi{'s' if nb_tournois > 1 else ''}) - Ligue de billard"
        texte_brut = (
            f"LIGUE DE BILLARD BOULE EN MAIN - HISTORIQUE OFFICIEL DES TOURNOIS\n"
            f"===============================================================\n\n"
            f"Nombre de tournois enregistrés : {nb_tournois}\n"
            f"Date de transmission : {date_now_str}\n\n"
            f"Le fichier complet (historique_tournois.json) est attaché en pièce jointe."
        )
        html_contenu = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #222;">
    <div style="max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #ddd; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.06);">
        <div style="background-color: #0b3c5d; color: #ffffff; padding: 18px 24px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px;">🎱 Ligue de billard Boule en main</h2>
            <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">Historique Complet des Tournois</p>
        </div>
        <div style="padding: 24px;">
            <p style="font-size: 15px; margin-top: 0;">Bonjour,</p>
            <p style="font-size: 14px; line-height: 1.5;">
                Veuillez trouver ci-joint le fichier d'historique officiel complet de tous les tournois enregistrés dans l'application ({nb_tournois} tournoi{'s' if nb_tournois > 1 else ''} au total).
            </p>
            <div style="background-color: #e8f4fd; border-left: 4px solid #1976d2; padding: 12px 16px; border-radius: 4px; margin: 18px 0; font-size: 13px; color: #0d47a1;">
                📎 <strong>Fichier attaché :</strong> <code>historique_tournois.json</code> ({nb_tournois} tournoi{'s' if nb_tournois > 1 else ''} archivé{'s' if nb_tournois > 1 else ''}).
            </div>
            <p style="font-size: 12px; color: #888;">Généré le {date_now_str} par l'application officielle de billard.</p>
        </div>
        <div style="background-color: #f1f3f5; padding: 12px 24px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #eee;">
            Ligue de billard Boule en main • Salle Le Saphir
        </div>
    </div>
</body>
</html>"""

    return envoyer_courriel(
        destinataires,
        sujet,
        texte_brut,
        html_contenu,
        config_email,
        pieces_jointes=pj
    )

def archiver_tournoi(tournoi_obj, mode="simple", notifier_admin=True):
    """Archive un tournoi dans l'historique officiel et envoie un courriel aux administrateurs définis dans SMTP avec en pièce jointe le fichier historique_tournois.json."""
    if not tournoi_obj or not isinstance(tournoi_obj, dict):
        return False

    import copy
    archive_item = copy.deepcopy(tournoi_obj)
    archive_item["mode"] = mode
    archive_item["date_archivage"] = datetime.now().strftime("%d/%m/%Y à %H:%M")

    id_archive = archive_item.get("id_archive")
    if not id_archive:
        id_archive = f"TOURNOI_{mode.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(100, 999)}"
        archive_item["id_archive"] = id_archive

    historique = charger_historique_tournois()

    idx_existant = -1
    for i, h in enumerate(historique):
        if h.get("id_archive") == id_archive or (
            h.get("titre") == archive_item.get("titre") and
            h.get("date_creation") == archive_item.get("date_creation") and
            h.get("mode") == mode
        ):
            idx_existant = i
            break

    if idx_existant >= 0:
        historique[idx_existant] = archive_item
    else:
        historique.insert(0, archive_item)

    sauvegarder_historique_tournois(historique)

    if notifier_admin:
        try:
            succes, msg = envoyer_courriel_sauvegarde_tournoi(archive_item, mode=mode)
            try:
                st.session_state["dernier_envoi_tournoi_statut"] = (succes, msg)
            except Exception:
                pass
        except Exception as e:
            try:
                st.session_state["dernier_envoi_tournoi_statut"] = (False, str(e))
            except Exception:
                pass

    return True

def supprimer_tournoi_historique(id_archive):
    """Supprime un tournoi spécifique de l'historique."""
    if not id_archive:
        return False
    historique = charger_historique_tournois()
    nouveau_h = [h for h in historique if h.get("id_archive") != id_archive]
    sauvegarder_historique_tournois(nouveau_h)
    return True

def sauvegarder_tournoi_dans_historique(mode, notifier_admin=True):
    """Sauvegarde l'état actuel du tournoi dans l'historique officiel et sur le disque."""
    td = charger_tournois_data()
    t = td.get(mode)
    if not t or not isinstance(t, dict):
        return False, "Aucun tournoi actif à sauvegarder."

    id_arch = t.get("id_archive")
    if not id_arch:
        id_arch = f"TOURNOI_{mode.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(100, 999)}"
        t["id_archive"] = id_arch
        td[mode] = t
        sauvegarder_tournois_data(td)

    archiver_tournoi(t, mode=mode, notifier_admin=notifier_admin)
    return True, "Tournoi sauvegardé dans l'historique avec succès !"

def annuler_completement_tournoi(mode):
    """Annule complètement le tournoi sans aucune sauvegarde ni envoi de courriel."""
    td = charger_tournois_data()
    t = td.get(mode)
    if t and isinstance(t, dict):
        id_a = t.get("id_archive")
        titre = t.get("titre")
        date_c = t.get("date_creation")
        # Si ce tournoi avait déjà été archivé dans l'historique lors d'une sauvegarde intermédiaire, le retirer
        try:
            hist = charger_historique_tournois()
            hist_nettoye = [
                h for h in hist
                if not (
                    (id_a and h.get("id_archive") == id_a) or
                    (h.get("titre") == titre and h.get("date_creation") == date_c and h.get("mode") == mode)
                )
            ]
            if len(hist_nettoye) != len(hist):
                sauvegarder_historique_tournois(hist_nettoye)
        except Exception:
            pass

    td[mode] = None
    sauvegarder_tournois_data(td)
    return True

def obtenir_tous_les_joueurs_tournoi(equipes_dict=None):
    """Récupère l'ensemble des joueurs réguliers inscrits dans la ligue."""
    joueurs_officiels = []
    eq_data = equipes_dict if equipes_dict else charger_equipes_csv()
    if eq_data:
        for eq, liste_j in eq_data.items():
            for j in liste_j:
                j_clean = (j or "").strip()
                if j_clean and not j_clean.startswith("Joueur ") and j_clean not in joueurs_officiels:
                    joueurs_officiels.append(j_clean)

    if not joueurs_officiels and os.path.exists(EQUIPES_CSV_FILE):
        try:
            with open(EQUIPES_CSV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = [p.strip() for p in line.strip().split(",") if p.strip()]
                    if len(parts) >= 2:
                        for p in parts[1:]:
                            if p and not p.startswith("Joueur ") and p not in joueurs_officiels:
                                joueurs_officiels.append(p)
        except Exception:
            pass

    return sorted(joueurs_officiels)

def obtenir_toutes_les_equipes_tournoi():
    """Récupère les 8 équipes officielles inscrites dans la ligue."""
    eq_data = charger_equipes_csv()
    if eq_data:
        return sorted(list(eq_data.keys()))
    return ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]

def ajuster_pause_diner(dt, duree):
    """
    S'assure qu'aucun match n'est cédulé ni joué entre 12:00 et 13:00 (pause dîner).
    Si un match débute entre 12:00 et 13:00 ou empiète sur cette tranche horaire,
    il est automatiquement décalé à 13:00.
    """
    pause_deb = dt.replace(hour=12, minute=0, second=0, microsecond=0)
    pause_fin = dt.replace(hour=13, minute=0, second=0, microsecond=0)

    # Si l'heure courante tombe pendant la pause (entre 12h00 et 12h59)
    if pause_deb <= dt < pause_fin:
        return pause_fin

    # Si le match commence avant 12h00 mais se terminerait après 12h00
    if dt < pause_deb and (dt + duree) > pause_deb:
        return pause_fin

    return dt

def planifier_horaires_elimination(tours, heure_debut="09:00", duree_min=30, nb_tables=2):
    """
    Planifie les heures approximatives de début de chaque match et attribue les tables (1 ou 2).
    Déroulement en une seule journée débutant à l'heure spécifiée (par défaut 9h00 a.m.).
    Aucun match n'est cédulé entre 12:00 et 13:00 tant en Simple qu'en Double (pause dîner).
    """
    try:
        cur_dt = datetime.strptime(heure_debut.strip(), "%H:%M")
    except Exception:
        cur_dt = datetime.strptime("09:00", "%H:%M")

    duree = timedelta(minutes=int(duree_min))

    for t in tours:
        matchs = t.get("matchs", [])
        if not matchs:
            continue

        # S'assurer que le début du tour ne commence pas pendant la pause dîner
        cur_dt = ajuster_pause_diner(cur_dt, duree)

        if int(nb_tables) >= 2:
            # 2 tables : 2 matchs en parallèle par vague
            nb_matchs = len(matchs)
            nb_vagues = (nb_matchs + 1) // 2

            for v in range(nb_vagues):
                v_dt = ajuster_pause_diner(cur_dt, duree)
                m1_idx = v * 2
                m2_idx = v * 2 + 1

                if m1_idx < nb_matchs:
                    matchs[m1_idx]["heure_estimee"] = v_dt.strftime("%Hh%M")
                    matchs[m1_idx]["table"] = "Table 1"
                    matchs[m1_idx]["table_courte"] = "T1"

                if m2_idx < nb_matchs:
                    matchs[m2_idx]["heure_estimee"] = v_dt.strftime("%Hh%M")
                    matchs[m2_idx]["table"] = "Table 2"
                    matchs[m2_idx]["table_courte"] = "T2"

                # L'heure courante avance après la fin de la vague et s'ajuste si pause dîner
                cur_dt = ajuster_pause_diner(v_dt + duree, duree)
        else:
            # 1 seule table disponible : matchs les uns après les autres
            for m in matchs:
                cur_dt = ajuster_pause_diner(cur_dt, duree)
                m["heure_estimee"] = cur_dt.strftime("%Hh%M")
                m["table"] = "Table 1"
                m["table_courte"] = "T1"
                cur_dt = ajuster_pause_diner(cur_dt + duree, duree)

    heure_fin = cur_dt.strftime("%Hh%M")
    return heure_fin

def planifier_horaires_round_robin(matchs, heure_debut="09:00", duree_min=30, nb_tables=2):
    """
    Planifie les horaires pour un championnat round-robin sur 1 ou 2 tables.
    Aucun match n'est cédulé entre 12:00 et 13:00 tant en Simple qu'en Double (pause dîner).
    """
    try:
        cur_dt = datetime.strptime(heure_debut.strip(), "%H:%M")
    except Exception:
        cur_dt = datetime.strptime("09:00", "%H:%M")

    duree = timedelta(minutes=int(duree_min))
    nb_matchs = len(matchs)

    if int(nb_tables) >= 2:
        nb_vagues = (nb_matchs + 1) // 2
        for v in range(nb_vagues):
            v_dt = ajuster_pause_diner(cur_dt, duree)
            m1_idx = v * 2
            m2_idx = v * 2 + 1

            if m1_idx < nb_matchs:
                matchs[m1_idx]["heure_estimee"] = v_dt.strftime("%Hh%M")
                matchs[m1_idx]["table"] = "Table 1"
                matchs[m1_idx]["table_courte"] = "T1"

            if m2_idx < nb_matchs:
                matchs[m2_idx]["heure_estimee"] = v_dt.strftime("%Hh%M")
                matchs[m2_idx]["table"] = "Table 2"
                matchs[m2_idx]["table_courte"] = "T2"

            cur_dt = ajuster_pause_diner(v_dt + duree, duree)
    else:
        for m in matchs:
            cur_dt = ajuster_pause_diner(cur_dt, duree)
            m["heure_estimee"] = cur_dt.strftime("%Hh%M")
            m["table"] = "Table 1"
            m["table_courte"] = "T1"
            cur_dt = ajuster_pause_diner(cur_dt + duree, duree)

    heure_fin = cur_dt.strftime("%Hh%M")
    return heure_fin

def calculer_structure_arbre(nb_participants):
    """
    Calcule le nombre de participants promus (passe-droit) au second tour
    afin de garantir un nombre pair de matchs au second tour (demi-finales = 2, quarts = 4, etc.).
    Retourne (nb_promus, nb_matchs_t1, nb_matchs_t2, puissance_b)
    """
    n = nb_participants
    if n < 2:
        return 0, 0, 0, 0
    if n == 2:
        return 0, 1, 0, 2
    if n == 3:
        return 1, 1, 1, 4
    if n == 4:
        return 0, 2, 1, 4

    b = 8
    while b < n:
        b *= 2

    nb_promus = b - n
    nb_matchs_t1 = n - (b // 2)
    nb_matchs_t2 = b // 4  # Toujours un nombre pair (2, 4, 8...) car b >= 8
    return nb_promus, nb_matchs_t1, nb_matchs_t2, b

def generer_arbre_elimination(participants, race_prelim=2, race_finale=3, titre="Tournoi", heure_debut="09:00", duree_min=30, nb_tables=2, passes_droits=None, passe_droit_participant=None):
    """
    Génère un arbre à élimination directe équilibré.
    Garantit suivant le nombre de participants d'avoir un nombre pair de matchs au second tour
    (2 en demi-finales, 4 en quarts, etc.) en promouvant un nombre suffisant de participants
    (passe-droit) directement au second tour.
    Format officiel des rondes :
    - Préliminaires : 2 de 3 (premier à 2 victoires, race_to = 2)
    - Finale : 3 de 5 (premier à 3 victoires, race_to = 3)
    """
    p_liste = list(participants)
    n = len(p_liste)
    if not p_liste or n < 2:
        return None

    nb_promus, nb_m_t1, nb_m_t2, b = calculer_structure_arbre(n)

    # Déterminer les participants promus (passe-droit)
    promus = []
    if passes_droits:
        if isinstance(passes_droits, str):
            passes_droits = [passes_droits]
        for p in passes_droits:
            if p in p_liste and p not in promus and len(promus) < nb_promus:
                promus.append(p)
    elif passe_droit_participant and passe_droit_participant in p_liste:
        promus.append(passe_droit_participant)

    candidats_restants = [p for p in p_liste if p not in promus]
    random.shuffle(candidats_restants)
    manquants = nb_promus - len(promus)
    if manquants > 0:
        promus.extend(candidats_restants[:manquants])
        candidats_restants = candidats_restants[manquants:]

    p_t1 = list(candidats_restants)
    random.shuffle(p_t1)

    tours_matchs = []

    # CAS N == 2 : Finale directe
    if n == 2:
        matchs_t1 = [{
            "id": "T1_M1",
            "equipe_a": p_liste[0],
            "equipe_b": p_liste[1],
            "score_a": 0, "score_b": 0,
            "termine": False, "vainqueur": None,
            "source_a": None, "source_b": None, "passe_droit": False
        }]
        tours_matchs.append(matchs_t1)

    # CAS N == 3 : Demi-finale (1 match) puis Finale (1 match)
    elif n == 3:
        matchs_t1 = [{
            "id": "T1_M1",
            "equipe_a": p_t1[0],
            "equipe_b": p_t1[1],
            "score_a": 0, "score_b": 0,
            "termine": False, "vainqueur": None,
            "source_a": None, "source_b": None, "passe_droit": False
        }]
        matchs_t2 = [{
            "id": "T2_M1",
            "equipe_a": "À déterminer",
            "equipe_b": promus[0],
            "score_a": 0, "score_b": 0,
            "termine": False, "vainqueur": None,
            "source_a": "T1_M1", "source_b": None, "passe_droit": False
        }]
        tours_matchs.append(matchs_t1)
        tours_matchs.append(matchs_t2)

    # CAS N == 4 : Demi-finales (2 matchs) puis Finale (1 match)
    elif n == 4:
        matchs_t1 = [
            {
                "id": "T1_M1",
                "equipe_a": p_t1[0], "equipe_b": p_t1[1],
                "score_a": 0, "score_b": 0,
                "termine": False, "vainqueur": None,
                "source_a": None, "source_b": None, "passe_droit": False
            },
            {
                "id": "T1_M2",
                "equipe_a": p_t1[2], "equipe_b": p_t1[3],
                "score_a": 0, "score_b": 0,
                "termine": False, "vainqueur": None,
                "source_a": None, "source_b": None, "passe_droit": False
            }
        ]
        matchs_t2 = [{
            "id": "T2_M1",
            "equipe_a": "À déterminer", "equipe_b": "À déterminer",
            "score_a": 0, "score_b": 0,
            "termine": False, "vainqueur": None,
            "source_a": "T1_M1", "source_b": "T1_M2", "passe_droit": False
        }]
        tours_matchs.append(matchs_t1)
        tours_matchs.append(matchs_t2)

    # CAS GÉNÉRAL N >= 5 (garantit un nombre pair de matchs au second tour)
    else:
        # Tour 1
        matchs_t1 = []
        for i in range(nb_m_t1):
            matchs_t1.append({
                "id": f"T1_M{i+1}",
                "equipe_a": p_t1[2*i],
                "equipe_b": p_t1[2*i+1],
                "score_a": 0, "score_b": 0,
                "termine": False, "vainqueur": None,
                "source_a": None, "source_b": None, "passe_droit": False
            })
        tours_matchs.append(matchs_t1)

        # Tour 2 (nb_m_t2 matchs : garanti toujours pair 2, 4, 8...)
        sources_t1 = [f"T1_M{i+1}" for i in range(nb_m_t1)]
        promus_copy = list(promus)
        random.shuffle(promus_copy)

        matchs_t2 = []
        M1 = nb_m_t1
        M2 = nb_m_t2

        if M1 <= M2:
            promu_idx = 0
            for i in range(M2):
                if i < M1:
                    src_a = sources_t1[i]
                    eq_a = "À déterminer"
                else:
                    src_a = None
                    eq_a = promus_copy[promu_idx]
                    promu_idx += 1

                src_b = None
                eq_b = promus_copy[promu_idx]
                promu_idx += 1

                matchs_t2.append({
                    "id": f"T2_M{i+1}",
                    "equipe_a": eq_a,
                    "equipe_b": eq_b,
                    "score_a": 0, "score_b": 0,
                    "termine": False, "vainqueur": None,
                    "source_a": src_a, "source_b": src_b, "passe_droit": False
                })
        else:
            promu_idx = 0
            nb_t1_in_b = M1 - M2
            for i in range(M2):
                src_a = sources_t1[i]
                eq_a = "À déterminer"

                if i < nb_t1_in_b:
                    src_b = sources_t1[M2 + i]
                    eq_b = "À déterminer"
                else:
                    src_b = None
                    eq_b = promus_copy[promu_idx]
                    promu_idx += 1

                matchs_t2.append({
                    "id": f"T2_M{i+1}",
                    "equipe_a": eq_a,
                    "equipe_b": eq_b,
                    "score_a": 0, "score_b": 0,
                    "termine": False, "vainqueur": None,
                    "source_a": src_a, "source_b": src_b, "passe_droit": False
                })
        tours_matchs.append(matchs_t2)

        # Tours suivants (T3 jusqu'à la Finale)
        curr_matchs = matchs_t2
        t_num = 2
        while len(curr_matchs) > 1:
            t_num += 1
            nb_curr = len(curr_matchs)
            next_m_list = []
            for m_i in range(nb_curr // 2):
                src_a = f"T{t_num-1}_M{2*m_i+1}"
                src_b = f"T{t_num-1}_M{2*m_i+2}"
                next_m_list.append({
                    "id": f"T{t_num}_M{m_i+1}",
                    "equipe_a": "À déterminer",
                    "equipe_b": "À déterminer",
                    "score_a": 0, "score_b": 0,
                    "termine": False, "vainqueur": None,
                    "source_a": src_a, "source_b": src_b, "passe_droit": False
                })
            tours_matchs.append(next_m_list)
            curr_matchs = next_m_list

    total_tours = len(tours_matchs)
    final_tours = []
    for idx, m_list in enumerate(tours_matchs, 1):
        is_finale = (idx == total_tours)
        race_t = race_finale if is_finale else race_prelim
        fmt_t = "3 de 5" if race_t == 3 else ("2 de 3" if race_t == 2 else f"Course à {race_t}")
        rounds_from_end = total_tours - idx + 1

        if rounds_from_end == 1:
            nom = "Finale"
        elif rounds_from_end == 2:
            nom = "Demi-finales"
        elif rounds_from_end == 3:
            nom = "Quarts de finale" if (idx == 1 and n >= 8) or (idx > 1) else "Tour préliminaire"
        elif rounds_from_end == 4:
            nom = "Huitièmes de finale" if (idx == 1 and n >= 16) or (idx > 1) else "Tour préliminaire"
        else:
            nom = "Tour préliminaire" if idx == 1 else f"Tour {idx}"

        for m in m_list:
            m["race_to"] = race_t
            m["format_label"] = fmt_t

        final_tours.append({
            "numero": idx,
            "nom": nom,
            "race_to": race_t,
            "format_label": fmt_t,
            "matchs": m_list
        })

    heure_fin = planifier_horaires_elimination(final_tours, heure_debut=heure_debut, duree_min=duree_min, nb_tables=nb_tables)

    return {
        "titre": titre,
        "date_creation": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "format": "elimination",
        "race_prelim": race_prelim,
        "race_finale": race_finale,
        "participants": p_liste,
        "promus_second_tour": promus,
        "total_tours": total_tours,
        "tours": final_tours,
        "heure_debut": heure_debut,
        "duree_match_min": duree_min,
        "nb_tables": nb_tables,
        "heure_fin_estimee": heure_fin,
        "statut": "en_cours",
        "vainqueur_final": None,
        "finaliste": None
    }

def planifier_horaires_double_elimination(tours, heure_debut="09:00", duree_min=30, nb_tables=2):
    """
    Planifie les horaires pour un tournoi en double élimination (Winner & Loser Bracket).
    Ordonne les rencontres selon les étapes logiques (W1 -> W2/L1 -> L2 -> W3/L3...)
    sans aucun match entre 12:00 et 13:00 (pause dîner).
    """
    try:
        cur_dt = datetime.strptime(heure_debut.strip(), "%H:%M")
    except Exception:
        cur_dt = datetime.strptime("09:00", "%H:%M")

    duree = timedelta(minutes=int(duree_min))

    etapes_map = {}
    for t in tours:
        for m in t.get("matchs", []):
            et = m.get("etape", 1)
            if et not in etapes_map:
                etapes_map[et] = []
            etapes_map[et].append(m)

    for et in sorted(etapes_map.keys()):
        m_list = [m for m in etapes_map[et] if not m.get("passe_droit")]
        if not m_list:
            continue

        cur_dt = ajuster_pause_diner(cur_dt, duree)
        nb_m = len(m_list)

        if int(nb_tables) >= 2:
            nb_vagues = (nb_m + 1) // 2
            for v in range(nb_vagues):
                v_dt = ajuster_pause_diner(cur_dt, duree)
                m1_idx = v * 2
                m2_idx = v * 2 + 1

                if m1_idx < nb_m:
                    m_list[m1_idx]["heure_estimee"] = v_dt.strftime("%Hh%M")
                    m_list[m1_idx]["table"] = "Table 1"
                    m_list[m1_idx]["table_courte"] = "T1"

                if m2_idx < nb_m:
                    m_list[m2_idx]["heure_estimee"] = v_dt.strftime("%Hh%M")
                    m_list[m2_idx]["table"] = "Table 2"
                    m_list[m2_idx]["table_courte"] = "T2"

                cur_dt = ajuster_pause_diner(v_dt + duree, duree)
        else:
            for m in m_list:
                cur_dt = ajuster_pause_diner(cur_dt, duree)
                m["heure_estimee"] = cur_dt.strftime("%Hh%M")
                m["table"] = "Table 1"
                m["table_courte"] = "T1"
                cur_dt = ajuster_pause_diner(cur_dt + duree, duree)

    heure_fin = cur_dt.strftime("%Hh%M")
    return heure_fin

def generer_arbre_double_elimination(participants, race_prelim=2, race_finale=3, titre="Tournoi Double Élimination", heure_debut="09:00", duree_min=30, nb_tables=2, passes_droits=None):
    """
    Génère un tableau complet en Double Élimination (Tableau des Gagnants, Tableau de Seconde Chance et Grande Finale).
    Chaque participant dispose d'une seconde chance après une première défaite.
    Supporte 4, 8 ou 16 participants (avec attribution de passe-droits au 1er tour si N n'est pas une puissance de 2).
    """
    p_liste = list(participants)
    n = len(p_liste)
    if n < 4:
        return None

    if n <= 4:
        b = 4
    elif n <= 8:
        b = 8
    else:
        b = 16

    nb_promus = b - n
    promus = []
    if passes_droits:
        if isinstance(passes_droits, str):
            passes_droits = [passes_droits]
        for p in passes_droits:
            if p in p_liste and p not in promus and len(promus) < nb_promus:
                promus.append(p)

    candidats_restants = [p for p in p_liste if p not in promus]
    random.shuffle(candidats_restants)
    manquants = nb_promus - len(promus)
    if manquants > 0:
        promus.extend(candidats_restants[:manquants])
        candidats_restants = candidats_restants[manquants:]

    nb_m_w1 = b // 2
    if b == 4:
        seed_order = [0, 1]
    elif b == 8:
        seed_order = [0, 2, 3, 1]
    else:
        seed_order = [0, 4, 6, 2, 7, 3, 5, 1]

    matchs_avec_promus = set(seed_order[:len(promus)])
    promus_places = list(promus)
    p_sans_pd = list(candidats_restants)
    random.shuffle(p_sans_pd)

    w1_matchs = []
    for m_i in range(nb_m_w1):
        mid = f"W1_M{m_i+1}"
        if m_i in matchs_avec_promus:
            p_benef = promus_places.pop(0)
            w1_matchs.append({
                "id": mid,
                "bracket": "winner",
                "etape": 1,
                "equipe_a": p_benef,
                "equipe_b": "Exempt (Passe-droit)",
                "score_a": race_prelim,
                "score_b": 0,
                "termine": True,
                "passe_droit": True,
                "vainqueur": p_benef,
                "perdant": "Exempt (Passe-droit)",
                "source_a": None, "source_b": None,
                "type_source_a": "vainqueur", "type_source_b": "vainqueur",
                "heure_estimee": "—", "table": "—", "table_courte": "—"
            })
        else:
            eq_a = p_sans_pd.pop(0)
            eq_b = p_sans_pd.pop(0)
            w1_matchs.append({
                "id": mid,
                "bracket": "winner",
                "etape": 1,
                "equipe_a": eq_a,
                "equipe_b": eq_b,
                "score_a": 0, "score_b": 0,
                "termine": False,
                "passe_droit": False,
                "vainqueur": None,
                "perdant": None,
                "source_a": None, "source_b": None,
                "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            })

    tours = []
    w1_nom = "Gagnants — 8ᵉ de finale" if b == 16 else ("Gagnants — Quarts de finale" if b == 8 else "Gagnants — Demi-finales")
    tours.append({
        "numero": 1,
        "nom": w1_nom,
        "section": "winner",
        "bracket": "winner",
        "race_to": race_prelim,
        "format_label": f"{race_prelim} de {2*race_prelim - 1}",
        "matchs": w1_matchs
    })

    if b == 4:
        tours.append({
            "numero": 2, "nom": "Gagnants — Finale", "section": "winner", "bracket": "winner",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "W2_M1", "bracket": "winner", "etape": 2,
                "equipe_a": w1_matchs[0]["vainqueur"] or "À déterminer",
                "equipe_b": w1_matchs[1]["vainqueur"] or "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "W1_M1", "source_b": "W1_M2",
                "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })
        tours.append({
            "numero": 3, "nom": "Seconde Chance — Demi-finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "L1_M1", "bracket": "loser", "etape": 2,
                "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "W1_M1", "source_b": "W1_M2",
                "type_source_a": "perdant", "type_source_b": "perdant"
            }]
        })
        tours.append({
            "numero": 4, "nom": "Seconde Chance — Finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "L2_M1", "bracket": "loser", "etape": 3,
                "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "L1_M1", "source_b": "W2_M1",
                "type_source_a": "vainqueur", "type_source_b": "perdant"
            }]
        })
        tours.append({
            "numero": 5, "nom": "🏆 Grande Finale Officielle", "section": "finale", "bracket": "finale",
            "race_to": race_finale, "format_label": f"{race_finale} de {2*race_finale - 1}",
            "matchs": [{
                "id": "GF_M1", "bracket": "finale", "etape": 4, "race_to": race_finale,
                "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "W2_M1", "source_b": "L2_M1",
                "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })

    elif b == 8:
        tours.append({
            "numero": 2, "nom": "Gagnants — Demi-finales", "section": "winner", "bracket": "winner",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {
                    "id": "W2_M1", "bracket": "winner", "etape": 2,
                    "equipe_a": w1_matchs[0]["vainqueur"] or "À déterminer",
                    "equipe_b": w1_matchs[1]["vainqueur"] or "À déterminer",
                    "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                    "source_a": "W1_M1", "source_b": "W1_M2",
                    "type_source_a": "vainqueur", "type_source_b": "vainqueur"
                },
                {
                    "id": "W2_M2", "bracket": "winner", "etape": 2,
                    "equipe_a": w1_matchs[2]["vainqueur"] or "À déterminer",
                    "equipe_b": w1_matchs[3]["vainqueur"] or "À déterminer",
                    "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                    "source_a": "W1_M3", "source_b": "W1_M4",
                    "type_source_a": "vainqueur", "type_source_b": "vainqueur"
                }
            ]
        })
        tours.append({
            "numero": 3, "nom": "Gagnants — Finale", "section": "winner", "bracket": "winner",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "W3_M1", "bracket": "winner", "etape": 4,
                "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "W2_M1", "source_b": "W2_M2",
                "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })
        tours.append({
            "numero": 4, "nom": "Seconde Chance — Tour 1", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {
                    "id": "L1_M1", "bracket": "loser", "etape": 2,
                    "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                    "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                    "source_a": "W1_M1", "source_b": "W1_M2",
                    "type_source_a": "perdant", "type_source_b": "perdant"
                },
                {
                    "id": "L1_M2", "bracket": "loser", "etape": 2,
                    "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                    "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                    "source_a": "W1_M3", "source_b": "W1_M4",
                    "type_source_a": "perdant", "type_source_b": "perdant"
                }
            ]
        })
        tours.append({
            "numero": 5, "nom": "Seconde Chance — Quarts de finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {
                    "id": "L2_M1", "bracket": "loser", "etape": 3,
                    "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                    "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                    "source_a": "L1_M1", "source_b": "W2_M2",
                    "type_source_a": "vainqueur", "type_source_b": "perdant"
                },
                {
                    "id": "L2_M2", "bracket": "loser", "etape": 3,
                    "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                    "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                    "source_a": "L1_M2", "source_b": "W2_M1",
                    "type_source_a": "vainqueur", "type_source_b": "perdant"
                }
            ]
        })
        tours.append({
            "numero": 6, "nom": "Seconde Chance — Demi-finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "L3_M1", "bracket": "loser", "etape": 4,
                "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "L2_M1", "source_b": "L2_M2",
                "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })
        tours.append({
            "numero": 7, "nom": "Seconde Chance — Finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "L4_M1", "bracket": "loser", "etape": 5,
                "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "L3_M1", "source_b": "W3_M1",
                "type_source_a": "vainqueur", "type_source_b": "perdant"
            }]
        })
        tours.append({
            "numero": 8, "nom": "🏆 Grande Finale Officielle", "section": "finale", "bracket": "finale",
            "race_to": race_finale, "format_label": f"{race_finale} de {2*race_finale - 1}",
            "matchs": [{
                "id": "GF_M1", "bracket": "finale", "etape": 6, "race_to": race_finale,
                "equipe_a": "À déterminer", "equipe_b": "À déterminer",
                "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None,
                "source_a": "W3_M1", "source_b": "L4_M1",
                "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })

    elif b == 16:
        tours.append({
            "numero": 2, "nom": "Gagnants — Quarts de finale", "section": "winner", "bracket": "winner",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {"id": f"W2_M{i+1}", "bracket": "winner", "etape": 2, "equipe_a": w1_matchs[2*i]["vainqueur"] or "À déterminer", "equipe_b": w1_matchs[2*i+1]["vainqueur"] or "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": f"W1_M{2*i+1}", "source_b": f"W1_M{2*i+2}", "type_source_a": "vainqueur", "type_source_b": "vainqueur"} for i in range(4)
            ]
        })
        tours.append({
            "numero": 3, "nom": "Gagnants — Demi-finales", "section": "winner", "bracket": "winner",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {"id": "W3_M1", "bracket": "winner", "etape": 4, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "W2_M1", "source_b": "W2_M2", "type_source_a": "vainqueur", "type_source_b": "vainqueur"},
                {"id": "W3_M2", "bracket": "winner", "etape": 4, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "W2_M3", "source_b": "W2_M4", "type_source_a": "vainqueur", "type_source_b": "vainqueur"}
            ]
        })
        tours.append({
            "numero": 4, "nom": "Gagnants — Finale", "section": "winner", "bracket": "winner",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "W4_M1", "bracket": "winner", "etape": 6, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "W3_M1", "source_b": "W3_M2", "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })
        tours.append({
            "numero": 5, "nom": "Seconde Chance — Tour 1", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {"id": f"L1_M{i+1}", "bracket": "loser", "etape": 2, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": f"W1_M{2*i+1}", "source_b": f"W1_M{2*i+2}", "type_source_a": "perdant", "type_source_b": "perdant"} for i in range(4)
            ]
        })
        w2_losers = ["W2_M4", "W2_M3", "W2_M2", "W2_M1"]
        tours.append({
            "numero": 6, "nom": "Seconde Chance — Tour 2", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {"id": f"L2_M{i+1}", "bracket": "loser", "etape": 3, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": f"L1_M{i+1}", "source_b": w2_losers[i], "type_source_a": "vainqueur", "type_source_b": "perdant"} for i in range(4)
            ]
        })
        tours.append({
            "numero": 7, "nom": "Seconde Chance — Quarts de finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {"id": "L3_M1", "bracket": "loser", "etape": 4, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "L2_M1", "source_b": "L2_M2", "type_source_a": "vainqueur", "type_source_b": "vainqueur"},
                {"id": "L3_M2", "bracket": "loser", "etape": 4, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "L2_M3", "source_b": "L2_M4", "type_source_a": "vainqueur", "type_source_b": "vainqueur"}
            ]
        })
        tours.append({
            "numero": 8, "nom": "Seconde Chance — Repêchage Demi-finales", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [
                {"id": "L4_M1", "bracket": "loser", "etape": 5, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "L3_M1", "source_b": "W3_M2", "type_source_a": "vainqueur", "type_source_b": "perdant"},
                {"id": "L4_M2", "bracket": "loser", "etape": 5, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "L3_M2", "source_b": "W3_M1", "type_source_a": "vainqueur", "type_source_b": "perdant"}
            ]
        })
        tours.append({
            "numero": 9, "nom": "Seconde Chance — Demi-finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "L5_M1", "bracket": "loser", "etape": 6, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "L4_M1", "source_b": "L4_M2", "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })
        tours.append({
            "numero": 10, "nom": "Seconde Chance — Finale", "section": "loser", "bracket": "loser",
            "race_to": race_prelim, "format_label": f"{race_prelim} de {2*race_prelim - 1}",
            "matchs": [{
                "id": "L6_M1", "bracket": "loser", "etape": 7, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "L5_M1", "source_b": "W4_M1", "type_source_a": "vainqueur", "type_source_b": "perdant"
            }]
        })
        tours.append({
            "numero": 11, "nom": "🏆 Grande Finale Officielle", "section": "finale", "bracket": "finale",
            "race_to": race_finale, "format_label": f"{race_finale} de {2*race_finale - 1}",
            "matchs": [{
                "id": "GF_M1", "bracket": "finale", "etape": 8, "race_to": race_finale, "equipe_a": "À déterminer", "equipe_b": "À déterminer", "score_a": 0, "score_b": 0, "termine": False, "passe_droit": False, "vainqueur": None, "source_a": "W4_M1", "source_b": "L6_M1", "type_source_a": "vainqueur", "type_source_b": "vainqueur"
            }]
        })

    # Propager les exemptions initiales de W1 vers les matchs correspondants
    for m in w1_matchs:
        if m.get("termine") and m.get("passe_droit"):
            mid = m["id"]
            for t in tours:
                for mf in t.get("matchs", []):
                    if mf.get("source_a") == mid:
                        mf["equipe_a"] = m["vainqueur"] if mf.get("type_source_a") == "vainqueur" else m["perdant"]
                    if mf.get("source_b") == mid:
                        mf["equipe_b"] = m["vainqueur"] if mf.get("type_source_b") == "vainqueur" else m["perdant"]

    heure_fin = planifier_horaires_double_elimination(tours, heure_debut=heure_debut, duree_min=duree_min, nb_tables=nb_tables)

    tournoi_obj = {
        "titre": titre,
        "date_creation": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "format": "double_elimination",
        "format_label": "Double élimination (Winner & Loser Bracket)",
        "race_prelim": race_prelim,
        "race_finale": race_finale,
        "participants": p_liste,
        "promus_second_tour": promus,
        "total_tours": len(tours),
        "tours": tours,
        "heure_debut": heure_debut,
        "duree_match_min": duree_min,
        "nb_tables": nb_tables,
        "heure_fin_estimee": heure_fin,
        "statut": "en_cours",
        "vainqueur_final": None,
        "finaliste": None
    }
    return tournoi_obj

def actualiser_score_elimination(tournoi, tour_num, match_id, score_a, score_b):
    """Enregistre le score et qualifie automatiquement le vainqueur (et perdant en double élimination)."""
    t_idx = tour_num - 1
    m_trouve = None
    tour_courant = None
    if 0 <= t_idx < len(tournoi.get("tours", [])):
        tour_courant = tournoi["tours"][t_idx]
        for m in tour_courant.get("matchs", []):
            if m["id"] == match_id:
                m_trouve = m
                break

    if not m_trouve:
        for idx, t in enumerate(tournoi.get("tours", [])):
            for m in t.get("matchs", []):
                if m["id"] == match_id:
                    m_trouve = m
                    tour_courant = t
                    tour_num = idx + 1
                    break
            if m_trouve:
                break

    if not m_trouve:
        return False

    race_to = m_trouve.get("race_to", tour_courant.get("race_to", 3 if tour_num == tournoi.get("total_tours") else 2))

    if score_a == score_b:
        return False
    if score_a < race_to and score_b < race_to:
        return False

    m_trouve["score_a"] = score_a
    m_trouve["score_b"] = score_b
    vainqueur = m_trouve["equipe_a"] if score_a > score_b else m_trouve["equipe_b"]
    perdant = m_trouve["equipe_b"] if score_a > score_b else m_trouve["equipe_a"]
    m_trouve["vainqueur"] = vainqueur
    m_trouve["perdant"] = perdant
    m_trouve["termine"] = True

    # Propagation directe selon source_a / source_b et type_source_a / type_source_b
    propage = False
    cascade_termines = []
    for t in tournoi.get("tours", []):
        for m_futur in t.get("matchs", []):
            if m_futur.get("source_a") == match_id:
                type_a = m_futur.get("type_source_a", "vainqueur")
                m_futur["equipe_a"] = vainqueur if type_a == "vainqueur" else perdant
                propage = True
            if m_futur.get("source_b") == match_id:
                type_b = m_futur.get("type_source_b", "vainqueur")
                m_futur["equipe_b"] = vainqueur if type_b == "vainqueur" else perdant
                propage = True

            # Traitement des exemptions si un slot devient "Exempt (Passe-droit)"
            if not m_futur.get("termine"):
                ea_f = m_futur.get("equipe_a")
                eb_f = m_futur.get("equipe_b")
                race_f = m_futur.get("race_to", 2)
                if ea_f and ea_f not in ["À déterminer", "Exempt (Passe-droit)"] and eb_f == "Exempt (Passe-droit)":
                    m_futur["score_a"] = race_f
                    m_futur["score_b"] = 0
                    m_futur["vainqueur"] = ea_f
                    m_futur["perdant"] = "Exempt (Passe-droit)"
                    m_futur["termine"] = True
                    m_futur["passe_droit"] = True
                    cascade_termines.append(m_futur["id"])
                elif eb_f and eb_f not in ["À déterminer", "Exempt (Passe-droit)"] and ea_f == "Exempt (Passe-droit)":
                    m_futur["score_a"] = 0
                    m_futur["score_b"] = race_f
                    m_futur["vainqueur"] = eb_f
                    m_futur["perdant"] = "Exempt (Passe-droit)"
                    m_futur["termine"] = True
                    m_futur["passe_droit"] = True
                    cascade_termines.append(m_futur["id"])
                elif ea_f == "Exempt (Passe-droit)" and eb_f == "Exempt (Passe-droit)":
                    m_futur["score_a"] = 0
                    m_futur["score_b"] = 0
                    m_futur["vainqueur"] = "Exempt (Passe-droit)"
                    m_futur["perdant"] = "Exempt (Passe-droit)"
                    m_futur["termine"] = True
                    m_futur["passe_droit"] = True
                    cascade_termines.append(m_futur["id"])

    # Traiter cascades de byes
    for casc_id in cascade_termines:
        for t in tournoi.get("tours", []):
            for m_futur in t.get("matchs", []):
                for t_src in tournoi.get("tours", []):
                    for mc in t_src.get("matchs", []):
                        if mc["id"] == casc_id:
                            cv = mc["vainqueur"]
                            cp = mc["perdant"]
                            if m_futur.get("source_a") == casc_id:
                                m_futur["equipe_a"] = cv if m_futur.get("type_source_a", "vainqueur") == "vainqueur" else cp
                            if m_futur.get("source_b") == casc_id:
                                m_futur["equipe_b"] = cv if m_futur.get("type_source_b", "vainqueur") == "vainqueur" else cp

    # Fallback pour élimination simple historique
    if not propage and tournoi.get("format") != "double_elimination" and tour_num < tournoi.get("total_tours", 1):
        try:
            m_idx_in_tour = tour_courant["matchs"].index(m_trouve)
            prochain_tour = tournoi["tours"][tour_num]
            prochain_match_idx = m_idx_in_tour // 2
            if prochain_match_idx < len(prochain_tour["matchs"]):
                prochain_match = prochain_tour["matchs"][prochain_match_idx]
                if m_idx_in_tour % 2 == 0:
                    prochain_match["equipe_a"] = vainqueur
                else:
                    prochain_match["equipe_b"] = vainqueur
        except Exception:
            pass

    est_finale = (tour_num == tournoi.get("total_tours")) or (match_id == "GF_M1")
    if est_finale:
        tournoi["vainqueur_final"] = vainqueur
        tournoi["finaliste"] = perdant
        tournoi["statut"] = "termine"
        archiver_tournoi(tournoi, mode=tournoi.get("mode", "simple"))
    return True

def attribuer_passe_droit_elimination(tournoi, tour_num, match_id, beneficiaire):
    """Accorde un passe-droit à un joueur ou duo dans un match et le promeut immédiatement."""
    m_trouve = None
    tour_courant = None
    for idx, t in enumerate(tournoi.get("tours", [])):
        for m in t.get("matchs", []):
            if m["id"] == match_id:
                m_trouve = m
                tour_courant = t
                tour_num = idx + 1
                break
        if m_trouve:
            break

    if not m_trouve:
        return False

    race_to = m_trouve.get("race_to", tour_courant.get("race_to", 3 if tour_num == tournoi.get("total_tours") else 2))
    ea = m_trouve.get("equipe_a")
    eb = m_trouve.get("equipe_b")

    m_trouve["passe_droit"] = True
    m_trouve["vainqueur"] = beneficiaire
    m_trouve["termine"] = True

    if beneficiaire == ea:
        m_trouve["score_a"] = race_to
        m_trouve["score_b"] = 0
        perdant = eb
    else:
        m_trouve["score_a"] = 0
        m_trouve["score_b"] = race_to
        perdant = ea
    m_trouve["perdant"] = perdant

    # Propagation directe
    propage = False
    for t in tournoi.get("tours", []):
        for m_futur in t.get("matchs", []):
            if m_futur.get("source_a") == match_id:
                type_a = m_futur.get("type_source_a", "vainqueur")
                m_futur["equipe_a"] = beneficiaire if type_a == "vainqueur" else perdant
                propage = True
            if m_futur.get("source_b") == match_id:
                type_b = m_futur.get("type_source_b", "vainqueur")
                m_futur["equipe_b"] = beneficiaire if type_b == "vainqueur" else perdant
                propage = True

    # Fallback pour élimination simple historique
    if not propage and tournoi.get("format") != "double_elimination" and tour_num < tournoi.get("total_tours", 1):
        try:
            m_idx_in_tour = tour_courant["matchs"].index(m_trouve)
            prochain_tour = tournoi["tours"][tour_num]
            prochain_match_idx = m_idx_in_tour // 2
            if prochain_match_idx < len(prochain_tour["matchs"]):
                prochain_match = prochain_tour["matchs"][prochain_match_idx]
                if m_idx_in_tour % 2 == 0:
                    prochain_match["equipe_a"] = beneficiaire
                else:
                    prochain_match["equipe_b"] = beneficiaire
        except Exception:
            pass

    est_finale = (tour_num == tournoi.get("total_tours")) or (match_id == "GF_M1")
    if est_finale:
        tournoi["vainqueur_final"] = beneficiaire
        tournoi["finaliste"] = perdant
        tournoi["statut"] = "termine"
        archiver_tournoi(tournoi, mode=tournoi.get("mode", "simple"))

    return True

def attribuer_passe_droit_round_robin(tournoi, match_id, beneficiaire):
    """Accorde un passe-droit dans une rencontre de Round-Robin (victoire par forfait/défaut)."""
    matchs_rr = tournoi.get("matchs", [])
    rr_race = tournoi.get("race_to", 2)
    for m in matchs_rr:
        if m["id"] == match_id:
            m["passe_droit"] = True
            m["termine"] = True
            m["vainqueur"] = beneficiaire
            if beneficiaire == m["equipe_a"]:
                m["score_a"] = rr_race
                m["score_b"] = 0
            else:
                m["score_a"] = 0
                m["score_b"] = rr_race
            return True
    return False



def generer_round_robin(participants, race_to=2, titre="Tournoi", heure_debut="09:00", duree_min=30, nb_tables=2):
    """Génère un championnat toutes rondes (Round-Robin). Format officiel : 2 de 3."""
    p_liste = list(participants)
    random.shuffle(p_liste)
    matchs = []
    m_idx = 1
    fmt_label = "2 de 3" if race_to == 2 else f"Course à {race_to}"
    for i in range(len(p_liste)):
        for j in range(i + 1, len(p_liste)):
            matchs.append({
                "id": f"RR_M{m_idx}",
                "equipe_a": p_liste[i],
                "equipe_b": p_liste[j],
                "score_a": 0,
                "score_b": 0,
                "race_to": race_to,
                "format_label": fmt_label,
                "termine": False,
                "vainqueur": None
            })
            m_idx += 1
    heure_fin = planifier_horaires_round_robin(matchs, heure_debut=heure_debut, duree_min=duree_min, nb_tables=nb_tables)

    return {
        "titre": titre,
        "date_creation": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "format": "round_robin",
        "race_to": race_to,
        "format_label": fmt_label,
        "participants": p_liste,
        "matchs": matchs,
        "heure_debut": heure_debut,
        "duree_match_min": duree_min,
        "nb_tables": nb_tables,
        "heure_fin_estimee": heure_fin,
        "statut": "en_cours",
        "vainqueur_final": None,
        "finaliste": None
    }

def calculer_classement_round_robin(tournoi_rr):
    """Calcule le classement en direct pour un tournoi round-robin."""
    stats = {p: {"pj": 0, "v": 0, "d": 0, "pour": 0, "contre": 0, "diff": 0, "pts": 0} for p in tournoi_rr.get("participants", [])}
    for m in tournoi_rr.get("matchs", []):
        if m.get("termine"):
            ea, eb = m["equipe_a"], m["equipe_b"]
            sa, sb = m["score_a"], m["score_b"]
            if ea in stats and eb in stats:
                stats[ea]["pj"] += 1
                stats[eb]["pj"] += 1
                stats[ea]["pour"] += sa
                stats[ea]["contre"] += sb
                stats[eb]["pour"] += sb
                stats[eb]["contre"] += sa
                if sa > sb:
                    stats[ea]["v"] += 1
                    stats[ea]["pts"] += 2
                    stats[eb]["d"] += 1
                elif sb > sa:
                    stats[eb]["v"] += 1
                    stats[eb]["pts"] += 2
                    stats[ea]["d"] += 1

    for p, s in stats.items():
        s["diff"] = s["pour"] - s["contre"]

    classement = sorted(stats.items(), key=lambda x: (x[1]["pts"], x[1]["diff"], x[1]["pour"]), reverse=True)
    return classement

def formater_nom_court_joueur(nom, avec_point=True):
    """Extrait l'initiale du prénom et le nom de famille (avec ou sans point)."""
    if not nom:
        return ""
    nom_str = str(nom).strip()
    lower = nom_str.lower()
    if lower in ["à déterminer", "a determiner", "bye", "en attente", "tbd", "exempt", "-", ""]:
        return nom_str
    if lower.startswith("exempt") or "passe-droit" in lower or "passe droit" in lower:
        return nom_str
    if lower.startswith("vainqueur") or lower.startswith("perdant") or lower.startswith("gagnant") or lower.startswith("match"):
        return nom_str

    parts = nom_str.split()
    if len(parts) <= 1:
        return nom_str

    prenom = parts[0]
    nom_famille = " ".join(parts[1:])
    initiale = prenom[0].upper()
    if avec_point:
        return f"{initiale}. {nom_famille}"
    else:
        return f"{initiale} {nom_famille}"

def formater_nom_abrege_joueur(nom_joueur):
    """Formate un nom de joueur ou de duo pour l'arborescence imprimable.
    Pour les duos (double) : ultra-compact sans point avec séparateur '/' (ex: G Vézina/M Caron).
    Pour les simples : première lettre du prénom avec point et nom de famille (ex: G. Vézina)."""
    if not nom_joueur:
        return ""
    nom_str = str(nom_joueur).strip()

    # Détection des duos en double (séparateurs ' & ', ' / ', ' et ')
    for sep in [" & ", " / ", " et "]:
        if sep in nom_str:
            duo_parts = nom_str.split(sep)
            return "/".join([formater_nom_court_joueur(p, avec_point=False) for p in duo_parts if p.strip()])

    if "/" in nom_str:
        duo_parts = nom_str.split("/")
        return "/".join([formater_nom_court_joueur(p, avec_point=False) for p in duo_parts if p.strip()])

    # Joueur individuel (Simple)
    return formater_nom_court_joueur(nom_str, avec_point=True)

def generer_html_tournoi(tournoi, mode="simple"):
    """Génère la feuille officielle imprimable du tournoi limitée strictement à l'arborescence (Arbre / Matrice)."""
    logo_b64 = charger_armoiries_base64()
    src_val = logo_b64 if logo_b64 else "cid:armoiries_logo"
    arm_existe = bool(logo_b64 or os.path.isfile(find_armoiries_path()))
    logo_td = f'<td class="header-logo-td" style="width: 50px; vertical-align: middle; padding-right: 10px;"><img class="header-logo-img" src="{src_val}" alt="Armoiries" style="height: 46px; width: 46px; object-fit: contain; border-radius: 4px;"></td>' if arm_existe else ''

    titre_t = tournoi.get("titre", "Tournoi officiel")
    date_t = tournoi.get("date_creation", "")
    mode_str = "Simple (1 contre 1)" if mode == "simple" else "Double / Équipes (2 contre 2)"
    is_double_elim = (tournoi.get("format") == "double_elimination")
    is_elim = (tournoi.get("format") == "elimination")

    if is_double_elim:
        race_p = tournoi.get("race_prelim", 2)
        race_f = tournoi.get("race_finale", 3)
        format_str = f"Double élimination (Gagnants & Seconde chance {race_p} de {2*race_p-1} • Grande Finale {race_f} de {2*race_f-1})"
    elif is_elim:
        race_p = tournoi.get("race_prelim", 2)
        race_f = tournoi.get("race_finale", 3)
        format_str = f"Élimination directe (Préliminaires {race_p} de {2*race_p-1} • Finale {race_f} de {2*race_f-1})"
    else:
        race_to = tournoi.get("race_to", 2)
        format_str = f"Championnat toutes rondes ({tournoi.get('format_label', '2 de 3')})"

    statut = tournoi.get("statut", "en_cours")

    podium_html = ""
    if statut == "termine" and tournoi.get("vainqueur_final"):
        v_final = formater_nom_abrege_joueur(tournoi["vainqueur_final"])
        fin_final = formater_nom_abrege_joueur(tournoi.get("finaliste", "Non spécifié"))
        podium_html = f"""
        <div style="background: linear-gradient(135deg, #fff9c4, #fffde7); border: 2px solid #fbc02d; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; text-align: center;">
            <div style="font-size: 13px; font-weight: bold; color: #f57f17; margin-bottom: 2px;">🏆 PALMARÈS OFFICIEL DU TOURNOI</div>
            <div style="font-size: 12px; color: #222;">
                🥇 <strong>Champion :</strong> <span style="font-size: 14px; color: #0b3c5d; font-weight: bold;">{v_final}</span>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                🥈 <strong>Finaliste :</strong> <span style="font-size: 13px; color: #555;">{fin_final}</span>
            </div>
        </div>
        """

    # BANNIÈRE PARTICIPANTS PROMUS AU SECOND TOUR
    promus_html = ""
    if (is_elim or is_double_elim) and tournoi.get("promus_second_tour"):
        promus_str = ", ".join([formater_nom_abrege_joueur(p) for p in tournoi["promus_second_tour"]])
        promus_html = f"""
        <div style="background: #eef7ff; border: 1px solid #90caf9; border-radius: 4px; padding: 5px 10px; margin-bottom: 8px; font-size: 11px; color: #0b3c5d;">
            🎟️ <strong>Participants promus d'office au 2ᵉ tour (Passe-droit) :</strong> {promus_str}
        </div>
        """

    # CONSTRUCTION DE L'ARBORESCENCE GRAPHIQUE (BRACKET OU MATRICE)
    arborescence_html = ""
    if is_double_elim:
        tours = tournoi.get("tours", [])
        promus_set = set(tournoi.get("promus_second_tour", []))

        def generer_carte_html_match(m, r_fmt):
            m_id = m.get("id", "")
            m_fmt = m.get("format_label", r_fmt)
            ea = m.get("equipe_a", "À déterminer")
            eb = m.get("equipe_b", "À déterminer")
            sa = m.get("score_a", 0)
            sb = m.get("score_b", 0)
            termine = m.get("termine", False)
            vainq = m.get("vainqueur")

            m_pd = m.get("passe_droit", False)
            if m_pd and termine:
                sc_a_disp = "BYE" if vainq == ea else "-"
                sc_b_disp = "BYE" if vainq == eb else "-"
            else:
                sc_a_disp = str(sa) if termine else "-"
                sc_b_disp = str(sb) if termine else "-"

            win_a = "winner" if (termine and vainq == ea) else ""
            win_b = "winner" if (termine and vainq == eb) else ""
            card_done = "is-done" if termine else ""

            m_h = m.get("heure_estimee", "")
            m_t_court = m.get("table_courte", "")
            if m_pd:
                h_badge = '<span style="color: #2e7d32; font-weight: bold;">🎟️ Passe-droit</span>'
            elif m_h and m_h != "—":
                h_badge = f'<span style="color: #0b3c5d; font-weight: bold;">⏰ {m_h} [{m_t_court}]</span>'
            else:
                h_badge = f'<span>{m_fmt}</span>'

            if ea == "À déterminer" and m.get("source_a"):
                type_a = m.get("type_source_a", "vainqueur")
                pfx_a = "Vainq." if type_a == "vainqueur" else "Perd."
                ea_disp = f"{pfx_a} {m['source_a']}"
            else:
                ea_disp = formater_nom_abrege_joueur(ea)
                if not m.get("source_a") and ea in promus_set:
                    ea_disp += " 🎟️"

            if eb == "À déterminer" and m.get("source_b"):
                type_b = m.get("type_source_b", "vainqueur")
                pfx_b = "Vainq." if type_b == "vainqueur" else "Perd."
                eb_disp = f"{pfx_b} {m['source_b']}"
            else:
                eb_disp = formater_nom_abrege_joueur(eb)
                if not m.get("source_b") and eb in promus_set:
                    eb_disp += " 🎟️"

            return f"""
            <div class="bracket-card {card_done}">
                <div class="card-header">
                    <span>{m_id} • {m_fmt}</span>
                    {h_badge}
                </div>
                <div class="card-body">
                    <div class="player-row {win_a}">
                        <span class="p-name" title="{ea}">{ea_disp}</span>
                        <span class="p-score">{sc_a_disp}</span>
                    </div>
                    <div class="player-row {win_b}">
                        <span class="p-name" title="{eb}">{eb_disp}</span>
                        <span class="p-score">{sc_b_disp}</span>
                    </div>
                </div>
            </div>
            """

        def generer_colonnes_section(liste_tours, classe_col=""):
            res = []
            for t in liste_tours:
                r_name = t.get("nom", f"Tour {t.get('numero', 1)}")
                r_fmt = t.get("format_label", "")
                cards = [generer_carte_html_match(m, r_fmt) for m in t.get("matchs", [])]
                res.append(f"""
                <div class="bracket-col {classe_col}">
                    <div class="bracket-round-title">
                        <div class="r-name">{r_name}</div>
                        <div class="r-fmt">{r_fmt}</div>
                    </div>
                    <div class="bracket-round-matches">
                        {''.join(cards)}
                    </div>
                </div>
                """)
            return res

        cols_winner = generer_colonnes_section([t for t in tours if t.get("bracket") == "winner"], "")
        cols_loser = generer_colonnes_section([t for t in tours if t.get("bracket") == "loser"], "loser-col")
        cols_finale = generer_colonnes_section([t for t in tours if t.get("bracket") == "finale"], "finale-col")

        vainq_final = tournoi.get("vainqueur_final") or "À déterminer"
        vainq_final_disp = formater_nom_abrege_joueur(vainq_final)
        champ_col_html = f"""
        <div class="bracket-col champion-col">
            <div class="bracket-round-title" style="background: #f57f17;">
                <div class="r-name">🏆 Champion</div>
                <div class="r-fmt">Titre officiel</div>
            </div>
            <div class="bracket-round-matches" style="justify-content: center;">
                <div class="champion-box">
                    <div class="champ-trophy">🥇</div>
                    <div class="champ-title">CHAMPION DU TOURNOI</div>
                    <div class="champ-name">{vainq_final_disp}</div>
                </div>
            </div>
        </div>
        """

        arborescence_html = f"""
        <div class="bracket-section">
            <div class="bracket-section-header winner">🟦 TABLEAU DES GAGNANTS (WINNER BRACKET)</div>
            <div class="bracket-wrapper">
                {''.join(cols_winner)}
            </div>

            <div class="bracket-section-header loser">🟧 TABLEAU DE SECONDE CHANCE (LOSER BRACKET — REPÊCHAGE)</div>
            <div class="bracket-wrapper">
                {''.join(cols_loser)}
            </div>

            <div class="bracket-section-header finale">🏆 GRANDE FINALE OFFICIELLE & PODIUM</div>
            <div class="bracket-wrapper" style="justify-content: flex-start; max-width: 620px;">
                {''.join(cols_finale)}
                {champ_col_html}
            </div>
        </div>
        """
    elif is_elim:
        cols_html = []
        tours = tournoi.get("tours", [])
        for t in tours:
            r_name = t.get("nom", f"Tour {t.get('numero', 1)}")
            r_fmt = t.get("format_label", "")
            cards = []
            for m in t.get("matchs", []):
                m_id = m.get("id", "")
                m_fmt = m.get("format_label", r_fmt)
                ea = m.get("equipe_a", "À déterminer")
                eb = m.get("equipe_b", "À déterminer")
                sa = m.get("score_a", 0)
                sb = m.get("score_b", 0)
                termine = m.get("termine", False)
                vainq = m.get("vainqueur")

                m_pd = m.get("passe_droit", False)
                if m_pd and termine:
                    sc_a_disp = "BYE" if vainq == ea else "-"
                    sc_b_disp = "BYE" if vainq == eb else "-"
                else:
                    sc_a_disp = str(sa) if termine else "-"
                    sc_b_disp = str(sb) if termine else "-"

                win_a = "winner" if (termine and vainq == ea) else ""
                win_b = "winner" if (termine and vainq == eb) else ""
                card_done = "is-done" if termine else ""

                m_h = m.get("heure_estimee", "")
                m_t_court = m.get("table_courte", "")
                if m_pd:
                    h_badge = '<span style="color: #2e7d32; font-weight: bold;">🎟️ Passe-droit</span>'
                elif m_h:
                    h_badge = f'<span style="color: #0b3c5d; font-weight: bold;">⏰ {m_h} [{m_t_court}]</span>'
                else:
                    h_badge = f'<span>{m_fmt}</span>'

                promus_set = set(tournoi.get("promus_second_tour", []))
                if ea == "À déterminer" and m.get("source_a"):
                    ea_disp = f"Vainq. {m['source_a']}"
                else:
                    ea_disp = formater_nom_abrege_joueur(ea)
                    if not m.get("source_a") and ea in promus_set:
                        ea_disp += " 🎟️"

                if eb == "À déterminer" and m.get("source_b"):
                    eb_disp = f"Vainq. {m['source_b']}"
                else:
                    eb_disp = formater_nom_abrege_joueur(eb)
                    if not m.get("source_b") and eb in promus_set:
                        eb_disp += " 🎟️"
                cards.append(f"""
                <div class="bracket-card {card_done}">
                    <div class="card-header">
                        <span>{m_id} • {m_fmt}</span>
                        {h_badge}
                    </div>
                    <div class="card-body">
                        <div class="player-row {win_a}">
                            <span class="p-name" title="{ea}">{ea_disp}</span>
                            <span class="p-score">{sc_a_disp}</span>
                        </div>
                        <div class="player-row {win_b}">
                            <span class="p-name" title="{eb}">{eb_disp}</span>
                            <span class="p-score">{sc_b_disp}</span>
                        </div>
                    </div>
                </div>
                """)

            cols_html.append(f"""
            <div class="bracket-col">
                <div class="bracket-round-title">
                    <div class="r-name">{r_name}</div>
                    <div class="r-fmt">{r_fmt}</div>
                </div>
                <div class="bracket-round-matches">
                    {''.join(cards)}
                </div>
            </div>
            """)

        vainq_final = tournoi.get("vainqueur_final") or "À déterminer"
        vainq_final_disp = formater_nom_abrege_joueur(vainq_final)
        cols_html.append(f"""
        <div class="bracket-col champion-col">
            <div class="bracket-round-title" style="background: #f57f17;">
                <div class="r-name">🏆 Champion</div>
                <div class="r-fmt">Titre officiel</div>
            </div>
            <div class="bracket-round-matches" style="justify-content: center;">
                <div class="champion-box">
                    <div class="champ-trophy">🥇</div>
                    <div class="champ-title">CHAMPION DU TOURNOI</div>
                    <div class="champ-name">{vainq_final_disp}</div>
                </div>
            </div>
        </div>
        """)

        arborescence_html = f"""
        <div class="bracket-section">
            <div class="bracket-wrapper">
                {''.join(cols_html)}
            </div>
        </div>
        """
    else:
        # Matrice Round-Robin (Face-à-face)
        participants = tournoi.get("participants", [])
        matchs_rr = tournoi.get("matchs", [])
        scores_matrix = {}
        for m in matchs_rr:
            ea, eb = m["equipe_a"], m["equipe_b"]
            scores_matrix[(ea, eb)] = m
            scores_matrix[(eb, ea)] = m

        th_parts = "".join([f'<th style="padding: 4px 6px; font-size: 10px; border: 1px solid #c8d9e6;" title="{p}">{formater_nom_abrege_joueur(p)}</th>' for p in participants])
        rows_rr_matrix = []
        for p1 in participants:
            cells = []
            for p2 in participants:
                if p1 == p2:
                    cells.append('<td style="background: #eef2f5; color: #888; font-weight: bold; border: 1px solid #ddd;">—</td>')
                else:
                    m = scores_matrix.get((p1, p2))
                    if m and m.get("termine"):
                        sa = m["score_a"] if m["equipe_a"] == p1 else m["score_b"]
                        sb = m["score_b"] if m["equipe_a"] == p1 else m["score_a"]
                        bg = "#e8f5e9" if sa > sb else "#ffebee"
                        fw = "bold" if sa > sb else "normal"
                        cells.append(f'<td style="background: {bg}; font-weight: {fw}; border: 1px solid #ddd; padding: 4px;">{sa}-{sb}</td>')
                    else:
                        cells.append('<td style="border: 1px solid #ddd; color: #aaa; padding: 4px;">-</td>')

            p1_disp = formater_nom_abrege_joueur(p1)
            rows_rr_matrix.append(f"""
            <tr style="text-align: center;">
                <td style="text-align: left; font-weight: bold; padding: 5px 8px; border: 1px solid #ddd; background: #fafafa;" title="{p1}">{p1_disp}</td>
                {''.join(cells)}
            </tr>
            """)

        arborescence_html = f"""
        <div class="bracket-section">
            <h3 style="color: #0b3c5d; margin: 10px 0 8px 0; font-size: 13px; border-bottom: 2px solid #0b3c5d; padding-bottom: 4px; text-transform: uppercase;">
                🔄 Matrice officielle des confrontations directes
            </h3>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 10px;">
                    <thead>
                        <tr style="background: #0b3c5d; color: white; text-align: center;">
                            <th style="padding: 5px 8px; text-align: left; border: 1px solid #c8d9e6;">Participant</th>
                            {th_parts}
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows_rr_matrix)}
                    </tbody>
                </table>
            </div>
        </div>
        """

    h_deb = tournoi.get("heure_debut", "09:00")
    h_fin = tournoi.get("heure_fin_estimee", "")
    nb_tab = tournoi.get("nb_tables", 2)
    duree_tab = tournoi.get("duree_match_min", 30)
    tab_str = f"{nb_tab} table{'s' if nb_tab > 1 else ''}"
    horaire_html = f"&nbsp;|&nbsp; ⏰ <strong>Horaire (1 journée) :</strong> {h_deb} à ~{h_fin}" if h_fin else f"&nbsp;|&nbsp; ⏰ <strong>Début :</strong> {h_deb}"

    html_header_p = f"""
    <p class="date-para" style="margin: 2px 0 4px 0; font-size: 10px;">
        <strong>Date :</strong> {date_t} {horaire_html} &nbsp;|&nbsp; 
        <strong>Disponibilité :</strong> {tab_str} (~{duree_tab} min/match) &nbsp;|&nbsp; 
        <strong>Format :</strong> {format_str} &nbsp;|&nbsp; 
        <strong>Participants :</strong> {len(tournoi.get('participants', []))}
    </p>
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Arborescence officielle du tournoi - {titre_t}</title>
    <style>
        {STYLE_PRINT_A4}
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.35;
            color: #222;
            margin: 0;
            padding: 10px;
            background: #ffffff;
        }}
        .fiche-a4 {{
            max-width: 1050px;
            margin: 0 auto;
        }}
        .no-print-bar {{
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #eef4f8;
            padding: 8px 14px;
            border-radius: 8px;
            border: 1px solid #c8d9e6;
        }}
        .btn-print {{
            background-color: #0b3c5d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-print:hover {{
            background-color: #082a42;
        }}
        .bracket-section {{
            margin: 8px 0 10px 0;
        }}
        .bracket-section-header {{
            font-size: 11px;
            font-weight: bold;
            padding: 4px 8px;
            margin: 12px 0 6px 0;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}
        .bracket-section-header.winner {{
            background: #e8f0fe;
            color: #0b3c5d;
            border-left: 4px solid #0b3c5d;
        }}
        .bracket-section-header.loser {{
            background: #fef3c7;
            color: #92400e;
            border-left: 4px solid #d97706;
        }}
        .bracket-section-header.finale {{
            background: #fef9c3;
            color: #854d0e;
            border-left: 4px solid #f59e0b;
        }}
        .bracket-col.loser-col .bracket-round-title {{
            background: #d97706 !important;
        }}
        .bracket-col.finale-col .bracket-round-title {{
            background: #b45309 !important;
        }}
        .bracket-wrapper {{
            display: flex;
            flex-direction: row;
            gap: 10px;
            align-items: stretch;
            justify-content: flex-start;
            overflow-x: auto;
            padding: 4px 2px;
        }}
        .bracket-col {{
            display: flex;
            flex-direction: column;
            flex: 1;
            min-width: 170px;
            max-width: 250px;
            background: #fbfcfe;
            border-radius: 8px;
            border: 1px solid #dce4ec;
            padding: 8px 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }}
        .bracket-round-title {{
            text-align: center;
            background: #0b3c5d;
            color: white;
            padding: 5px 6px;
            border-radius: 5px;
            margin-bottom: 8px;
        }}
        .r-name {{
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .r-fmt {{
            font-size: 9px;
            color: #cbdbee;
            margin-top: 1px;
        }}
        .bracket-round-matches {{
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            flex: 1;
            gap: 8px;
        }}
        .bracket-card {{
            background: white;
            border: 1.5px solid #0b3c5d;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            overflow: hidden;
            page-break-inside: avoid;
        }}
        .bracket-card.is-done {{
            border-color: #2e7d32;
        }}
        .card-header {{
            background: #f0f4f8;
            color: #444;
            font-size: 8.5px;
            font-weight: bold;
            padding: 2px 6px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
        }}
        .player-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 6px;
            font-size: 10.5px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .player-row:last-child {{
            border-bottom: none;
        }}
        .player-row.winner {{
            background: #e8f5e9;
            font-weight: bold;
            color: #1b5e20;
        }}
        .p-name {{
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-right: 6px;
        }}
        .p-score {{
            background: #0b3c5d;
            color: white;
            font-size: 10.5px;
            font-weight: bold;
            padding: 1px 5px;
            border-radius: 3px;
            min-width: 16px;
            text-align: center;
        }}
        .player-row.winner .p-score {{
            background: #2e7d32;
        }}
        .champion-box {{
            background: linear-gradient(135deg, #fff9c4, #fffde7);
            border: 2px solid #fbc02d;
            border-radius: 8px;
            padding: 14px 8px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(251, 192, 45, 0.25);
            page-break-inside: avoid;
        }}
        .champ-trophy {{
            font-size: 26px;
            line-height: 1;
            margin-bottom: 4px;
        }}
        .champ-title {{
            font-size: 9.5px;
            font-weight: bold;
            color: #f57f17;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 3px;
        }}
        .champ-name {{
            font-size: 12px;
            font-weight: bold;
            color: #0b3c5d;
        }}
        @media print {{
            @page {{
                size: landscape;
                margin: 5mm 6mm;
            }}
            body {{
                margin: 0 !important;
                padding: 0 !important;
                background: #ffffff !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            .fiche-a4 {{
                max-width: 100% !important;
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }}
            .no-print-bar {{
                display: none !important;
            }}
            .bracket-section {{
                margin: 4px 0 0 0 !important;
            }}
            .bracket-wrapper {{
                overflow: visible !important;
                gap: 6px !important;
                padding: 0 !important;
                width: 100% !important;
            }}
            .bracket-col {{
                min-width: 0 !important;
                max-width: none !important;
                flex: 1 1 0px !important;
                padding: 3px 2px !important;
                border: 1px solid #b0c4de !important;
                box-shadow: none !important;
                background: #fafcfe !important;
            }}
            .bracket-round-title {{
                padding: 2px 2px !important;
                margin-bottom: 4px !important;
            }}
            .r-name {{
                font-size: 9px !important;
            }}
            .r-fmt {{
                font-size: 7px !important;
            }}
            .bracket-round-matches {{
                gap: 3px !important;
            }}
            .bracket-card {{
                border-width: 1px !important;
                box-shadow: none !important;
            }}
            .card-header {{
                font-size: 7.5px !important;
                padding: 1px 3px !important;
            }}
            .player-row {{
                padding: 1px 3px !important;
                font-size: 8px !important;
            }}
            .p-score {{
                font-size: 8px !important;
                padding: 0 2px !important;
                min-width: 12px !important;
            }}
            .champion-box {{
                padding: 6px 3px !important;
                box-shadow: none !important;
            }}
            .champ-trophy {{
                font-size: 16px !important;
                margin-bottom: 2px !important;
            }}
            .champ-title {{
                font-size: 7.5px !important;
            }}
            .champ-name {{
                font-size: 9px !important;
            }}
            .footer-note {{
                font-size: 8px !important;
                margin-top: 4px !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="fiche-a4">
        <div class="no-print-bar">
            <div>
                <strong style="color: #0b3c5d; font-size: 13px;">🌳 Arborescence officielle du tournoi</strong>
                <div style="font-size: 11px; color: #555;">Format calibré pour impression sur une seule page A4 (Orientation paysage recommandée)</div>
            </div>
            <button class="btn-print" onclick="window.print()">
                🖨️ Imprimer l'arborescence (A4)
            </button>
        </div>
        <table class="header-table" style="width: 100%; border-bottom: 2px solid #0b3c5d; padding-bottom: 4px; margin-bottom: 6px; border-collapse: collapse;">
            <tr>
                {logo_td}
                <td class="header-title" style="vertical-align: middle;">
                    <h2 class="header-title-h2" style="color: #0b3c5d; margin: 0; font-size: 16px;">🎱 Ligue de billard Boule en main</h2>
                    <div class="header-title-sub" style="color: #555; font-size: 11px; font-weight: bold; margin-top: 1px;">{titre_t} — {mode_str}</div>
                </td>
            </tr>
        </table>
        {html_header_p}
        {podium_html}
        {promus_html}
        {arborescence_html}
        <p class="footer-note" style="font-size: 8px; color: #777; margin-top: 6px; text-align: center;">
            Arborescence officielle générée via l'application de la Ligue de billard Boule en main.
        </p>
    </div>
</body>
</html>
"""
    return html

@st.dialog("🌳 Arborescence officielle du tournoi", width="large")
def modal_arborescence_tournoi(tournoi_obj, mode_str="simple"):
    """Dialogue grand format affichant l'arborescence complète, les matchs et les options d'impression."""
    html_feuille = generer_html_tournoi(tournoi_obj, mode=mode_str)
    html_json_str = json.dumps(html_feuille)

    col_btn_print, col_btn_ext, col_btn_refresh, col_btn_close = st.columns([1.3, 1.4, 1.2, 0.8])
    with col_btn_print:
        st.components.v1.html(
            f"""
            <button onclick="imprimerTournoiModal()" style="width:100%; height:38px; background-color:#0b3c5d; color:white; border:none; border-radius:6px; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
                🖨️ Imprimer (A4)
            </button>
            <script>
            function imprimerTournoiModal() {{
                var win = window.open('', '_blank');
                win.document.open();
                win.document.write({html_json_str});
                win.document.close();
                win.focus();
                win.document.title = "Feuille officielle de tournoi - Impression";
                setTimeout(function() {{
                    win.print();
                }}, 350);
            }}
            </script>
            """,
            height=42
        )
    with col_btn_ext:
        st.components.v1.html(
            f"""
            <button onclick="ouvrirTournoiNouvelOnglet()" style="width:100%; height:38px; background-color:#2e7d32; color:white; border:none; border-radius:6px; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
                🌐 Nouvel onglet
            </button>
            <script>
            function ouvrirTournoiNouvelOnglet() {{
                var win = window.open('', '_blank');
                win.document.open();
                win.document.write({html_json_str});
                win.document.close();
                win.focus();
                win.document.title = "Feuille de Tournoi";
            }}
            </script>
            """,
            height=42
        )
    with col_btn_refresh:
        if st.button("🔄 Actualiser", use_container_width=True, key=f"btn_act_dlg_{mode_str}", help="Recharge les derniers résultats saisis pour ce tournoi"):
            st.rerun()
    with col_btn_close:
        if st.button("✖️ Fermer", use_container_width=True, key=f"btn_close_dlg_{mode_str}"):
            st.rerun()

    st.components.v1.html(html_feuille, height=650, scrolling=True)

def actualiser_resultats_tournoi(notif_msg=None):
    """Actualise systématiquement l'ensemble des résultats du tournoi depuis le disque."""
    for k in list(st.session_state.keys()):
        if k.startswith("sc_a_") or k.startswith("sc_b_") or k.startswith("rr_a_") or k.startswith("rr_b_"):
            try:
                del st.session_state[k]
            except Exception:
                pass
    if os.path.exists(TOURNOIS_FILE):
        try:
            st.session_state["dernier_mtime_tournois_vu"] = os.path.getmtime(TOURNOIS_FILE)
        except Exception:
            pass
    msg = notif_msg if notif_msg else "🔄 Résultats du tournoi actualisés !"
    try:
        st.toast(msg, icon="🏆")
    except Exception:
        pass
    st.rerun()

def afficher_bandeau_verrou_tournoi():
    """Affiche le bandeau d'état du verrou exclusif et de gestion de prise/cession de main pour les tournois."""
    my_session_id = st.session_state.get("user_session_id", "")
    est_spectateur = st.session_state.get("est_spectateur", False) or not st.session_state.get("authentifie", False)

    if est_spectateur:
        est_editeur = False
        autre_editeur_actif = False
        temps_restant = 0
    else:
        veut_editer = not st.session_state.get("mode_consultation", False)
        est_editeur, temps_restant, autre_editeur_actif = gerer_verrou_session(my_session_id, veut_etre_editeur=veut_editer)

    if "msg_prise_main" in st.session_state:
        st.success(st.session_state.pop("msg_prise_main"))
    if "msg_cession_main" in st.session_state:
        st.info(st.session_state.pop("msg_cession_main"))

    td = charger_tournois_data()
    infos_sauv = td.get("derniere_sauvegarde", {})
    date_sauv = infos_sauv.get("date", "")
    action_sauv = infos_sauv.get("action", "")
    mention_sauv = f" • 💾 Dernière sauvegarde disque : {date_sauv}" if date_sauv else ""

    modes_actifs = [m for m in ["simple", "double"] if td.get(m) and isinstance(td.get(m), dict)]
    tournoi_actif = any(td.get(m) and isinstance(td.get(m), dict) and td.get(m).get("statut") == "en_cours" for m in ["simple", "double"])

    if est_editeur:
        col_lk1, col_lk2 = st.columns([2.6, 1.8] if modes_actifs else [3.2, 1.2])
        col_lk1.success(f"🟢 **Vous avez la main exclusive pour marquer et configurer le tournoi.**{mention_sauv}")
        with col_lk2:
            if modes_actifs:
                cb1, cb2, cb3 = st.columns([1.0, 1.3, 1.2])
                with cb1:
                    if st.button("🔓 Céder", key="btn_ceder_main_tournoi", use_container_width=True, help="Sauvegarde le tournoi sur disque et libère la main"):
                        with st.spinner("Sauvegarde et libération..."):
                            ceder_la_main_avec_sauvegarde(my_session_id)
                        st.rerun()
                with cb2:
                    with st.popover("💾 Sauvegarder", use_container_width=True, help="Sauvegarder dans l'historique du tournoi"):
                        st.markdown("##### 💾 Sauvegarde dans l'historique du tournoi")
                        for m_act in modes_actifs:
                            t_act = td.get(m_act)
                            lbl_m = "Simple (1 vs 1)" if m_act == "simple" else "Double (2 vs 2)"
                            if st.button(f"💾 Sauvegarder {lbl_m}", key=f"btn_bnd_save_hist_{m_act}", use_container_width=True, help=f"Sauvegarde le tournoi {lbl_m} dans l'historique officiel"):
                                sauvegarder_tournoi_dans_historique(m_act, notifier_admin=True)
                                st.success(f"✅ {lbl_m} sauvegardé dans l'historique !")
                                time.sleep(0.8)
                                st.rerun()
                with cb3:
                    with st.popover("❌ Annuler", use_container_width=True, help="Annulation complète du tournoi sans aucune sauvegarde"):
                        st.markdown("##### ⚠️ Annulation complète du tournoi")
                        st.write("Confirmez l'annulation complète. **Dans ce cas, aucune sauvegarde ne sera effectuée** :")
                        for m_act in modes_actifs:
                            t_act = td.get(m_act)
                            lbl_m = "Simple" if m_act == "simple" else "Double"
                            if st.button(f"🔴 Confirmer annulation {lbl_m}", key=f"btn_bnd_cancel_act_{m_act}", type="primary", use_container_width=True):
                                annuler_completement_tournoi(m_act)
                                st.session_state[f"msg_annulation_{m_act}"] = f"❌ Le tournoi {lbl_m} a été complètement annulé (aucune sauvegarde)."
                                st.rerun()
            else:
                if st.button("🔓 Céder la main", key="btn_ceder_main_tournoi", use_container_width=True, help="Sauvegarde automatiquement le tournoi sur le disque et libère la main"):
                    with st.spinner("Sauvegarde du tournoi et libération..."):
                        ceder_la_main_avec_sauvegarde(my_session_id)
                    st.rerun()
    elif est_spectateur:
        col_lk1, col_lk2 = st.columns([3.2, 1.2])
        texte_spec = "👁️ **Mode spectateur (Lecture seule) :** Consultation en direct du tournoi actif." if tournoi_actif else "👁️ **Mode spectateur (Lecture seule) :** Consultation des tournois. La saisie des scores est réservée au marqueur."
        col_lk1.info(texte_spec)
        col_lk1.caption("🔄 *Veille automatique active : dès que le marqueur met à jour le tournoi, les résultats sont actualisés systématiquement.*")
        with col_lk2:
            if st.button("🔄 Actualiser", key="btn_refresh_t_spec", type="primary" if tournoi_actif else "secondary", use_container_width=True, help="Recharge les derniers résultats et scores en direct du tournoi"):
                actualiser_resultats_tournoi()
    else:
        col_lk1, col_lk2 = st.columns([2.8, 1.4])
        if autre_editeur_actif:
            mins = temps_restant // 60
            secs = temps_restant % 60
            col_lk1.warning(f"🔒 **Mode consultation (Lecture seule) :** Un autre marqueur a actuellement la main sur la saisie. Vos modifications sont verrouillées.{mention_sauv} *(Inactivité restante : {mins}m {secs:02d}s)*")
            col_lk1.caption("🔄 *Veille automatique active : dès que le marqueur met à jour le tournoi, les résultats sont actualisés systématiquement.*")
        else:
            col_lk1.info(f"🔒 **Mode consultation (Lecture seule) :** Vous consultez le tournoi.{mention_sauv}")

        with col_lk2:
            if tournoi_actif:
                col_pm, col_act = st.columns([1.2, 1.2])
                with col_pm:
                    if st.button("⚡ Prendre la main", key="btn_prendre_main_tournoi", use_container_width=True, help="Prend le contrôle de la saisie, charge la dernière sauvegarde du tournoi et active l'édition"):
                        with st.spinner("Prise de la main et chargement..."):
                            prendre_la_main_avec_rechargement(my_session_id)
                        st.rerun()
                with col_act:
                    if st.button("🔄 Actualiser", key="btn_refresh_t_ed_consult", use_container_width=True, help="Recharge les résultats du tournoi sans prendre la main"):
                        actualiser_resultats_tournoi()
            else:
                if st.button("⚡ Prendre la main", key="btn_prendre_main_tournoi", use_container_width=True, help="Prend le contrôle de la saisie, charge la dernière sauvegarde du tournoi et active l'édition"):
                    with st.spinner("Prise de la main et chargement..."):
                        prendre_la_main_avec_rechargement(my_session_id)
                    st.rerun()

    # Veille automatique réactive pour spectateurs et mode consultation
    if not est_editeur:
        @st.fragment(run_every="4s")
        def surveiller_maj_marqueur_tournoi():
            if os.path.exists(TOURNOIS_FILE):
                try:
                    mtime_actuel = os.path.getmtime(TOURNOIS_FILE)
                except Exception:
                    mtime_actuel = 0
                cle_vu = "dernier_mtime_tournois_vu"
                if cle_vu not in st.session_state:
                    st.session_state[cle_vu] = mtime_actuel
                elif mtime_actuel > st.session_state.get(cle_vu, 0):
                    st.session_state[cle_vu] = mtime_actuel
                    time.sleep(0.2)
                    actualiser_resultats_tournoi("🔔 Le marqueur a mis à jour le tournoi ! Actualisation systématique des résultats effectuée.")

        surveiller_maj_marqueur_tournoi()

    return est_editeur

def afficher_formulaire_creation_tournoi(mode="simple", key_suffix="", est_editeur=True):
    """
    Formulaire universel et réutilisable pour la création et la configuration
    d'un nouveau tournoi (en Simple ou en Double / Équipes).
    """
    libelle_mode = "Tournoi en Simple (1 contre 1)" if mode == "simple" else "Tournoi en Double / Équipes (2 contre 2)"
    tournois_data = charger_tournois_data()

    st.caption(f"Configurez les paramètres et inscrivez les participants pour lancer un nouveau {libelle_mode.lower()}.")
    with st.container(border=True):
        col_cfg1, col_cfg2 = st.columns([2, 1])
        with col_cfg1:
            titre_defaut = f"Tournoi {'Simple' if mode == 'simple' else 'Double'} — {datetime.now().strftime('%d/%m/%Y')}"
            titre_saisi = st.text_input("Nom du tournoi :", value=titre_defaut, key=f"tournoi_titre_{mode}{key_suffix}")
            type_format = st.radio(
                "Format de compétition :",
                [
                    "🏆 Élimination directe (Arbre de tournoi)",
                    "🛡️ Double élimination (Winner & Loser Bracket — Seconde chance)",
                    "🔄 Championnat toutes rondes (Round-Robin)"
                ],
                key=f"tournoi_format_{mode}{key_suffix}"
            )
        with col_cfg2:
            st.markdown("**Formule officielle des matchs :**")
            if "Double élimination" in type_format:
                st.info(
                    "🛡️ **Double élimination :** Seconde chance garantie en cas de 1ʳᵉ défaite !\n\n"
                    "🔹 **Gagnants :** 2 de 3 *(premier à 2)*\n\n"
                    "🔸 **Seconde chance :** 2 de 3 *(premier à 2)*\n\n"
                    "🏆 **Grande Finale :** 3 de 5 *(premier à 3)*"
                )
            elif "Élimination" in type_format:
                st.info(
                    "🔹 **Préliminaires :** 2 de 3 *(premier à 2)*\n\n"
                    "🏆 **Grande Finale :** 3 de 5 *(premier à 3)*"
                )
            else:
                st.info(
                    "🔄 **Round-Robin :** 2 de 3 *(premier à 2)*\n\n"
                    "Chaque participant rencontre tous les autres."
                )

        st.markdown("##### 📅 Organisation, Disponibilité des tables & Horaires (1 seule journée)")
        st.caption("ℹ️ *Une pause dîner est automatiquement intégrée de 12:00 à 13:00 : aucun match n'est cédulé durant cette période.*")
        col_hor1, col_hor2, col_hor3 = st.columns([1.5, 1.2, 1.3])
        with col_hor1:
            choix_tables = st.radio(
                "Tables de billard disponibles :",
                ["🎱 2 tables (Recommandé - 2 matchs en parallèle)", "🎱 1 table (Matchs en alternance)"],
                index=0,
                key=f"tournoi_tables_{mode}{key_suffix}",
                help="Si 2 tables sont disponibles, 2 matchs se jouent en simultané. Si 1 table, les matchs se déroulent en alternance."
            )
            nb_tables_saisi = 2 if "2 tables" in choix_tables else 1
        with col_hor2:
            heure_debut_str = st.selectbox(
                "Heure de début du tournoi :",
                ["09:00", "08:30", "09:30", "10:00", "13:00"],
                index=0,
                key=f"tournoi_h_deb_{mode}{key_suffix}",
                help="Les tournois se déroulent en une seule journée et débutent à 9h a.m."
            )
        with col_hor3:
            duree_min_saisie = st.selectbox(
                "Durée estimée par match :",
                [30, 25, 35, 40, 45],
                index=0,
                format_func=lambda x: f"{x} minutes",
                key=f"tournoi_duree_{mode}{key_suffix}",
                help="Durée estimée d'un match (30 minutes par défaut)."
            )

        st.divider()

        # Sélection des participants
        joueurs_disponibles = obtenir_tous_les_joueurs_tournoi()

        # Gestion des invités personnalisés
        key_invites = f"invites_tournoi_{mode}{key_suffix}"
        if key_invites not in st.session_state:
            st.session_state[key_invites] = []

        col_inv1, col_inv2 = st.columns([3, 1])
        with col_inv1:
            nouveau_joueur = st.text_input("Ajouter un joueur invité / remplaçant :", key=f"input_invite_{mode}{key_suffix}", placeholder="Ex: Jean Tremblay")
        with col_inv2:
            st.write("")
            if st.button("➕ Ajouter l'invité", key=f"btn_add_invite_{mode}{key_suffix}", use_container_width=True):
                if nouveau_joueur.strip():
                    nom_prop = nouveau_joueur.strip()
                    if nom_prop not in joueurs_disponibles and nom_prop not in st.session_state[key_invites]:
                        st.session_state[key_invites].append(nom_prop)
                        st.rerun()

        tous_candidats = sorted(list(set(joueurs_disponibles + st.session_state[key_invites])))

        participants_finaux = []

        if mode == "simple":
            st.markdown("##### 👤 Liste des joueurs inscrits")
            col_sel_btn1, col_sel_btn2 = st.columns([1.5, 3.5])
            with col_sel_btn1:
                if st.button("👥 Sélectionner tous les inscrits", key=f"btn_all_{mode}{key_suffix}", use_container_width=True):
                    st.session_state[f"sel_participants_{mode}{key_suffix}"] = tous_candidats
                    st.rerun()
            with col_sel_btn2:
                st.caption("ℹ️ Par défaut, **tous les joueurs réguliers inscrits** participent au tournoi.")

            selection_j = st.multiselect(
                "Joueurs participants au tournoi :",
                options=tous_candidats,
                default=st.session_state.get(f"sel_participants_{mode}{key_suffix}", tous_candidats),
                key=f"sel_participants_{mode}{key_suffix}",
                help="Tous les joueurs inscrits sont sélectionnés par défaut."
            )
            participants_finaux = selection_j
            st.caption(f"🎯 **{len(participants_finaux)} joueur(s) inscrit(s)** participant au tournoi.")

        else:
            # Mode DOUBLE : Sélection des duos de joueurs avec drop boxes
            st.markdown("##### 👥 Sélection des duos de joueurs inscrits (Drop boxes)")
            st.caption("Constituez les équipes de double en sélectionnant les deux joueurs de chaque duo dans les listes déroulantes ci-dessous.")

            col_nb_d1, col_nb_d2 = st.columns([1.5, 3])
            with col_nb_d1:
                nb_duos_choisi = st.selectbox(
                    "Nombre de duos participant :",
                    options=[8, 4, 12, 16, 2, 6, 10, 14],
                    index=0,
                    key=f"nb_duos_select_{mode}{key_suffix}",
                    help="Sélectionnez le nombre de duos (8 duos = 16 joueurs, idéal pour un tournoi à élimination sur 3 rondes sans passe-droit)."
                )
            with col_nb_d2:
                col_btn_pige, col_btn_reset = st.columns(2)
                with col_btn_pige:
                    st.write("")
                    if st.button("🎲 Piger au hasard", key=f"btn_pige_drop_{mode}{key_suffix}", use_container_width=True, help="Remplit aléatoirement les drop boxes avec les joueurs inscrits"):
                        pool_pige = list(tous_candidats)
                        random.shuffle(pool_pige)
                        for d_idx in range(nb_duos_choisi):
                            if len(pool_pige) >= 2:
                                st.session_state[f"duo_{d_idx}_j1_{mode}{key_suffix}"] = pool_pige.pop(0)
                                st.session_state[f"duo_{d_idx}_j2_{mode}{key_suffix}"] = pool_pige.pop(0)
                        st.rerun()
                with col_btn_reset:
                    st.write("")
                    if st.button("🔄 Réinitialiser", key=f"btn_reset_duos_{mode}{key_suffix}", use_container_width=True, help="Restaure la sélection séquentielle des joueurs"):
                        for d_idx in range(16):
                            st.session_state.pop(f"duo_{d_idx}_j1_{mode}{key_suffix}", None)
                            st.session_state.pop(f"duo_{d_idx}_j2_{mode}{key_suffix}", None)
                        st.rerun()

            st.markdown("###### 📋 Choix des joueurs par duo :")

            duos_selectionnes = []
            joueurs_dans_duos = []
            doublons = set()

            cols_duos = st.columns(2)
            for i in range(nb_duos_choisi):
                with cols_duos[i % 2]:
                    with st.container(border=True):
                        st.markdown(f"**🎯 Duo #{i + 1}**")
                        col_j1, col_j2 = st.columns(2)

                        def_idx1 = (i * 2) % len(tous_candidats) if tous_candidats else 0
                        def_idx2 = (i * 2 + 1) % len(tous_candidats) if len(tous_candidats) > 1 else 0

                        with col_j1:
                            st.caption("Joueur 1 :")
                            j1 = st.selectbox(
                                f"Joueur 1 (Duo {i+1}){key_suffix}",
                                options=tous_candidats,
                                index=def_idx1,
                                key=f"duo_{i}_j1_{mode}{key_suffix}",
                                label_visibility="collapsed"
                            )
                        with col_j2:
                            st.caption("Joueur 2 :")
                            j2 = st.selectbox(
                                f"Joueur 2 (Duo {i+1}){key_suffix}",
                                options=tous_candidats,
                                index=def_idx2,
                                key=f"duo_{i}_j2_{mode}{key_suffix}",
                                label_visibility="collapsed"
                            )

                        if j1 == j2:
                            st.error(f"⚠️ Un joueur ne peut pas être jumelé avec lui-même ({j1}).")
                            doublons.add(j1)
                        if j1 in joueurs_dans_duos:
                            doublons.add(j1)
                        joueurs_dans_duos.append(j1)
                        if j2 in joueurs_dans_duos:
                            doublons.add(j2)
                        joueurs_dans_duos.append(j2)

                        duo_nom = f"{j1} & {j2}"
                        st.markdown(f"🤝 **Duo #{i+1} :** `{duo_nom}`")
                        duos_selectionnes.append(duo_nom)

            participants_finaux = duos_selectionnes

            if doublons:
                doublons_str = ", ".join(sorted(list(doublons)))
                st.warning(f"⚠️ **Joueurs sélectionnés en double :** {doublons_str}. Chaque joueur ne doit figurer que dans un seul duo.")
            else:
                st.success(f"🟢 **{len(participants_finaux)} duos constitués** avec succès ({len(set(joueurs_dans_duos))} joueurs distincts prêts pour le tournoi en double).")

        st.divider()

        nb_p = len(participants_finaux)
        is_double_elim = "Double élimination" in type_format
        is_simple_elim = "Élimination directe" in type_format
        is_elim = is_simple_elim or is_double_elim
        bloquer_lancement = bool(doublons) if (mode == "double" and 'doublons' in locals()) else False
        if not est_editeur:
            bloquer_lancement = True

        promus_selectionnes = []
        if nb_p < 2:
            bloquer_lancement = True
            st.info(f"ℹ️ Sélectionnez au moins 2 {'équipes' if mode == 'double' else 'joueurs'} pour configurer le tournoi.")
        elif is_double_elim and nb_p < 4:
            bloquer_lancement = True
            st.warning("⚠️ **Double élimination :** Un minimum de **4 participants** est requis pour déployer la formule avec tableau des gagnants et tableau de repêchage (seconde chance).")
        elif is_elim:
            if is_double_elim:
                if nb_p <= 4:
                    b_pow = 4
                elif nb_p <= 8:
                    b_pow = 8
                else:
                    b_pow = 16
                nb_promus = b_pow - nb_p
                nb_m_t1 = (nb_p - nb_promus) // 2
                nb_m_t2 = b_pow // 4
            else:
                nb_promus, nb_m_t1, nb_m_t2, b_pow = calculer_structure_arbre(nb_p)

            if nb_promus > 0:
                st.markdown(
                    f"<div style='background: #eef7ff; border: 1px solid #90caf9; border-radius: 8px; padding: 12px 16px; margin: 8px 0;'>"
                    f"<strong style='color: #0b3c5d;'>🎟️ Équilibrage officiel de l'arbre ({nb_p} participants)</strong><br>"
                    f"<span style='font-size: 13px; color: #222;'>"
                    f"Pour garantir un <strong>nombre pair de matchs au second tour ({nb_m_t2} matchs)</strong>, "
                    f"<strong>{nb_promus} participant{'s' if nb_promus > 1 else ''}</strong> {'bénéficient' if nb_promus > 1 else 'bénéficie'} "
                    f"d'un passe-droit et {'sont directement promus' if nb_promus > 1 else 'est directement promu'} au 2ᵉ tour. "
                    f"Les {nb_p - nb_promus} autres participants disputeront le 1ᵉʳ tour ({nb_m_t1} match{'s' if nb_m_t1 > 1 else ''})."
                    f"</span></div>",
                    unsafe_allow_html=True
                )

                key_promus = f"liste_promus_{mode}{key_suffix}"
                cnt_add_key = f"cnt_add_promu_{mode}{key_suffix}"
                cnt_del_key = f"cnt_del_promu_{mode}{key_suffix}"

                if cnt_add_key not in st.session_state:
                    st.session_state[cnt_add_key] = 0
                if cnt_del_key not in st.session_state:
                    st.session_state[cnt_del_key] = 0

                # Initialisation de la liste des promus si non présente
                if key_promus not in st.session_state:
                    st.session_state[key_promus] = list(participants_finaux[:nb_promus])
                else:
                    # Ne conserver que les participants encore présents dans la liste finale
                    st.session_state[key_promus] = [p for p in st.session_state[key_promus] if p in participants_finaux]

                candidats = [p for p in participants_finaux if p not in st.session_state[key_promus]]
                promus = list(st.session_state[key_promus])

                placeholder_add = "➕ Choisir un participant à promouvoir..."
                placeholder_del = "➖ Choisir un promu à replacer..."

                key_add = f"sel_add_{mode}{key_suffix}_{st.session_state[cnt_add_key]}"
                key_del = f"sel_del_{mode}{key_suffix}_{st.session_state[cnt_del_key]}"

                st.markdown(f"###### 🔄 Sélection et transfert des participants promus ({len(promus)} / {nb_promus}) :")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.markdown(f"**📋 Participants à sélectionner ({len(candidats)}) :**")
                    choix_add = st.selectbox(
                        "Déplacer vers la liste des promus :",
                        options=[placeholder_add] + candidats,
                        index=0,
                        key=key_add,
                        label_visibility="collapsed",
                        help="Sélectionnez un participant dans cette liste pour le promouvoir au 2ᵉ tour (le déplace vers la liste des promus)."
                    )
                    if choix_add != placeholder_add:
                        if choix_add not in st.session_state[key_promus]:
                            st.session_state[key_promus].append(choix_add)
                        st.session_state[cnt_add_key] += 1
                        st.rerun()

                    if not candidats:
                        st.caption("ℹ️ Tous les participants sont actuellement promus.")

                with col_p2:
                    st.markdown(f"**🎟️ Participants promus au 2ᵉ tour ({len(promus)} / {nb_promus}) :**")
                    choix_del = st.selectbox(
                        "Replacer dans la liste à sélectionner :",
                        options=[placeholder_del] + promus,
                        index=0,
                        key=key_del,
                        label_visibility="collapsed",
                        help="Sélectionnez un promu dans cette liste pour le retirer et le replacer dans la liste à sélectionner."
                    )
                    if choix_del != placeholder_del:
                        if choix_del in st.session_state[key_promus]:
                            st.session_state[key_promus].remove(choix_del)
                        st.session_state[cnt_del_key] += 1
                        st.rerun()

                    if not promus:
                        st.caption("ℹ️ Aucun participant n'est encore promu.")

                col_b1, col_b2 = st.columns([1, 1])
                with col_b1:
                    if st.button("🎲 Tirage au sort des promus", key=f"btn_pige_promus_{mode}{key_suffix}", use_container_width=True, help="Tire au sort exactement le nombre requis de promus parmi les participants"):
                        st.session_state[key_promus] = random.sample(participants_finaux, min(nb_promus, len(participants_finaux)))
                        st.session_state[cnt_add_key] += 1
                        st.session_state[cnt_del_key] += 1
                        st.rerun()
                with col_b2:
                    if st.button("🔄 Réinitialiser la liste des promus", key=f"btn_reset_promus_{mode}{key_suffix}", use_container_width=True, help="Remet tous les promus dans la liste des participants à sélectionner"):
                        st.session_state[key_promus] = []
                        st.session_state[cnt_add_key] += 1
                        st.session_state[cnt_del_key] += 1
                        st.rerun()

                promus_selectionnes = list(st.session_state[key_promus])
                nb_actuel = len(promus_selectionnes)

                if nb_actuel == nb_promus:
                    p_pills = " • ".join([f"`🎟️ {p}`" for p in promus_selectionnes])
                    st.success(f"🟢 **Quota atteint ({nb_actuel}/{nb_promus}) :** {p_pills}")
                elif nb_actuel < nb_promus:
                    bloquer_lancement = True
                    p_pills = " • ".join([f"`🎟️ {p}`" for p in promus_selectionnes]) if promus_selectionnes else "*(aucun)*"
                    st.warning(f"⚠️ **Sélection incomplète :** Veuillez encore promouvoir **{nb_promus - nb_actuel} participant(s)** via la liste déroulante ci-dessus (actuellement {nb_actuel}/{nb_promus} promus : {p_pills}).")
                else:
                    bloquer_lancement = True
                    st.error(f"⚠️ **Trop de promus :** Veuillez replacer **{nb_actuel - nb_promus} participant(s)** dans la liste à sélectionner via la liste déroulante de droite ({nb_actuel}/{nb_promus}).")
            else:
                st.success(
                    f"🟢 **Effectif équilibré ({nb_p} participants) :** "
                    f"Aucun passe-droit requis. Tous les participants débuteront au 1ᵉʳ tour ({nb_m_t1} matchs) "
                    f"et le second tour comportera exactement **{nb_m_t2} matchs (nombre pair)**."
                )
        else:
            nb_matchs_tot = (nb_p * (nb_p - 1)) // 2
            st.success(f"🟢 **Championnat Round-Robin :** Les **{nb_p} participants inscrits** s'affronteront tous sans exception ({nb_matchs_tot} rencontres au total) !")

        if not est_editeur:
            st.info("🔒 *Bouton de lancement désactivé en mode consultation (prenez la main ci-dessus pour lancer le tournoi).*")

        btn_lancer = st.button(
            "🚀 Lancer le tournoi et générer le tableau officiel",
            type="primary",
            use_container_width=True,
            disabled=bloquer_lancement,
            key=f"btn_lancer_{mode}{key_suffix}",
            help="Génère l'arbre officiel des rencontres avec promotion automatique pour assurer un nombre pair de matchs au 2e tour."
        )

        if btn_lancer and est_editeur:
            # Archivage automatique si un tournoi existait déjà dans ce mode
            if tournois_data.get(mode):
                sauvegarder_tournoi_dans_historique(mode, notifier_admin=True)

            if is_double_elim:
                t_cree = generer_arbre_double_elimination(
                    participants_finaux,
                    race_prelim=2,
                    race_finale=3,
                    titre=titre_saisi,
                    heure_debut=heure_debut_str,
                    duree_min=duree_min_saisie,
                    nb_tables=nb_tables_saisi,
                    passes_droits=(promus_selectionnes if (promus_selectionnes and len(promus_selectionnes) == nb_promus) else None)
                )
            elif is_simple_elim:
                t_cree = generer_arbre_elimination(
                    participants_finaux,
                    race_prelim=2,
                    race_finale=3,
                    titre=titre_saisi,
                    heure_debut=heure_debut_str,
                    duree_min=duree_min_saisie,
                    nb_tables=nb_tables_saisi,
                    passes_droits=(promus_selectionnes if (promus_selectionnes and len(promus_selectionnes) == nb_promus) else None)
                )
            else:
                t_cree = generer_round_robin(
                    participants_finaux,
                    race_to=2,
                    titre=titre_saisi,
                    heure_debut=heure_debut_str,
                    duree_min=duree_min_saisie,
                    nb_tables=nb_tables_saisi
                )

            if t_cree:
                t_cree["mode"] = mode
                tournois_data[mode] = t_cree
                sauvegarder_tournois_data(tournois_data)
                st.session_state[f"ouvrir_arborescence_auto_{mode}"] = True
                promus_msg = t_cree.get("promus_second_tour", [])
                if promus_msg:
                    st.success(f"✅ Tournoi généré avec succès ! {len(promus_msg)} participant(s) promu(s) au 2ᵉ tour : {', '.join(promus_msg)}.")
                else:
                    st.success("✅ Tournoi officiel généré avec succès !")
                st.rerun()

def afficher_onglet_nouveau_tournoi():
    """Onglet dédié à la création d'un nouveau tournoi (Simple ou Double)."""
    my_session_id = st.session_state.get("user_session_id", "")
    est_spectateur = st.session_state.get("est_spectateur", False) or not st.session_state.get("authentifie", False)

    if est_spectateur:
        est_editeur = False
    else:
        veut_editer = not st.session_state.get("mode_consultation", False)
        est_editeur, _, _ = gerer_verrou_session(my_session_id, veut_etre_editeur=veut_editer)

    st.markdown("### ➕ Créer un nouveau tournoi officiel")
    st.caption("Configurez et lancez une nouvelle compétition officielle en Simple (1 vs 1) ou en Double / Équipes (2 vs 2).")

    if not est_editeur:
        with st.container(border=True):
            st.warning("🔒 **La création et la configuration des tournois officiels sont réservées au marqueur officiel avec la main active.**")
            col_lck1, col_lck2 = st.columns([2, 1])
            with col_lck1:
                st.info("Prenez la main ci-contre pour configurer les participants, les tables et lancer un nouveau tournoi.")
            with col_lck2:
                if not est_spectateur:
                    if st.button("⚡ Prendre la main pour créer un tournoi", key="btn_take_lock_new_t", type="primary", use_container_width=True):
                        with st.spinner("Prise de la main..."):
                            prendre_la_main_avec_rechargement(my_session_id)
                        st.rerun()
                else:
                    if st.button("🔑 Connexion éditeur / Marqueur", key="btn_login_ed_new_t", type="primary", use_container_width=True):
                        st.session_state["est_spectateur"] = False
                        st.session_state["authentifie"] = False
                        st.rerun()

    choix_type = st.radio(
        "Type de tournoi à organiser :",
        ["👤 Tournoi en Simple (1 contre 1 - Joueurs individuels)", "👥 Tournoi en Double / Équipes (2 contre 2 - Duos)"],
        horizontal=True,
        key="rad_choix_type_nouveau_tournoi"
    )

    mode_choisi = "simple" if "Simple" in choix_type else "double"

    td = charger_tournois_data()
    t_existant = td.get(mode_choisi)
    if t_existant and isinstance(t_existant, dict):
        titre_ex = t_existant.get("titre", "Tournoi en cours")
        statut_ex = t_existant.get("statut", "en_cours")
        st.warning(
            f"ℹ️ **Un tournoi {mode_choisi.capitalize()} est actuellement enregistré :** « **{titre_ex}** » ({'🟢 En cours' if statut_ex == 'en_cours' else '🏆 Terminé'}).\n\n"
            f"En lançant un nouveau tournoi, le tournoi actuel sera **automatiquement archivé dans l'historique officiel** pour conserver l'ensemble de ses données et résultats."
        )

    afficher_formulaire_creation_tournoi(mode=mode_choisi, key_suffix="_tab_creer", est_editeur=est_editeur)


def afficher_section_tournoi(mode="simple"):
    """Affiche l'interface complète de configuration ou de déroulement d'un tournoi (Simple ou Double)."""
    if f"msg_annulation_{mode}" in st.session_state:
        st.info(st.session_state.pop(f"msg_annulation_{mode}"))

    # Actualisation systématique si mise à jour du marqueur détectée
    if not (st.session_state.get("est_spectateur", False) or not st.session_state.get("authentifie", False)):
        my_sid = st.session_state.get("user_session_id", "")
        veut_ed = not st.session_state.get("mode_consultation", False)
        is_ed, _, _ = gerer_verrou_session(my_sid, veut_etre_editeur=veut_ed)
    else:
        is_ed = False

    if not is_ed and os.path.exists(TOURNOIS_FILE):
        try:
            mtime_t = os.path.getmtime(TOURNOIS_FILE)
            cle_t = "dernier_mtime_tournois_vu"
            if cle_t in st.session_state and mtime_t > st.session_state[cle_t]:
                st.session_state[cle_t] = mtime_t
                actualiser_resultats_tournoi("🔔 Le marqueur a mis à jour le tournoi ! Actualisation systématique des résultats.")
        except Exception:
            pass

    est_spectateur = st.session_state.get("est_spectateur", False) or not st.session_state.get("authentifie", False)
    if est_spectateur:
        est_editeur = False
    else:
        my_session_id = st.session_state.get("user_session_id", "")
        veut_editer = not st.session_state.get("mode_consultation", False)
        est_editeur, _, _ = gerer_verrou_session(my_session_id, veut_etre_editeur=veut_editer)

    tournois_data = charger_tournois_data()
    tournoi = tournois_data.get(mode)

    libelle_mode = "Tournoi en Simple (1 contre 1)" if mode == "simple" else "Tournoi en Double / Équipes (2 contre 2)"
    st.markdown(f"### {'👤' if mode == 'simple' else '👥'} {libelle_mode}")

    # 1. CAS OÙ AUCUN TOURNOI N'EST EN COURS : FORMULAIRE DE CRÉATION OU CONSULTATION
    if not tournoi:
        if not est_editeur:
            with st.container(border=True):
                st.markdown(f"#### 👁️ **{libelle_mode} — Mode Consultation**")
                st.info(
                    "🔒 **La création et la configuration des tournois sont réservées au marqueur officiel.**\n\n"
                    "Aucun tournoi n'est actuellement en cours. "
                    "Dès que le marqueur officiel lancera la compétition, "
                    "vous pourrez consulter ici en direct l'arborescence des rencontres, les résultats des matchs et le classement."
                )
                if not est_spectateur:
                    if st.button("⚡ Prendre la main pour créer un tournoi", key=f"btn_take_sec_{mode}", type="primary", use_container_width=True):
                        prendre_la_main_avec_rechargement(my_session_id)
                        st.rerun()
                else:
                    if st.button("🔑 Connexion éditeur", key=f"btn_login_sec_{mode}", type="primary", use_container_width=True):
                        st.session_state["est_spectateur"] = False
                        st.session_state["authentifie"] = False
                        st.rerun()
                if st.button("🔄 Vérifier si un tournoi a été lancé", key=f"btn_check_launch_{mode}", use_container_width=True, help="Vérifie si le marqueur a débuté un nouveau tournoi"):
                    st.rerun()
            return

        afficher_formulaire_creation_tournoi(mode=mode, key_suffix=f"_sec_{mode}", est_editeur=est_editeur)
        return

    # 2. CAS OÙ UN TOURNOI EST EN COURS OU TERMINÉ
    else:
        titre_t = tournoi.get("titre", "Tournoi officiel")
        format_type = tournoi.get("format", "elimination")
        race_to = tournoi.get("race_to", 2)
        statut = tournoi.get("statut", "en_cours")

        if st.session_state.pop(f"ouvrir_arborescence_auto_{mode}", False):
            modal_arborescence_tournoi(tournoi, mode_str=mode)

        html_tournoi = generer_html_tournoi(tournoi, mode=mode)
        html_t_json = json.dumps(html_tournoi)

        if est_editeur:
            col_top1, col_top2, col_top3, col_top_new, col_top4, col_top5 = st.columns([1.6, 1.0, 1.0, 1.1, 1.2, 1.2])
        else:
            col_top1, col_top2, col_top3, col_top4 = st.columns([2.1, 1.2, 1.1, 1.3])

        with col_top1:
            st.markdown(f"#### 🏆 **{titre_t}**")
            badge_statut = "🟢 **En cours**" if statut == "en_cours" else "🏆 **Tournoi Terminé**"
            if format_type == "double_elimination":
                format_nom = "Double élimination (Gagnants & Seconde chance 2 de 3 • Grande Finale 3 de 5)"
            elif format_type == "elimination":
                format_nom = "Élimination directe (Préliminaires 2 de 3 • Finale 3 de 5)"
            else:
                format_nom = "Championnat Round-Robin (2 de 3)"

            h_deb = tournoi.get("heure_debut", "09:00")
            h_fin = tournoi.get("heure_fin_estimee", "")
            nb_t = tournoi.get("nb_tables", 2)
            duree_m = tournoi.get("duree_match_min", 30)
            tables_txt = f"{nb_t} table{'s' if nb_t > 1 else ''}"
            mention_pause = " *(Pause 12h-13h)*" if (h_fin and (h_deb < "12:00" and h_fin > "12h00")) else ""
            horaire_txt = f" &nbsp;|&nbsp; ⏰ <strong>Horaire :</strong> {h_deb} à ~{h_fin}{mention_pause}" if h_fin else f" &nbsp;|&nbsp; ⏰ <strong>Début :</strong> {h_deb}"
            tables_info = f" &nbsp;|&nbsp; 🎱 <strong>{tables_txt}</strong> (~{duree_m} min/match)"

            st.caption(f"Statut : {badge_statut} &nbsp;|&nbsp; Formule : `{format_nom}`{horaire_txt}{tables_info}", unsafe_allow_html=True)
            if "dernier_envoi_tournoi_statut" in st.session_state:
                succes_env_t, msg_env_t = st.session_state.pop("dernier_envoi_tournoi_statut")
                if succes_env_t:
                    st.success("📧 Notification transmise aux administrateurs avec `historique_tournois.json` en pièce jointe !")
                else:
                    cfg_v = charger_config_email()
                    if cfg_v.get("destinataires") and cfg_v.get("smtp_expediteur"):
                        st.info(f"ℹ️ Info courriel administrateurs : {msg_env_t}")
            if not est_editeur:
                heure_actuelle_str = datetime.now().strftime("%H:%M:%S")
                st.caption(f"👁️ *Mode Consultation (Lecture seule)* &nbsp;•&nbsp; ⏱️ *Dernière actualisation : {heure_actuelle_str}*")

        with col_top2:
            if st.button("🌳 Visualiser l'arborescence", key=f"btn_visu_modal_{mode}", type="primary", use_container_width=True, help="Affiche l'arborescence complète, tous les matchs et permet l'impression"):
                modal_arborescence_tournoi(tournoi, mode_str=mode)

        with col_top3:
            st.components.v1.html(
                f"""
                <button onclick="imprimerTournoi()" style="width:100%; height:38px; background-color:#0b3c5d; color:white; border:none; border-radius:6px; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
                    🖨️ Imprimer l'arborescence (A4)
                </button>
                <script>
                function imprimerTournoi() {{
                    var win = window.open('', '_blank');
                    win.document.open();
                    win.document.write({html_t_json});
                    win.document.close();
                    win.focus();
                    win.document.title = "Feuille de Tournoi - A4";
                    setTimeout(function() {{
                        win.print();
                    }}, 350);
                }}
                </script>
                """,
                height=42
            )

        if est_editeur:
            with col_top_new:
                with st.popover("➕ Nouveau", use_container_width=True, help="Créer un nouveau tournoi (archive l'actuel)"):
                    st.markdown(f"##### ➕ Nouveau tournoi en {mode.capitalize()}")
                    st.write(f"Voulez-vous créer et lancer un nouveau {libelle_mode.lower()} ?")
                    st.caption("✅ Le tournoi actuel sera automatiquement archivé dans l'historique officiel.")
                    if st.button("🚀 Créer un nouveau tournoi", type="primary", use_container_width=True, key=f"btn_pop_new_{mode}"):
                        sauvegarder_tournoi_dans_historique(mode, notifier_admin=True)
                        tournois_data[mode] = None
                        sauvegarder_tournois_data(tournois_data)
                        st.rerun()

        if est_editeur:
            with col_top4:
                with st.popover("💾 Sauvegarder dans l'historique", use_container_width=True, help="Sauvegarder l'état actuel du tournoi dans l'historique officiel"):
                    st.markdown("### 💾 Sauvegarde dans l'historique du tournoi")
                    st.write(f"Sauvegardez l'état actuel du **{libelle_mode.lower()}** dans l'historique officiel des tournois.")
                    st.caption("✅ Le tournoi apparaîtra dans la liste déroulante des tournois sauvegardés et un courriel avec l'historique sera transmis aux administrateurs.")
                    if st.button("💾 Sauvegarder dans l'historique", type="primary", use_container_width=True, key=f"btn_arch_only_{mode}"):
                        with st.spinner("Sauvegarde dans l'historique du tournoi..."):
                            sauvegarder_tournoi_dans_historique(mode, notifier_admin=True)
                        st.success("✅ Tournoi sauvegardé avec succès dans l'historique !")
                        time.sleep(1.0)
                        st.rerun()

                    if statut == "termine":
                        st.divider()
                        st.markdown("#### 🏆 Clôture définitive")
                        st.write("Le tournoi est terminé. Vous pouvez clôturer la session pour archiver le tournoi et libérer la grille.")
                        if st.button("🏁 Clôturer & Libérer la grille", type="primary", use_container_width=True, key=f"btn_confirm_cloture_{mode}"):
                            with st.spinner("Clôture et archivage final..."):
                                sauvegarder_tournoi_dans_historique(mode, notifier_admin=True)
                                tournois_data[mode] = None
                                sauvegarder_tournois_data(tournois_data)
                            st.session_state[f"msg_annulation_{mode}"] = f"🏆 Le {libelle_mode.lower()} a été clôturé et archivé avec succès."
                            st.rerun()

            with col_top5:
                with st.popover("❌ Annulation complète", use_container_width=True, help="Annulation complète du tournoi sans aucune sauvegarde"):
                    st.markdown("### ⚠️ Annulation complète du tournoi")
                    st.warning("Voulez-vous vraiment annuler complètement le tournoi en cours ?")
                    st.write("🛑 **Dans ce cas, aucune sauvegarde ne sera effectuée** et la grille du tournoi sera immédiatement effacée.")
                    if st.button("🔴 Confirmer l'annulation", type="primary", use_container_width=True, key=f"btn_confirm_cancel_action_{mode}", help="Annule complètement le tournoi sans aucune sauvegarde"):
                        annuler_completement_tournoi(mode)
                        st.session_state[f"msg_annulation_{mode}"] = f"❌ Le {libelle_mode.lower()} a été complètement annulé (aucune sauvegarde effectuée)."
                        st.rerun()
        else:
            with col_top4:
                col_r_btn, col_r_auto = st.columns([1.6, 1.1])
                with col_r_btn:
                    if st.button("🔄 Actualiser", key=f"btn_refresh_tournoi_{mode}", type="primary", use_container_width=True, help="Recharge immédiatement les derniers scores et l'avancement du tournoi"):
                        actualiser_resultats_tournoi()
                with col_r_auto:
                    auto_refresh_actif = st.checkbox("⏱️ 30s", key=f"chk_auto_refresh_{mode}", help="Actualise automatiquement les scores du tournoi toutes les 30 secondes")

                if auto_refresh_actif:
                    st.components.v1.html(
                        f"""
                        <script>
                        setTimeout(function() {{
                            var btns = window.parent.document.querySelectorAll('button');
                            for (var i = 0; i < btns.length; i++) {{
                                if (btns[i].innerText.includes('Actualiser')) {{
                                    btns[i].click();
                                    break;
                                }}
                            }}
                        }}, 30000);
                        </script>
                        """,
                        height=0
                    )

        # Podium si terminé
        if statut == "termine" and tournoi.get("vainqueur_final"):
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #fff9c4, #fffde7); border: 2px solid #fbc02d; border-radius: 8px; padding: 14px; text-align: center;">
                        <div style="font-size: 18px; font-weight: bold; color: #f57f17; margin-bottom: 6px;">🎉 FÉLICITATIONS AU CHAMPION 🎉</div>
                        <div style="font-size: 20px; color: #0b3c5d; font-weight: bold; margin-bottom: 4px;">🥇 {tournoi['vainqueur_final']}</div>
                        <div style="font-size: 15px; color: #555;">🥈 Finaliste : <strong>{tournoi.get('finaliste', 'N/D')}</strong></div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # --- BARRE DE PROGRESSION DU TOURNOI & PROCHAINS MATCHS SUR LES TABLES ---
        tous_les_matchs_t = []
        if format_type in ["elimination", "double_elimination"]:
            for t_iter in tournoi.get("tours", []):
                for m_iter in t_iter.get("matchs", []):
                    ea_i = m_iter.get("equipe_a", "")
                    eb_i = m_iter.get("equipe_b", "")
                    if "Exempt" not in str(ea_i) and "Exempt" not in str(eb_i):
                        tous_les_matchs_t.append(m_iter)
        else:
            tous_les_matchs_t = list(tournoi.get("matchs", []))

        nb_tot_m = len(tous_les_matchs_t)
        nb_term_m = sum(1 for m_i in tous_les_matchs_t if m_i.get("termine", False))
        pct_prog = int(round((nb_term_m / nb_tot_m) * 100)) if nb_tot_m > 0 else 0

        prochains_jouables = [
            m_i for m_i in tous_les_matchs_t
            if not m_i.get("termine", False)
            and m_i.get("equipe_a") not in ["À déterminer", "Exempt (Passe-droit)", ""]
            and m_i.get("equipe_b") not in ["À déterminer", "Exempt (Passe-droit)", ""]
        ]

        with st.container(border=True):
            col_pg1, col_pg2 = st.columns([1.4, 2.6])
            with col_pg1:
                st.markdown(f"**📊 Progression du tournoi : {nb_term_m} / {nb_tot_m} matchs ({pct_prog}%)**")
                st.progress(pct_prog / 100.0 if nb_tot_m > 0 else 0.0)
                st.caption(f"🟢 {nb_term_m} terminé(s) • ⏳ {max(0, nb_tot_m - nb_term_m)} restant(s)")
            with col_pg2:
                if statut == "termine":
                    st.success("🏁 **Toutes les rencontres de ce tournoi sont terminées !**")
                elif prochains_jouables:
                    st.markdown("**🎱 En direct / Prochains matchs prêts à appeler aux tables :**")
                    nb_tables_aff = max(2, int(tournoi.get("nb_tables", 2)))
                    cartes_html = []
                    for m_p in prochains_jouables[:nb_tables_aff]:
                        mid_p = m_p.get("id", "")
                        ea_p = m_p.get("equipe_a", "")
                        eb_p = m_p.get("equipe_b", "")
                        tbl_p = m_p.get("table", "Table 1")
                        hr_p = m_p.get("heure_estimee", "")
                        hr_badge = f" • ⏰ {hr_p}" if (hr_p and hr_p != "—") else ""
                        cartes_html.append(
                            f"<div style='background:#f0f7ff; border:1px solid #90caf9; border-left:4px solid #0b3c5d; border-radius:6px; padding:6px 10px; font-size:12.5px;'>"
                            f"<strong style='color:#0b3c5d;'>🎱 {tbl_p}{hr_badge} ({mid_p}) :</strong> "
                            f"<strong>{ea_p}</strong> <span style='color:#64748b;'>vs</span> <strong>{eb_p}</strong>"
                            f"</div>"
                        )
                    st.markdown(
                        "<div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:8px;'>"
                        + "".join(cartes_html)
                        + "</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.info("⏳ En attente de la fin des rencontres précédentes pour déterminer les prochaines affiches.")

        # Arborescence graphique complète et toujours à jour (ouverte en permanence)
        st.markdown("##### 🌳 Arborescence officielle du tournoi")
        st.components.v1.html(html_tournoi, height=560, scrolling=True)

        st.divider()

        # DÉROULEMENT SELON LE FORMAT
        if format_type in ["elimination", "double_elimination"]:
            st.markdown("##### 🎯 Saisie des scores & Déroulement des rencontres")
            if tournoi.get("promus_second_tour"):
                promus_str_view = ", ".join(tournoi["promus_second_tour"])
                st.info(f"🎟️ **Participants promus d'office (Passe-droit) :** {promus_str_view}")

            def afficher_carte_rencontre(m, tour_courant, tour_num, tour_race, tour_fmt):
                m_id = m["id"]
                ea = m["equipe_a"]
                eb = m["equipe_b"]
                termine = m.get("termine", False)
                vainq = m.get("vainqueur")
                sa = m.get("score_a", 0)
                sb = m.get("score_b", 0)
                m_race = m.get("race_to", tour_race)
                m_fmt = m.get("format_label", tour_fmt)
                b_type = m.get("bracket", tour_courant.get("bracket", "winner"))

                if b_type == "loser":
                    badge_b = "<span style='background:#fff3e0; color:#e65100; border:1px solid #ffb74d; padding:2px 7px; border-radius:8px; font-size:11px; font-weight:700;'>🟧 Seconde Chance</span>"
                elif b_type == "finale":
                    badge_b = "<span style='background:#fff8e1; color:#b45309; border:1px solid #f59e0b; padding:2px 7px; border-radius:8px; font-size:11px; font-weight:700;'>🏆 Grande Finale</span>"
                elif format_type == "double_elimination":
                    badge_b = "<span style='background:#e0f2fe; color:#0369a1; border:1px solid #7dd3fc; padding:2px 7px; border-radius:8px; font-size:11px; font-weight:700;'>🟦 Gagnants</span>"
                else:
                    badge_b = ""

                m_h = m.get("heure_estimee", "")
                m_tbl = m.get("table", "Table 1")
                badge_horaire = f"<span style='background:#e8f0fe; color:#0b3c5d; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;'>⏰ {m_h} • {m_tbl}</span>" if (m_h and m_h != "—") else ""

                with st.container(border=True):
                    col_m1, col_m2 = st.columns([3, 2])
                    with col_m1:
                        if termine:
                            st.markdown(f"{badge_b} **{m_id}** : **{ea}** ({sa}) vs ({sb}) **{eb}** &nbsp; {badge_horaire}", unsafe_allow_html=True)
                            if m.get("passe_droit"):
                                st.success(f"🎟️ **Passe-droit accordé :** {vainq} est promu au tour suivant !")
                            else:
                                st.success(f"🏆 **Qualifié :** {vainq} *(score final {sa}-{sb})*")
                        else:
                            if ea == "À déterminer" or eb == "À déterminer":
                                st.markdown(f"{badge_b} **{m_id}** : `{ea}` vs `{eb}` &nbsp; {badge_horaire}", unsafe_allow_html=True)
                                st.caption("⏳ En attente des vainqueurs / perdants des tours précédents...")
                            else:
                                st.markdown(f"{badge_b} **{m_id}** : 🎯 **{ea}** vs **{eb}** &nbsp; {badge_horaire}", unsafe_allow_html=True)
                                st.caption(f"Format officiel : **{m_fmt}** (premier à {m_race} victoires)")

                    with col_m2:
                        if not termine:
                            if est_editeur:
                                col_s1, col_s2, col_s3, col_s4 = st.columns([1, 1, 1.2, 1.4])
                                with col_s1:
                                    sc_a_in = st.number_input(f"{formater_nom_abrege_joueur(ea)}", min_value=0, max_value=m_race, value=0, key=f"sc_a_{mode}_{m_id}")
                                with col_s2:
                                    sc_b_in = st.number_input(f"{formater_nom_abrege_joueur(eb)}", min_value=0, max_value=m_race, value=0, key=f"sc_b_{mode}_{m_id}")
                                with col_s3:
                                    st.write("")
                                    peut_valider = (ea != "À déterminer" and eb != "À déterminer")
                                    if st.button("✅ Valider", key=f"btn_v_{mode}_{m_id}", use_container_width=True, disabled=not peut_valider):
                                        if sc_a_in == sc_b_in:
                                            st.error("Match nul impossible.")
                                        elif sc_a_in < m_race and sc_b_in < m_race:
                                            st.warning(f"Un joueur/duo doit remporter {m_race} manches ({m_fmt}).")
                                        else:
                                            actualiser_score_elimination(tournoi, tour_num, m_id, sc_a_in, sc_b_in)
                                            sauvegarder_tournois_data(tournois_data)
                                            st.rerun()
                                with col_s4:
                                    st.write("")
                                    candidats_pd = [p for p in [ea, eb] if p and p not in ["À déterminer", "Exempt (Passe-droit)"]]
                                    if candidats_pd:
                                        with st.popover("🎟️ Passe-droit", use_container_width=True, help="Promouvoir directement un participant au tour suivant"):
                                            st.markdown(f"##### 🎟️ Accorder un passe-droit")
                                            st.caption(f"Promouvoir au tour suivant pour la rencontre **{m_id}** :")
                                            choix_promo = st.radio(
                                                "Bénéficiaire du passe-droit :",
                                                options=candidats_pd,
                                                format_func=lambda x: f"🚀 {x}",
                                                key=f"rad_pd_{mode}_{m_id}"
                                            )
                                            if st.button("🚀 Promouvoir au tour suivant", type="primary", use_container_width=True, key=f"btn_apply_pd_{mode}_{m_id}"):
                                                attribuer_passe_droit_elimination(tournoi, tour_num, m_id, choix_promo)
                                                sauvegarder_tournois_data(tournois_data)
                                                st.success(f"🎟️ Passe-droit accordé ! {choix_promo} est promu au tour suivant.")
                                                st.rerun()
                            else:
                                st.caption("⏳ *Rencontre en attente de score (saisie réservée au marqueur)*")

            tours = tournoi.get("tours", [])

            if format_type == "double_elimination":
                tours_winner = [t for t in tours if t.get("bracket") == "winner"]
                tours_loser = [t for t in tours if t.get("bracket") == "loser"]
                tours_finale = [t for t in tours if t.get("bracket") == "finale"]

                tab_w, tab_l, tab_f = st.tabs([
                    f"🟦 Tableau des Gagnants ({len(tours_winner)} tours)",
                    f"🟧 Seconde Chance — Repêchage ({len(tours_loser)} tours)",
                    "🏆 Grande Finale"
                ])

                with tab_w:
                    for tour_courant in tours_winner:
                        tour_num = tour_courant["numero"]
                        tour_race = tour_courant.get("race_to", 2)
                        tour_fmt = tour_courant.get("format_label", "2 de 3")
                        st.markdown(f"###### **{tour_courant['nom']}** — Format `{tour_fmt}` (premier à {tour_race} victoires)")
                        for m in tour_courant.get("matchs", []):
                            afficher_carte_rencontre(m, tour_courant, tour_num, tour_race, tour_fmt)

                with tab_l:
                    for tour_courant in tours_loser:
                        tour_num = tour_courant["numero"]
                        tour_race = tour_courant.get("race_to", 2)
                        tour_fmt = tour_courant.get("format_label", "2 de 3")
                        st.markdown(f"###### **{tour_courant['nom']}** — Format `{tour_fmt}` (premier à {tour_race} victoires)")
                        for m in tour_courant.get("matchs", []):
                            afficher_carte_rencontre(m, tour_courant, tour_num, tour_race, tour_fmt)

                with tab_f:
                    for tour_courant in tours_finale:
                        tour_num = tour_courant["numero"]
                        tour_race = tour_courant.get("race_to", 3)
                        tour_fmt = tour_courant.get("format_label", "3 de 5")
                        st.markdown(f"###### **{tour_courant['nom']}** — Format `{tour_fmt}` (premier à {tour_race} victoires)")
                        for m in tour_courant.get("matchs", []):
                            afficher_carte_rencontre(m, tour_courant, tour_num, tour_race, tour_fmt)

            else:
                # Elimination directe simple
                tours_onglets = [t["nom"] for t in tours]
                if tours_onglets:
                    tabs_t = st.tabs(tours_onglets)
                    for t_idx, tab_tour in enumerate(tabs_t):
                        tour_courant = tours[t_idx]
                        tour_num = tour_courant["numero"]
                        tour_race = tour_courant.get("race_to", 3 if tour_num == tournoi.get("total_tours") else 2)
                        tour_fmt = tour_courant.get("format_label", "3 de 5" if tour_race == 3 else "2 de 3")
                        with tab_tour:
                            st.markdown(f"###### **{tour_courant['nom']}** — Format `{tour_fmt}` (premier à {tour_race} manches gagnantes)")
                            for m in tour_courant.get("matchs", []):
                                afficher_carte_rencontre(m, tour_courant, tour_num, tour_race, tour_fmt)

        else:
            # FORMAT ROUND-ROBIN
            st.markdown("##### 📊 Classement en direct (Round-Robin)")
            classement_rr = calculer_classement_round_robin(tournoi)

            lignes_rr = []
            medailles_rr = {1: "🥇", 2: "🥈", 3: "🥉"}
            for rang, (part, s_data) in enumerate(classement_rr, start=1):
                badge_r = medailles_rr.get(rang, f"#{rang}")
                diff_str = f"+{s_data['diff']}" if s_data['diff'] > 0 else str(s_data['diff'])
                lignes_rr.append({
                    "Rang": badge_r,
                    "Participant": part,
                    "PJ": s_data["pj"],
                    "V": s_data["v"],
                    "D": s_data["d"],
                    "Manches Pour": s_data["pour"],
                    "Manches Contre": s_data["contre"],
                    "Différence": diff_str,
                    "Points": s_data["pts"]
                })

            df_rr = pd.DataFrame(lignes_rr)
            st.dataframe(df_rr, use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("##### 📋 Calendrier des rencontres")

            matchs_rr = tournoi.get("matchs", [])
            tous_termines = True
            for m in matchs_rr:
                m_id = m["id"]
                ea, eb = m["equipe_a"], m["equipe_b"]
                termine = m.get("termine", False)
                if not termine:
                    tous_termines = False
                sa, sb = m.get("score_a", 0), m.get("score_b", 0)

                m_h = m.get("heure_estimee", "")
                m_tbl = m.get("table", "Table 1")
                badge_horaire_rr = f"<span style='background:#e8f0fe; color:#0b3c5d; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;'>⏰ {m_h} • {m_tbl}</span>" if m_h else ""

                with st.container(border=True):
                    col_rm1, col_rm2 = st.columns([3, 2])
                    rr_race = tournoi.get("race_to", 2)
                    rr_fmt = tournoi.get("format_label", "2 de 3")
                    with col_rm1:
                        if termine:
                            st.markdown(f"**{m_id}** : **{ea}** ({sa}) vs ({sb}) **{eb}** &nbsp; {badge_horaire_rr}", unsafe_allow_html=True)
                            if m.get("passe_droit"):
                                st.success(f"🎟️ **Passe-droit accordé :** {m['vainqueur']} remporte la rencontre !")
                            else:
                                st.success(f"🏆 Vainqueur : {m['vainqueur']} *(score final {sa}-{sb})*")
                        else:
                            st.markdown(f"**{m_id}** : 🎯 **{ea}** vs **{eb}** &nbsp; {badge_horaire_rr}", unsafe_allow_html=True)
                            st.caption(f"Format officiel : **{rr_fmt}** (premier à {rr_race} victoires)")

                    with col_rm2:
                        if not termine:
                            if est_editeur:
                                col_s1, col_s2, col_s3, col_s4 = st.columns([1, 1, 1.2, 1.4])
                                with col_s1:
                                    sc_a_in = st.number_input(f"{formater_nom_abrege_joueur(ea)}", min_value=0, max_value=rr_race, value=0, key=f"rr_a_{mode}_{m_id}")
                                with col_s2:
                                    sc_b_in = st.number_input(f"{formater_nom_abrege_joueur(eb)}", min_value=0, max_value=rr_race, value=0, key=f"rr_b_{mode}_{m_id}")
                                with col_s3:
                                    st.write("")
                                    if st.button("✅ Valider", key=f"btn_rr_{mode}_{m_id}", use_container_width=True):
                                        if sc_a_in == sc_b_in:
                                            st.error("Match nul impossible.")
                                        elif sc_a_in < rr_race and sc_b_in < rr_race:
                                            st.warning(f"Un joueur/duo doit remporter {rr_race} manches ({rr_fmt}).")
                                        else:
                                            m["score_a"] = sc_a_in
                                            m["score_b"] = sc_b_in
                                            m["vainqueur"] = ea if sc_a_in > sc_b_in else eb
                                            m["termine"] = True
                                            sauvegarder_tournois_data(tournois_data)
                                            st.rerun()
                                with col_s4:
                                    st.write("")
                                    with st.popover("🎟️ Passe-droit", use_container_width=True, help="Accorder une victoire par passe-droit"):
                                        st.markdown("##### 🎟️ Victoire par passe-droit")
                                        st.caption(f"Rencontre **{m_id}** :")
                                        choix_promo_rr = st.radio(
                                            "Bénéficiaire du passe-droit :",
                                            options=[ea, eb],
                                            format_func=lambda x: f"🚀 {x}",
                                            key=f"rad_pd_rr_{mode}_{m_id}"
                                        )
                                        if st.button("🚀 Accorder la victoire", type="primary", use_container_width=True, key=f"btn_apply_pd_rr_{mode}_{m_id}"):
                                            attribuer_passe_droit_round_robin(tournoi, m_id, choix_promo_rr)
                                            sauvegarder_tournois_data(tournois_data)
                                            st.success(f"🎟️ Passe-droit accordé à {choix_promo_rr} !")
                                            st.rerun()
                            else:
                                st.caption("⏳ *Rencontre en attente de score (saisie réservée au marqueur)*")

            if tous_termines and statut != "termine" and classement_rr:
                tournoi["statut"] = "termine"
                tournoi["vainqueur_final"] = classement_rr[0][0]
                if len(classement_rr) > 1:
                    tournoi["finaliste"] = classement_rr[1][0]
                archiver_tournoi(tournoi, mode=mode)
                sauvegarder_tournois_data(tournois_data)
                st.rerun()

def afficher_section_historique_tournois():
    """Affiche la section des tournois sauvegardés avec une liste déroulante au premier plan et affichage immédiat du tournoi sélectionné."""
    est_spectateur = st.session_state.get("est_spectateur", False) or not st.session_state.get("authentifie", False)
    if est_spectateur:
        est_editeur = False
    else:
        my_session_id = st.session_state.get("user_session_id", "")
        veut_editer = not st.session_state.get("mode_consultation", False)
        est_editeur, _, _ = gerer_verrou_session(my_session_id, veut_etre_editeur=veut_editer)

    historique = charger_historique_tournois(inclure_actifs=True)

    col_h_h1, col_h_h2, col_h_h3 = st.columns([2.5, 1.1, 1.4])
    with col_h_h1:
        st.markdown("### 📜 Liste des tournois sauvegardés")
        st.caption("Sélectionnez un tournoi dans la liste déroulante ci-dessous pour afficher immédiatement son déroulement, son podium et son arborescence officielle. Accessible aux spectateurs et aux marqueurs.")
    with col_h_h2:
        if st.button("🔄 Actualiser la liste", key="btn_refresh_hist_tournois", use_container_width=True, help="Recharge la liste des tournois sauvegardés depuis le disque"):
            actualiser_resultats_tournoi()
    with col_h_h3:
        if est_editeur:
            if st.button("📧 Envoyer l'historique aux admins", key="btn_send_hist_tournois_mail", use_container_width=True, help="Transmet le fichier historique_tournois.json par courriel aux administrateurs définis dans SMTP"):
                with st.spinner("Envoi du courriel aux administrateurs..."):
                    ok_s, msg_s = envoyer_courriel_sauvegarde_tournoi(None)
                if ok_s:
                    st.success("✅ Historique envoyé aux administrateurs avec pièce jointe !")
                else:
                    st.warning(f"⚠️ {msg_s}")

    if est_editeur:
        td_active = charger_tournois_data()
        tournois_actifs_h = [m for m in ["simple", "double"] if td_active.get(m) and isinstance(td_active.get(m), dict)]
        if tournois_actifs_h:
            with st.container(border=True):
                st.markdown("##### ⚡ Marqueur officiel — Actions sur le tournoi en cours")
                for m_act in tournois_actifs_h:
                    t_act = td_active.get(m_act)
                    lbl_m = "Simple (1 vs 1)" if m_act == "simple" else "Double (2 vs 2)"
                    c_info, c_save, c_annul = st.columns([2.4, 1.4, 1.4])
                    with c_info:
                        st.write(f"🟢 **Tournoi {lbl_m} actif :** *{t_act.get('titre')}* ({t_act.get('format')})")
                    with c_save:
                        if st.button(f"💾 Sauvegarder dans l'historique", key=f"btn_top_hist_save_{m_act}", use_container_width=True, help="Sauvegarder l'état actuel dans l'historique officiel"):
                            sauvegarder_tournoi_dans_historique(m_act, notifier_admin=True)
                            st.success(f"✅ Tournoi {lbl_m} sauvegardé dans l'historique !")
                            time.sleep(0.8)
                            st.rerun()
                    with c_annul:
                        with st.popover(f"❌ Annulation complète", use_container_width=True, help="Annulation complète sans aucune sauvegarde"):
                            st.markdown("###### ⚠️ Annulation complète du tournoi")
                            st.warning(f"Voulez-vous vraiment annuler complètement le tournoi {lbl_m} ?")
                            st.write("🛑 **Dans ce cas, aucune sauvegarde ne sera effectuée.**")
                            if st.button("🔴 Confirmer l'annulation", type="primary", use_container_width=True, key=f"btn_top_hist_cancel_{m_act}"):
                                annuler_completement_tournoi(m_act)
                                st.session_state[f"msg_annulation_{m_act}"] = f"❌ Le tournoi {lbl_m} a été complètement annulé (aucune sauvegarde)."
                                st.rerun()

    if not historique:
        with st.container(border=True):
            st.info("ℹ️ Aucun tournoi sauvegardé pour le moment. Dès qu'un tournoi sera créé, sauvegardé ou terminé, il apparaîtra automatiquement dans la liste déroulante.")
        return

    # 1. LISTE DÉROULANTE DES TOURNOIS AU PREMIER PLAN
    col_f_cat, col_f_sel = st.columns([1.1, 2.9])
    with col_f_cat:
        filtre_cat = st.selectbox(
            "Catégorie :",
            ["Toutes les catégories", "👤 Simples (1 vs 1)", "👥 Doubles (2 vs 2)"],
            key="filtre_cat_hist_tournois"
        )

    liste_filtree = []
    for h in historique:
        mode_h = h.get("mode", "simple")
        if filtre_cat == "👤 Simples (1 vs 1)" and mode_h != "simple":
            continue
        if filtre_cat == "👥 Doubles (2 vs 2)" and mode_h != "double":
            continue
        liste_filtree.append(h)

    if not liste_filtree:
        st.warning("Aucun tournoi sauvegardé ne correspond à cette catégorie.")
        return

    options_select = []
    for idx, h in enumerate(liste_filtree):
        mode_icon = "👤" if h.get("mode") == "simple" else "👥"
        titre = h.get("titre", "Tournoi")
        date_c = h.get("date_creation", h.get("date_archivage", ""))
        v_fin = h.get("vainqueur_final") or ("En cours" if h.get("statut") == "en_cours" or h.get("est_actif") else "")
        champ_txt = f" • 🥇 {v_fin}" if v_fin else ""
        statut_tag = "🟢 Actif" if h.get("est_actif") else ("🏆 Terminé" if h.get("statut") == "termine" else "💾 Archivé")
        options_select.append((idx, f"{mode_icon} [{statut_tag}] {titre} — {date_c}{champ_txt}"))

    with col_f_sel:
        choix_idx = st.selectbox(
            "🏆 Choisir un tournoi dans la liste déroulante :",
            options=[idx for idx, label in options_select],
            format_func=lambda x: dict(options_select).get(x, ""),
            key="select_tournoi_detail_hist"
        )

    # 2. SUR SÉLECTION : MONTRER LE TOURNOI IMMÉDIATEMENT
    tournoi_choisi = liste_filtree[choix_idx]
    mode_choisi = tournoi_choisi.get("mode", "simple")

    with st.container(border=True):
        col_dt1, col_dt2, col_dt3, col_dt4 = st.columns([2.2, 1.1, 1.2, 0.9])
        with col_dt1:
            st.markdown(f"#### 🏆 **{tournoi_choisi.get('titre', 'Tournoi')}**")
            mode_lbl = "Simple (1 contre 1)" if mode_choisi == "simple" else "Double / Équipes (2 contre 2)"
            fmt_lbl = "Double élimination" if tournoi_choisi.get("format") == "double_elimination" else ("Élimination directe" if tournoi_choisi.get("format") == "elimination" else "Round-Robin")
            h_deb = tournoi_choisi.get("heure_debut", "09:00")
            h_fin = tournoi_choisi.get("heure_fin_estimee", "")
            nb_tab = tournoi_choisi.get("nb_tables", 2)
            horaire_info = f"&nbsp;|&nbsp; ⏰ {h_deb} à ~{h_fin}" if h_fin else f"&nbsp;|&nbsp; ⏰ Début : {h_deb}"

            statut_choisi = tournoi_choisi.get("statut", "en_cours")
            if tournoi_choisi.get("est_actif"):
                badge_st = "🟢 **Actif en cours (Sauvegardé)**"
            elif statut_choisi == "termine":
                badge_st = "🏆 **Tournoi Terminé**"
            elif statut_choisi == "annule":
                badge_st = "❌ **Tournoi Annulé**"
            else:
                badge_st = "💾 **Archivé**"

            st.caption(f"Statut : {badge_st} &nbsp;|&nbsp; Modalité : **{mode_lbl}** &nbsp;|&nbsp; Format : `{fmt_lbl}`{horaire_info} &nbsp;|&nbsp; 🎱 {nb_tab} table(s)")
            st.caption(f"Créé le : {tournoi_choisi.get('date_creation', 'N/D')} &nbsp;|&nbsp; Participants : {len(tournoi_choisi.get('participants', []))}")

        html_arch = generer_html_tournoi(tournoi_choisi, mode=mode_choisi)
        html_arch_json = json.dumps(html_arch)

        with col_dt2:
            st.components.v1.html(
                f"""
                <button onclick="imprimerTournoiArchive()" style="width:100%; height:38px; background-color:#0b3c5d; color:white; border:none; border-radius:6px; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; font-size:12px; font-weight:600; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
                    🖨️ Imprimer l'arborescence (A4)
                </button>
                <script>
                function imprimerTournoiArchive() {{
                    var win = window.open('', '_blank');
                    win.document.open();
                    win.document.write({html_arch_json});
                    win.document.close();
                    win.focus();
                    win.document.title = "Arborescence Tournoi - A4";
                    setTimeout(function() {{
                        win.print();
                    }}, 350);
                }}
                </script>
                """,
                height=42
            )

        with col_dt3:
            if est_editeur:
                if st.button("📧 Notifier admins", key=f"btn_mail_arch_{tournoi_choisi.get('id_archive', choix_idx)}", use_container_width=True, help="Envoie ce tournoi et le fichier historique_tournois.json aux administrateurs SMTP"):
                    with st.spinner("Envoi du courriel aux administrateurs..."):
                        ok_arch, msg_arch = envoyer_courriel_sauvegarde_tournoi(tournoi_choisi, mode=mode_choisi)
                    if ok_arch:
                        st.success("✅ Courriel envoyé avec succès !")
                    else:
                        st.warning(f"⚠️ {msg_arch}")

        with col_dt4:
            if est_editeur:
                if tournoi_choisi.get("est_actif"):
                    mode_c = tournoi_choisi.get("mode", "simple")
                    col_act_h1, col_act_h2 = st.columns([1, 1])
                    with col_act_h1:
                        if st.button("💾 Sauvegarder", key=f"btn_hist_save_t_{choix_idx}", use_container_width=True, help="Sauvegarder dans l'historique du tournoi"):
                            sauvegarder_tournoi_dans_historique(mode_c, notifier_admin=True)
                            st.success("✅ Sauvegardé dans l'historique !")
                            time.sleep(0.8)
                            st.rerun()
                    with col_act_h2:
                        with st.popover("❌ Annuler", use_container_width=True, help="Annulation complète du tournoi sans sauvegarde"):
                            st.markdown("###### ⚠️ Annulation complète")
                            st.write("Confirmez l'annulation complète. **Dans ce cas, aucune sauvegarde ne sera effectuée** :")
                            if st.button("🔴 Confirmer l'annulation", type="primary", use_container_width=True, key=f"btn_hist_cancel_t_{choix_idx}"):
                                annuler_completement_tournoi(mode_c)
                                st.session_state[f"msg_annulation_{mode_c}"] = f"❌ Le tournoi a été complètement annulé (aucune sauvegarde)."
                                st.rerun()
                else:
                    with st.popover("🗑️ Supprimer", use_container_width=True):
                        st.markdown("### ⚠️ Suppression définitive")
                        st.write(f"Supprimer le tournoi **{tournoi_choisi.get('titre')}** de l'historique ?")
                        st.caption("Cette action est irréversible.")
                        if st.button("🔴 Confirmer la suppression", type="primary", use_container_width=True, key=f"btn_del_arch_{tournoi_choisi.get('id_archive', choix_idx)}"):
                            supprimer_tournoi_historique(tournoi_choisi.get("id_archive"))
                            st.success("Tournoi supprimé de l'historique.")
                            st.rerun()

        # Palmarès / Podium si le vainqueur est déterminé
        if tournoi_choisi.get("vainqueur_final"):
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #fff9c4, #fffde7); border: 2px solid #fbc02d; border-radius: 8px; padding: 10px 14px; margin: 10px 0; text-align: center;">
                    <div style="font-size: 14px; font-weight: bold; color: #f57f17; margin-bottom: 2px;">🏆 PALMARÈS DU TOURNOI</div>
                    <div style="font-size: 13px; color: #222;">
                        🥇 <strong>Champion :</strong> <span style="font-size: 15px; color: #0b3c5d; font-weight: bold;">{tournoi_choisi.get('vainqueur_final')}</span>
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        🥈 <strong>Finaliste :</strong> <span style="font-size: 13px; color: #555;">{tournoi_choisi.get('finaliste', 'N/D')}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif tournoi_choisi.get("statut") == "annule":
            st.info("ℹ️ Ce tournoi a été annulé par le marqueur officiel.")

        # Arborescence graphique complète du tournoi sélectionné
        st.markdown("###### 🌳 Arborescence officielle du tournoi")
        st.components.v1.html(html_arch, height=540, scrolling=True)

    # 3. TABLEAU RÉCAPITULATIF REPLIÉ EN OPTION
    with st.expander("📋 Voir le tableau récapitulatif de tous les tournois sauvegardés", expanded=False):
        lignes_recap = []
        for h in liste_filtree:
            mode_label = "👤 Simple" if h.get("mode") == "simple" else "👥 Double"
            fmt_label = "Double élimination" if h.get("format") == "double_elimination" else ("Élimination" if h.get("format") == "elimination" else "Round-Robin")
            nb_part = len(h.get("participants", []))
            champ = h.get("vainqueur_final") or ("En cours" if h.get("statut") == "en_cours" or h.get("est_actif") else "Non déterminé")
            finaliste = h.get("finaliste") or ("En cours" if h.get("statut") == "en_cours" or h.get("est_actif") else "-")
            statut_raw = h.get("statut", "en_cours")
            if h.get("est_actif"):
                statut_label = "🟢 Actif (En cours)"
            elif statut_raw == "termine":
                statut_label = "🏆 Terminé"
            elif statut_raw == "annule":
                statut_label = "❌ Annulé"
            else:
                statut_label = "💾 Sauvegardé"

            date_aff = h.get("date_creation", h.get("date_archivage", ""))
            lignes_recap.append({
                "Date": date_aff,
                "Titre du tournoi": h.get("titre", "Tournoi officiel"),
                "Modalité": mode_label,
                "Format": fmt_label,
                "Participants": nb_part,
                "Statut": statut_label,
                "🥇 Champion": champ,
                "🥈 Finaliste": finaliste
            })
        if lignes_recap:
            df_recap = pd.DataFrame(lignes_recap)
            st.dataframe(df_recap, use_container_width=True, hide_index=True)

def afficher_onglet_tournois():
    """Onglet principal Tournois avec bandeau de verrou, prise/cession de main, Création de nouveau tournoi, Simple, Double et Historique."""
    afficher_bandeau_verrou_tournoi()

    td = charger_tournois_data()
    t_simple = td.get("simple")
    t_double = td.get("double")
    simple_actif = bool(t_simple and isinstance(t_simple, dict) and (t_simple.get("tours") or t_simple.get("matchs")))
    double_actif = bool(t_double and isinstance(t_double, dict) and (t_double.get("tours") or t_double.get("matchs")))

    lbl_simple = "👤 Tournoi Simple 🟢 (Actif)" if simple_actif else "👤 Tournoi Simple"
    lbl_double = "👥 Tournoi Double 🟢 (Actif)" if double_actif else "👥 Tournoi Double"

    # Si un tournoi est actif, son onglet est positionné en premier pour afficher immédiatement son arborescence à jour
    if double_actif and not simple_actif:
        tabs = st.tabs([
            lbl_double,
            lbl_simple,
            "➕ Créer un nouveau tournoi",
            "📜 Liste des tournois sauvegardés & Historique"
        ])
        with tabs[0]:
            afficher_section_tournoi(mode="double")
        with tabs[1]:
            afficher_section_tournoi(mode="simple")
        with tabs[2]:
            afficher_onglet_nouveau_tournoi()
        with tabs[3]:
            afficher_section_historique_tournois()

    elif simple_actif:
        tabs = st.tabs([
            lbl_simple,
            lbl_double,
            "➕ Créer un nouveau tournoi",
            "📜 Liste des tournois sauvegardés & Historique"
        ])
        with tabs[0]:
            afficher_section_tournoi(mode="simple")
        with tabs[1]:
            afficher_section_tournoi(mode="double")
        with tabs[2]:
            afficher_onglet_nouveau_tournoi()
        with tabs[3]:
            afficher_section_historique_tournois()

    else:
        # Aucun tournoi actif : affichage du formulaire de création au premier plan
        tabs = st.tabs([
            "➕ Créer un nouveau tournoi",
            lbl_simple,
            lbl_double,
            "📜 Liste des tournois sauvegardés & Historique"
        ])
        with tabs[0]:
            afficher_onglet_nouveau_tournoi()
        with tabs[1]:
            afficher_section_tournoi(mode="simple")
        with tabs[2]:
            afficher_section_tournoi(mode="double")
        with tabs[3]:
            afficher_section_historique_tournois()


# ==============================================================================
# CONTRÔLE D'ACCÈS À L'ENTRÉE (AUTHENTIFICATION MARQUEUR OU SPECTATEUR)

# ==============================================================================
# MODULE DE STATISTIQUES & PROGRESSION (ÉQUIPES ET JOUEURS)
# ==============================================================================
def calculer_statistiques_et_progression(historique):
    """
    Calcule l'ensemble des indicateurs de performance et de progression
    pour les équipes et les joueurs à partir de l'historique complet des matchs.
    """
    if not historique:
        return {}, pd.DataFrame(), {}

    stats_equipes = {}
    stats_joueurs = {}
    all_teams = set()

    for m in historique:
        rec = (m.get("receveur") or m.get("equipe_receveur") or "Receveur").strip()
        vis = (m.get("visiteur") or m.get("equipe_visiteur") or "Visiteur").strip()
        if rec:
            all_teams.add(rec)
        if vis:
            all_teams.add(vis)

    timeline_data = {t: [] for t in all_teams}
    running_totals = {t: 0 for t in all_teams}
    match_labels = []

    for idx, m in enumerate(historique, 1):
        rec = (m.get("receveur") or m.get("equipe_receveur") or "Receveur").strip()
        vis = (m.get("visiteur") or m.get("equipe_visiteur") or "Visiteur").strip()
        d_m = m.get("date_enregistrement", m.get("date", f"Match #{idx}"))
        lbl = f"M{idx}"
        match_labels.append(lbl)

        tr = m.get("total_receveur")
        tv = m.get("total_visiteur")
        if tr is None or tv is None:
            tr = sum(m.get("matchs", {}).get(str(i), {}).get("score_a", 0) for i in range(1, 10))
            tv = sum(m.get("matchs", {}).get(str(i), {}).get("score_b", 0) for i in range(1, 10))

        # Progression cumulée par match
        running_totals[rec] += tr
        running_totals[vis] += tv
        for t in all_teams:
            timeline_data[t].append(running_totals[t])

        # Initialisation équipes
        for eq in [rec, vis]:
            if eq not in stats_equipes:
                stats_equipes[eq] = {
                    "nom": eq, "pj": 0, "v": 0, "d": 0, "n": 0,
                    "pour": 0, "contre": 0, "forme": [], "matchs": []
                }

        stats_equipes[rec]["pj"] += 1
        stats_equipes[vis]["pj"] += 1
        stats_equipes[rec]["pour"] += tr
        stats_equipes[rec]["contre"] += tv
        stats_equipes[vis]["pour"] += tv
        stats_equipes[vis]["contre"] += tr

        if tr > tv:
            stats_equipes[rec]["v"] += 1
            stats_equipes[rec]["forme"].append("V")
            stats_equipes[vis]["d"] += 1
            stats_equipes[vis]["forme"].append("D")
            res_rec, res_vis = "Victoire", "Défaite"
        elif tv > tr:
            stats_equipes[vis]["v"] += 1
            stats_equipes[vis]["forme"].append("V")
            stats_equipes[rec]["d"] += 1
            stats_equipes[rec]["forme"].append("D")
            res_rec, res_vis = "Défaite", "Victoire"
        else:
            stats_equipes[rec]["n"] += 1
            stats_equipes[rec]["forme"].append("N")
            stats_equipes[vis]["n"] += 1
            stats_equipes[vis]["forme"].append("N")
            res_rec, res_vis = "Match nul", "Match nul"

        stats_equipes[rec]["matchs"].append({
            "idx": idx, "date": d_m, "role": "Receveur", "adversaire": vis,
            "pour": tr, "contre": tv, "resultat": res_rec, "diff": tr - tv
        })
        stats_equipes[vis]["matchs"].append({
            "idx": idx, "date": d_m, "role": "Visiteur", "adversaire": rec,
            "pour": tv, "contre": tr, "resultat": res_vis, "diff": tv - tr
        })

        # Traitement des 9 manches pour les joueurs
        for num_str, manche in m.get("matchs", {}).items():
            ja = (manche.get("joueur_a") or "").strip()
            jb = (manche.get("joueur_b") or "").strip()
            sa = int(manche.get("score_a", 0) or 0)
            sb = int(manche.get("score_b", 0) or 0)

            for j_nom, sc, sc_adv, adv in [(ja, sa, sb, jb), (jb, sb, sa, ja)]:
                if not j_nom:
                    continue
                if j_nom not in stats_joueurs:
                    stats_joueurs[j_nom] = {
                        "nom": j_nom, "manches": 0, "total_pts": 0, "nb_8pts": 0,
                        "matchs_joues": set(), "chronologie": [], "matchs_synthese": {}
                    }
                stats_joueurs[j_nom]["manches"] += 1
                stats_joueurs[j_nom]["total_pts"] += sc
                if sc == 8:
                    stats_joueurs[j_nom]["nb_8pts"] += 1
                stats_joueurs[j_nom]["matchs_joues"].add(idx)

                res_m = "Victoire" if sc > sc_adv else ("Défaite" if sc < sc_adv else "Nul")
                stats_joueurs[j_nom]["chronologie"].append({
                    "match_idx": idx, "date": d_m, "manche": int(num_str) if num_str.isdigit() else num_str,
                    "adversaire": adv, "score": sc, "score_adv": sc_adv, "resultat": res_m
                })

                if idx not in stats_joueurs[j_nom]["matchs_synthese"]:
                    stats_joueurs[j_nom]["matchs_synthese"][idx] = {
                        "date": d_m, "pts": 0, "manches": 0, "adversaires": []
                    }
                stats_joueurs[j_nom]["matchs_synthese"][idx]["pts"] += sc
                stats_joueurs[j_nom]["matchs_synthese"][idx]["manches"] += 1
                if adv and adv not in stats_joueurs[j_nom]["matchs_synthese"][idx]["adversaires"]:
                    stats_joueurs[j_nom]["matchs_synthese"][idx]["adversaires"].append(adv)

    # Calcul des ratios équipes
    for eq, st_e in stats_equipes.items():
        pj = st_e["pj"]
        st_e["diff"] = st_e["pour"] - st_e["contre"]
        st_e["moy_pour"] = (st_e["pour"] / pj) if pj > 0 else 0.0
        st_e["moy_contre"] = (st_e["contre"] / pj) if pj > 0 else 0.0

    df_prog_equipes = pd.DataFrame(timeline_data, index=match_labels) if match_labels else pd.DataFrame()

    # Post-traitement joueurs
    for j_nom, sj in stats_joueurs.items():
        sj["nb_matchs"] = len(sj["matchs_joues"])
        m_count = sj["manches"]
        sj["moyenne"] = (sj["total_pts"] / m_count) if m_count > 0 else 0.0
        sj["pct_8pts"] = (sj["nb_8pts"] / m_count * 100) if m_count > 0 else 0.0

        sorted_m_indices = sorted(sj["matchs_synthese"].keys())
        if len(sorted_m_indices) >= 2:
            last_m = sj["matchs_synthese"][sorted_m_indices[-1]]
            moy_last = last_m["pts"] / last_m["manches"] if last_m["manches"] > 0 else 0.0
            pts_prev = sum(sj["matchs_synthese"][k]["pts"] for k in sorted_m_indices[:-1])
            manches_prev = sum(sj["matchs_synthese"][k]["manches"] for k in sorted_m_indices[:-1])
            moy_prev = (pts_prev / manches_prev) if manches_prev > 0 else moy_last

            delta = moy_last - moy_prev
            sj["delta_dernier_match"] = delta
            if delta >= 0.25:
                sj["tendance"] = "↗️ En hausse"
            elif delta <= -0.25:
                sj["tendance"] = "↘️ En baisse"
            else:
                sj["tendance"] = "➡️ Stable"
        else:
            sj["delta_dernier_match"] = 0.0
            sj["tendance"] = "➡️ Stable"

    return stats_equipes, df_prog_equipes, stats_joueurs


def afficher_tableau_de_bord_progression(historique):
    """
    Rendu interactif complet du tableau de bord de progression
    avec sous-onglets Équipes et Joueurs.
    """
    st.markdown("### 📈 Tableau de bord — Progression & Statistiques de la Ligue")
    st.caption("Consultez les bilans complets, les graphiques d'évolution et les classements détaillés des équipes et des joueurs.")

    if not historique:
        st.info("ℹ️ Aucun match n'est encore archivé dans l'historique. Le tableau de bord et les graphiques de progression s'activeront dès l'enregistrement de votre première rencontre.")
        return

    stats_equipes, df_prog_equipes, stats_joueurs = calculer_statistiques_et_progression(historique)

    subtab_eq, subtab_jo = st.tabs([
        "🏆 Progression des Équipes",
        "👤 Progression des Joueurs"
    ])

    # =========================================================================
    # SOUS-ONGLET 1 : PROGRESSION DES ÉQUIPES
    # =========================================================================
    with subtab_eq:
        if not stats_equipes:
            st.info("ℹ️ Aucune donnée d'équipe disponible.")
        else:
            classement_equipes = sorted(
                stats_equipes.values(),
                key=lambda x: (x["v"], x["diff"], x["pour"]),
                reverse=True
            )
            leader = classement_equipes[0]
            max_attaque = max(stats_equipes.values(), key=lambda x: x["pour"])

            # 1. Cartes KPI Équipes
            k1, k2, k3 = st.columns(3)
            k1.metric("🏁 Matchs joués", f"{len(historique)} rencontres")
            k2.metric("🥇 Leader actuel", leader["nom"], f"{leader['v']}V - {leader['d']}D")
            k3.metric("🔥 Meilleure attaque", max_attaque["nom"], f"{max_attaque['pour']} pts ({max_attaque['moy_pour']:.1f}/m)")

            # Podium visuel Top 3 Équipes
            if classement_equipes:
                cartes_podium_eq = []
                classes_pod = ["saphir-podium-1", "saphir-podium-2", "saphir-podium-3"]
                ic_pod = ["🥇 1<sup>re</sup> place", "🥈 2<sup>e</sup> place", "🥉 3<sup>e</sup> place"]
                for idx_p, eq_p in enumerate(classement_equipes[:3]):
                    diff_p = f"+{eq_p['diff']}" if eq_p["diff"] > 0 else str(eq_p["diff"])
                    cartes_podium_eq.append(
                        f"<div class='saphir-podium-card {classes_pod[idx_p]}'>"
                        f"<div style='font-size:13px; font-weight:700; color:#475569; margin-bottom:4px;'>{ic_pod[idx_p]}</div>"
                        f"<div style='font-size:17px; font-weight:800; color:#0b3c5d; margin-bottom:4px;'>{eq_p['nom']}</div>"
                        f"<div style='font-size:12.5px; color:#334155;'><strong>{eq_p['v']}V - {eq_p['d']}D</strong> &nbsp;•&nbsp; {eq_p['pour']} pts (Diff {diff_p})</div>"
                        f"</div>"
                    )
                st.markdown(f"<div class='saphir-podium-grid'>{''.join(cartes_podium_eq)}</div>", unsafe_allow_html=True)

            st.markdown("---")

            # 2. Tableau de classement avec forme
            st.markdown("#### 🏆 Classement général & Forme récente")
            
            medailles = {1: "🥇", 2: "🥈", 3: "🥉"}
            lignes_tab = []
            for rang, eq_data in enumerate(classement_equipes, start=1):
                badge_rang = medailles.get(rang, f"#{rang}")

                lignes_tab.append({
                    "Rang": badge_rang,
                    "Équipe": eq_data["nom"],
                    "PJ": eq_data["pj"],
                    "V": eq_data["v"],
                    "D": eq_data["d"],
                    "Points Pour (BP)": eq_data["pour"],
                    "Moy. Pts/Match": f"{eq_data['moy_pour']:.1f}"
                })

            df_standings = pd.DataFrame(lignes_tab)
            st.dataframe(df_standings, use_container_width=True, hide_index=True)



            st.markdown("---")

            # 4. Fiche détaillée par équipe
            st.markdown("#### 🔍 Fiche détaillée & Performances par équipe")
            noms_equipes_liste = [eq["nom"] for eq in classement_equipes]
            choix_eq = st.selectbox(
                "Choisir une équipe à analyser :",
                options=noms_equipes_liste,
                key="stats_select_equipe"
            )

            if choix_eq and choix_eq in stats_equipes:
                f_eq = stats_equipes[choix_eq]
                rang_eq = next((i for i, x in enumerate(classement_equipes, 1) if x["nom"] == choix_eq), 1)

                f1, f2, f3, f4 = st.columns(4)
                f1.metric("Position au classement", f"#{rang_eq} sur {len(classement_equipes)}", f"{f_eq['v']}V - {f_eq['d']}D - {f_eq['n']}N")
                f2.metric("Points marqués", f"{f_eq['pour']} pts", f"Moyenne : {f_eq['moy_pour']:.1f} / match")
                f3.metric("Points concédés", f"{f_eq['contre']} pts", f"Moyenne : {f_eq['moy_contre']:.1f} / match")
                diff_val_str = f"+{f_eq['diff']}" if f_eq['diff'] > 0 else str(f_eq['diff'])
                f4.metric("Différentiel global", diff_val_str)

                # Graphique en barres Pour vs Contre par match
                if f_eq["matchs"]:
                    st.markdown(f"##### 📊 Points marqués vs Points concédés par rencontre ({choix_eq})")
                    labels_bar = [f"M#{m['idx']} vs {m['adversaire']}" for m in f_eq["matchs"]]
                    df_bar = pd.DataFrame({
                        "Points marqués": [m["pour"] for m in f_eq["matchs"]],
                        "Points concédés": [m["contre"] for m in f_eq["matchs"]]
                    }, index=labels_bar)
                    st.bar_chart(df_bar, height=300)

                    # Tableau chronologique des matchs de l'équipe
                    st.markdown(f"##### 📋 Liste des rencontres disputées ({choix_eq})")
                    df_eq_matchs = pd.DataFrame([
                        {
                            "Match #": f"#{m['idx']}",
                            "Date": m["date"],
                            "Rôle": m["role"],
                            "Adversaire": m["adversaire"],
                            "Score Pour": m["pour"],
                            "Score Contre": m["contre"],
                            "Diff": f"+{m['diff']}" if m['diff'] > 0 else str(m['diff']),
                            "Résultat": "🏆 Victoire" if m["resultat"] == "Victoire" else ("❌ Défaite" if m["resultat"] == "Défaite" else "🤝 Nul")
                        }
                        for m in f_eq["matchs"]
                    ])
                    st.dataframe(df_eq_matchs, use_container_width=True, hide_index=True)

    # =========================================================================
    # SOUS-ONGLET 2 : PROGRESSION DES JOUEURS
    # =========================================================================
    with subtab_jo:
        if not stats_joueurs:
            st.info("ℹ️ Aucune donnée de joueur disponible.")
        else:
            classement_joueurs = sorted(
                stats_joueurs.values(),
                key=lambda x: (x["moyenne"], x["total_pts"], x["nb_8pts"]),
                reverse=True
            )

            # Cartes KPI
            top_moyenne = classement_joueurs[0]
            top_pts = max(stats_joueurs.values(), key=lambda x: x["total_pts"])
            top_8pts = max(stats_joueurs.values(), key=lambda x: x["nb_8pts"])
            total_manches_ligue = sum(x["manches"] for x in stats_joueurs.values()) // 2

            jk1, jk2, jk3, jk4 = st.columns(4)
            jk1.metric("🎯 Meilleure moyenne", top_moyenne["nom"], f"{top_moyenne['moyenne']:.2f} / 8.00")
            jk2.metric("👑 Meilleur marqueur", top_pts["nom"], f"{top_pts['total_pts']} pts cumulés")
            jk3.metric("🎯 Spécialiste 8 pts", top_8pts["nom"], f"{top_8pts['nb_8pts']} manches gagnées à 8")
            jk4.metric("🎱 Manches disputées", f"{total_manches_ligue} manches", f"{len(stats_joueurs)} joueurs actifs")

            # Podium visuel Top 3 Joueurs
            if classement_joueurs:
                cartes_podium_jo = []
                classes_pod = ["saphir-podium-1", "saphir-podium-2", "saphir-podium-3"]
                ic_pod = ["🥇 1<sup>er</sup> joueur", "🥈 2<sup>e</sup> joueur", "🥉 3<sup>e</sup> joueur"]
                for idx_p, jo_p in enumerate(classement_joueurs[:3]):
                    cartes_podium_jo.append(
                        f"<div class='saphir-podium-card {classes_pod[idx_p]}'>"
                        f"<div style='font-size:13px; font-weight:700; color:#475569; margin-bottom:4px;'>{ic_pod[idx_p]}</div>"
                        f"<div style='font-size:17px; font-weight:800; color:#0b3c5d; margin-bottom:4px;'>{jo_p['nom']}</div>"
                        f"<div style='font-size:12.5px; color:#334155;'><strong>Moy. {jo_p['moyenne']:.2f}/8</strong> &nbsp;•&nbsp; {jo_p['total_pts']} pts ({jo_p['nb_8pts']}x 8pts)</div>"
                        f"</div>"
                    )
                st.markdown(f"<div class='saphir-podium-grid'>{''.join(cartes_podium_jo)}</div>", unsafe_allow_html=True)

            st.markdown("---")

            # Leaderboard complet
            st.markdown("#### 🥇 Tableau des meneurs individuels (Leaderboard)")
            st.caption("Classement établi selon la moyenne de points par manche disputée, le total de points et le nombre de manches parfaites à 8 points.")

            lignes_lead = []
            medailles_j = {1: "🥇", 2: "🥈", 3: "🥉"}
            for rang, j_data in enumerate(classement_joueurs, start=1):
                badge_rang = medailles_j.get(rang, f"#{rang}")
                lignes_lead.append({
                    "Rang": badge_rang,
                    "Joueur": j_data["nom"],
                    "Matchs": j_data["nb_matchs"],
                    "Manches": j_data["manches"],
                    "Total Points": j_data["total_pts"],
                    "Moyenne / 8": f"{j_data['moyenne']:.2f}",
                    "Manches à 8 pts 🎯": j_data["nb_8pts"],
                    "% Victoires à 8": f"{j_data['pct_8pts']:.1f}%",
                    "Tendance récente": j_data["tendance"]
                })

            df_lead = pd.DataFrame(lignes_lead)
            st.dataframe(df_lead, use_container_width=True, hide_index=True)

            st.markdown("---")

            # Fiche individuelle et progression
            st.markdown("#### 🔍 Fiche individuelle & Évolution d'un joueur")
            noms_joueurs_liste = [j["nom"] for j in classement_joueurs]
            choix_j = st.selectbox(
                "Sélectionner un joueur pour afficher son analyse complète :",
                options=noms_joueurs_liste,
                key="stats_select_joueur"
            )

            if choix_j and choix_j in stats_joueurs:
                fj = stats_joueurs[choix_j]
                rang_j = next((i for i, x in enumerate(classement_joueurs, 1) if x["nom"] == choix_j), 1)

                p1, p2, p3, p4 = st.columns(4)
                delta_str = f"{fj['delta_dernier_match']:+.2f} vs matchs préc." if fj['delta_dernier_match'] != 0 else "Stable"
                p1.metric(
                    "Moyenne par manche",
                    f"{fj['moyenne']:.2f} / 8.00",
                    delta=delta_str,
                    help="Moyenne de points marqués sur 8 points possibles par manche"
                )
                p2.metric(
                    "Total des points",
                    f"{fj['total_pts']} pts",
                    f"#{rang_j} au classement général"
                )
                p3.metric(
                    "Victoires à 8 pts (🎯)",
                    f"{fj['nb_8pts']} manches",
                    f"{fj['pct_8pts']:.1f}% de réussite"
                )
                p4.metric(
                    "Assiduité",
                    f"{fj['nb_matchs']} matchs joués",
                    f"{fj['manches']} manches au total"
                )

                # Graphique de pointage et moyenne du joueur par match (Bar chart fixe 0 à 24)
                if fj["matchs_synthese"]:
                    st.markdown(f"##### 📊 Pointage et moyenne match par match ({choix_j}) — Échelle fixe 0 à 24")
                    indices_m = sorted(fj["matchs_synthese"].keys())

                    rows_chart = []
                    for im in indices_m:
                        sm = fj["matchs_synthese"][im]
                        pts_m = sm["pts"]
                        man_m = sm["manches"]
                        moy_m = round(pts_m / man_m, 2) if man_m > 0 else 0.0

                        d_raw = str(sm.get("date", f"Match #{im}"))
                        d_clean = d_raw.split()[0] if " " in d_raw else d_raw
                        parts_d = d_clean.split("-")
                        if len(parts_d) == 3 and len(parts_d[0]) == 4:
                            d_clean = f"{parts_d[2]}/{parts_d[1]}/{parts_d[0]}"

                        label_m = f"M#{im} • {d_clean} ({pts_m} pts)"
                        advs_str = ", ".join(sm.get("adversaires", [])) or "Adversaires"

                        rows_chart.append({
                            "Match": label_m,
                            "Pointage": pts_m,
                            "Date": d_clean,
                            "Moyenne": f"{moy_m:.2f} / 8.00",
                            "Adversaires": advs_str
                        })

                    df_chart_j = pd.DataFrame(rows_chart)

                    try:
                        import altair as alt
                        bars = alt.Chart(df_chart_j).mark_bar(
                            color="#0b3c5d",
                            cornerRadiusTopLeft=5,
                            cornerRadiusTopRight=5
                        ).encode(
                            x=alt.X("Match:N", sort=None, title="Rencontre, Date & Pointage", axis=alt.Axis(labelAngle=-25)),
                            y=alt.Y("Pointage:Q", scale=alt.Scale(domain=[0, 24]), title="Pointage du match (Fixe de 0 à 24 pts)"),
                            tooltip=[
                                alt.Tooltip("Match:N", title="Rencontre"),
                                alt.Tooltip("Date:N", title="Date du match"),
                                alt.Tooltip("Pointage:Q", title="Pointage (/24 pts)"),
                                alt.Tooltip("Moyenne:N", title="Moyenne par manche (/8)"),
                                alt.Tooltip("Adversaires:N", title="Adversaires affrontés")
                            ]
                        )
                        text_labels = bars.mark_text(
                            align="center",
                            baseline="bottom",
                            dy=-5,
                            fontSize=12,
                            fontWeight="bold",
                            color="#0b3c5d"
                        ).encode(
                            text="Pointage:Q"
                        )
                        chart_final = (bars + text_labels).properties(height=340)
                        st.altair_chart(chart_final, use_container_width=True)
                    except Exception:
                        df_fallback = pd.DataFrame({
                            "Pointage du match (/24)": [r["Pointage"] for r in rows_chart]
                        }, index=[r["Match"] for r in rows_chart])
                        st.bar_chart(df_fallback, height=320)

                # Historique détaillé de toutes ses manches
                if fj["chronologie"]:
                    st.markdown(f"##### 📜 Historique détaillé de chaque manche disputée ({choix_j})")
                    df_chron_j = pd.DataFrame([
                        {
                            "Match #": f"#{c['match_idx']}",
                            "Date": c["date"],
                            "Manche": f"M{c['manche']}",
                            "Adversaire": c["adversaire"] if c["adversaire"] else "Adversaire",
                            "Score Joueur": c["score"],
                            "Score Adversaire": c["score_adv"],
                            "Résultat": "🏆 Victoire" if c["resultat"] == "Victoire" else ("❌ Défaite" if c["resultat"] == "Défaite" else "🤝 Nul")
                        }
                        for c in fj["chronologie"]
                    ])
                    st.dataframe(df_chron_j, use_container_width=True, hide_index=True)


# ==============================================================================
# Injection des balises d'icône pour écran d'accueil mobile et tablette (iOS & Android)
injecter_meta_icones_mobiles()
injecter_theme_css_saphir()
# Remontée forcée en haut de page désactivée

est_connecte = st.session_state.get("authentifie", False)
est_spectateur = st.session_state.get("est_spectateur", False)

if not est_connecte and not est_spectateur:
    col_l1, col_l2, col_l3 = st.columns([1, 1.4, 1])
    with col_l2:
        b64_logo_login = charger_armoiries_base64((220, 220))
        arm_p = find_armoiries_path()
        if b64_logo_login:
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 8px;">
                    <img src="{b64_logo_login}" alt="Armoiries Ligue de billard Boule en main" style="width: 130px; height: 130px; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.18));">
                </div>
                """,
                unsafe_allow_html=True
            )
        elif os.path.isfile(arm_p):
            col_img1, col_img2, col_img3 = st.columns([1, 1, 1])
            with col_img2:
                st.image(arm_p, width=130)

        st.markdown("<div style='text-align: center; margin-top: 5px;'>", unsafe_allow_html=True)
        st.title("🎱 Ligue de billard Boule en main")
        st.subheader("Accès à la feuille de match et aux résultats")
        st.markdown("Veuillez choisir votre mode d'accès ci-dessous.")
        st.markdown("</div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### 🔒 Accès Marqueur / Éditeur")
            st.caption("Permet la saisie des manches, la validation officielle et l'administration.")
            with st.form("form_login_marqueur", clear_on_submit=False):
                mdp_saisi = st.text_input("Mot de passe", type="password", key="login_pass_input", placeholder="Entrez le mot de passe...")
                bouton_login = st.form_submit_button("🔓 Se connecter pour saisir", type="primary", use_container_width=True)
                if bouton_login:
                    if verifier_mot_de_passe_admin(mdp_saisi):
                        st.session_state["authentifie"] = True
                        st.session_state["est_spectateur"] = False
                        st.session_state["mode_consultation"] = False
                        st.rerun()
                    else:
                        st.error("❌ Mot de passe incorrect.")
            st.caption("💡 *Mot de passe par défaut : `saphir2026`*")

        st.markdown("<div style='text-align:center; font-weight:bold; margin: 16px 0;'>OU</div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### 👁️ Accès Spectateur")
            st.caption("Consultez en direct les résultats du match en cours en mode lecture seule (aucun mot de passe requis).")
            if st.button("👁️ Entrer en tant que spectateur", use_container_width=True):
                st.session_state["est_spectateur"] = True
                st.session_state["authentifie"] = False
                st.session_state["mode_consultation"] = True
                st.rerun()
    st.stop()

# ==============================================================================
# IDENTIFICATION DE SESSION & GESTION DU VERROU
# ==============================================================================
if "user_session_id" not in st.session_state:
    st.session_state["user_session_id"] = str(uuid.uuid4())
my_session_id = st.session_state["user_session_id"]

est_spectateur = st.session_state.get("est_spectateur", False)

if est_spectateur:
    st.session_state["mode_consultation"] = True
    est_editeur = False
    temps_restant_verrou = 0
    autre_editeur_actif = False
else:
    if "mode_consultation" not in st.session_state:
        st.session_state["mode_consultation"] = False

    est_editeur, temps_restant_verrou, autre_editeur_actif = gerer_verrou_session(
        my_session_id,
        veut_etre_editeur=not st.session_state["mode_consultation"]
    )

# ==============================================================================
# RESTAURATION INITIALE AU CHARGEMENT (ÉVITE LA PERTE DE DONNÉES SUR RAFRAÎCHISSEMENT)
# ==============================================================================
sauvegarde_existante = charger_sauvegarde()
demande_rechargement = st.session_state.pop("forcer_rechargement", False)

if demande_rechargement or ("app_initialisee" not in st.session_state) or (not est_editeur):
    st.session_state.app_initialisee = True
    if sauvegarde_existante and "matchs" in sauvegarde_existante:
        try:
            restaurer_session(sauvegarde_existante)
        except Exception:
            pass

# Chargement de la configuration email au démarrage
config_email = charger_config_email()

# Chargement du fichier équipes CSV
equipes_disponibles = charger_equipes_csv()
noms_equipes = list(equipes_disponibles.keys())

# --- ENTÊTE DU SITE WEB DE RÉFÉRENCE ---
b64_logo_header = charger_armoiries_base64((140, 140))
if b64_logo_header:
    col_hd_logo, col_hd_txt = st.columns([0.10, 0.90])
    with col_hd_logo:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: center; padding-top: 10px;">
                <img src="{b64_logo_header}" alt="Armoiries" style="width: 75px; height: 75px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.12));">
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_hd_txt:
        st.title("🎱 Ligue de billard Boule en main")
        st.subheader("Application de saisie des résultats - Format 3 contre 3")
        st.markdown("*Plateforme officielle de gestion des matchs, de la cédule et des présences.*")
else:
    st.title("🎱 Ligue de billard Boule en main")
    st.subheader("Application de saisie des résultats - Format 3 contre 3")
    st.markdown("*Plateforme officielle de gestion des matchs, de la cédule et des présences.*")

if "message_validation_reussie" in st.session_state:
    st.success(st.session_state.pop("message_validation_reussie"))


# ==============================================================================
# NAVIGATION PRINCIPALE PAR ONGLETS (FEUILLE DE MATCH vs STATISTIQUES vs TOURNOIS vs ADMINISTRATION)
# ==============================================================================
historique_matchs = charger_historique_matchs()

if not est_spectateur:
    tab_feuille, tab_stats, tab_tournoi, tab_admin = st.tabs([
        "🎱 Feuille de match & Consultation",
        "📈 Statistiques & Progression",
        "🏆 Tournois",
        "⚙️ Administration"
    ])
else:
    tab_feuille, tab_stats, tab_tournoi = st.tabs([
        "🎱 Feuille de match & Consultation",
        "📈 Statistiques & Progression",
        "🏆 Tournois"
    ])
    tab_admin = None

with tab_feuille:
    # --- BANDEAU D'ÉTAT DU VERROU EXCLUSIF (UN SEUL MARQUEUR À LA FOIS) ---
    col_lock1, col_lock2 = st.columns([3, 1])
    if est_editeur:
        col_lock1.success("🟢 **Vous avez la main exclusive pour la saisie et la validation du match.**")
        with col_lock2:
            if st.button("🔓 Céder la main", use_container_width=True, help="Sauvegarde automatiquement le tournoi et le match sur le disque avant de libérer la main"):
                with st.spinner("Sauvegarde et libération de la main..."):
                    ceder_la_main_avec_sauvegarde(my_session_id)
                st.rerun()
    elif est_spectateur:
        col_lock1.info("👁️ **Mode spectateur (Lecture seule) :** Vous consultez le match en direct. La saisie et l'administration sont désactivées.")
        with col_lock2:
            st.button("⚡ Prendre la main", use_container_width=True, disabled=True, help="Le bouton Prendre la main est désactivé en mode spectateur (mot de passe requis)")
            if st.button("🔑 Connexion éditeur", use_container_width=True, help="Se connecter avec mot de passe pour éditer ou administrer"):
                st.session_state["est_spectateur"] = False
                st.session_state["authentifie"] = False
                st.rerun()
    else:
        if autre_editeur_actif:
            mins = temps_restant_verrou // 60
            secs = temps_restant_verrou % 60
            col_lock1.warning(f"🔒 **Mode consultation (Lecture seule) :** Un autre utilisateur effectue actuellement la saisie. Vos champs sont verrouillés pour éviter les conflits. *(Inactivité restante : {mins}m {secs:02d}s)*")
        else:
            col_lock1.info("🔒 **Mode consultation (Lecture seule) :** Vous êtes en mode lecture. La feuille est disponible pour être saisie.")

        with col_lock2:
            if st.button("⚡ Prendre la main", use_container_width=True, help="Prend le contrôle de la saisie, charge les sauvegardes du tournoi et du match depuis le disque et active l'édition"):
                with st.spinner("Prise de la main et rechargement des sauvegardes..."):
                    prendre_la_main_avec_rechargement(my_session_id)
                st.rerun()

    # --- BOUTONS D'ACTION HAUT DE PAGE (RESTAURER / ANNULER EFFACEMENT / NOUVEAU MATCH) ---
    a_corbeille = os.path.exists(CORBEILLE_FILE)
    date_sauv_str = sauvegarde_existante.get("date", "")

    if not est_spectateur:
        if a_corbeille:
            col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1.2, 1.5, 1.2])
        else:
            col_h1, col_h2, col_h4 = st.columns([2, 1.2, 1.2])

        if date_sauv_str:
            col_h1.caption(f"💾 *Dernière sauvegarde automatique : {date_sauv_str}*")

        with col_h2:
            with st.popover(
                "🔄 Restaurer saisie", 
                use_container_width=True, 
                disabled=not est_editeur, 
                help="✅ Sauvegarde automatique active.\nEn cas de coupure, cliquez sur 'Restaurer' pour récupérer votre saisie."
            ):
                st.markdown("### 🔄 Restauration")
                st.write("Voulez-vous restaurer les données de la dernière sauvegarde automatique ?")
                if date_sauv_str:
                    st.caption(f"💾 *Dernière sauvegarde : {date_sauv_str}*")
                st.caption("⚠️ *Les champs actuels seront remplacés par l'état enregistré.*")
                if st.button("🔵 Confirmer la restauration", type="primary", use_container_width=True):
                    data_a_restaurer = charger_sauvegarde()
                    if data_a_restaurer and "matchs" in data_a_restaurer:
                        restaurer_session(data_a_restaurer)
                        st.success("✅ Données récupérées avec succès !")
                        st.rerun()
                    else:
                        st.warning("⚠️ Aucune sauvegarde valide trouvée.")
    
        if a_corbeille:
            with col_h3:
                if st.button("↩️ Annuler effacement", use_container_width=True, disabled=not est_editeur, help="Restaure le match qui vient d'être effacé par 'Nouveau match'"):
                    try:
                        with open(CORBEILLE_FILE, "r", encoding="utf-8") as f:
                            data_annulee = json.load(f)
                        if data_annulee and "matchs" in data_annulee:
                            restaurer_session(data_annulee)
                            sauvegarder_donnees(data_annulee)
                            try:
                                os.remove(CORBEILLE_FILE)
                            except Exception:
                                pass
                            st.success("✅ Match précédent restauré avec succès !")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la récupération : {e}")
    
        with col_h4:
            with st.popover("🗑️ Nouveau match", use_container_width=True, disabled=not est_editeur):
                st.markdown("### ⚠️ Réinitialisation")
                st.write("Voulez-vous vraiment effacer la saisie du match en cours ?")
                st.caption("💡 *Une copie de secours est automatiquement conservée. Vous pourrez annuler en cas d'erreur.*")
                if st.button("🔴 Confirmer et tout effacer", type="primary", use_container_width=True):
                    # 1. Sauvegarder dans la corbeille avant d'effacer
                    if os.path.exists(BACKUP_FILE):
                        try:
                            import shutil
                            shutil.copyfile(BACKUP_FILE, CORBEILLE_FILE)
                        except Exception:
                            pass
                    elif "sauvegarde_existante" in locals() and sauvegarde_existante:
                        try:
                            with open(CORBEILLE_FILE, "w", encoding="utf-8") as f:
                                json.dump(sauvegarde_existante, f, ensure_ascii=False, indent=4)
                        except Exception:
                            pass
    
                    # 2. Supprimer la sauvegarde active
                    if os.path.exists(BACKUP_FILE):
                        try:
                            os.remove(BACKUP_FILE)
                        except Exception:
                            pass
    
                    # 3. Conserver l'authentification, l'identifiant de session et l'état de consultation
                    auth_ok = st.session_state.get("authentifie", False)
                    spec_ok = st.session_state.get("est_spectateur", False)
                    user_sess = st.session_state.get("user_session_id")
                    mode_c = st.session_state.get("mode_consultation", False)
                    st.session_state.clear()
                    st.session_state["authentifie"] = auth_ok
                    st.session_state["est_spectateur"] = spec_ok
                    if user_sess:
                        st.session_state["user_session_id"] = user_sess
                    st.session_state["mode_consultation"] = mode_c
                    st.session_state["app_initialisee"] = True
                    st.session_state["match_en_cours_deja_valide"] = False
    
                    # 4. Remise à zéro explicite de toutes les manches (0 - 0)
                    for num in range(1, 10):
                        st.session_state[f"s_a_{num}"] = 0
                        st.session_state[f"s_b_{num}"] = 0
    
                    # 5. Réinitialisation des présences (tous présents), moyennes et scores par défaut
                    for p_id in ["j1_rec", "j2_rec", "j3_rec", "j1_vis", "j2_vis", "j3_vis"]:
                        st.session_state[f"pres_{p_id}"] = True
                        st.session_state[f"pts_{p_id}"] = 0
                        st.session_state[f"moy_{p_id}"] = 0.625
                        st.session_state[f"prev_state_{p_id}"] = True
                        st.session_state[f"prev_pts_{p_id}"] = 0
                        st.session_state[f"cust_{p_id}"] = ""
    
                    # 6. Réinitialisation des noms personnalisés
                    st.session_state["input_custom_rec"] = "Équipe 1"
                    st.session_state["input_custom_vis"] = "Équipe 2"
    
                    st.rerun()
    
        if a_corbeille:
            st.info("ℹ️ Un match en cours a été effacé récemment. Si c'était une erreur, cliquez sur **« ↩️ Annuler effacement »** ci-dessus pour le récupérer.")

        st.divider()
    else:
        if date_sauv_str:
            st.caption(f"💾 *Dernière mise à jour du marqueur : {date_sauv_str}*")
        st.divider()

    # --- BARRE LATÉRALE : SÉLECTION DU MATCH ET JOUEURS ---
    st.sidebar.header("📋 Paramètres du Match")
    if st.sidebar.button("🚪 Déconnexion / Accueil", use_container_width=True, help="Sauvegarde les tournois et le match, libère la main et retourne à l'écran d'accueil"):
        ceder_la_main_avec_sauvegarde(my_session_id)
        st.session_state["authentifie"] = False
        st.session_state["est_spectateur"] = False
        st.session_state["mode_consultation"] = False
        st.rerun()

    with st.sidebar.container(border=True):
        st.markdown("#### 🔵 Équipe Receveuse (🏠)")
        if noms_equipes:
            options_rec = noms_equipes + ["Autre / Personnalisée"]
            if "sel_equipe_rec" in st.session_state and st.session_state["sel_equipe_rec"] not in options_rec:
                st.session_state["sel_equipe_rec"] = options_rec[0]
            def_idx_rec = 0
            if "sel_equipe_rec" in st.session_state and st.session_state["sel_equipe_rec"] in options_rec:
                def_idx_rec = options_rec.index(st.session_state["sel_equipe_rec"])
            choix_rec = st.selectbox("Équipe Receveuse :", options_rec, index=def_idx_rec, key="sel_equipe_rec", disabled=not est_editeur)

            if choix_rec == "Autre / Personnalisée":
                equipe_receveur = st.text_input("Nom équipe receveuse", value=st.session_state.get("input_custom_rec", "Équipe 1"), key="input_custom_rec", disabled=not est_editeur)
                roster_rec = ["Joueur 1", "Joueur 2", "Joueur 3"]
            else:
                equipe_receveur = choix_rec
                roster_rec = equipes_disponibles[choix_rec]
        else:
            equipe_receveur = st.text_input("Équipe Receveuse", value="Équipe 1", key="input_custom_rec", disabled=not est_editeur)
            roster_rec = ["Jean-François", "Christian", "Antoine"]
            choix_rec = equipe_receveur

        st.markdown(f"**👥 Alignement — {equipe_receveur}**")

        # Options sécurisées pour Joueur 1
        options_j1_rec = list(roster_rec) + ["Remplaçant..."]
        if "sel_j1_rec" in st.session_state and st.session_state["sel_j1_rec"] not in options_j1_rec:
            st.session_state["sel_j1_rec"] = options_j1_rec[0]

        def_idx_j1_rec = 0
        if "sel_j1_rec" in st.session_state and st.session_state["sel_j1_rec"] in options_j1_rec:
            def_idx_j1_rec = options_j1_rec.index(st.session_state["sel_j1_rec"])

        col_j1_r1, col_j1_r2 = st.columns([3, 2])
        sel_j1_rec = col_j1_r1.selectbox("Sélection Joueur 1 :", options_j1_rec, index=def_idx_j1_rec, key="sel_j1_rec", disabled=not est_editeur)
        if sel_j1_rec == "Remplaçant...":
            j1_rec = st.text_input("Nom Joueur 1 (Remplaçant)", value=st.session_state.get("cust_j1_rec", "Remplaçant 1"), key="cust_j1_rec", disabled=not est_editeur)
        else:
            j1_rec = sel_j1_rec
        j1_rec_pres = col_j1_r2.toggle("Présent", value=st.session_state.get("pres_j1_rec", True), key="pres_j1_rec", disabled=not est_editeur)
        if not j1_rec_pres:
            def_moy_j1 = float(st.session_state.get("moy_j1_rec", 0.625))
            col_m1, col_m2 = st.columns([3, 2])
            moy_j1 = col_m1.number_input(
                f"Moyenne de {j1_rec} :",
                min_value=0.0,
                max_value=100.0,
                value=def_moy_j1,
                step=0.025,
                format="%.3f",
                key="moy_j1_rec",
                disabled=not est_editeur,
                help="Saisissez la moyenne (ex. 0.650 ou 65%). Formule : arrondi(moyenne × 24 ÷ 3), max 7."
            )
            j1_rec_pts = calculer_score_absent(moy_j1)
            st.session_state["pts_j1_rec"] = j1_rec_pts
            col_m2.metric("Score", f"{j1_rec_pts} pts")
            st.caption(f"📊 *Score calculé : {j1_rec_pts} pts/manche (max 7)*")
        else:
            j1_rec_pts = int(st.session_state.get("pts_j1_rec", 0))

        # Options sécurisées pour Joueur 2
        options_j2_rec = [p for p in roster_rec if p != sel_j1_rec] + ["Remplaçant..."]
        if "sel_j2_rec" in st.session_state and st.session_state["sel_j2_rec"] not in options_j2_rec:
            st.session_state["sel_j2_rec"] = options_j2_rec[0]

        def_idx_j2_rec = 0
        if "sel_j2_rec" in st.session_state and st.session_state["sel_j2_rec"] in options_j2_rec:
            def_idx_j2_rec = options_j2_rec.index(st.session_state["sel_j2_rec"])

        col_j2_r1, col_j2_r2 = st.columns([3, 2])
        sel_j2_rec = col_j2_r1.selectbox("Sélection Joueur 2 :", options_j2_rec, index=def_idx_j2_rec, key="sel_j2_rec", disabled=not est_editeur)
        if sel_j2_rec == "Remplaçant...":
            j2_rec = st.text_input("Nom Joueur 2 (Remplaçant)", value=st.session_state.get("cust_j2_rec", "Remplaçant 2"), key="cust_j2_rec", disabled=not est_editeur)
        else:
            j2_rec = sel_j2_rec
        j2_rec_pres = col_j2_r2.toggle("Présent", value=st.session_state.get("pres_j2_rec", True), key="pres_j2_rec", disabled=not est_editeur)
        if not j2_rec_pres:
            def_moy_j2 = float(st.session_state.get("moy_j2_rec", 0.625))
            col_m1, col_m2 = st.columns([3, 2])
            moy_j2 = col_m1.number_input(
                f"Moyenne de {j2_rec} :",
                min_value=0.0,
                max_value=100.0,
                value=def_moy_j2,
                step=0.025,
                format="%.3f",
                key="moy_j2_rec",
                disabled=not est_editeur,
                help="Saisissez la moyenne (ex. 0.650 ou 65%). Formule : arrondi(moyenne × 24 ÷ 3), max 7."
            )
            j2_rec_pts = calculer_score_absent(moy_j2)
            st.session_state["pts_j2_rec"] = j2_rec_pts
            col_m2.metric("Score", f"{j2_rec_pts} pts")
            st.caption(f"📊 *Score calculé : {j2_rec_pts} pts/manche (max 7)*")
        else:
            j2_rec_pts = int(st.session_state.get("pts_j2_rec", 0))

        # Joueur 3 (Évident / Déduit automatiquement)
        col_j3_r1, col_j3_r2 = st.columns([3, 2])
        restants_rec = [p for p in roster_rec if p != sel_j1_rec and p != sel_j2_rec]
        j3_rec = restants_rec[0] if restants_rec else "Joueur 3"
        col_j3_r1.markdown(f"**Joueur 3 (défini) :**<br>`{j3_rec}`", unsafe_allow_html=True)
        j3_rec_pres = col_j3_r2.toggle("Présent", value=st.session_state.get("pres_j3_rec", True), key="pres_j3_rec", disabled=not est_editeur)
        if not j3_rec_pres:
            def_moy_j3 = float(st.session_state.get("moy_j3_rec", 0.625))
            col_m1, col_m2 = st.columns([3, 2])
            moy_j3 = col_m1.number_input(
                f"Moyenne de {j3_rec} :",
                min_value=0.0,
                max_value=100.0,
                value=def_moy_j3,
                step=0.025,
                format="%.3f",
                key="moy_j3_rec",
                disabled=not est_editeur,
                help="Saisissez la moyenne (ex. 0.650 ou 65%). Formule : arrondi(moyenne × 24 ÷ 3), max 7."
            )
            j3_rec_pts = calculer_score_absent(moy_j3)
            st.session_state["pts_j3_rec"] = j3_rec_pts
            col_m2.metric("Score", f"{j3_rec_pts} pts")
            st.caption(f"📊 *Score calculé : {j3_rec_pts} pts/manche (max 7)*")
        else:
            j3_rec_pts = int(st.session_state.get("pts_j3_rec", 0))

    with st.sidebar.container(border=True):
        st.markdown("#### 🟠 Équipe Visiteuse (🚗)")
        if noms_equipes:
            options_vis = noms_equipes + ["Autre / Personnalisée"]
            def_idx_vis = 1 if len(noms_equipes) > 1 else 0
            if "sel_equipe_vis" in st.session_state and st.session_state["sel_equipe_vis"] not in options_vis:
                st.session_state["sel_equipe_vis"] = options_vis[def_idx_vis]
            if "sel_equipe_vis" in st.session_state and st.session_state["sel_equipe_vis"] in options_vis:
                def_idx_vis = options_vis.index(st.session_state["sel_equipe_vis"])
            choix_vis = st.selectbox("Équipe Visiteuse :", options_vis, index=def_idx_vis, key="sel_equipe_vis", disabled=not est_editeur)

            if choix_vis == "Autre / Personnalisée":
                equipe_visiteur = st.text_input("Nom équipe visiteuse", value=st.session_state.get("input_custom_vis", "Équipe 2"), key="input_custom_vis", disabled=not est_editeur)
                roster_vis = ["Joueur 1", "Joueur 2", "Joueur 3"]
            else:
                equipe_visiteur = choix_vis
                roster_vis = equipes_disponibles[choix_vis]
        else:
            equipe_visiteur = st.text_input("Équipe Visiteuse", value="Équipe 2", key="input_custom_vis", disabled=not est_editeur)
            roster_vis = ["Michel", "Nicolas", "Guy"]
            choix_vis = equipe_visiteur

        st.markdown(f"**👥 Alignement — {equipe_visiteur}**")

        # Options sécurisées pour Joueur 1
        options_j1_vis = list(roster_vis) + ["Remplaçant..."]
        if "sel_j1_vis" in st.session_state and st.session_state["sel_j1_vis"] not in options_j1_vis:
            st.session_state["sel_j1_vis"] = options_j1_vis[0]

        def_idx_j1_vis = 0
        if "sel_j1_vis" in st.session_state and st.session_state["sel_j1_vis"] in options_j1_vis:
            def_idx_j1_vis = options_j1_vis.index(st.session_state["sel_j1_vis"])

        col_j1_v1, col_j1_v2 = st.columns([3, 2])
        sel_j1_vis = col_j1_v1.selectbox("Sélection Joueur 1 :", options_j1_vis, index=def_idx_j1_vis, key="sel_j1_vis", disabled=not est_editeur)
        if sel_j1_vis == "Remplaçant...":
            j1_vis = st.text_input("Nom Visiteur 1 (Remplaçant)", value=st.session_state.get("cust_j1_vis", "Remplaçant 1"), key="cust_j1_vis", disabled=not est_editeur)
        else:
            j1_vis = sel_j1_vis
        j1_vis_pres = col_j1_v2.toggle("Présent", value=st.session_state.get("pres_j1_vis", True), key="pres_j1_vis", disabled=not est_editeur)
        if not j1_vis_pres:
            def_moy_v1 = float(st.session_state.get("moy_j1_vis", 0.625))
            col_m1, col_m2 = st.columns([3, 2])
            moy_v1 = col_m1.number_input(
                f"Moyenne de {j1_vis} :",
                min_value=0.0,
                max_value=100.0,
                value=def_moy_v1,
                step=0.025,
                format="%.3f",
                key="moy_j1_vis",
                disabled=not est_editeur,
                help="Saisissez la moyenne (ex. 0.650 ou 65%). Formule : arrondi(moyenne × 24 ÷ 3), max 7."
            )
            j1_vis_pts = calculer_score_absent(moy_v1)
            st.session_state["pts_j1_vis"] = j1_vis_pts
            col_m2.metric("Score", f"{j1_vis_pts} pts")
            st.caption(f"📊 *Score calculé : {j1_vis_pts} pts/manche (max 7)*")
        else:
            j1_vis_pts = int(st.session_state.get("pts_j1_vis", 0))

        # Options sécurisées pour Joueur 2
        options_j2_vis = [p for p in roster_vis if p != sel_j1_vis] + ["Remplaçant..."]
        if "sel_j2_vis" in st.session_state and st.session_state["sel_j2_vis"] not in options_j2_vis:
            st.session_state["sel_j2_vis"] = options_j2_vis[0]

        def_idx_j2_vis = 0
        if "sel_j2_vis" in st.session_state and st.session_state["sel_j2_vis"] in options_j2_vis:
            def_idx_j2_vis = options_j2_vis.index(st.session_state["sel_j2_vis"])

        col_j2_v1, col_j2_v2 = st.columns([3, 2])
        sel_j2_vis = col_j2_v1.selectbox("Sélection Joueur 2 :", options_j2_vis, index=def_idx_j2_vis, key="sel_j2_vis", disabled=not est_editeur)
        if sel_j2_vis == "Remplaçant...":
            j2_vis = st.text_input("Nom Visiteur 2 (Remplaçant)", value=st.session_state.get("cust_j2_vis", "Remplaçant 2"), key="cust_j2_vis", disabled=not est_editeur)
        else:
            j2_vis = sel_j2_vis
        j2_vis_pres = col_j2_v2.toggle("Présent", value=st.session_state.get("pres_j2_vis", True), key="pres_j2_vis", disabled=not est_editeur)
        if not j2_vis_pres:
            def_moy_v2 = float(st.session_state.get("moy_j2_vis", 0.625))
            col_m1, col_m2 = st.columns([3, 2])
            moy_v2 = col_m1.number_input(
                f"Moyenne de {j2_vis} :",
                min_value=0.0,
                max_value=100.0,
                value=def_moy_v2,
                step=0.025,
                format="%.3f",
                key="moy_j2_vis",
                disabled=not est_editeur,
                help="Saisissez la moyenne (ex. 0.650 ou 65%). Formule : arrondi(moyenne × 24 ÷ 3), max 7."
            )
            j2_vis_pts = calculer_score_absent(moy_v2)
            st.session_state["pts_j2_vis"] = j2_vis_pts
            col_m2.metric("Score", f"{j2_vis_pts} pts")
            st.caption(f"📊 *Score calculé : {j2_vis_pts} pts/manche (max 7)*")
        else:
            j2_vis_pts = int(st.session_state.get("pts_j2_vis", 0))

        # Joueur 3 (Évident / Déduit automatiquement)
        col_j3_v1, col_j3_v2 = st.columns([3, 2])
        restants_vis = [p for p in roster_vis if p != sel_j1_vis and p != sel_j2_vis]
        j3_vis = restants_vis[0] if restants_vis else "Joueur 3"
        col_j3_v1.markdown(f"**Joueur 3 (défini) :**<br>`{j3_vis}`", unsafe_allow_html=True)
        j3_vis_pres = col_j3_v2.toggle("Présent", value=st.session_state.get("pres_j3_vis", True), key="pres_j3_vis", disabled=not est_editeur)
        if not j3_vis_pres:
            def_moy_v3 = float(st.session_state.get("moy_j3_vis", 0.625))
            col_m1, col_m2 = st.columns([3, 2])
            moy_v3 = col_m1.number_input(
                f"Moyenne de {j3_vis} :",
                min_value=0.0,
                max_value=100.0,
                value=def_moy_v3,
                step=0.025,
                format="%.3f",
                key="moy_j3_vis",
                disabled=not est_editeur,
                help="Saisissez la moyenne (ex. 0.650 ou 65%). Formule : arrondi(moyenne × 24 ÷ 3), max 7."
            )
            j3_vis_pts = calculer_score_absent(moy_v3)
            st.session_state["pts_j3_vis"] = j3_vis_pts
            col_m2.metric("Score", f"{j3_vis_pts} pts")
            st.caption(f"📊 *Score calculé : {j3_vis_pts} pts/manche (max 7)*")
        else:
            j3_vis_pts = int(st.session_state.get("pts_j3_vis", 0))

    # Dictionnaire complet des joueurs
    dict_joueurs = {
        "j1_rec": {"nom": j1_rec, "present": j1_rec_pres, "moyenne": float(st.session_state.get("moy_j1_rec", 0.0)), "pts_absent": j1_rec_pts, "equipe": equipe_receveur},
        "j2_rec": {"nom": j2_rec, "present": j2_rec_pres, "moyenne": float(st.session_state.get("moy_j2_rec", 0.0)), "pts_absent": j2_rec_pts, "equipe": equipe_receveur},
        "j3_rec": {"nom": j3_rec, "present": j3_rec_pres, "moyenne": float(st.session_state.get("moy_j3_rec", 0.0)), "pts_absent": j3_rec_pts, "equipe": equipe_receveur},
        "j1_vis": {"nom": j1_vis, "present": j1_vis_pres, "moyenne": float(st.session_state.get("moy_j1_vis", 0.0)), "pts_absent": j1_vis_pts, "equipe": equipe_visiteur},
        "j2_vis": {"nom": j2_vis, "present": j2_vis_pres, "moyenne": float(st.session_state.get("moy_j2_vis", 0.0)), "pts_absent": j2_vis_pts, "equipe": equipe_visiteur},
        "j3_vis": {"nom": j3_vis, "present": j3_vis_pres, "moyenne": float(st.session_state.get("moy_j3_vis", 0.0)), "pts_absent": j3_vis_pts, "equipe": equipe_visiteur},
    }

    # ==============================================================================
    # STRUCTURE DES 9 DUELS (AUCUN JOUEUR NE JOUE DEUX MATCHS DE SUITE)
    # ==============================================================================
    matchs_pairs = [
        (1, "j1_rec", "j1_vis"),
        (2, "j2_rec", "j2_vis"),
        (3, "j3_rec", "j3_vis"),
        (4, "j1_rec", "j2_vis"),
        (5, "j2_rec", "j3_vis"),
        (6, "j3_rec", "j1_vis"),
        (7, "j1_rec", "j3_vis"),
        (8, "j2_rec", "j1_vis"),
        (9, "j3_rec", "j2_vis")
    ]

    # Synchronisation automatique des scores UNIQUEMENT lors d'un vrai changement d'état Présent/Absent ou score défaut
    for p_id in dict_joueurs:
        info_j = dict_joueurs[p_id]
        state_key = f"prev_state_{p_id}"
        pts_key = f"prev_pts_{p_id}"
    
        presence_changed = (state_key in st.session_state and st.session_state[state_key] != info_j["present"])
        pts_changed = (not info_j["present"] and pts_key in st.session_state and st.session_state[pts_key] != info_j["pts_absent"])

        if presence_changed or pts_changed:
            for num_m, k_a, k_b in matchs_pairs:
                if k_a == p_id or k_b == p_id:
                    info_a = dict_joueurs[k_a]
                    info_b = dict_joueurs[k_b]
                    if not info_a["present"] and info_b["present"]:
                        st.session_state[f"s_a_{num_m}"] = info_a["pts_absent"]
                        st.session_state[f"s_b_{num_m}"] = 8
                    elif not info_b["present"] and info_a["present"]:
                        st.session_state[f"s_a_{num_m}"] = 8
                        st.session_state[f"s_b_{num_m}"] = info_b["pts_absent"]
                    elif not info_a["present"] and not info_b["present"]:
                        st.session_state[f"s_a_{num_m}"] = info_a["pts_absent"]
                        st.session_state[f"s_b_{num_m}"] = info_b["pts_absent"]
                    else:
                        st.session_state[f"s_a_{num_m}"] = 0
                        st.session_state[f"s_b_{num_m}"] = 0

        st.session_state[state_key] = info_j["present"]
        st.session_state[pts_key] = info_j["pts_absent"]

    # Liste des absents pour information
    absents_detectes = [f"{j['nom']} ({j['equipe']}) — moy: {j['moyenne']:.3f} → {j['pts_absent']} pts" for j in dict_joueurs.values() if not j["present"]]
    if absents_detectes:
        st.warning(f"⚠️ **Joueur(s) absent(s) :** {', '.join(absents_detectes)}. Leurs scores de défaut sont automatiquement appliqués dans leurs manches respectives.")

    def calculer_totaux_actuels(dict_joueurs_ref, matchs_pairs_ref):
        """Calcule les totaux d'équipes, de joueurs et les détails des manches à partir de session_state."""
        tot_rec = 0
        tot_vis = 0
        pts_j = {p_id: 0 for p_id in dict_joueurs_ref}
        details_manches = []
    
        for num_m, id_a, id_b in matchs_pairs_ref:
            sa = int(st.session_state.get(f"s_a_{num_m}", 0))
            sb = int(st.session_state.get(f"s_b_{num_m}", 0))
            tot_rec += sa
            tot_vis += sb
            pts_j[id_a] += sa
            pts_j[id_b] += sb
        
            ja = dict_joueurs_ref[id_a]["nom"]
            jb = dict_joueurs_ref[id_b]["nom"]
            details_manches.append({
                "manche": num_m,
                "ja": ja,
                "sa": sa,
                "sb": sb,
                "jb": jb,
                "abs_a": not dict_joueurs_ref[id_a]["present"],
                "abs_b": not dict_joueurs_ref[id_b]["present"]
            })
        
        return tot_rec, tot_vis, pts_j, details_manches

    # ==============================================================================
    # CONSULTATION DE L'HISTORIQUE ET DES RÉSULTATS (SPECTATEUR ET ÉDITEUR MARQUEUR)
    # ==============================================================================
    historique_matchs = charger_historique_matchs()

    label_direct = "🔴 Saisie du match en direct (En cours)" if not est_spectateur else "🔴 Match en direct (En cours)"
    options_matchs = [label_direct]
    mapping_matchs = {}
    for m in reversed(historique_matchs or []):
        date_m = m.get("date_enregistrement", m.get("date", "Date inconnue"))
        rec_m = m.get("receveur", "Receveur")
        vis_m = m.get("visiteur", "Visiteur")
        tot_r = m.get("total_receveur", 0)
        tot_v = m.get("total_visiteur", 0)
        label = f"📜 {date_m} — {rec_m} ({tot_r}) vs {vis_m} ({tot_v})"
        options_matchs.append(label)
        mapping_matchs[label] = m

    def callback_retour_match_en_cours():
        """Callback officiel Streamlit exécuté avant l'instanciation des widgets lors du clic sur Retour."""
        st.session_state["choix_match_vue"] = label_direct

    # S'assurer que la sélection est valide avant l'affichage du selectbox
    if "choix_match_vue" in st.session_state and st.session_state["choix_match_vue"] not in options_matchs:
        st.session_state["choix_match_vue"] = label_direct

    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        choix_vue = st.selectbox(
            "📜 **Consulter les résultats d'un match :**",
            options_matchs,
            index=0,
            key="choix_match_vue",
            help="Sélectionnez le match en direct ou une copie officielle archivée envoyée par courriel"
        )
    with col_sel2:
        st.write("")
        if choix_vue == label_direct:
            if not est_editeur:
                if st.button("🔄 Actualiser les résultats", use_container_width=True, help="Recharge les derniers scores saisis par le marqueur"):
                    st.session_state["forcer_rechargement"] = True
                    st.rerun()
        else:
            st.button("🔙 Revenir au match en cours", on_click=callback_retour_match_en_cours, use_container_width=True, help="Retourner à la saisie du match actuel")

    # 1. Si une archive officielle est sélectionnée
    if choix_vue != label_direct:
        st.session_state["venant_de_archive"] = True
        m_arch = mapping_matchs[choix_vue]
        html_arch = obtenir_html_match(m_arch)
    
        with st.container(border=True):
            st.markdown(f"#### 📜 Feuille officielle archivée — {m_arch.get('date_enregistrement', m_arch.get('date', ''))}")
            if m_arch.get("approbateur_receveur") or m_arch.get("approbateur_visiteur"):
                app_r_txt = m_arch.get("approbateur_receveur", "Non spécifié")
                app_v_txt = m_arch.get("approbateur_visiteur", "Non spécifié")
                st.caption(f"✍️ **Feuille officielle approuvée par :** `{app_r_txt}` ({m_arch.get('receveur', 'Receveur')}) et `{app_v_txt}` ({m_arch.get('visiteur', 'Visiteur')})")
            date_slug = str(m_arch.get('date_enregistrement', 'match')).replace('/', '-').replace(' ', '_').replace(':', 'h').replace('à', '')
            rec_slug = str(m_arch.get('receveur', 'rec')).replace(' ', '_')
            vis_slug = str(m_arch.get('visiteur', 'vis')).replace(' ', '_')

            c_btn1, c_btn2, c_btn3 = st.columns([2, 1, 1])
            c_btn1.info("✉️ **Copie certifiée conforme :** Ce résultat correspond exactement à la feuille de match officielle transmise par courriel lors de la validation.")
            with c_btn2:
                st.download_button(
                    label="📥 Télécharger (HTML)",
                    data=html_arch,
                    file_name=f"feuille_{rec_slug}_vs_{vis_slug}_{date_slug}.html",
                    mime="text/html",
                    use_container_width=True,
                    key=f"dl_arch_{date_slug}"
                )
            with c_btn3:
                html_print_data = json.dumps(html_arch)
                st.components.v1.html(
                    f"""
                    <button onclick="lancerImpression()" style="width:100%; height:38px; background-color:#0b3c5d; color:white; border:none; border-radius:6px; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; font-size:14px; font-weight:600; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
                        🖨️ Imprimer (Page A4)
                    </button>
                    <script>
                    function lancerImpression() {{
                        var win = window.open('', '_blank');
                        win.document.open();
                        win.document.write({html_print_data});
                        win.document.close();
                        win.focus();
                        win.document.title = "Feuille de match officielle - A4";
                        setTimeout(function() {{
                            win.print();
                        }}, 350);
                    }}
                    </script>
                    """,
                    height=42
                )

            # Option d'envoi par courriel à une adresse saisie dans un champ adjacent
            col_m_input, col_m_btn = st.columns([3, 1])
            with col_m_input:
                email_dest_saisie = st.text_input(
                    "Adresse courriel du destinataire",
                    placeholder="Entrez une adresse courriel pour recevoir cette feuille (ex: joueur@courriel.com)...",
                    key=f"mail_dest_{date_slug}",
                    label_visibility="collapsed"
                )
            with col_m_btn:
                btn_envoyer_mail = st.button(
                    "📧 Envoyer par courriel",
                    use_container_width=True,
                    key=f"btn_send_{date_slug}",
                    help="Transmettre cette feuille officielle par courriel à l'adresse spécifiée"
                )

            if btn_envoyer_mail:
                dest_propre = email_dest_saisie.strip()
                if not dest_propre or "@" not in dest_propre:
                    st.error("⚠️ Veuillez saisir une adresse courriel valide avant d'envoyer.")
                else:
                    with st.spinner("Envoi du courriel en cours..."):
                        cfg_courriel = charger_config_email()
                        rec_m = m_arch.get("receveur", "Receveur")
                        vis_m = m_arch.get("visiteur", "Visiteur")
                        tot_r = m_arch.get("total_receveur", 0)
                        tot_v = m_arch.get("total_visiteur", 0)
                        date_m = m_arch.get("date_enregistrement", m_arch.get("date", "Date inconnue"))
                    
                        sujet_envoi = f"🎱 Feuille de match : {rec_m} ({tot_r}) vs {vis_m} ({tot_v}) - {date_m}"
                        texte_envoi = (
                            f"Feuille de match officielle - Ligue de billard Boule en main\n"
                            f"Date : {date_m}\n"
                            f"Rencontre : {rec_m} ({tot_r} pts) vs {vis_m} ({tot_v} pts)\n\n"
                            f"Veuillez consulter la version HTML de ce courriel pour visualiser la feuille officielle complète."
                        )
                        pj = [HISTORIQUE_FILE] if os.path.exists(HISTORIQUE_FILE) else None
                        succes_envoi, msg_envoi = envoyer_courriel(
                            dest_propre,
                            sujet_envoi,
                            texte_envoi,
                            html_arch,
                            cfg_courriel,
                            pieces_jointes=pj
                        )
                    if succes_envoi:
                        st.success(f"✅ Feuille de match transmise avec succès à `{dest_propre}` !")
                    else:
                        st.error(f"❌ {msg_envoi}")
        
            st.components.v1.html(html_arch, height=650, scrolling=True)

    # 2. Si le match en cours est sélectionné
    else:
        # Restauration automatique des scores en mémoire si l'on revient de la consultation d'une archive
        if st.session_state.get("venant_de_archive", False) and "scores_en_cours_backup" in st.session_state:
            for k_b, v_b in st.session_state["scores_en_cours_backup"].items():
                st.session_state[k_b] = v_b
            st.session_state["venant_de_archive"] = False

        if est_spectateur:
            @st.fragment(run_every="5s")
            def fragment_tableau_spectateur():
                # 1. Vérification des mises à jour faites par le marqueur
                sauv = charger_sauvegarde()
                mtime_actuel = 0
                if os.path.exists(BACKUP_FILE):
                    try:
                        mtime_actuel = os.path.getmtime(BACKUP_FILE)
                    except Exception:
                        mtime_actuel = 0

                if "dernier_mtime_vu" not in st.session_state:
                    st.session_state["dernier_mtime_vu"] = mtime_actuel
                elif mtime_actuel > st.session_state.get("dernier_mtime_vu", 0):
                    st.session_state["dernier_mtime_vu"] = mtime_actuel
                    if sauv and "matchs" in sauv:
                        restaurer_session(sauv)
                    st.toast("🔔 Le marqueur a mis à jour les résultats du match !", icon="🎱")

                heure_maj = sauv.get("derniere_mise_a_jour", datetime.now().strftime("%H:%M:%S"))
                tot_rec_c, tot_vis_c, pts_j_c, details_c = calculer_totaux_actuels(dict_joueurs, matchs_pairs)

                with st.container(border=True):
                    col_t_titre, col_t_badge = st.columns([2.5, 1.5])
                    with col_t_titre:
                        st.markdown(f"#### 🎱 Résultats courants : **{equipe_receveur}** ({tot_rec_c} pts) vs **{equipe_visiteur}** ({tot_vis_c} pts)")
                    with col_t_badge:
                        st.markdown(
                            f"<div style='text-align: right; font-size: 13px; color: #2e7d32; font-weight: bold; padding-top: 5px;'>"
                            f"🟢 En direct (Synchro auto : {heure_maj})"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                    if tot_rec_c > tot_vis_c:
                        st.success(f"🏆 **{equipe_receveur}** mène par **{tot_rec_c - tot_vis_c} point(s)** ({tot_rec_c} à {tot_vis_c}).")
                    elif tot_vis_c > tot_rec_c:
                        st.success(f"🏆 **{equipe_visiteur}** mène par **{tot_vis_c - tot_rec_c} point(s)** ({tot_vis_c} à {tot_rec_c}).")
                    else:
                        st.info(f"🤝 **Égalité provisoire** : {tot_rec_c} à {tot_vis_c}.")

                    # Scores par équipe
                    c_sc1, c_sc2 = st.columns(2)
                    c_sc1.metric(f"Total {equipe_receveur}", f"{tot_rec_c} pts")
                    c_sc2.metric(f"Total {equipe_visiteur}", f"{tot_vis_c} pts")

                    # Points des joueurs
                    st.markdown("##### 👤 Points individuels cumulés")
                    col_pj1, col_pj2 = st.columns(2)
                    with col_pj1:
                        st.markdown(f"**🏠 {equipe_receveur}**")
                        cr1, cr2, cr3 = st.columns(3)
                        p1 = dict_joueurs["j1_rec"]
                        p2 = dict_joueurs["j2_rec"]
                        p3 = dict_joueurs["j3_rec"]
                        cr1.metric(p1["nom"] + (" (Abs.)" if not p1["present"] else ""), f"{pts_j_c['j1_rec']} pts")
                        cr2.metric(p2["nom"] + (" (Abs.)" if not p2["present"] else ""), f"{pts_j_c['j2_rec']} pts")
                        cr3.metric(p3["nom"] + (" (Abs.)" if not p3["present"] else ""), f"{pts_j_c['j3_rec']} pts")

                    with col_pj2:
                        st.markdown(f"**🚗 {equipe_visiteur}**")
                        cv1, cv2, cv3 = st.columns(3)
                        pv1 = dict_joueurs["j1_vis"]
                        pv2 = dict_joueurs["j2_vis"]
                        pv3 = dict_joueurs["j3_vis"]
                        cv1.metric(pv1["nom"] + (" (Abs.)" if not pv1["present"] else ""), f"{pts_j_c['j1_vis']} pts")
                        cv2.metric(pv2["nom"] + (" (Abs.)" if not pv2["present"] else ""), f"{pts_j_c['j2_vis']} pts")
                        cv3.metric(pv3["nom"] + (" (Abs.)" if not pv3["present"] else ""), f"{pts_j_c['j3_vis']} pts")

                    # Tableau récapitulatif des 9 manches
                    st.markdown("##### 📋 État des 9 manches")
                    lignes_md = [
                        f"| Manche | Joueur ({equipe_receveur}) | Pts {equipe_receveur} | Pts {equipe_visiteur} | Joueur ({equipe_visiteur}) | Statut |",
                        "| :---: | :--- | :---: | :---: | :--- | :--- |"
                    ]
                    for row in details_c:
                        nom_a = f"**{row['ja']}**" + (" *(Absent)*" if row["abs_a"] else "")
                        nom_b = f"**{row['jb']}**" + (" *(Absent)*" if row["abs_b"] else "")
                        sa_val = row["sa"]
                        sb_val = row["sb"]
                    
                        if sa_val == 8:
                            sc_a = f"**{sa_val}**"
                            sc_b = f"{sb_val}"
                            statut = f"🏆 **Gagné ({row['ja']})**"
                        elif sb_val == 8:
                            sc_a = f"{sa_val}"
                            sc_b = f"**{sb_val}**"
                            statut = f"🏆 **Gagné ({row['jb']})**"
                        elif sa_val > 0 or sb_val > 0:
                            sc_a = f"{sa_val}"
                            sc_b = f"{sb_val}"
                            statut = "⏳ *En cours*"
                        else:
                            sc_a = "0"
                            sc_b = "0"
                            statut = "⚪ *À jouer*"

                        lignes_md.append(f"| **Manche {row['manche']}** | {nom_a} | {sc_a} | {sc_b} | {nom_b} | {statut} |")

                    st.markdown("\n".join(lignes_md))
                    st.caption("⚡ *Synchronisation en direct active : votre écran se met à jour automatiquement toutes les 5 secondes dès qu'un point est inscrit.*")

            fragment_tableau_spectateur()

        else:
            # Bandeau Scoreboard Live permanent pour le marqueur / éditeur
            tot_rec_c, tot_vis_c, pts_j_c, details_c = calculer_totaux_actuels(dict_joueurs, matchs_pairs)
            nb_manches_term = sum(1 for r_m in details_c if (r_m["sa"] == 8 or r_m["sb"] == 8) and not (r_m["sa"] == 8 and r_m["sb"] == 8))
            pct_manches = int(round((nb_manches_term / 9.0) * 100))

            if tot_rec_c > tot_vis_c:
                statut_live_html = f"🏆 <strong>{equipe_receveur}</strong> mène par <strong>+{tot_rec_c - tot_vis_c} pt(s)</strong>"
            elif tot_vis_c > tot_rec_c:
                statut_live_html = f"🏆 <strong>{equipe_visiteur}</strong> mène par <strong>+{tot_vis_c - tot_rec_c} pt(s)</strong>"
            else:
                statut_live_html = f"🤝 <strong>Égalité parfaite</strong> ({tot_rec_c} - {tot_vis_c})"

            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #0b3c5d 0%, #16527a 100%); color: white; border-radius: 12px; padding: 14px 20px; margin: 8px 0 12px 0; box-shadow: 0 4px 12px rgba(11, 60, 93, 0.2); border-bottom: 4px solid #f59e0b;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div style="flex: 1; min-width: 160px;">
                            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #93c5fd; font-weight: 700;">🔵 Équipe Receveuse (🏠)</div>
                            <div style="font-size: 18px; font-weight: 800; color: #ffffff;">{equipe_receveur}</div>
                        </div>
                        <div style="text-align: center; padding: 4px 18px; background: rgba(255,255,255,0.12); border-radius: 10px; border: 1px solid rgba(255,255,255,0.22);">
                            <div style="font-size: 26px; font-weight: 900; letter-spacing: 1px; color: #fbbf24;">
                                {tot_rec_c} <span style="font-size: 15px; color: #e2e8f0; font-weight: 600;">pts</span>
                                &nbsp;—&nbsp;
                                {tot_vis_c} <span style="font-size: 15px; color: #e2e8f0; font-weight: 600;">pts</span>
                            </div>
                            <div style="font-size: 12px; color: #f8fafc; margin-top: 2px;">{statut_live_html} &nbsp;•&nbsp; ✅ {nb_manches_term}/9 manches ({pct_manches}%)</div>
                        </div>
                        <div style="flex: 1; min-width: 160px; text-align: right;">
                            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #fdba74; font-weight: 700;">🟠 Équipe Visiteuse (🚗)</div>
                            <div style="font-size: 18px; font-weight: 800; color: #ffffff;">{equipe_visiteur}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col_t1, col_t2 = st.columns([2, 2])
            with col_t1:
                afficher_dashboard = st.toggle(
                    "📊 **Afficher le détail des points individuels en direct**",
                    value=st.session_state.get("toggle_voir_resultats_editeur", False),
                    key="toggle_voir_resultats_editeur"
                )
            with col_t2:
                replier_manches_terminees = st.toggle(
                    "🔽 **Replier automatiquement les manches terminées (8 pts)**",
                    value=st.session_state.get("toggle_replier_manches_term", False),
                    key="toggle_replier_manches_term"
                )

            if afficher_dashboard:
                with st.container(border=True):
                    st.markdown("##### 👤 Points individuels cumulés en direct")
                    col_pj1, col_pj2 = st.columns(2)
                    with col_pj1:
                        st.markdown(f"**🏠 {equipe_receveur}**")
                        cr1, cr2, cr3 = st.columns(3)
                        p1 = dict_joueurs["j1_rec"]
                        p2 = dict_joueurs["j2_rec"]
                        p3 = dict_joueurs["j3_rec"]
                        cr1.metric(p1["nom"] + (" (Abs.)" if not p1["present"] else ""), f"{pts_j_c['j1_rec']} pts")
                        cr2.metric(p2["nom"] + (" (Abs.)" if not p2["present"] else ""), f"{pts_j_c['j2_rec']} pts")
                        cr3.metric(p3["nom"] + (" (Abs.)" if not p3["present"] else ""), f"{pts_j_c['j3_rec']} pts")

                    with col_pj2:
                        st.markdown(f"**🚗 {equipe_visiteur}**")
                        cv1, cv2, cv3 = st.columns(3)
                        pv1 = dict_joueurs["j1_vis"]
                        pv2 = dict_joueurs["j2_vis"]
                        pv3 = dict_joueurs["j3_vis"]
                        cv1.metric(pv1["nom"] + (" (Abs.)" if not pv1["present"] else ""), f"{pts_j_c['j1_vis']} pts")
                        cv2.metric(pv2["nom"] + (" (Abs.)" if not pv2["present"] else ""), f"{pts_j_c['j2_vis']} pts")
                        cv3.metric(pv3["nom"] + (" (Abs.)" if not pv3["present"] else ""), f"{pts_j_c['j3_vis']} pts")

    if not est_spectateur and choix_vue != label_direct:
        col_av1, col_av2 = st.columns([3, 1])
        with col_av1:
            st.info("💡 **Feuille archivée affichée ci-dessus.** La grille de saisie du match en cours est temporairement masquée.")
        with col_av2:
            st.button("🔙 Reprendre la saisie", on_click=callback_retour_match_en_cours, type="primary", use_container_width=True, key="btn_reprendre_saisie")
    elif not est_spectateur:
        st.markdown("---")
        st.markdown("### 🎯 Grille de saisie des 9 manches (Rotation alternée 3 contre 3)")
        st.info(
            "📌 **Règle de rotation :** Aucun joueur ne joue deux manches consécutives.\n\n"
            "🎱 **Règle du jeu au 8 :** Le vainqueur obtient **8 points**, le perdant obtient de **0 à 7 points**."
        )

        donnees_a_sauvegarder = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "receveur": equipe_receveur,
            "visiteur": equipe_visiteur,
            "choix_rec": choix_rec,
            "choix_vis": choix_vis,
            "input_custom_rec": st.session_state.get("input_custom_rec", ""),
            "input_custom_vis": st.session_state.get("input_custom_vis", ""),
            "sel_j1_rec": sel_j1_rec,
            "sel_j2_rec": sel_j2_rec,
            "sel_j1_vis": sel_j1_vis,
            "sel_j2_vis": sel_j2_vis,
            "joueurs": {p_id: {"nom": j["nom"], "present": j["present"], "moyenne": j.get("moyenne", 0.0), "pts_absent": j["pts_absent"]} for p_id, j in dict_joueurs.items()},
            "matchs": {}
        }

        manches_invalides = []
        replier_auto = st.session_state.get("toggle_replier_manches_term", False)

        for num_manche, id_a, id_b in matchs_pairs:
            info_a = dict_joueurs[id_a]
            info_b = dict_joueurs[id_b]
            joueur_a = info_a["nom"]
            joueur_b = info_b["nom"]
            a_pres = info_a["present"]
            b_pres = info_b["present"]

            # Valeur par défaut si non encore définie dans session_state
            if not a_pres and b_pres:
                init_val_a = info_a["pts_absent"]
                init_val_b = 8
            elif not b_pres and a_pres:
                init_val_a = 8
                init_val_b = info_b["pts_absent"]
            elif not a_pres and not b_pres:
                init_val_a = info_a["pts_absent"]
                init_val_b = info_b["pts_absent"]
            else:
                init_val_a = 0
                init_val_b = 0

            if f"s_a_{num_manche}" not in st.session_state:
                st.session_state[f"s_a_{num_manche}"] = max(0, min(8, int(init_val_a)))
            if f"s_b_{num_manche}" not in st.session_state:
                st.session_state[f"s_b_{num_manche}"] = max(0, min(8, int(init_val_b)))

            cur_sa = int(st.session_state.get(f"s_a_{num_manche}", 0))
            cur_sb = int(st.session_state.get(f"s_b_{num_manche}", 0))
            manche_terminee = ((cur_sa == 8 and cur_sb < 8) or (cur_sb == 8 and cur_sa < 8))

            status_label = ""
            if not a_pres and not b_pres:
                status_label = " • ❌ Forfait double (2 absents)"
            elif not a_pres:
                status_label = f" • ❌ {joueur_a} absent ({info_a['pts_absent']} pts)"
            elif not b_pres:
                status_label = f" • ❌ {joueur_b} absent ({info_b['pts_absent']} pts)"

            if cur_sa == 8 and cur_sb == 8:
                icone_manche = "⚠️"
                resume_score_hdr = f"({cur_sa} - {cur_sb}) — Erreur 8-8"
            elif manche_terminee:
                icone_manche = "✅"
                gagnant_m = joueur_a if cur_sa == 8 else joueur_b
                resume_score_hdr = f"[{cur_sa} - {cur_sb}] 🏆 {gagnant_m}"
            elif cur_sa > 0 or cur_sb > 0:
                icone_manche = "⏳"
                resume_score_hdr = f"[{cur_sa} - {cur_sb}] — En cours"
            else:
                icone_manche = "⚪"
                resume_score_hdr = "À jouer"

            ouvrir_manche = not (replier_auto and manche_terminee)

            with st.expander(f"{icone_manche} Manche {num_manche} : {joueur_a} ({equipe_receveur}) vs {joueur_b} ({equipe_visiteur}) — {resume_score_hdr}{status_label}", expanded=ouvrir_manche):
                c1, c2 = st.columns(2)

                with c1:
                    label_champ_a = f"🔵 Points de {joueur_a} ({equipe_receveur})" + (f" [Absent : {info_a['pts_absent']} pts]" if not a_pres else "")
                    score_a = st.number_input(
                        label_champ_a, 
                        0, 8, 
                        key=f"s_a_{num_manche}",
                        disabled=not est_editeur
                    )
                with c2:
                    label_champ_b = f"🟠 Points de {joueur_b} ({equipe_visiteur})" + (f" [Absent : {info_b['pts_absent']} pts]" if not b_pres else "")
                    score_b = st.number_input(
                        label_champ_b, 
                        0, 8, 
                        key=f"s_b_{num_manche}",
                        disabled=not est_editeur
                    )
            
                # Validation logique du billard au 8 et retour visuel immédiat
                if score_a == 8 and score_b == 8:
                    st.warning("⚠️ Les deux joueurs ne peuvent pas avoir 8 points.")
                    manches_invalides.append(num_manche)
                elif score_a == 8:
                    st.caption(f"🏆 **Manche {num_manche} remportée par {joueur_a}** ({score_a} à {score_b})")
                elif score_b == 8:
                    st.caption(f"🏆 **Manche {num_manche} remportée par {joueur_b}** ({score_b} à {score_a})")

                donnees_a_sauvegarder["matchs"][str(num_manche)] = {
                    "score_a": score_a,
                    "score_b": score_b,
                    "joueur_a": joueur_a,
                    "joueur_b": joueur_b,
                    "joueur_a_absent": not a_pres,
                    "joueur_b_absent": not b_pres
                }

        # --- CALCULS FINAUX ET TOTAUX (PAR ÉQUIPE ET PAR JOUEUR) ---
        total_pts_receveur = sum(m["score_a"] for m in donnees_a_sauvegarder["matchs"].values())
        total_pts_visiteur = sum(m["score_b"] for m in donnees_a_sauvegarder["matchs"].values())

        # Calcul des points individuels par joueur (3 manches par joueur = max 24 pts)
        pts_joueurs = {p_id: 0 for p_id in dict_joueurs}
        for num_m, id_a, id_b in matchs_pairs:
            m = donnees_a_sauvegarder["matchs"].get(str(num_m), {})
            pts_joueurs[id_a] += m.get("score_a", 0)
            pts_joueurs[id_b] += m.get("score_b", 0)

        st.divider()
        st.markdown("### 📊 Résultats et Totaux")

        # 1. Totaux par équipe
        col_res1, col_res2 = st.columns(2)
        col_res1.metric(label=f"🏆 Total {equipe_receveur}", value=f"{total_pts_receveur} pts")
        col_res2.metric(label=f"🏆 Total {equipe_visiteur}", value=f"{total_pts_visiteur} pts")

        # 2. Totaux individuels par joueur
        st.markdown("#### 👤 Points individuels par joueur")

        col_rec_pts, col_vis_pts = st.columns(2)

        with col_rec_pts:
            st.markdown(f"**🏠 {equipe_receveur}**")
            cr1, cr2, cr3 = st.columns(3)
            p1 = dict_joueurs["j1_rec"]
            p2 = dict_joueurs["j2_rec"]
            p3 = dict_joueurs["j3_rec"]
            cr1.metric(label=f"{p1['nom']}" + (" (Abs.)" if not p1['present'] else ""), value=f"{pts_joueurs['j1_rec']} pts")
            cr2.metric(label=f"{p2['nom']}" + (" (Abs.)" if not p2['present'] else ""), value=f"{pts_joueurs['j2_rec']} pts")
            cr3.metric(label=f"{p3['nom']}" + (" (Abs.)" if not p3['present'] else ""), value=f"{pts_joueurs['j3_rec']} pts")

        with col_vis_pts:
            st.markdown(f"**🚗 {equipe_visiteur}**")
            cv1, cv2, cv3 = st.columns(3)
            pv1 = dict_joueurs["j1_vis"]
            pv2 = dict_joueurs["j2_vis"]
            pv3 = dict_joueurs["j3_vis"]
            cv1.metric(label=f"{pv1['nom']}" + (" (Abs.)" if not pv1['present'] else ""), value=f"{pts_joueurs['j1_vis']} pts")
            cv2.metric(label=f"{pv2['nom']}" + (" (Abs.)" if not pv2['present'] else ""), value=f"{pts_joueurs['j2_vis']} pts")
            cv3.metric(label=f"{pv3['nom']}" + (" (Abs.)" if not pv3['present'] else ""), value=f"{pts_joueurs['j3_vis']} pts")

        st.divider()

        # --- VALIDATION FINALE ET ENREGISTREMENT OFFICIEL ---
        st.markdown("### 🚀 Validation finale et Enregistrement officiel")

        dest_actuels = config_email.get("destinataires", "").strip()
        if dest_actuels:
            st.info(f"✉️ **Envoi automatique configuré vers :** `{dest_actuels}` *(modifiable dans l'Espace Administration ci-dessous)*")
        else:
            st.warning(f"⚠️ **Aucun destinataire configuré.** Ouvrez l'Espace Administration en bas de page pour configurer la messagerie.")

        st.divider()

        # --- VALIDATION FINALE DU MATCH ET ENVOI AUTOMATIQUE ---
        date_du_match = datetime.now().strftime("%d/%m/%Y à %H:%M")
        texte_resume, html_resume = generer_resume_match(
            equipe_receveur,
            equipe_visiteur,
            donnees_a_sauvegarder["matchs"],
            total_pts_receveur,
            total_pts_visiteur,
            pts_joueurs,
            dict_joueurs,
            date_du_match,
            absents_detectes
        )

        @st.dialog("📋 Sommaire & Approbation de la feuille de match", width="large")
        def modal_sommaire_approbation(
            equipe_rec,
            equipe_vis,
            matchs_dict,
            tot_rec,
            tot_vis,
            pts_j,
            dict_j,
            d_match,
            absents_det,
            txt_res,
            html_res,
            cfg_email,
            sess_id,
            donnees_sauv,
            roster_rec=None,
            roster_vis=None,
            est_deja_valide=False
        ):
            if est_deja_valide:
                st.warning(
                    "⚠️ **Ce match a déjà été validé et archivé officiellement.**\n\n"
                    "Il ne peut pas être validé de nouveau afin d'éviter les doublons.\n\n"
                    "👉 Si vous souhaitez modifier les résultats de ce match, veuillez utiliser l'option de modification **« ✏️ Rectifier un match archivé »** située dans la section **Espace Administration** en bas de page."
                )
                if st.button("Fermer", use_container_width=True):
                    st.rerun()
                return

            st.markdown("### 🎱 Sommaire officiel de la rencontre")
            st.caption(f"📅 **Date :** {d_match}")

            # Totaux par équipe
            col_t1, col_t2 = st.columns(2)
            vainq_rec = tot_rec > tot_vis
            vainq_vis = tot_vis > tot_rec
            col_t1.metric(
                label=f"Équipe Receveur : {equipe_rec}",
                value=f"{tot_rec} pts",
                delta="Vainqueur 🏆" if vainq_rec else None
            )
            col_t2.metric(
                label=f"Équipe Visiteur : {equipe_vis}",
                value=f"{tot_vis} pts",
                delta="Vainqueur 🏆" if vainq_vis else None
            )
            if tot_rec == tot_vis:
                st.info("⚖️ **Résultat du match :** Égalité parfaite (Match nul)")

            st.markdown("#### 🎯 Détail des 9 manches")
            table_md = [
                f"| Manche | Joueur ({equipe_rec}) | {equipe_rec} | {equipe_vis} | Joueur ({equipe_vis}) |",
                "| :---: | :--- | :---: | :---: | :--- |"
            ]
            for num in range(1, 10):
                m = matchs_dict.get(str(num), {})
                sa = m.get("score_a", 0)
                sb = m.get("score_b", 0)
                ja = str(m.get("joueur_a", "")).replace("|", "/")
                jb = str(m.get("joueur_b", "")).replace("|", "/")
                ja_abs = " *(Absent)*" if m.get("joueur_a_absent") else ""
                jb_abs = " *(Absent)*" if m.get("joueur_b_absent") else ""

                # Score vert en gras pour le vainqueur de la manche (8 pts)
                sc_a_str = f"**{sa}**" if sa == 8 else f"{sa}"
                sc_b_str = f"**{sb}**" if sb == 8 else f"{sb}"

                table_md.append(f"| **Manche {num}** | {ja}{ja_abs} | {sc_a_str} | {sc_b_str} | {jb}{jb_abs} |")

            table_md.append(f"| **TOTAL** | **{equipe_rec}** | **{tot_rec} pts** | **{tot_vis} pts** | **{equipe_vis}** |")

            st.markdown("\n".join(table_md))

            # Points individuels
            st.markdown("#### 👤 Points individuels par joueur")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown(f"**{equipe_rec} :**")
                for k in ["j1_rec", "j2_rec", "j3_rec"]:
                    nom = dict_j[k]["nom"]
                    pts = pts_j[k]
                    abs_str = " *(Absent)*" if not dict_j[k]["present"] else ""
                    st.write(f"- {nom} : **{pts} pts**{abs_str}")
            with col_p2:
                st.markdown(f"**{equipe_vis} :**")
                for k in ["j1_vis", "j2_vis", "j3_vis"]:
                    nom = dict_j[k]["nom"]
                    pts = pts_j[k]
                    abs_str = " *(Absent)*" if not dict_j[k]["present"] else ""
                    st.write(f"- {nom} : **{pts} pts**{abs_str}")

            if absents_det:
                st.warning(f"⚠️ **Joueur(s) absent(s) :** {', '.join(absents_det)}")

            # Sélection des approbateurs de chaque équipe via dropdown boxes
            st.markdown("#### ✍️ Sélection des approbateurs officiels")
            st.caption("Sélectionnez le joueur ou capitaine qui approuve les résultats officiels pour chaque équipe :")

            liste_app_rec = []
            for p in [dict_j["j1_rec"]["nom"], dict_j["j2_rec"]["nom"], dict_j["j3_rec"]["nom"]]:
                if p and p not in liste_app_rec:
                    liste_app_rec.append(p)
            if roster_rec:
                for p in roster_rec:
                    if p and p not in liste_app_rec:
                        liste_app_rec.append(p)
            if not liste_app_rec:
                liste_app_rec = [equipe_rec]

            liste_app_vis = []
            for p in [dict_j["j1_vis"]["nom"], dict_j["j2_vis"]["nom"], dict_j["j3_vis"]["nom"]]:
                if p and p not in liste_app_vis:
                    liste_app_vis.append(p)
            if roster_vis:
                for p in roster_vis:
                    if p and p not in liste_app_vis:
                        liste_app_vis.append(p)
            if not liste_app_vis:
                liste_app_vis = [equipe_vis]

            col_app_r, col_app_v = st.columns(2)
            with col_app_r:
                sel_app_rec = st.selectbox(
                    f"Approbateur — {equipe_rec} :",
                    options=liste_app_rec,
                    key="sel_app_rec_choix",
                    help=f"Joueur ou représentant validant la feuille pour {equipe_rec}"
                )
            with col_app_v:
                sel_app_vis = st.selectbox(
                    f"Approbateur — {equipe_vis} :",
                    options=liste_app_vis,
                    key="sel_app_vis_choix",
                    help=f"Joueur ou représentant validant la feuille pour {equipe_vis}"
                )

            st.info(f"📋 **Feuille officielle approuvée par :** `{sel_app_rec}` ({equipe_rec}) et `{sel_app_vis}` ({equipe_vis})")

            # Notification par courriel
            destinataires_envoi = cfg_email.get("destinataires", "").strip()
            if destinataires_envoi:
                st.info(f"✉️ **Courriel officiel :** Sera automatiquement envoyé à `{destinataires_envoi}` avec mention des approbateurs dès votre confirmation.")
            else:
                st.caption("ℹ️ Aucun courriel configuré dans les paramètres.")

            st.markdown("---")
            st.markdown("##### ⚖️ Souhaitez-vous approuver ou annuler l'enregistrement de ce match ?")

            col_btn_ann, col_btn_app = st.columns([1, 1])

            with col_btn_ann:
                if st.button("❌ Annuler / Modifier", use_container_width=True, key="dlg_btn_annuler"):
                    st.rerun()

            with col_btn_app:
                if st.button("✅ Approuver et enregistrer", type="primary", use_container_width=True, key="dlg_btn_approuver"):
                    historique = []
                    if os.path.exists(HISTORIQUE_FILE):
                        try:
                            with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
                                historique = json.load(f)
                        except Exception:
                            historique = []

                    # Régénération des résumés texte et HTML avec les approbateurs sélectionnés
                    txt_res_final, html_res_final = generer_resume_match(
                        equipe_rec,
                        equipe_vis,
                        matchs_dict,
                        tot_rec,
                        tot_vis,
                        pts_j,
                        dict_j,
                        d_match,
                        absents_det,
                        approbateur_rec=sel_app_rec,
                        approbateur_vis=sel_app_vis
                    )

                    donnees_finales = dict(donnees_sauv)
                    donnees_finales["total_receveur"] = tot_rec
                    donnees_finales["total_visiteur"] = tot_vis
                    donnees_finales["approbateur_receveur"] = sel_app_rec
                    donnees_finales["approbateur_visiteur"] = sel_app_vis
                    donnees_finales["points_par_joueur"] = {
                        p_id: {
                            "nom": dict_j[p_id]["nom"],
                            "equipe": dict_j[p_id]["equipe"],
                            "points": pts_j[p_id],
                            "present": dict_j[p_id]["present"],
                            "moyenne": dict_j[p_id].get("moyenne", 0.0)
                        }
                        for p_id in dict_j
                    }
                    donnees_finales["date_enregistrement"] = d_match
                    donnees_finales["html_officiel"] = html_res_final
                    historique.append(donnees_finales)

                    with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
                        json.dump(historique, f, ensure_ascii=False, indent=4)

                    st.session_state["match_en_cours_deja_valide"] = True

                    msg_flash = f"✅ Le match entre **{equipe_rec}** ({tot_rec} pts) et **{equipe_vis}** ({tot_vis} pts) a été approuvé par **{sel_app_rec}** ({equipe_rec}) et **{sel_app_vis}** ({equipe_vis}), et archivé avec succès !"

                    if destinataires_envoi:
                        sujet = f"🎱 Ligue de billard Boule en main : {equipe_rec} ({tot_rec}) vs {equipe_vis} ({tot_vis}) - {d_match}"
                        pj_historique = [HISTORIQUE_FILE] if os.path.exists(HISTORIQUE_FILE) else None
                        with st.spinner("Envoi automatique du courriel en cours (avec historique en pièce jointe)..."):
                            succes_mail, msg_mail = envoyer_courriel(
                                destinataires_envoi,
                                sujet,
                                txt_res_final,
                                html_res_final,
                                cfg_email,
                                pieces_jointes=pj_historique
                            )
                        if succes_mail:
                            mention_pj = f" avec le fichier `{HISTORIQUE_FILE}` en pièce jointe" if pj_historique else ""
                            msg_flash += f"\n\n✉️ {msg_mail} (Envoyé automatiquement{mention_pj} à : `{destinataires_envoi}`)"
                        else:
                            msg_flash += f"\n\n⚠️ {msg_mail}"

                    # Nettoyage et libération
                    if os.path.exists(BACKUP_FILE):
                        try:
                            os.remove(BACKUP_FILE)
                        except Exception:
                            pass
                    if os.path.exists(CORBEILLE_FILE):
                        try:
                            os.remove(CORBEILLE_FILE)
                        except Exception:
                            pass
                    liberer_verrou(sess_id)
                    st.session_state["mode_consultation"] = True
                    st.session_state["message_validation_reussie"] = msg_flash
                    st.rerun()

        # Aperçu rapide disponible avant de déclencher la validation
        with st.expander("👁️ Aperçu rapide du sommaire du match", expanded=False):
            col_ap1, col_ap2 = st.columns(2)
            col_ap1.metric(f"{equipe_receveur}", f"{total_pts_receveur} pts")
            col_ap2.metric(f"{equipe_visiteur}", f"{total_pts_visiteur} pts")

            table_ap_md = [
                f"| Manche | Joueur ({equipe_receveur}) | {equipe_receveur} | {equipe_visiteur} | Joueur ({equipe_visiteur}) |",
                "| :---: | :--- | :---: | :---: | :--- |"
            ]
            for num in range(1, 10):
                m_ap = donnees_a_sauvegarder["matchs"].get(str(num), {})
                sa = m_ap.get("score_a", 0)
                sb = m_ap.get("score_b", 0)
                ja = str(m_ap.get("joueur_a", "")).replace("|", "/")
                jb = str(m_ap.get("joueur_b", "")).replace("|", "/")
                sc_a_str = f"**{sa}**" if sa == 8 else f"{sa}"
                sc_b_str = f"**{sb}**" if sb == 8 else f"{sb}"
                table_ap_md.append(f"| **Manche {num}** | {ja} | {sc_a_str} | {sc_b_str} | {jb} |")
            table_ap_md.append(f"| **TOTAL** | **{equipe_receveur}** | **{total_pts_receveur} pts** | **{total_pts_visiteur} pts** | **{equipe_visiteur}** |")
            st.markdown("\n".join(table_ap_md))

        match_valide = False

        est_deja_valide, date_valid_info = verifier_match_deja_valide(
            equipe_receveur,
            equipe_visiteur,
            donnees_a_sauvegarder["matchs"],
            historique_matchs
        )

        if est_deja_valide:
            mention_date = f" (archivé le {date_valid_info})" if date_valid_info and date_valid_info != "session_actuelle" else ""
            st.warning(
                f"⚠️ **Ce match a déjà été validé et archivé officiellement{mention_date}.**\n\n"
                "Il ne peut pas être validé de nouveau afin d'éviter les doublons dans le classement et les statistiques.\n\n"
                "👉 **Pour modifier les scores ou les joueurs de ce match :** "
                "veuillez utiliser l'option de modification **« ✏️ Rectifier un match archivé »** située dans la section **Espace Administration** en bas de page.\n\n"
                "👉 **Pour enregistrer une nouvelle rencontre :** "
                "cliquez sur le bouton **« 🗑️ Nouveau match »** en haut de page pour réinitialiser la feuille."
            )

        btn_label = "🔒 Match déjà validé (Utiliser la section Administration pour modifier)" if est_deja_valide else "🚀 Valider et enregistrer la feuille de match officielle"
        btn_disabled = (not est_editeur) or est_deja_valide

        if st.button(
            btn_label,
            type="primary" if not est_deja_valide else "secondary",
            use_container_width=True,
            disabled=btn_disabled,
            key="btn_valider_match_principal",
            help="Ce match est déjà validé. Utilisez l'administration pour le rectifier." if est_deja_valide else None
        ):
            if est_deja_valide:
                st.warning("⚠️ Ce match a déjà été validé. Veuillez utiliser l'option de modification dans la section administration ci-dessous.")
            elif manches_invalides:
                st.error(f"❌ Impossible d'enregistrer : veuillez d'abord corriger les manches suivantes : {', '.join(map(str, sorted(set(manches_invalides))))}.")
            else:
                modal_sommaire_approbation(
                    equipe_receveur,
                    equipe_visiteur,
                    donnees_a_sauvegarder["matchs"],
                    total_pts_receveur,
                    total_pts_visiteur,
                    pts_joueurs,
                    dict_joueurs,
                    date_du_match,
                    absents_detectes,
                    texte_resume,
                    html_resume,
                    config_email,
                    my_session_id,
                    donnees_a_sauvegarder,
                    roster_rec,
                    roster_vis,
                    est_deja_valide=est_deja_valide
                )

        # Sauvegarde automatique en arrière-plan (uniquement par l'éditeur actif et si le match n'est pas validé)
        if est_editeur and not match_valide:
            sauvegarder_donnees(donnees_a_sauvegarder)
            st.session_state["scores_en_cours_backup"] = {
                f"s_a_{n}": st.session_state.get(f"s_a_{n}", 0) for n in range(1, 10)
            }
            st.session_state["scores_en_cours_backup"].update({
                f"s_b_{n}": st.session_state.get(f"s_b_{n}", 0) for n in range(1, 10)
            })

        st.divider()

    # ==============================================================================
    # ESPACE ADMINISTRATION (SAISON, SMTP ET SÉCURITÉ) — ONGLET DÉDIÉ
    # ==============================================================================
    if not est_spectateur:
        st.caption("💡 *Astuce : L'Espace Administration (édition des équipes, nouvelle saison, rectification d'un match, SMTP et mot de passe) est accessible directement via l'onglet **⚙️ Administration** en haut de page.*")

if tab_admin is not None:
    with tab_admin:
        st.markdown("### ⚙️ Espace Administration de la Ligue")
        st.caption("Gérez la composition officielle des équipes, rectifiez un match archivé, démarrez une nouvelle saison ou configurez la messagerie SMTP et la sécurité.")
        if True:
            tab_equipes, tab_saison, tab_rectif, tab_export, tab_smtp, tab_secu = st.tabs([
                "👥 Édition des équipes & joueurs",
                "🗓️ Démarrer une nouvelle saison",
                "✏️ Rectifier un match archivé",
                "📤 Envoyer l'historique complet",
                "📧 Configuration SMTP",
                "🔑 Mot de passe d'accès"
            ])

            with tab_equipes:
                st.markdown("#### 👥 Édition des équipes et des joueurs (`equipes-saphir.csv`)")
                st.caption(
                    "Gérez la composition officielle des équipes et de leurs joueurs. "
                    "Conformément au format officiel, **le premier champ est l'équipe, et les trois suivants sont les noms des joueurs de cette équipe**."
                )

                eq_actuelles = charger_equipes_csv()
                lignes_df = []
                for eq_nom, j_liste in eq_actuelles.items():
                    lignes_df.append({
                        "Equipe": eq_nom,
                        "Joueur 1": j_liste[0] if len(j_liste) > 0 else "",
                        "Joueur 2": j_liste[1] if len(j_liste) > 1 else "",
                        "Joueur 3": j_liste[2] if len(j_liste) > 2 else ""
                    })

                df_initial = pd.DataFrame(lignes_df)

                st.markdown("##### 📝 Tableau modifiable des équipes et joueurs")
                st.info("💡 **Instructions :** Vous pouvez modifier directement n'importe quelle cellule ci-dessous. Vous pouvez ajouter une équipe avec la ligne `+` ou en supprimer en sélectionnant la ligne et en appuyant sur `Suppr`.")

                df_modifie = st.data_editor(
                    df_initial,
                    num_rows="dynamic",
                    use_container_width=True,
                    column_config={
                        "Equipe": st.column_config.TextColumn(
                            "Équipe (1er champ)",
                            help="Nom officiel de l'équipe (premier champ dans equipes-saphir.csv)",
                            required=True,
                            width="medium"
                        ),
                        "Joueur 1": st.column_config.TextColumn(
                            "Joueur 1",
                            help="Nom du premier joueur de l'équipe",
                            required=True,
                            width="medium"
                        ),
                        "Joueur 2": st.column_config.TextColumn(
                            "Joueur 2",
                            help="Nom du deuxième joueur de l'équipe",
                            required=True,
                            width="medium"
                        ),
                        "Joueur 3": st.column_config.TextColumn(
                            "Joueur 3",
                            help="Nom du troisième joueur de l'équipe",
                            required=True,
                            width="medium"
                        )
                    },
                    key="data_editor_equipes_saphir"
                )

                col_sv1, col_sv2, col_sv3 = st.columns([1.6, 1.2, 1.2])
                with col_sv1:
                    if st.button("💾 Enregistrer dans equipes-saphir.csv", type="primary", use_container_width=True, key="btn_save_equipes_csv"):
                        noms_vides = df_modifie["Equipe"].astype(str).str.strip() == ""
                        if noms_vides.any():
                            st.error("❌ Certaines lignes ont un nom d'équipe vide. Veuillez renseigner le nom de chaque équipe avant de sauvegarder.")
                        else:
                            succes_eq, msg_eq = sauvegarder_equipes_csv(df_modifie)
                            if succes_eq:
                                st.success(f"✅ {msg_eq}")
                                time.sleep(1.0)
                                st.rerun()
                            else:
                                st.error(f"❌ {msg_eq}")

                with col_sv2:
                    csv_bytes = ""
                    if os.path.exists(EQUIPES_CSV_FILE):
                        try:
                            with open(EQUIPES_CSV_FILE, "r", encoding="utf-8") as f_dl:
                                csv_bytes = f_dl.read()
                        except Exception:
                            pass
                    st.download_button(
                        label="📥 Télécharger equipes-saphir.csv",
                        data=csv_bytes,
                        file_name="equipes-saphir.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="btn_dl_equipes_csv"
                    )

                with col_sv3:
                    with st.popover("📤 Importer un fichier CSV", use_container_width=True):
                        st.markdown("###### Importer un fichier `equipes-saphir.csv`")
                        st.caption("Format par ligne : Équipe, Joueur 1, Joueur 2, Joueur 3.")
                        fichier_importe = st.file_uploader("Choisir un fichier CSV", type=["csv"], key="upload_equipes_csv")
                        if fichier_importe is not None:
                            if st.button("Confirmer le remplacement du fichier", type="primary", use_container_width=True, key="btn_confirm_upload_csv"):
                                try:
                                    contenu_str = fichier_importe.getvalue().decode("utf-8")
                                    lignes_valides = []
                                    for l_imp in contenu_str.strip().splitlines():
                                        pts = [p.strip() for p in l_imp.split(",") if p.strip()]
                                        if len(pts) >= 2:
                                            eq_imp = pts[0]
                                            j_imp = pts[1:]
                                            while len(j_imp) < 3:
                                                j_imp.append(f"Joueur {len(j_imp)+1}")
                                            lignes_valides.append(f"{eq_imp},{j_imp[0]},{j_imp[1]},{j_imp[2]}\n")
                                    if lignes_valides:
                                        with open(EQUIPES_CSV_FILE, "w", encoding="utf-8") as f_w:
                                            f_w.writelines(lignes_valides)
                                        st.success(f"✅ {len(lignes_valides)} équipe(s) importée(s) avec succès !")
                                        time.sleep(1.0)
                                        st.rerun()
                                    else:
                                        st.error("Aucune ligne d'équipe valide trouvée dans le fichier.")
                                except Exception as e_imp:
                                    st.error(f"Erreur lors de l'importation : {e_imp}")

                with st.expander("➕ Formulaire d'ajout rapide d'une équipe", expanded=False):
                    with st.form("form_ajout_equipe_rapide", clear_on_submit=True):
                        col_add1, col_add2, col_add3, col_add4 = st.columns(4)
                        with col_add1:
                            nouveau_nom_eq = st.text_input("Nom de l'équipe :", placeholder="Ex: India")
                        with col_add2:
                            nouveau_j1 = st.text_input("Joueur 1 :", placeholder="Nom du joueur 1")
                        with col_add3:
                            nouveau_j2 = st.text_input("Joueur 2 :", placeholder="Nom du joueur 2")
                        with col_add4:
                            nouveau_j3 = st.text_input("Joueur 3 :", placeholder="Nom du joueur 3")

                        btn_creer_eq = st.form_submit_button("➕ Ajouter l'équipe à equipes-saphir.csv", type="primary")
                        if btn_creer_eq:
                            if not nouveau_nom_eq.strip():
                                st.error("❌ Le nom de l'équipe ne peut pas être vide.")
                            elif nouveau_nom_eq.strip() in eq_actuelles:
                                st.error(f"❌ L'équipe '{nouveau_nom_eq.strip()}' existe déjà dans la liste.")
                            else:
                                j1_final = nouveau_j1.strip() or "Joueur 1"
                                j2_final = nouveau_j2.strip() or "Joueur 2"
                                j3_final = nouveau_j3.strip() or "Joueur 3"
                                eq_actuelles[nouveau_nom_eq.strip()] = [j1_final, j2_final, j3_final]
                                succes_add, msg_add = sauvegarder_equipes_csv(eq_actuelles)
                                if succes_add:
                                    st.success(f"✅ L'équipe '{nouveau_nom_eq.strip()}' a été ajoutée avec succès !")
                                    time.sleep(1.0)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg_add}")

            with tab_saison:
                st.markdown("#### 🗓️ Démarrer une nouvelle saison")
            
                nb_matchs = 0
                if os.path.exists(HISTORIQUE_FILE):
                    try:
                        with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
                            data_hist = json.load(f)
                            if isinstance(data_hist, list):
                                nb_matchs = len(data_hist)
                    except Exception:
                        nb_matchs = 0

                st.write(f"📊 **Statut de l'historique :** `{nb_matchs} match(s)` actuellement enregistré(s) dans `{HISTORIQUE_FILE}`.")
                st.warning("⚠️ **Attention :** Démarrer une nouvelle saison réinitialise complètement l'historique de tous les matchs précédents. Aucun archivage n'est effectué.")

                with st.popover("🚨 Réinitialiser et démarrer la nouvelle saison", use_container_width=True):
                    st.markdown("### ⚠️ Confirmation obligatoire")
                    st.write(f"Voulez-vous vraiment effacer les **{nb_matchs} match(s)** enregistrés dans l'historique ?")
                    st.write("Cette action est irréversible et supprimera le fichier d'historique.")
                    if st.button("🔴 Confirmer la réinitialisation de la saison", type="primary", use_container_width=True):
                        try:
                            if os.path.exists(HISTORIQUE_FILE):
                                os.remove(HISTORIQUE_FILE)
                            st.success("✅ Historique réinitialisé avec succès ! La nouvelle saison est ouverte.")
                            st.rerun()
                        except Exception as e_hist:
                            st.error(f"Erreur lors de la suppression de l'historique : {e_hist}")

            with tab_rectif:
                st.markdown("#### ✏️ Rectifier un match archivé")
                st.caption("Permet de corriger une erreur de score ou de joueur sur un match passé. Une copie de sauvegarde automatique de l'historique est effectuée avant chaque modification.")

                historique_complet = charger_historique_matchs()
                if not historique_complet:
                    st.info("Aucun match n'est actuellement archivé dans l'historique.")
                else:
                    options_rectif = []
                    for i, m_h in enumerate(historique_complet):
                        d_h = m_h.get("date_enregistrement", m_h.get("date", "Date inconnue"))
                        r_h = m_h.get("receveur", "Receveur")
                        v_h = m_h.get("visiteur", "Visiteur")
                        tr_h = m_h.get("total_receveur", 0)
                        tv_h = m_h.get("total_visiteur", 0)
                        rectif_tag = " [Rectifié]" if m_h.get("date_rectification") else ""
                        options_rectif.append(f"Match #{i+1} : {d_h} — {r_h} ({tr_h}) vs {v_h} ({tv_h}){rectif_tag}")

                    idx_sel = st.selectbox(
                        "Sélectionnez le match à corriger :",
                        range(len(options_rectif)),
                        format_func=lambda x: options_rectif[x],
                        key="select_match_to_rectify"
                    )
                    m_sel = historique_complet[idx_sel]

                    rec_sel = m_sel.get("receveur", "Receveur")
                    vis_sel = m_sel.get("visiteur", "Visiteur")
                    date_sel = m_sel.get("date_enregistrement", m_sel.get("date", "Date inconnue"))

                    if m_sel.get("date_rectification"):
                        st.warning(f"ℹ️ Ce match a déjà été rectifié le **{m_sel.get('date_rectification')}** (Motif : *{m_sel.get('motif_rectification')}*).")

                    col_mot1, col_mot2 = st.columns([2, 1])
                    with col_mot1:
                        motif_saisi = st.text_input(
                            "Motif officiel de la rectification :",
                            placeholder="Ex: Correction score manche 3 suite à erreur de feuille",
                            key=f"motif_input_{idx_sel}"
                        )
                    with col_mot2:
                        envoyer_mail_rectif = st.checkbox(
                            "📧 Envoyer courriel rectificatif",
                            value=bool(config_email.get("destinataires")),
                            key=f"check_mail_rect_{idx_sel}",
                            help="Transmet la feuille rectifiée aux destinataires configurés"
                        )

                    if envoyer_mail_rectif:
                        dest_rectif_input = st.text_input(
                            "Destinataire(s) du rectificatif :",
                            value=config_email.get("destinataires", ""),
                            key=f"dest_mail_rect_{idx_sel}"
                        )

                    st.markdown("##### 📋 Correction des 9 manches")
                    matchs_dict_sel = m_sel.get("matchs", {})

                    nouveaux_scores = {}
                    erreurs_manches = []

                    for num_m in range(1, 10):
                        str_m = str(num_m)
                        m_data = matchs_dict_sel.get(str_m, {})
                        ja_def = m_data.get("joueur_a", f"Joueur 1 ({rec_sel})")
                        jb_def = m_data.get("joueur_b", f"Joueur 2 ({vis_sel})")
                        sa_def = int(m_data.get("score_a", 0))
                        sb_def = int(m_data.get("score_b", 0))
                        ja_abs = bool(m_data.get("joueur_a_absent", False))
                        jb_abs = bool(m_data.get("joueur_b_absent", False))

                        with st.container(border=True):
                            c_m_titre, c_m_ja, c_m_sa, c_m_sb, c_m_jb = st.columns([1, 2, 1, 1, 2])
                            c_m_titre.markdown(f"**Manche {num_m}**")
                        
                            nom_a_edite = c_m_ja.text_input(f"Joueur ({rec_sel})", value=ja_def, key=f"rec_ja_{idx_sel}_{num_m}")
                            sa_edite = c_m_sa.number_input(f"Pts {rec_sel}", min_value=0, max_value=8, value=sa_def, key=f"rec_sa_{idx_sel}_{num_m}")
                            sb_edite = c_m_sb.number_input(f"Pts {vis_sel}", min_value=0, max_value=8, value=sb_def, key=f"rec_sb_{idx_sel}_{num_m}")
                            nom_b_edite = c_m_jb.text_input(f"Joueur ({vis_sel})", value=jb_def, key=f"rec_jb_{idx_sel}_{num_m}")

                            if sa_edite == 8 and sb_edite == 8:
                                st.error(f"❌ Manche {num_m} : Les deux joueurs ne peuvent pas avoir 8 points.")
                                erreurs_manches.append(num_m)
                            elif sa_edite < 8 and sb_edite < 8 and (sa_edite > 0 or sb_edite > 0):
                                st.warning(f"⚠️ Manche {num_m} : Un des deux joueurs doit avoir 8 points (règle du billard au 8).")
                                erreurs_manches.append(num_m)

                            nouveaux_scores[str_m] = {
                                "score_a": int(sa_edite),
                                "score_b": int(sb_edite),
                                "joueur_a": nom_a_edite.strip(),
                                "joueur_b": nom_b_edite.strip(),
                                "joueur_a_absent": ja_abs,
                                "joueur_b_absent": jb_abs
                            }

                    tot_rec_nouveau = sum(m["score_a"] for m in nouveaux_scores.values())
                    tot_vis_nouveau = sum(m["score_b"] for m in nouveaux_scores.values())

                    st.markdown(f"**Nouveau score total :** `{rec_sel}` **{tot_rec_nouveau}** — **{tot_vis_nouveau}** `{vis_sel}`")

                    if st.button("💾 Enregistrer la rectification officielle", type="primary", use_container_width=True, key=f"btn_confirm_rectif_{idx_sel}"):
                        if erreurs_manches:
                            st.error(f"❌ Veuillez corriger les erreurs sur les manches : {', '.join(map(str, sorted(set(erreurs_manches))))}")
                        elif not motif_saisi.strip():
                            st.error("❌ Veuillez obligatoirement renseigner un motif pour justifier la rectification de la feuille officielle.")
                        else:
                            # 1. Sauvegarde de sécurité automatique
                            try:
                                backup_fn = os.path.join(BASE_DIR, f"historique_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                                with open(backup_fn, "w", encoding="utf-8") as f_bk:
                                    json.dump(historique_complet, f_bk, ensure_ascii=False, indent=4)
                            except Exception:
                                pass

                            # 2. Mise à jour du match
                            date_rectif_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
                            m_sel["matchs"] = nouveaux_scores
                            m_sel["total_receveur"] = tot_rec_nouveau
                            m_sel["total_visiteur"] = tot_vis_nouveau
                            m_sel["date_rectification"] = date_rectif_str
                            m_sel["motif_rectification"] = motif_saisi.strip()

                            # Reconstitution propre du HTML officiel avec bandeau de rectification
                            m_sel["html_officiel"] = None
                            nouveau_html = obtenir_html_match(m_sel)
                            m_sel["html_officiel"] = nouveau_html

                            historique_complet[idx_sel] = m_sel

                            # 3. Enregistrement sur le disque
                            with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f_h:
                                json.dump(historique_complet, f_h, ensure_ascii=False, indent=4)

                            st.success(f"✅ Match #{idx_sel+1} rectifié avec succès et sauvegardé dans l'historique !")

                            # 4. Envoi éventuel du courriel de rectificatif
                            if envoyer_mail_rectif and dest_rectif_input.strip():
                                sujet_rect = f"[RECTIFICATIF] 🎱 Ligue de billard Boule en main : {rec_sel} ({tot_rec_nouveau}) vs {vis_sel} ({tot_vis_nouveau}) - {date_sel}"
                                texte_rect = (
                                    f"RECTIFICATIF DE MATCH OFFICIEL - Ligue de billard Boule en main\n"
                                    f"Date du match : {date_sel}\n"
                                    f"Date de rectification : {date_rectif_str}\n"
                                    f"Motif : {motif_saisi.strip()}\n\n"
                                    f"Nouveau résultat : {rec_sel} ({tot_rec_nouveau}) vs {vis_sel} ({tot_vis_nouveau})\n\n"
                                    f"Veuillez consulter la feuille HTML ci-jointe pour le détail des manches corrigées."
                                )
                                pj_rect = [HISTORIQUE_FILE] if os.path.exists(HISTORIQUE_FILE) else None
                                with st.spinner("Envoi du courriel de rectificatif en cours..."):
                                    ok_m, rep_m = envoyer_courriel(
                                        dest_rectif_input.strip(),
                                        sujet_rect,
                                        texte_rect,
                                        nouveau_html,
                                        config_email,
                                        pieces_jointes=pj_rect
                                    )
                                if ok_m:
                                    st.success(f"✉️ Courriel de rectificatif envoyé à `{dest_rectif_input.strip()}` !")
                                else:
                                    st.warning(f"⚠️ {rep_m}")

                            time.sleep(1.5)
                            st.rerun()

            with tab_export:
                st.markdown("#### 📤 Envoyer l'historique complet des matchs par courriel")
                st.caption("Génère un bilan officiel complet et convivial (classement général des équipes, chronologie et détails des rencontres) et l'expédie à l'adresse de votre choix.")

                historique_export = charger_historique_matchs()
                if not historique_export:
                    st.info("ℹ️ Aucun match n'est actuellement archivé dans l'historique. L'envoi sera disponible dès qu'une rencontre aura été validée.")
                else:
                    col_nb1, col_nb2 = st.columns(2)
                    col_nb1.metric("📊 Total de matchs archivés", f"{len(historique_export)} match(s)")

                    pts_totaux_saison = 0
                    for m_tmp in historique_export:
                        tr_tmp = m_tmp.get("total_receveur")
                        tv_tmp = m_tmp.get("total_visiteur")
                        if tr_tmp is None:
                            tr_tmp = sum(m_tmp.get("matchs", {}).get(str(i), {}).get("score_a", 0) for i in range(1, 10))
                        if tv_tmp is None:
                            tv_tmp = sum(m_tmp.get("matchs", {}).get(str(i), {}).get("score_b", 0) for i in range(1, 10))
                        try:
                            pts_totaux_saison += int(tr_tmp) + int(tv_tmp)
                        except (ValueError, TypeError):
                            pass

                    col_nb2.metric("🎱 Points cumulés dans la ligue", f"{pts_totaux_saison} pts")

                    st.markdown("##### ✉️ Paramètres d'envoi du bilan officiel")
                    dest_def = config_email.get("destinataires", "").strip()

                    col_dest_in, col_dest_pj = st.columns([3, 2])
                    with col_dest_in:
                        dest_rapport = st.text_input(
                            "Adresse(s) courriel de destination :",
                            value=dest_def,
                            placeholder="Ex: president@ligue.com, secretaire@ligue.com",
                            key="input_dest_rapport_historique",
                            help="Saisissez une ou plusieurs adresses courriel séparées par des virgules."
                        )
                    with col_dest_pj:
                        st.write("")
                        st.write("")
                        inclure_pj_json = st.checkbox(
                            "Joindre le fichier brut (`historique_matchs.json`)",
                            value=True,
                            key="chk_pj_json_hist",
                            help="Ajoute le fichier JSON officiel en pièce jointe du courriel pour archivage informatique."
                        )

                    texte_rapport, html_rapport = generer_rapport_historique_convivial(historique_export)

                    col_btn_send, col_btn_dl = st.columns([2, 1])
                    with col_btn_send:
                        if st.button("📤 Envoyer le rapport officiel complet", type="primary", use_container_width=True, key="btn_send_rapport_complet"):
                            dest_clean = dest_rapport.strip()
                            if not dest_clean or "@" not in dest_clean:
                                st.error("⚠️ Veuillez renseigner au moins une adresse courriel valide.")
                            elif not config_email.get("smtp_serveur"):
                                st.error("⚠️ Le serveur SMTP n'est pas encore configuré. Rendez-vous dans l'onglet 'Configuration SMTP' pour le configurer.")
                            else:
                                date_jour = datetime.now().strftime("%d/%m/%Y")
                                sujet_rapport = f"🎱 Ligue de billard Boule en main : Bilan officiel et Historique ({len(historique_export)} matchs) - {date_jour}"
                                pj_list = [HISTORIQUE_FILE] if (inclure_pj_json and os.path.exists(HISTORIQUE_FILE)) else None

                                with st.spinner("Génération et envoi de l'historique complet en cours..."):
                                    ok_env, msg_env = envoyer_courriel(
                                        dest_clean,
                                        sujet_rapport,
                                        texte_rapport,
                                        html_rapport,
                                        config_email,
                                        pieces_jointes=pj_list
                                    )
                                if ok_env:
                                    pj_str = " (avec `historique_matchs.json` en pièce jointe)" if pj_list else ""
                                    st.success(f"✅ {msg_env} — Bilan officiel envoyé à `{dest_clean}`{pj_str} !")
                                else:
                                    st.error(f"❌ Échec de l'envoi : {msg_env}")

                    with col_btn_dl:
                        st.download_button(
                            label="📥 Télécharger le bilan (HTML)",
                            data=html_rapport,
                            file_name=f"bilan_historique_boule_en_main_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                            mime="text/html",
                            use_container_width=True,
                            key="dl_rapport_historique_html"
                        )

                    with st.expander("👁️ Prévisualiser le rapport convivial avant l'envoi", expanded=False):
                        st.components.v1.html(html_rapport, height=650, scrolling=True)

                st.divider()
                st.markdown("#### 🏆 Envoyer l'historique officiel des tournois par courriel")
                st.caption("Expédie le fichier officiel `historique_tournois.json` avec la liste et les résultats de tous les tournois enregistrés aux administrateurs définis dans la configuration SMTP.")
                hist_t_exp = charger_historique_tournois()
                col_exp_t1, col_exp_t2 = st.columns(2)
                col_exp_t1.metric("🏆 Tournois dans l'historique", f"{len(hist_t_exp)} tournoi(s)")
                dest_def_t = config_email.get("destinataires", "").strip()
                col_exp_t2.metric("📬 Destinataire(s) SMTP", dest_def_t if dest_def_t else "Non configuré")

                dest_t_input = st.text_input(
                    "Adresse(s) courriel des administrateurs destinataires :",
                    value=dest_def_t,
                    placeholder="Ex: president@ligue.com, marqueur@ligue.com",
                    key="input_dest_t_export",
                    help="Par défaut, les adresses des administrateurs enregistrées dans la configuration SMTP ci-dessous."
                )

                if st.button("📤 Envoyer l'historique des tournois (avec pièce jointe JSON)", type="primary", key="btn_send_export_t_email"):
                    with st.spinner("Envoi de l'historique des tournois en cours..."):
                        ok_exp_t, msg_exp_t = envoyer_courriel_sauvegarde_tournoi(None, destinataires_specifiques=dest_t_input.strip())
                    if ok_exp_t:
                        st.success(f"✅ {msg_exp_t} (Envoyé à : `{dest_t_input.strip()}` avec `{os.path.basename(HISTORIQUE_TOURNOIS_FILE)}`)")
                    else:
                        st.error(f"❌ {msg_exp_t}")

            with tab_smtp:
                st.markdown("#### ⚙️ Configuration du serveur de messagerie (SMTP)")
                smtp_dest = st.text_input("Courriels administrateurs / Destinataire(s) (séparés par virgule)", value=config_email.get("destinataires", ""), key="admin_smtp_dest", help="Adresses qui recevront les résultats officiels des matchs ainsi que les sauvegardes des tournois avec historique_tournois.json en pièce jointe.")
                col_c1, col_c2 = st.columns(2)
                smtp_serveur = col_c1.text_input("Serveur SMTP", value=config_email.get("smtp_serveur", "smtp.gmail.com"), key="admin_smtp_serveur")
                smtp_port = col_c2.number_input("Port SMTP", value=int(config_email.get("smtp_port", 587)), key="admin_smtp_port")
                smtp_expediteur = col_c1.text_input("Courriel expéditeur", value=config_email.get("smtp_expediteur", ""), key="admin_smtp_exp")
                smtp_mdp = col_c2.text_input("Mot de passe / Clé d'application", type="password", value=config_email.get("smtp_mdp", ""), key="admin_smtp_pwd")
                smtp_ssl = st.checkbox("Utiliser SSL (Port 465)", value=config_email.get("smtp_ssl", False), key="admin_smtp_ssl")

                col_btn_cfg1, col_btn_cfg2 = st.columns(2)
                with col_btn_cfg1:
                    if st.button("💾 Enregistrer la configuration SMTP", use_container_width=True):
                        nouvelle_cfg = {
                            "destinataires": smtp_dest,
                            "smtp_serveur": smtp_serveur,
                            "smtp_port": int(smtp_port),
                            "smtp_expediteur": smtp_expediteur,
                            "smtp_mdp": smtp_mdp,
                            "smtp_ssl": smtp_ssl
                        }
                        if sauvegarder_config_email(nouvelle_cfg):
                            config_email = nouvelle_cfg
                            st.success("✅ Configuration SMTP enregistrée avec succès dans le fichier !")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la sauvegarde du fichier.")

                with col_btn_cfg2:
                    if st.button("🧪 Tester la configuration (courriel test)", use_container_width=True):
                        if not smtp_dest:
                            st.error("⚠️ Veuillez renseigner au moins une adresse de destinataire.")
                        elif not smtp_expediteur:
                            st.error("⚠️ Veuillez renseigner l'adresse courriel de l'expéditeur.")
                        else:
                            cfg_test = {
                                "destinataires": smtp_dest,
                                "smtp_serveur": smtp_serveur,
                                "smtp_port": int(smtp_port),
                                "smtp_expediteur": smtp_expediteur,
                                "smtp_mdp": smtp_mdp,
                                "smtp_ssl": smtp_ssl
                            }
                            with st.spinner("Test de connexion SMTP en cours..."):
                                succes_test, msg_test = envoyer_courriel(
                                    smtp_dest,
                                    "🎱 Test de configuration SMTP - Ligue de billard Boule en main",
                                    "Ce message confirme que votre configuration SMTP fonctionne correctement !",
                                    "<p>Ce message confirme que votre configuration <strong>SMTP</strong> fonctionne correctement !</p>",
                                    cfg_test
                                )
                            if succes_test:
                                st.success(f"✅ {msg_test} (Envoyé à : `{smtp_dest}`)")
                            else:
                                st.error(f"❌ {msg_test}")

            with tab_secu:
                st.markdown("#### 🔑 Modifier le mot de passe d'accès à l'application")
                nouveau_mdp = st.text_input("Nouveau mot de passe d'accès", type="password", key="new_admin_pwd")
                confirm_mdp = st.text_input("Confirmer le nouveau mot de passe", type="password", key="confirm_admin_pwd")
                if st.button("💾 Mettre à jour le mot de passe", use_container_width=True):
                    if not nouveau_mdp:
                        st.error("Le mot de passe ne peut pas être vide.")
                    elif nouveau_mdp != confirm_mdp:
                        st.error("Les deux mots de passe ne correspondent pas.")
                    else:
                        if sauvegarder_mot_de_passe_admin(nouveau_mdp):
                            st.success("✅ Mot de passe d'accès mis à jour avec succès !")
                        else:
                            st.error("Erreur lors de la sauvegarde.")


with tab_stats:
    afficher_tableau_de_bord_progression(historique_matchs)

with tab_tournoi:
    afficher_onglet_tournois()
