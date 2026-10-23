import json
import math
import random
import os
import re
import smtplib
import time
import uuid
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Ligue de billard Boule en main - Saisie",
    page_icon="🎱",
    layout="wide"
)

# Fichiers de données et chemins d'accès robustes
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

BACKUP_FILE = get_data_path("sauvegarde_saisie_secours.json")
CORBEILLE_FILE = get_data_path("sauvegarde_annulee_secours.json")
HISTORIQUE_FILE = get_data_path("historique_matchs.json")
TOURNOIS_FILE = get_data_path("tournois_data.json")
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

def sauvegarder_tournois_data(data):
    """Enregistre les données des tournois dans le fichier JSON."""
    try:
        with open(TOURNOIS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Erreur lors de l'enregistrement du tournoi : {e}")
        return False

def obtenir_tous_les_joueurs_tournoi(equipes_dict=None):
    """Récupère l'ensemble des joueurs disponibles (équipes et historique)."""
    joueurs = set()
    if equipes_dict:
        for eq, liste_j in equipes_dict.items():
            for j in liste_j:
                if j and not j.startswith("Joueur "):
                    joueurs.add(j.strip())
    if os.path.exists(EQUIPES_CSV_FILE):
        try:
            with open(EQUIPES_CSV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = [p.strip() for p in line.strip().split(",") if p.strip()]
                    if len(parts) >= 2:
                        for p in parts[1:]:
                            if p and not p.startswith("Joueur "):
                                joueurs.add(p)
        except Exception:
            pass
    if os.path.exists(HISTORIQUE_FILE):
        try:
            with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
                h = json.load(f)
                for m in h:
                    for num, manche in m.get("matchs", {}).items():
                        ja = (manche.get("joueur_a") or "").strip()
                        jb = (manche.get("joueur_b") or "").strip()
                        if ja and not ja.startswith("Joueur "): joueurs.add(ja)
                        if jb and not jb.startswith("Joueur "): joueurs.add(jb)
        except Exception:
            pass
    return sorted(list(joueurs))

def generer_arbre_elimination(participants, race_to=2, titre="Tournoi"):
    """Génère un arbre à élimination directe complet avec Byes automatiques."""
    p_liste = list(participants)
    random.shuffle(p_liste)
    n = len(p_liste)
    if n < 2:
        return None

    k = 1
    while k < n:
        k *= 2

    noms_tours = {
        2: ["Finale"],
        4: ["Demi-finales", "Finale"],
        8: ["Quarts de finale", "Demi-finales", "Finale"],
        16: ["Huitièmes de finale", "Quarts de finale", "Demi-finales", "Finale"],
        32: ["1/16 de finale", "Huitièmes de finale", "Quarts de finale", "Demi-finales", "Finale"]
    }
    total_tours = int(math.log2(k))
    tours_labels = noms_tours.get(k, [f"Tour {i+1}" for i in range(total_tours)])

    nb_byes = k - n
    liste_depart = []
    part_idx = 0
    bye_count = 0
    for i in range(k):
        if bye_count < nb_byes and i % 2 == 1:
            liste_depart.append("BYE (Exempt)")
            bye_count += 1
        else:
            if part_idx < len(p_liste):
                liste_depart.append(p_liste[part_idx])
                part_idx += 1
            else:
                liste_depart.append("BYE (Exempt)")

    tours = []
    nb_matchs_tour = k // 2
    matchs_tour_1 = []
    for m_i in range(nb_matchs_tour):
        eq_a = liste_depart[2 * m_i]
        eq_b = liste_depart[2 * m_i + 1]
        termine = False
        vainqueur = None
        sc_a, sc_b = 0, 0
        if eq_b == "BYE (Exempt)" and eq_a != "BYE (Exempt)":
            termine = True
            vainqueur = eq_a
            sc_a = race_to
        elif eq_a == "BYE (Exempt)" and eq_b != "BYE (Exempt)":
            termine = True
            vainqueur = eq_b
            sc_b = race_to

        matchs_tour_1.append({
            "id": f"T1_M{m_i+1}",
            "equipe_a": eq_a,
            "equipe_b": eq_b,
            "score_a": sc_a,
            "score_b": sc_b,
            "termine": termine,
            "vainqueur": vainqueur
        })

    tours.append({
        "numero": 1,
        "nom": tours_labels[0],
        "matchs": matchs_tour_1
    })

    for t_i in range(2, total_tours + 1):
        nb_matchs = k // (2 ** t_i)
        matchs_t = []
        for m_i in range(nb_matchs):
            match_source_1 = tours[t_i - 2]["matchs"][2 * m_i]
            match_source_2 = tours[t_i - 2]["matchs"][2 * m_i + 1]
            eq_a = match_source_1["vainqueur"] or "À déterminer"
            eq_b = match_source_2["vainqueur"] or "À déterminer"
            matchs_t.append({
                "id": f"T{t_i}_M{m_i+1}",
                "equipe_a": eq_a,
                "equipe_b": eq_b,
                "score_a": 0,
                "score_b": 0,
                "termine": False,
                "vainqueur": None
            })
        tours.append({
            "numero": t_i,
            "nom": tours_labels[t_i - 1],
            "matchs": matchs_t
        })

    return {
        "titre": titre,
        "date_creation": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "format": "elimination",
        "race_to": race_to,
        "participants": p_liste,
        "total_tours": total_tours,
        "tours": tours,
        "statut": "en_cours",
        "vainqueur_final": None,
        "finaliste": None
    }

def actualiser_score_elimination(tournoi, tour_num, match_id, score_a, score_b):
    """Enregistre le score et qualifie automatiquement le vainqueur pour le tour suivant."""
    t_idx = tour_num - 1
    if t_idx < 0 or t_idx >= len(tournoi["tours"]):
        return False
    tour_courant = tournoi["tours"][t_idx]

    m_trouve = None
    m_idx_in_tour = 0
    for idx, m in enumerate(tour_courant["matchs"]):
        if m["id"] == match_id:
            m_trouve = m
            m_idx_in_tour = idx
            break

    if not m_trouve:
        return False

    m_trouve["score_a"] = score_a
    m_trouve["score_b"] = score_b
    if score_a == score_b:
        return False

    vainqueur = m_trouve["equipe_a"] if score_a > score_b else m_trouve["equipe_b"]
    perdant = m_trouve["equipe_b"] if score_a > score_b else m_trouve["equipe_a"]
    m_trouve["vainqueur"] = vainqueur
    m_trouve["termine"] = True

    if tour_num < tournoi["total_tours"]:
        prochain_tour = tournoi["tours"][tour_num]
        prochain_match_idx = m_idx_in_tour // 2
        prochain_match = prochain_tour["matchs"][prochain_match_idx]
        if m_idx_in_tour % 2 == 0:
            prochain_match["equipe_a"] = vainqueur
        else:
            prochain_match["equipe_b"] = vainqueur
    else:
        tournoi["vainqueur_final"] = vainqueur
        tournoi["finaliste"] = perdant
        tournoi["statut"] = "termine"
    return True

def generer_round_robin(participants, race_to=2, titre="Tournoi"):
    """Génère un championnat toutes rondes (Round-Robin)."""
    p_liste = list(participants)
    random.shuffle(p_liste)
    matchs = []
    m_idx = 1
    for i in range(len(p_liste)):
        for j in range(i + 1, len(p_liste)):
            matchs.append({
                "id": f"RR_M{m_idx}",
                "equipe_a": p_liste[i],
                "equipe_b": p_liste[j],
                "score_a": 0,
                "score_b": 0,
                "termine": False,
                "vainqueur": None
            })
            m_idx += 1
    return {
        "titre": titre,
        "date_creation": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "format": "round_robin",
        "race_to": race_to,
        "participants": p_liste,
        "matchs": matchs,
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

def generer_html_tournoi(tournoi, mode="simple"):
    """Génère la feuille officielle imprimable du tournoi calibrée pour une page A4."""
    logo_b64 = charger_armoiries_base64()
    src_val = logo_b64 if logo_b64 else "cid:armoiries_logo"
    arm_existe = bool(logo_b64 or os.path.isfile(find_armoiries_path()))
    logo_td = f'<td class="header-logo-td" style="width: 50px; vertical-align: middle; padding-right: 10px;"><img class="header-logo-img" src="{src_val}" alt="Armoiries" style="height: 46px; width: 46px; object-fit: contain; border-radius: 4px;"></td>' if arm_existe else ''

    titre_t = tournoi.get("titre", "Tournoi officiel")
    date_t = tournoi.get("date_creation", "")
    mode_str = "Simple (1 contre 1)" if mode == "simple" else "Double (2 contre 2)"
    race_to = tournoi.get("race_to", 2)
    format_str = f"Élimination directe (Course à {race_to})" if tournoi.get("format") == "elimination" else f"Championnat toutes rondes (Course à {race_to})"

    podium_html = ""
    if tournoi.get("statut") == "termine" and tournoi.get("vainqueur_final"):
        v_final = tournoi["vainqueur_final"]
        fin_final = tournoi.get("finaliste", "Non spécifié")
        podium_html = f"""
        <div style="background: linear-gradient(135deg, #fff9c4, #fffde7); border: 2px solid #fbc02d; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; text-align: center;">
            <div style="font-size: 14px; font-weight: bold; color: #f57f17; margin-bottom: 2px;">🏆 PALMARÈS DU TOURNOI</div>
            <div style="font-size: 13px; color: #222;">
                🥇 <strong>Champion :</strong> <span style="font-size: 15px; color: #0b3c5d; font-weight: bold;">{v_final}</span>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                🥈 <strong>Finaliste :</strong> <span style="font-size: 13px; color: #555;">{fin_final}</span>
            </div>
        </div>
        """

    lignes_matchs = []
    if tournoi.get("format") == "elimination":
        for t in tournoi.get("tours", []):
            nom_tour = t["nom"]
            for m in t["matchs"]:
                ea = m["equipe_a"]
                eb = m["equipe_b"]
                sa = m.get("score_a", 0)
                sb = m.get("score_b", 0)
                vainq = m.get("vainqueur")
                statut_txt = f"🏆 <strong>{vainq}</strong>" if m.get("termine") else "En attente"
                score_txt = f"{sa} - {sb}" if m.get("termine") else "-"
                lignes_matchs.append(f"""
                <tr style="border-bottom: 1px solid #e0e0e0; text-align: center;">
                    <td style="padding: 4px; font-weight: bold; color: #0b3c5d;">{nom_tour}</td>
                    <td style="padding: 4px; text-align: left;">{ea}</td>
                    <td style="padding: 4px; font-weight: bold; font-size: 12px;">{score_txt}</td>
                    <td style="padding: 4px; text-align: left;">{eb}</td>
                    <td style="padding: 4px;">{statut_txt}</td>
                </tr>
                """)
    else:
        for idx, m in enumerate(tournoi.get("matchs", []), 1):
            ea = m["equipe_a"]
            eb = m["equipe_b"]
            sa = m.get("score_a", 0)
            sb = m.get("score_b", 0)
            vainq = m.get("vainqueur")
            statut_txt = f"🏆 <strong>{vainq}</strong>" if m.get("termine") else "En attente"
            score_txt = f"{sa} - {sb}" if m.get("termine") else "-"
            lignes_matchs.append(f"""
            <tr style="border-bottom: 1px solid #e0e0e0; text-align: center;">
                <td style="padding: 4px; font-weight: bold; color: #0b3c5d;">Match #{idx}</td>
                <td style="padding: 4px; text-align: left;">{ea}</td>
                <td style="padding: 4px; font-weight: bold; font-size: 12px;">{score_txt}</td>
                <td style="padding: 4px; text-align: left;">{eb}</td>
                <td style="padding: 4px;">{statut_txt}</td>
            </tr>
            """)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Feuille officielle de tournoi - {titre_t}</title>
    <style>
        {STYLE_PRINT_A4}
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.4;
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
        <table class="header-table" style="width: 100%; border-bottom: 2px solid #0b3c5d; padding-bottom: 5px; margin-bottom: 8px; border-collapse: collapse;">
            <tr>
                {logo_td}
                <td class="header-title" style="vertical-align: middle;">
                    <h2 class="header-title-h2" style="color: #0b3c5d; margin: 0; font-size: 18px;">🎱 Ligue de billard Boule en main</h2>
                    <div class="header-title-sub" style="color: #555; font-size: 12px; font-weight: bold; margin-top: 2px;">{titre_t} — {mode_str}</div>
                </td>
            </tr>
        </table>
        <p class="date-para" style="margin: 3px 0 6px 0; font-size: 11px;">
            <strong>Date :</strong> {date_t} &nbsp;|&nbsp; 
            <strong>Format :</strong> {format_str} &nbsp;|&nbsp; 
            <strong>Participants :</strong> {len(tournoi.get('participants', []))}
        </p>
        {podium_html}
        <table class="manches-table" style="width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 4px;">
            <thead>
                <tr style="background-color: #0b3c5d; color: white;">
                    <th style="padding: 5px 4px;">Tour / Rencontre</th>
                    <th style="padding: 5px 4px; text-align: left;">Participant A</th>
                    <th style="padding: 5px 4px;">Score</th>
                    <th style="padding: 5px 4px; text-align: left;">Participant B</th>
                    <th style="padding: 5px 4px;">Vainqueur</th>
                </tr>
            </thead>
            <tbody>
                {''.join(lignes_matchs)}
            </tbody>
        </table>
        <p class="footer-note" style="font-size: 9px; color: #777; margin-top: 8px; text-align: center;">
            Tableau officiel généré via l'application de la Ligue de billard Boule en main.
        </p>
    </div>
</body>
</html>
"""
    return html

def afficher_section_tournoi(mode="simple"):
    """Affiche l'interface complète de configuration ou de déroulement d'un tournoi (Simple ou Double)."""
    est_spectateur = st.session_state.get("est_spectateur", False)
    est_editeur = not est_spectateur

    tournois_data = charger_tournois_data()
    tournoi = tournois_data.get(mode)

    libelle_mode = "Tournoi en Simple (1 contre 1)" if mode == "simple" else "Tournoi en Double (2 contre 2)"
    st.markdown(f"### {'👤' if mode == 'simple' else '👥'} {libelle_mode}")

    # 1. CAS OÙ AUCUN TOURNOI N'EST EN COURS : FORMULAIRE DE CRÉATION
    if not tournoi:
        st.caption(f"Configurez les paramètres et inscrivez les participants pour lancer un nouveau {libelle_mode.lower()}.")
        with st.container(border=True):
            col_cfg1, col_cfg2 = st.columns([2, 1])
            with col_cfg1:
                titre_defaut = f"Tournoi {'Simple' if mode == 'simple' else 'Double'} — {datetime.now().strftime('%d/%m/%Y')}"
                titre_saisi = st.text_input("Nom du tournoi :", value=titre_defaut, key=f"tournoi_titre_{mode}")
                type_format = st.radio(
                    "Format de compétition :",
                    ["🏆 Élimination directe (Arbre de tournoi)", "🔄 Championnat toutes rondes (Round-Robin)"],
                    key=f"tournoi_format_{mode}"
                )
            with col_cfg2:
                race_to = st.number_input(
                    "Nombre de manches gagnantes (Course à) :",
                    min_value=1,
                    max_value=10,
                    value=2,
                    step=1,
                    key=f"tournoi_race_{mode}",
                    help="Le premier joueur ou duo à atteindre ce nombre de manches remporte la rencontre."
                )

            st.divider()

            # Sélection des participants
            joueurs_disponibles = obtenir_tous_les_joueurs_tournoi()

            # Gestion des invités personnalisés
            key_invites = f"invites_tournoi_{mode}"
            if key_invites not in st.session_state:
                st.session_state[key_invites] = []

            col_inv1, col_inv2 = st.columns([3, 1])
            with col_inv1:
                nouveau_joueur = st.text_input("Ajouter un joueur invité / remplaçant :", key=f"input_invite_{mode}", placeholder="Ex: Jean Tremblay")
            with col_inv2:
                st.write("")
                if st.button("➕ Ajouter l'invité", key=f"btn_add_invite_{mode}", use_container_width=True):
                    if nouveau_joueur.strip():
                        nom_prop = nouveau_joueur.strip()
                        if nom_prop not in joueurs_disponibles and nom_prop not in st.session_state[key_invites]:
                            st.session_state[key_invites].append(nom_prop)
                            st.rerun()

            tous_candidats = sorted(list(set(joueurs_disponibles + st.session_state[key_invites])))

            participants_finaux = []

            if mode == "simple":
                st.markdown("##### 👤 Liste des joueurs participants")
                selection_j = st.multiselect(
                    "Sélectionnez les joueurs inscrits :",
                    options=tous_candidats,
                    default=tous_candidats[:8] if len(tous_candidats) >= 8 else tous_candidats,
                    key=f"sel_participants_{mode}",
                    help="Cochez tous les joueurs qui participent au tournoi."
                )
                participants_finaux = selection_j
                st.caption(f"ℹ️ **{len(participants_finaux)} joueur(s) inscrit(s)** au tournoi.")

            else:
                # Mode DOUBLE
                st.markdown("##### 👥 Constitution des équipes de double")
                methode_duos = st.radio(
                    "Méthode de constitution des duos :",
                    ["🎲 Tirage au sort aléatoire (Pige des équipes)", "✍️ Formation manuelle des duos"],
                    key=f"methode_duos_{mode}"
                )

                if methode_duos == "🎲 Tirage au sort aléatoire (Pige des équipes)":
                    selection_pool = st.multiselect(
                        "Sélectionnez tous les joueurs qui participeront au tirage au sort :",
                        options=tous_candidats,
                        default=tous_candidats[:8] if len(tous_candidats) >= 8 else tous_candidats,
                        key=f"pool_double_{mode}"
                    )
                    st.caption(f"Pool de joueurs sélectionnés : **{len(selection_pool)} joueurs**")

                    if len(selection_pool) % 2 != 0:
                        st.warning("⚠️ Le nombre de joueurs sélectionnés est impair. Veuillez ajouter ou retirer un joueur pour former des paires complètes.")

                    if f"paires_tirees_{mode}" in st.session_state and st.session_state[f"paires_tirees_{mode}"]:
                        st.markdown("###### 🎲 Paires tirées au sort :")
                        for idx_p, p_nom in enumerate(st.session_state[f"paires_tirees_{mode}"], 1):
                            st.markdown(f"• **Duo #{idx_p}** : `{p_nom}`")
                        participants_finaux = st.session_state[f"paires_tirees_{mode}"]

                    if st.button("🎲 Tirer les équipes au sort", key=f"btn_pige_{mode}", disabled=len(selection_pool) < 4 or len(selection_pool) % 2 != 0):
                        pool_shuffled = list(selection_pool)
                        random.shuffle(pool_shuffled)
                        paires = []
                        for i in range(0, len(pool_shuffled), 2):
                            paires.append(f"{pool_shuffled[i]} & {pool_shuffled[i+1]}")
                        st.session_state[f"paires_tirees_{mode}"] = paires
                        participants_finaux = paires
                        st.rerun()

                else:
                    # Formation manuelle des duos
                    st.caption("Entrez les noms des équipes ou paires (ex: Guy V. & André St-P.) :")
                    nb_duos = st.number_input("Nombre de duos :", min_value=2, max_value=16, value=4, step=1, key=f"nb_duos_man_{mode}")
                    duos_manuels = []
                    for i in range(int(nb_duos)):
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            j_a = st.selectbox(f"Duo #{i+1} — Joueur 1 :", options=tous_candidats, index=i % len(tous_candidats) if tous_candidats else 0, key=f"duo_{i}_ja_{mode}")
                        with col_d2:
                            j_b = st.selectbox(f"Duo #{i+1} — Joueur 2 :", options=tous_candidats, index=(i+1) % len(tous_candidats) if tous_candidats else 0, key=f"duo_{i}_jb_{mode}")
                        duos_manuels.append(f"{j_a} & {j_b}")
                    participants_finaux = duos_manuels

            st.divider()

            btn_lancer = st.button(
                "🚀 Lancer le tournoi et générer le tableau officiel",
                type="primary",
                use_container_width=True,
                disabled=len(participants_finaux) < 2,
                key=f"btn_lancer_{mode}"
            )

            if btn_lancer:
                if len(participants_finaux) < 2:
                    st.error("⚠️ Il faut au moins 2 participants pour démarrer un tournoi.")
                else:
                    format_slug = "elimination" if "Élimination" in type_format else "round_robin"
                    if format_slug == "elimination":
                        t_cree = generer_arbre_elimination(participants_finaux, race_to=race_to, titre=titre_saisi)
                    else:
                        t_cree = generer_round_robin(participants_finaux, race_to=race_to, titre=titre_saisi)

                    tournois_data[mode] = t_cree
                    sauvegarder_tournois_data(tournois_data)
                    st.success("✅ Tournoi généré avec succès !")
                    st.rerun()

    # 2. CAS OÙ UN TOURNOI EST EN COURS OU TERMINÉ
    else:
        titre_t = tournoi.get("titre", "Tournoi officiel")
        format_type = tournoi.get("format", "elimination")
        race_to = tournoi.get("race_to", 2)
        statut = tournoi.get("statut", "en_cours")

        col_top1, col_top2, col_top3 = st.columns([2.5, 1, 1])
        with col_top1:
            st.markdown(f"#### 🏆 **{titre_t}**")
            badge_statut = "🟢 **En cours**" if statut == "en_cours" else "🏆 **Tournoi Terminé**"
            format_nom = f"Élimination directe (Course à {race_to})" if format_type == "elimination" else f"Championnat Round-Robin (Course à {race_to})"
            st.caption(f"Statut : {badge_statut} &nbsp;|&nbsp; Format : `{format_nom}` &nbsp;|&nbsp; Créé le : {tournoi.get('date_creation', 'N/D')}")

        with col_top2:
            html_tournoi = generer_html_tournoi(tournoi, mode=mode)
            html_t_json = json.dumps(html_tournoi)
            st.components.v1.html(
                f"""
                <button onclick="imprimerTournoi()" style="width:100%; height:38px; background-color:#0b3c5d; color:white; border:none; border-radius:6px; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif; font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
                    🖨️ Imprimer (A4)
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

        with col_top3:
            with st.popover("🔄 Réinitialiser", use_container_width=True, disabled=not est_editeur):
                st.markdown("### ⚠️ Réinitialisation")
                st.write("Voulez-vous clôturer ce tournoi et en configurer un nouveau ?")
                st.caption("Les données actuelles seront effacées pour démarrer une nouvelle compétition.")
                if st.button("🔴 Confirmer la réinitialisation", type="primary", use_container_width=True, key=f"btn_confirm_reset_{mode}"):
                    tournois_data[mode] = None
                    sauvegarder_tournois_data(tournois_data)
                    st.rerun()

        # Podium si terminé
        if statut == "termine" and tournoi.get("vainqueur_final"):
            st.balloons()
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

        st.divider()

        # DÉROULEMENT SELON LE FORMAT
        if format_type == "elimination":
            st.markdown("##### 🌳 Tableau des rencontres (Arbre de tournoi)")
            tours = tournoi.get("tours", [])
            tours_onglets = [t["nom"] for t in tours]

            if tours_onglets:
                tabs_t = st.tabs(tours_onglets)
                for t_idx, tab_tour in enumerate(tabs_t):
                    tour_courant = tours[t_idx]
                    tour_num = tour_courant["numero"]
                    with tab_tour:
                        st.markdown(f"###### **{tour_courant['nom']}** (Course à {race_to})")
                        matchs = tour_courant.get("matchs", [])

                        for m in matchs:
                            m_id = m["id"]
                            ea = m["equipe_a"]
                            eb = m["equipe_b"]
                            termine = m.get("termine", False)
                            vainq = m.get("vainqueur")
                            sa = m.get("score_a", 0)
                            sb = m.get("score_b", 0)

                            with st.container(border=True):
                                col_m1, col_m2 = st.columns([3, 2])
                                with col_m1:
                                    if termine:
                                        st.markdown(f"**{m_id}** : **{ea}** ({sa}) vs ({sb}) **{eb}**")
                                        st.success(f"🏆 **Qualifié :** {vainq}")
                                    else:
                                        if ea == "À déterminer" or eb == "À déterminer":
                                            st.markdown(f"**{m_id}** : `{ea}` vs `{eb}`")
                                            st.caption("⏳ En attente des vainqueurs du tour précédent...")
                                        elif ea == "BYE (Exempt)" or eb == "BYE (Exempt)":
                                            st.markdown(f"**{m_id}** : `{ea}` vs `{eb}`")
                                            st.info(f"✨ Qualifié d'office par Bye : **{vainq or ea or eb}**")
                                        else:
                                            st.markdown(f"**{m_id}** : 🎯 **{ea}** vs **{eb}**")
                                            st.caption(f"Course à {race_to} victoires")

                                with col_m2:
                                    if not termine and ea != "À déterminer" and eb != "À déterminer" and "BYE" not in ea and "BYE" not in eb:
                                        col_s1, col_s2, col_s3 = st.columns([1, 1, 1.5])
                                        with col_s1:
                                            sc_a_in = st.number_input(f"{ea[:10]}", min_value=0, max_value=race_to, value=0, key=f"sc_a_{mode}_{m_id}")
                                        with col_s2:
                                            sc_b_in = st.number_input(f"{eb[:10]}", min_value=0, max_value=race_to, value=0, key=f"sc_b_{mode}_{m_id}")
                                        with col_s3:
                                            st.write("")
                                            if st.button("✅ Valider", key=f"btn_v_{mode}_{m_id}", use_container_width=True, disabled=not est_editeur):
                                                if sc_a_in == sc_b_in:
                                                    st.error("Match nul impossible.")
                                                elif sc_a_in < race_to and sc_b_in < race_to:
                                                    st.warning(f"Un joueur doit atteindre {race_to} victoires.")
                                                else:
                                                    actualiser_score_elimination(tournoi, tour_num, m_id, sc_a_in, sc_b_in)
                                                    sauvegarder_tournois_data(tournois_data)
                                                    st.rerun()

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

                with st.container(border=True):
                    col_rm1, col_rm2 = st.columns([3, 2])
                    with col_rm1:
                        if termine:
                            st.markdown(f"**{m_id}** : **{ea}** ({sa}) vs ({sb}) **{eb}**")
                            st.success(f"🏆 Vainqueur : {m['vainqueur']}")
                        else:
                            st.markdown(f"**{m_id}** : 🎯 **{ea}** vs **{eb}**")
                            st.caption(f"Course à {race_to} victoires")

                    with col_rm2:
                        if not termine:
                            col_s1, col_s2, col_s3 = st.columns([1, 1, 1.5])
                            with col_s1:
                                sc_a_in = st.number_input(f"{ea[:10]}", min_value=0, max_value=race_to, value=0, key=f"rr_a_{mode}_{m_id}")
                            with col_s2:
                                sc_b_in = st.number_input(f"{eb[:10]}", min_value=0, max_value=race_to, value=0, key=f"rr_b_{mode}_{m_id}")
                            with col_s3:
                                st.write("")
                                if st.button("✅ Valider", key=f"btn_rr_{mode}_{m_id}", use_container_width=True, disabled=not est_editeur):
                                    if sc_a_in == sc_b_in:
                                        st.error("Match nul impossible.")
                                    elif sc_a_in < race_to and sc_b_in < race_to:
                                        st.warning(f"Un joueur doit atteindre {race_to} victoires.")
                                    else:
                                        m["score_a"] = sc_a_in
                                        m["score_b"] = sc_b_in
                                        m["vainqueur"] = ea if sc_a_in > sc_b_in else eb
                                        m["termine"] = True
                                        sauvegarder_tournois_data(tournois_data)
                                        st.rerun()

            if tous_termines and statut != "termine" and classement_rr:
                tournoi["statut"] = "termine"
                tournoi["vainqueur_final"] = classement_rr[0][0]
                if len(classement_rr) > 1:
                    tournoi["finaliste"] = classement_rr[1][0]
                sauvegarder_tournois_data(tournois_data)
                st.rerun()

def afficher_onglet_tournois():
    """Onglet principal Tournois avec sous-onglets Simple et Double."""
    subtab_simple, subtab_double = st.tabs([
        "👤 Tournoi en Simple",
        "👥 Tournoi en Double"
    ])

    with subtab_simple:
        afficher_section_tournoi(mode="simple")

    with subtab_double:
        afficher_section_tournoi(mode="double")


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
            meilleure_defense = min(stats_equipes.values(), key=lambda x: x["moy_contre"])

            # 1. Cartes KPI Équipes
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("🏁 Matchs joués", f"{len(historique)} rencontres")
            k2.metric("🥇 Leader actuel", leader["nom"], f"{leader['v']}V - {leader['d']}D - {leader['n']}N")
            k3.metric("🔥 Meilleure attaque", max_attaque["nom"], f"{max_attaque['pour']} pts ({max_attaque['moy_pour']:.1f}/m)")
            k4.metric("🛡️ Meilleure défense", meilleure_defense["nom"], f"{meilleure_defense['moy_contre']:.1f} pts/m concédés")

            st.markdown("---")

            # 2. Tableau de classement avec forme
            st.markdown("#### 🏆 Classement général & Forme récente")
            
            medailles = {1: "🥇", 2: "🥈", 3: "🥉"}
            lignes_tab = []
            for rang, eq_data in enumerate(classement_equipes, start=1):
                badge_rang = medailles.get(rang, f"#{rang}")
                forme_icons = []
                for res in eq_data["forme"][-5:]:
                    if res == "V":
                        forme_icons.append("🟢")
                    elif res == "D":
                        forme_icons.append("🔴")
                    else:
                        forme_icons.append("🟡")
                forme_str = " ".join(forme_icons) if forme_icons else "-"
                diff_sym = f"+{eq_data['diff']}" if eq_data['diff'] > 0 else str(eq_data['diff'])

                lignes_tab.append({
                    "Rang": badge_rang,
                    "Équipe": eq_data["nom"],
                    "PJ": eq_data["pj"],
                    "V": eq_data["v"],
                    "D": eq_data["d"],
                    "N": eq_data["n"],
                    "Points Pour (BP)": eq_data["pour"],
                    "Points Contre (BC)": eq_data["contre"],
                    "Différence": diff_sym,
                    "Moy. Pts/Match": f"{eq_data['moy_pour']:.1f}",
                    "5 derniers matchs": forme_str
                })

            df_standings = pd.DataFrame(lignes_tab)
            st.dataframe(df_standings, use_container_width=True, hide_index=True)

            st.markdown("---")

            # 3. Graphique d'évolution des points cumulés
            st.markdown("#### 📈 Course au championnat — Points cumulés au fil des rencontres")
            st.caption("Ce graphique illustre l'accumulation des points pour chaque équipe match après match.")
            if not df_prog_equipes.empty:
                st.line_chart(df_prog_equipes, height=360)

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

                # Graphique d'évolution du joueur par match
                if fj["matchs_synthese"]:
                    st.markdown(f"##### 📈 Évolution de la moyenne match après match ({choix_j})")
                    indices_m = sorted(fj["matchs_synthese"].keys())

                    labels_pj = []
                    moys_match = []
                    moys_cumul = []
                    cumul_pts_j = 0
                    cumul_manches_j = 0

                    for im in indices_m:
                        sm = fj["matchs_synthese"][im]
                        pts_m = sm["pts"]
                        man_m = sm["manches"]
                        cumul_pts_j += pts_m
                        cumul_manches_j += man_m
                        
                        labels_pj.append(f"M#{im}")
                        moys_match.append(round(pts_m / man_m, 2) if man_m > 0 else 0)
                        moys_cumul.append(round(cumul_pts_j / cumul_manches_j, 2) if cumul_manches_j > 0 else 0)

                    df_chart_j = pd.DataFrame({
                        "Moyenne du match": moys_match,
                        "Moyenne générale cumulée": moys_cumul
                    }, index=labels_pj)

                    st.line_chart(df_chart_j, height=300)

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
# NAVIGATION PRINCIPALE PAR ONGLETS (FEUILLE DE MATCH vs STATISTIQUES & PROGRESSION)
# ==============================================================================
historique_matchs = charger_historique_matchs()

tab_feuille, tab_stats, tab_tournoi = st.tabs([
    "🎱 Feuille de match & Consultation",
    "📈 Statistiques & Progression",
    "🏆 Tournois"
])

with tab_feuille:
    # --- BANDEAU D'ÉTAT DU VERROU EXCLUSIF (UN SEUL MARQUEUR À LA FOIS) ---
    col_lock1, col_lock2 = st.columns([3, 1])
    if est_editeur:
        col_lock1.success("🟢 **Vous avez la main exclusive pour la saisie et la validation du match.**")
        with col_lock2:
            if st.button("🔓 Céder la main", use_container_width=True, help="Bascule en mode lecture et libère la feuille de match"):
                liberer_verrou(my_session_id)
                st.session_state["mode_consultation"] = True
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
            if st.button("⚡ Prendre la main", use_container_width=True, help="Prend le contrôle de la saisie, rafraîchit la page et active l'édition"):
                forcer_prise_de_main(my_session_id)
                st.session_state["mode_consultation"] = False
                # Rafraîchir immédiatement les scores depuis la dernière sauvegarde sur le disque
                sauv_fraiche = charger_sauvegarde()
                if sauv_fraiche and "matchs" in sauv_fraiche:
                    restaurer_session(sauv_fraiche)
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
    if st.sidebar.button("🚪 Déconnexion / Accueil", use_container_width=True, help="Ferme la session et retourne à l'écran d'accueil"):
        liberer_verrou(my_session_id)
        st.session_state["authentifie"] = False
        st.session_state["est_spectateur"] = False
        st.session_state["mode_consultation"] = False
        st.rerun()

    if noms_equipes:
        options_rec = noms_equipes + ["Autre / Personnalisée"]
        options_vis = noms_equipes + ["Autre / Personnalisée"]
    
        # Équipe Receveuse
        if "sel_equipe_rec" in st.session_state and st.session_state["sel_equipe_rec"] not in options_rec:
            st.session_state["sel_equipe_rec"] = options_rec[0]
        def_idx_rec = 0
        if "sel_equipe_rec" in st.session_state and st.session_state["sel_equipe_rec"] in options_rec:
            def_idx_rec = options_rec.index(st.session_state["sel_equipe_rec"])
        choix_rec = st.sidebar.selectbox("Équipe Receveuse :", options_rec, index=def_idx_rec, key="sel_equipe_rec", disabled=not est_editeur)
    
        if choix_rec == "Autre / Personnalisée":
            equipe_receveur = st.sidebar.text_input("Nom équipe receveuse", value=st.session_state.get("input_custom_rec", "Équipe 1"), key="input_custom_rec", disabled=not est_editeur)
            roster_rec = ["Joueur 1", "Joueur 2", "Joueur 3"]
        else:
            equipe_receveur = choix_rec
            roster_rec = equipes_disponibles[choix_rec]

        # Équipe Visiteuse
        def_idx_vis = 1 if len(noms_equipes) > 1 else 0
        if "sel_equipe_vis" in st.session_state and st.session_state["sel_equipe_vis"] not in options_vis:
            st.session_state["sel_equipe_vis"] = options_vis[def_idx_vis]
        if "sel_equipe_vis" in st.session_state and st.session_state["sel_equipe_vis"] in options_vis:
            def_idx_vis = options_vis.index(st.session_state["sel_equipe_vis"])
        choix_vis = st.sidebar.selectbox("Équipe Visiteuse :", options_vis, index=def_idx_vis, key="sel_equipe_vis", disabled=not est_editeur)
    
        if choix_vis == "Autre / Personnalisée":
            equipe_visiteur = st.sidebar.text_input("Nom équipe visiteuse", value=st.session_state.get("input_custom_vis", "Équipe 2"), key="input_custom_vis", disabled=not est_editeur)
            roster_vis = ["Joueur 1", "Joueur 2", "Joueur 3"]
        else:
            equipe_visiteur = choix_vis
            roster_vis = equipes_disponibles[choix_vis]
    else:
        equipe_receveur = st.sidebar.text_input("Équipe Receveuse", value="Équipe 1", key="input_custom_rec", disabled=not est_editeur)
        equipe_visiteur = st.sidebar.text_input("Équipe Visiteuse", value="Équipe 2", key="input_custom_vis", disabled=not est_editeur)
        roster_rec = ["Jean-François", "Christian", "Antoine"]
        roster_vis = ["Michel", "Nicolas", "Guy"]
        choix_rec = equipe_receveur
        choix_vis = equipe_visiteur

    # --- SÉLECTION DES JOUEURS : ÉQUIPE RECEVEUSE ---
    st.sidebar.markdown(f"### 👥 Joueurs — {equipe_receveur}")

    # Options sécurisées pour Joueur 1
    options_j1_rec = list(roster_rec) + ["Remplaçant..."]
    if "sel_j1_rec" in st.session_state and st.session_state["sel_j1_rec"] not in options_j1_rec:
        st.session_state["sel_j1_rec"] = options_j1_rec[0]

    def_idx_j1_rec = 0
    if "sel_j1_rec" in st.session_state and st.session_state["sel_j1_rec"] in options_j1_rec:
        def_idx_j1_rec = options_j1_rec.index(st.session_state["sel_j1_rec"])

    col_j1_r1, col_j1_r2 = st.sidebar.columns([3, 2])
    sel_j1_rec = col_j1_r1.selectbox("Sélection Joueur 1 :", options_j1_rec, index=def_idx_j1_rec, key="sel_j1_rec", disabled=not est_editeur)
    if sel_j1_rec == "Remplaçant...":
        j1_rec = st.sidebar.text_input("Nom Joueur 1 (Remplaçant)", value=st.session_state.get("cust_j1_rec", "Remplaçant 1"), key="cust_j1_rec", disabled=not est_editeur)
    else:
        j1_rec = sel_j1_rec
    j1_rec_pres = col_j1_r2.toggle("Présent", value=st.session_state.get("pres_j1_rec", True), key="pres_j1_rec", disabled=not est_editeur)
    if not j1_rec_pres:
        def_moy_j1 = float(st.session_state.get("moy_j1_rec", 0.625))
        col_m1, col_m2 = st.sidebar.columns([3, 2])
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
        st.sidebar.caption(f"📊 *Score calculé : {j1_rec_pts} pts/manche (max 7)*")
    else:
        j1_rec_pts = int(st.session_state.get("pts_j1_rec", 0))

    # Options sécurisées pour Joueur 2
    options_j2_rec = [p for p in roster_rec if p != sel_j1_rec] + ["Remplaçant..."]
    if "sel_j2_rec" in st.session_state and st.session_state["sel_j2_rec"] not in options_j2_rec:
        st.session_state["sel_j2_rec"] = options_j2_rec[0]

    def_idx_j2_rec = 0
    if "sel_j2_rec" in st.session_state and st.session_state["sel_j2_rec"] in options_j2_rec:
        def_idx_j2_rec = options_j2_rec.index(st.session_state["sel_j2_rec"])

    col_j2_r1, col_j2_r2 = st.sidebar.columns([3, 2])
    sel_j2_rec = col_j2_r1.selectbox("Sélection Joueur 2 :", options_j2_rec, index=def_idx_j2_rec, key="sel_j2_rec", disabled=not est_editeur)
    if sel_j2_rec == "Remplaçant...":
        j2_rec = st.sidebar.text_input("Nom Joueur 2 (Remplaçant)", value=st.session_state.get("cust_j2_rec", "Remplaçant 2"), key="cust_j2_rec", disabled=not est_editeur)
    else:
        j2_rec = sel_j2_rec
    j2_rec_pres = col_j2_r2.toggle("Présent", value=st.session_state.get("pres_j2_rec", True), key="pres_j2_rec", disabled=not est_editeur)
    if not j2_rec_pres:
        def_moy_j2 = float(st.session_state.get("moy_j2_rec", 0.625))
        col_m1, col_m2 = st.sidebar.columns([3, 2])
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
        st.sidebar.caption(f"📊 *Score calculé : {j2_rec_pts} pts/manche (max 7)*")
    else:
        j2_rec_pts = int(st.session_state.get("pts_j2_rec", 0))

    # Joueur 3 (Évident / Déduit automatiquement)
    col_j3_r1, col_j3_r2 = st.sidebar.columns([3, 2])
    restants_rec = [p for p in roster_rec if p != sel_j1_rec and p != sel_j2_rec]
    j3_rec = restants_rec[0] if restants_rec else "Joueur 3"
    col_j3_r1.markdown(f"**Joueur 3 (défini) :**<br>`{j3_rec}`", unsafe_allow_html=True)
    j3_rec_pres = col_j3_r2.toggle("Présent", value=st.session_state.get("pres_j3_rec", True), key="pres_j3_rec", disabled=not est_editeur)
    if not j3_rec_pres:
        def_moy_j3 = float(st.session_state.get("moy_j3_rec", 0.625))
        col_m1, col_m2 = st.sidebar.columns([3, 2])
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
        st.sidebar.caption(f"📊 *Score calculé : {j3_rec_pts} pts/manche (max 7)*")
    else:
        j3_rec_pts = int(st.session_state.get("pts_j3_rec", 0))

    # --- SÉLECTION DES JOUEURS : ÉQUIPE VISITEUSE ---
    st.sidebar.markdown(f"### 👥 Joueurs — {equipe_visiteur}")

    # Options sécurisées pour Joueur 1
    options_j1_vis = list(roster_vis) + ["Remplaçant..."]
    if "sel_j1_vis" in st.session_state and st.session_state["sel_j1_vis"] not in options_j1_vis:
        st.session_state["sel_j1_vis"] = options_j1_vis[0]

    def_idx_j1_vis = 0
    if "sel_j1_vis" in st.session_state and st.session_state["sel_j1_vis"] in options_j1_vis:
        def_idx_j1_vis = options_j1_vis.index(st.session_state["sel_j1_vis"])

    col_j1_v1, col_j1_v2 = st.sidebar.columns([3, 2])
    sel_j1_vis = col_j1_v1.selectbox("Sélection Joueur 1 :", options_j1_vis, index=def_idx_j1_vis, key="sel_j1_vis", disabled=not est_editeur)
    if sel_j1_vis == "Remplaçant...":
        j1_vis = st.sidebar.text_input("Nom Visiteur 1 (Remplaçant)", value=st.session_state.get("cust_j1_vis", "Remplaçant 1"), key="cust_j1_vis", disabled=not est_editeur)
    else:
        j1_vis = sel_j1_vis
    j1_vis_pres = col_j1_v2.toggle("Présent", value=st.session_state.get("pres_j1_vis", True), key="pres_j1_vis", disabled=not est_editeur)
    if not j1_vis_pres:
        def_moy_v1 = float(st.session_state.get("moy_j1_vis", 0.625))
        col_m1, col_m2 = st.sidebar.columns([3, 2])
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
        st.sidebar.caption(f"📊 *Score calculé : {j1_vis_pts} pts/manche (max 7)*")
    else:
        j1_vis_pts = int(st.session_state.get("pts_j1_vis", 0))

    # Options sécurisées pour Joueur 2
    options_j2_vis = [p for p in roster_vis if p != sel_j1_vis] + ["Remplaçant..."]
    if "sel_j2_vis" in st.session_state and st.session_state["sel_j2_vis"] not in options_j2_vis:
        st.session_state["sel_j2_vis"] = options_j2_vis[0]

    def_idx_j2_vis = 0
    if "sel_j2_vis" in st.session_state and st.session_state["sel_j2_vis"] in options_j2_vis:
        def_idx_j2_vis = options_j2_vis.index(st.session_state["sel_j2_vis"])

    col_j2_v1, col_j2_v2 = st.sidebar.columns([3, 2])
    sel_j2_vis = col_j2_v1.selectbox("Sélection Joueur 2 :", options_j2_vis, index=def_idx_j2_vis, key="sel_j2_vis", disabled=not est_editeur)
    if sel_j2_vis == "Remplaçant...":
        j2_vis = st.sidebar.text_input("Nom Visiteur 2 (Remplaçant)", value=st.session_state.get("cust_j2_vis", "Remplaçant 2"), key="cust_j2_vis", disabled=not est_editeur)
    else:
        j2_vis = sel_j2_vis
    j2_vis_pres = col_j2_v2.toggle("Présent", value=st.session_state.get("pres_j2_vis", True), key="pres_j2_vis", disabled=not est_editeur)
    if not j2_vis_pres:
        def_moy_v2 = float(st.session_state.get("moy_j2_vis", 0.625))
        col_m1, col_m2 = st.sidebar.columns([3, 2])
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
        st.sidebar.caption(f"📊 *Score calculé : {j2_vis_pts} pts/manche (max 7)*")
    else:
        j2_vis_pts = int(st.session_state.get("pts_j2_vis", 0))

    # Joueur 3 (Évident / Déduit automatiquement)
    col_j3_v1, col_j3_v2 = st.sidebar.columns([3, 2])
    restants_vis = [p for p in roster_vis if p != sel_j1_vis and p != sel_j2_vis]
    j3_vis = restants_vis[0] if restants_vis else "Joueur 3"
    col_j3_v1.markdown(f"**Joueur 3 (défini) :**<br>`{j3_vis}`", unsafe_allow_html=True)
    j3_vis_pres = col_j3_v2.toggle("Présent", value=st.session_state.get("pres_j3_vis", True), key="pres_j3_vis", disabled=not est_editeur)
    if not j3_vis_pres:
        def_moy_v3 = float(st.session_state.get("moy_j3_vis", 0.625))
        col_m1, col_m2 = st.sidebar.columns([3, 2])
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
        st.sidebar.caption(f"📊 *Score calculé : {j3_vis_pts} pts/manche (max 7)*")
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
    for m in reversed(historique_matchs):
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
            # Affichage pour l'éditeur avec toggle optionnel
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                afficher_dashboard = st.toggle(
                    "📊 **Afficher le résumé des scores en direct**",
                    value=st.session_state.get("toggle_voir_resultats_editeur", False),
                    key="toggle_voir_resultats_editeur"
                )

            if afficher_dashboard:
                tot_rec_c, tot_vis_c, pts_j_c, details_c = calculer_totaux_actuels(dict_joueurs, matchs_pairs)
                with st.container(border=True):
                    st.markdown(f"#### 🎱 Résultats courants : **{equipe_receveur}** ({tot_rec_c} pts) vs **{equipe_visiteur}** ({tot_vis_c} pts)")
                
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

        for num_manche, id_a, id_b in matchs_pairs:
            info_a = dict_joueurs[id_a]
            info_b = dict_joueurs[id_b]
            joueur_a = info_a["nom"]
            joueur_b = info_b["nom"]
            a_pres = info_a["present"]
            b_pres = info_b["present"]

            status_label = ""
            if not a_pres and not b_pres:
                status_label = " ❌ (Forfait double : 2 absents)"
            elif not a_pres:
                status_label = f" ❌ ({joueur_a} absent : {info_a['pts_absent']} pts)"
            elif not b_pres:
                status_label = f" ❌ ({joueur_b} absent : {info_b['pts_absent']} pts)"

            with st.expander(f"Manche {num_manche} : {joueur_a} ({equipe_receveur}) vs {joueur_b} ({equipe_visiteur}){status_label}", expanded=True):
                c1, c2 = st.columns(2)
            
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

                with c1:
                    label_champ_a = f"Points de {joueur_a}" + (f" (Absent : {info_a['pts_absent']} pts)" if not a_pres else "")
                    score_a = st.number_input(
                        label_champ_a, 
                        0, 8, 
                        key=f"s_a_{num_manche}",
                        disabled=not est_editeur
                    )
                with c2:
                    label_champ_b = f"Points de {joueur_b}" + (f" (Absent : {info_b['pts_absent']} pts)" if not b_pres else "")
                    score_b = st.number_input(
                        label_champ_b, 
                        0, 8, 
                        key=f"s_b_{num_manche}",
                        disabled=not est_editeur
                    )
            
                # Validation logique du billard au 8
                if score_a == 8 and score_b == 8:
                    st.warning("⚠️ Les deux joueurs ne peuvent pas avoir 8 points.")
                    manches_invalides.append(num_manche)

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
    # ESPACE ADMINISTRATION (SAISON, SMTP ET SÉCURITÉ)
    # ==============================================================================
    if not est_spectateur:
        st.markdown("### ⚙️ Espace Administration")

        with st.expander("🛠️ Ouvrir le panneau d'administration (Saison, SMTP et Sécurité)", expanded=False):
            tab_saison, tab_rectif, tab_export, tab_smtp, tab_secu = st.tabs([
                "🗓️ Démarrer une nouvelle saison",
                "✏️ Rectifier un match archivé",
                "📤 Envoyer l'historique complet",
                "📧 Configuration SMTP",
                "🔑 Mot de passe d'accès"
            ])

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

            with tab_smtp:
                st.markdown("#### ⚙️ Configuration du serveur de messagerie (SMTP)")
                smtp_dest = st.text_input("Destinataire(s) (séparés par virgule)", value=config_email.get("destinataires", ""), key="admin_smtp_dest")
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
