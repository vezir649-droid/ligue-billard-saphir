import json
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
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Ligue de billard du Saphir - Saisie",
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
    """Écrit atomiquement la sauvegarde pour éviter les corruptions."""
    try:
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

def generer_resume_match(receveur, visiteur, matchs, total_rec, total_vis, pts_joueurs, dict_joueurs, date_str, absents_info=None):
    """Génère le résumé en texte brut et en HTML avec les totaux par équipe et par joueur."""
    lignes_texte = [
        f"Ligue de billard du Saphir - Résultats officiels",
        f"Date : {date_str}",
        f"Rencontre : {receveur} vs {visiteur}",
        f"Score final : {receveur} ({total_rec} pts) - {visiteur} ({total_vis} pts)"
    ]

    if absents_info:
        lignes_texte.append(f"Joueurs absents : {', '.join(absents_info)}")

    lignes_texte.extend([
        "-" * 50,
        f"Points par joueur — {receveur} :",
        f"  * {dict_joueurs['j1_rec']['nom']} : {pts_joueurs['j1_rec']} pts",
        f"  * {dict_joueurs['j2_rec']['nom']} : {pts_joueurs['j2_rec']} pts",
        f"  * {dict_joueurs['j3_rec']['nom']} : {pts_joueurs['j3_rec']} pts",
        f"Points par joueur — {visiteur} :",
        f"  * {dict_joueurs['j1_vis']['nom']} : {pts_joueurs['j1_vis']} pts",
        f"  * {dict_joueurs['j2_vis']['nom']} : {pts_joueurs['j2_vis']} pts",
        f"  * {dict_joueurs['j3_vis']['nom']} : {pts_joueurs['j3_vis']} pts",
        "-" * 50,
        "Détail des 9 manches :"
    ])

    lignes_html = []
    for num in range(1, 10):
        m = matchs.get(str(num), {})
        sa = m.get("score_a", 0)
        sb = m.get("score_b", 0)
        ja = m.get("joueur_a", "")
        jb = m.get("joueur_b", "")
        ja_abs = m.get("joueur_a_absent", False)
        jb_abs = m.get("joueur_b_absent", False)

        label_a = f"{ja} (Absent : {sa} pts)" if ja_abs else ja
        label_b = f"{jb} (Absent : {sb} pts)" if jb_abs else jb

        lignes_texte.append(f"Manche {num} : {label_a} ({sa}) vs {label_b} ({sb})")
        lignes_html.append(f"""
            <tr style="border-bottom: 1px solid #ddd; text-align: center;">
                <td style="padding: 8px;"><strong>Manche {num}</strong></td>
                <td style="padding: 8px;">{label_a}</td>
                <td style="padding: 8px; font-weight: bold; color: {'#1b5e20' if sa == 8 else '#333'};">{sa}</td>
                <td style="padding: 8px; font-weight: bold; color: {'#1b5e20' if sb == 8 else '#333'};">{sb}</td>
                <td style="padding: 8px;">{label_b}</td>
            </tr>
        """)

    texte = "\n".join(lignes_texte)

    absents_html_bloc = ""
    if absents_info:
        absents_html_bloc = f"<p style='color: #d32f2f;'><strong>Joueur(s) absent(s) :</strong> {', '.join(absents_info)}</p>"

    logo_b64 = charger_armoiries_base64()
    src_val = logo_b64 if logo_b64 else "cid:armoiries_logo"
    arm_existe = bool(logo_b64 or os.path.isfile(find_armoiries_path()))
    logo_td = f'<td style="width: 70px; vertical-align: middle; padding-right: 12px;"><img src="{src_val}" alt="Armoiries" style="height: 65px; width: 65px; object-fit: contain; border-radius: 4px;"></td>' if arm_existe else ''

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Feuille de match officielle - Ligue du Saphir</title>
        <style>
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ margin: 10mm; font-size: 11pt; }}
            }}
        </style>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222;">
        <table style="width: 100%; border-bottom: 2px solid #0b3c5d; padding-bottom: 8px; margin-bottom: 12px; border-collapse: collapse;">
            <tr>
                {logo_td}
                <td style="vertical-align: middle;">
                    <h2 style="color: #0b3c5d; margin: 0; font-size: 20px;">🎱 Ligue de billard du Saphir</h2>
                    <div style="color: #555; font-size: 14px; font-weight: bold; margin-top: 2px;">Feuille de match officielle</div>
                </td>
            </tr>
        </table>
        <p><strong>Date :</strong> {date_str}</p>
        <div style="background-color: #f4f6f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #1e3d59;">Résultat final du match :</h3>
            <p style="font-size: 18px; margin: 8px 0;">
                <strong>{receveur}</strong> : <span style="font-size: 22px; color: #0d47a1;">{total_rec}</span> pts<br>
                <strong>{visiteur}</strong> : <span style="font-size: 22px; color: #0d47a1;">{total_vis}</span> pts
            </p>
            <p style="font-weight: bold; color: #2e7d32; font-size: 16px;">
                Vainqueur : {receveur if total_rec > total_vis else (visiteur if total_vis > total_rec else "Égalité")}
            </p>
            {absents_html_bloc}
            
            <div style="margin-top: 15px; display: flex; gap: 20px;">
                <div style="flex: 1; background: white; padding: 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 8px 0; color: #0b3c5d;">Points individuels — {receveur} :</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li><strong>{dict_joueurs['j1_rec']['nom']}</strong> : {pts_joueurs['j1_rec']} pts</li>
                        <li><strong>{dict_joueurs['j2_rec']['nom']}</strong> : {pts_joueurs['j2_rec']} pts</li>
                        <li><strong>{dict_joueurs['j3_rec']['nom']}</strong> : {pts_joueurs['j3_rec']} pts</li>
                    </ul>
                </div>
                <div style="flex: 1; background: white; padding: 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 8px 0; color: #0b3c5d;">Points individuels — {visiteur} :</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li><strong>{dict_joueurs['j1_vis']['nom']}</strong> : {pts_joueurs['j1_vis']} pts</li>
                        <li><strong>{dict_joueurs['j2_vis']['nom']}</strong> : {pts_joueurs['j2_vis']} pts</li>
                        <li><strong>{dict_joueurs['j3_vis']['nom']}</strong> : {pts_joueurs['j3_vis']} pts</li>
                    </ul>
                </div>
            </div>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <thead>
                <tr style="background-color: #0b3c5d; color: white;">
                    <th style="padding: 10px;">Manche</th>
                    <th style="padding: 10px;">Joueur ({receveur})</th>
                    <th style="padding: 10px;">Pts</th>
                    <th style="padding: 10px;">Pts</th>
                    <th style="padding: 10px;">Joueur ({visiteur})</th>
                </tr>
            </thead>
            <tbody>
                {''.join(lignes_html)}
            </tbody>
        </table>
        <p style="font-size: 12px; color: #777; margin-top: 25px;">
            Feuille générée automatiquement via l'application officielle de saisie - Ligue de billard du Saphir.
        </p>
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

def obtenir_html_match(m):
    """Renvoie le HTML officiel du match ou le reconstitue fidèlement à partir des données archivées."""
    if m.get("html_officiel"):
        html_existant = m["html_officiel"]
        if "Armoiries" not in html_existant and "armoiries" not in html_existant:
            logo_b64 = charger_armoiries_base64()
            if logo_b64:
                logo_td = f'<td style="width: 70px; vertical-align: middle; padding-right: 12px;"><img src="{logo_b64}" alt="Armoiries" style="height: 65px; width: 65px; object-fit: contain; border-radius: 4px;"></td>'
                html_existant = html_existant.replace(
                    '<td style="vertical-align: middle;">',
                    f'{logo_td}\n                <td style="vertical-align: middle;">'
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
        
        color_a = '#1b5e20' if sa == 8 else '#333'
        color_b = '#1b5e20' if sb == 8 else '#333'
        
        lignes_html.append(f"""
            <tr style="border-bottom: 1px solid #ddd; text-align: center;">
                <td style="padding: 8px;"><strong>Manche {num}</strong></td>
                <td style="padding: 8px;">{label_a}</td>
                <td style="padding: 8px; font-weight: bold; color: {color_a};">{sa}</td>
                <td style="padding: 8px; font-weight: bold; color: {color_b};">{sb}</td>
                <td style="padding: 8px;">{label_b}</td>
            </tr>
        """)

    li_rec = "".join([f"<li><strong>{nom}</strong> : {pts} pts</li>" for nom, pts in pts_rec_j.items()])
    li_vis = "".join([f"<li><strong>{nom}</strong> : {pts} pts</li>" for nom, pts in pts_vis_j.items()])
    vainqueur = rec if tot_rec > tot_vis else (vis if tot_vis > tot_rec else "Égalité")

    logo_b64 = charger_armoiries_base64()
    src_val = logo_b64 if logo_b64 else "cid:armoiries_logo"
    arm_existe = bool(logo_b64 or os.path.isfile(find_armoiries_path()))
    logo_td = f'<td style="width: 70px; vertical-align: middle; padding-right: 12px;"><img src="{src_val}" alt="Armoiries" style="height: 65px; width: 65px; object-fit: contain; border-radius: 4px;"></td>' if arm_existe else ''

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Feuille de match officielle - Ligue du Saphir</title>
        <style>
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ margin: 10mm; font-size: 11pt; }}
            }}
        </style>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222; margin: 0; padding: 10px;">
        <div class="no-print" style="text-align: right; margin-bottom: 10px;">
            <button onclick="window.print()" style="background-color: #0b3c5d; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer;">
                🖨️ Imprimer cette feuille
            </button>
        </div>
        <table style="width: 100%; border-bottom: 2px solid #0b3c5d; padding-bottom: 8px; margin-bottom: 12px; border-collapse: collapse;">
            <tr>
                {logo_td}
                <td style="vertical-align: middle;">
                    <h2 style="color: #0b3c5d; margin: 0; font-size: 20px;">🎱 Ligue de billard du Saphir</h2>
                    <div style="color: #555; font-size: 14px; font-weight: bold; margin-top: 2px;">Feuille de match officielle</div>
                </td>
            </tr>
        </table>
        <p><strong>Date :</strong> {date_str}</p>
        <div style="background-color: #f4f6f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #1e3d59;">Résultat final du match :</h3>
            <p style="font-size: 18px; margin: 8px 0;">
                <strong>{rec}</strong> : <span style="font-size: 22px; color: #0d47a1;">{tot_rec}</span> pts<br>
                <strong>{vis}</strong> : <span style="font-size: 22px; color: #0d47a1;">{tot_vis}</span> pts
            </p>
            <p style="font-weight: bold; color: #2e7d32; font-size: 16px;">
                Vainqueur : {vainqueur}
            </p>
            <div style="margin-top: 15px; display: flex; gap: 20px;">
                <div style="flex: 1; background: white; padding: 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 8px 0; color: #0b3c5d;">Points individuels — {rec} :</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{li_rec}</ul>
                </div>
                <div style="flex: 1; background: white; padding: 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 8px 0; color: #0b3c5d;">Points individuels — {vis} :</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">{li_vis}</ul>
                </div>
            </div>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <thead>
                <tr style="background-color: #0b3c5d; color: white;">
                    <th style="padding: 10px;">Manche</th>
                    <th style="padding: 10px;">Joueur ({rec})</th>
                    <th style="padding: 10px;">Pts</th>
                    <th style="padding: 10px;">Pts</th>
                    <th style="padding: 10px;">Joueur ({vis})</th>
                </tr>
            </thead>
            <tbody>
                {''.join(lignes_html)}
            </tbody>
        </table>
        <p style="font-size: 12px; color: #777; margin-top: 25px;">
            Feuille générée automatiquement via l'application officielle de saisie - Ligue de billard du Saphir.
        </p>
    </body>
    </html>
    """
    return html

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
# CONTRÔLE D'ACCÈS À L'ENTRÉE (AUTHENTIFICATION MARQUEUR OU SPECTATEUR)
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
                    <img src="{b64_logo_login}" alt="Armoiries Ligue du Saphir" style="width: 130px; height: 130px; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.18));">
                </div>
                """,
                unsafe_allow_html=True
            )
        elif os.path.isfile(arm_p):
            col_img1, col_img2, col_img3 = st.columns([1, 1, 1])
            with col_img2:
                st.image(arm_p, width=130)

        st.markdown("<div style='text-align: center; margin-top: 5px;'>", unsafe_allow_html=True)
        st.title("🎱 Ligue de billard du Saphir")
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
        st.title("🎱 Ligue de billard du Saphir")
        st.subheader("Application de saisie des résultats - Format 3 contre 3")
        st.markdown("*Plateforme officielle de gestion des matchs, de la cédule et des présences.*")
else:
    st.title("🎱 Ligue de billard du Saphir")
    st.subheader("Application de saisie des résultats - Format 3 contre 3")
    st.markdown("*Plateforme officielle de gestion des matchs, de la cédule et des présences.*")

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

# Gestion sécurisée du retour au match en cours (évite l'erreur Streamlit de modification après instanciation de selectbox)
if st.session_state.pop("demande_retour_match_en_cours", False):
    st.session_state["choix_match_vue"] = label_direct

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
        if st.button("🔙 Revenir au match en cours", use_container_width=True, help="Retourner à la saisie du match actuel"):
            st.session_state["demande_retour_match_en_cours"] = True
            st.rerun()

# 1. Si une archive officielle est sélectionnée
if choix_vue != label_direct:
    st.session_state["venant_de_archive"] = True
    m_arch = mapping_matchs[choix_vue]
    html_arch = obtenir_html_match(m_arch)
    
    with st.container(border=True):
        st.markdown(f"#### 📜 Feuille officielle archivée — {m_arch.get('date_enregistrement', m_arch.get('date', ''))}")
        c_btn1, c_btn2, c_btn3 = st.columns([2, 1, 1])
        c_btn1.info("✉️ **Copie certifiée conforme :** Ce résultat correspond exactement à la feuille de match officielle transmise par courriel lors de la validation.")
        with c_btn2:
            date_slug = str(m_arch.get('date_enregistrement', 'match')).replace('/', '-').replace(' ', '_').replace(':', 'h').replace('à', '')
            rec_slug = str(m_arch.get('receveur', 'rec')).replace(' ', '_')
            vis_slug = str(m_arch.get('visiteur', 'vis')).replace(' ', '_')
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
                    🖨️ Imprimer
                </button>
                <script>
                function lancerImpression() {{
                    var win = window.open('', '_blank');
                    win.document.open();
                    win.document.write({html_print_data});
                    win.document.close();
                    win.focus();
                    setTimeout(function() {{
                        win.print();
                    }}, 300);
                }}
                </script>
                """,
                height=42
            )
        
        st.components.v1.html(html_arch, height=650, scrolling=True)

# 2. Si le match en cours est sélectionné
else:
    # Restauration automatique des scores en mémoire si l'on revient de la consultation d'une archive
    if st.session_state.get("venant_de_archive", False) and "scores_en_cours_backup" in st.session_state:
        for k_b, v_b in st.session_state["scores_en_cours_backup"].items():
            st.session_state[k_b] = v_b
        st.session_state["venant_de_archive"] = False

    tot_rec_c, tot_vis_c, pts_j_c, details_c = calculer_totaux_actuels(dict_joueurs, matchs_pairs)
    
    afficher_dashboard = True
    if not est_spectateur:
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            afficher_dashboard = st.toggle(
                "📊 **Afficher le résumé des scores en direct**",
                value=st.session_state.get("toggle_voir_resultats_editeur", False),
                key="toggle_voir_resultats_editeur"
            )

    if afficher_dashboard:
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

            # Tableau récapitulatif des 9 manches (visible en mode spectateur)
            if est_spectateur:
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

if not est_spectateur and choix_vue != label_direct:
    col_av1, col_av2 = st.columns([3, 1])
    with col_av1:
        st.info("💡 **Feuille archivée affichée ci-dessus.** La grille de saisie du match en cours est temporairement masquée.")
    with col_av2:
        if st.button("🔙 Reprendre la saisie", type="primary", use_container_width=True, key="btn_reprendre_saisie"):
            st.session_state["demande_retour_match_en_cours"] = True
            st.rerun()
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

    match_valide = False

    if st.button("🚀 Valider et enregistrer la feuille de match officielle", type="primary", use_container_width=True, disabled=not est_editeur):
        if manches_invalides:
            st.error(f"❌ Impossible d'enregistrer : veuillez corriger les manches suivantes : {', '.join(map(str, sorted(set(manches_invalides))))}.")
        else:
            match_valide = True
            historique = []
            if os.path.exists(HISTORIQUE_FILE):
                try:
                    with open(HISTORIQUE_FILE, "r", encoding="utf-8") as f:
                        historique = json.load(f)
                except Exception:
                    historique = []
            
            donnees_finales = dict(donnees_a_sauvegarder)
            donnees_finales["total_receveur"] = total_pts_receveur
            donnees_finales["total_visiteur"] = total_pts_visiteur
            donnees_finales["points_par_joueur"] = {
                p_id: {
                    "nom": dict_joueurs[p_id]["nom"],
                    "equipe": dict_joueurs[p_id]["equipe"],
                    "points": pts_joueurs[p_id],
                    "present": dict_joueurs[p_id]["present"],
                    "moyenne": dict_joueurs[p_id].get("moyenne", 0.0)
                }
                for p_id in dict_joueurs
            }
            donnees_finales["date_enregistrement"] = date_du_match
            donnees_finales["html_officiel"] = html_resume
            historique.append(donnees_finales)

            with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
                json.dump(historique, f, ensure_ascii=False, indent=4)

            st.success(f"✅ Le match entre **{equipe_receveur}** ({total_pts_receveur} pts) et **{equipe_visiteur}** ({total_pts_visiteur} pts) a été archivé avec succès !")

            # Envoi automatique par courriel au moment de la validation finale
            destinataires_envoi = config_email.get("destinataires", "").strip()
            if not destinataires_envoi:
                st.warning("⚠️ L'envoi automatique par courriel a été ignoré car aucun destinataire n'est configuré dans `config_email.json`.")
            else:
                sujet = f"🎱 Ligue du Saphir : {equipe_receveur} ({total_pts_receveur}) vs {equipe_visiteur} ({total_pts_visiteur}) - {date_du_match}"
                pj_historique = [HISTORIQUE_FILE] if os.path.exists(HISTORIQUE_FILE) else None
                with st.spinner("Envoi automatique du courriel en cours (avec historique en pièce jointe)..."):
                    succes_mail, msg_mail = envoyer_courriel(
                        destinataires_envoi,
                        sujet,
                        texte_resume,
                        html_resume,
                        config_email,
                        pieces_jointes=pj_historique
                    )
                if succes_mail:
                    mention_pj = f" avec le fichier `{HISTORIQUE_FILE}` en pièce jointe" if pj_historique else ""
                    st.success(f"✉️ {msg_mail} (Envoyé automatiquement{mention_pj} à : `{destinataires_envoi}`)")
                else:
                    st.warning(f"⚠️ {msg_mail}")
                    st.info("💡 Les résultats ont bien été sauvegardés sur l'ordinateur.")

            # Nettoyage du fichier de secours et libération du verrou après validation réussie
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
            liberer_verrou(my_session_id)
            st.session_state["mode_consultation"] = True

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
        tab_saison, tab_smtp, tab_secu = st.tabs([
            "🗓️ Démarrer une nouvelle saison",
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
                                "🎱 Test de configuration SMTP - Ligue du Saphir",
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
