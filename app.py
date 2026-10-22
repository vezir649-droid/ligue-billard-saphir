import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.parse
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Ligue de billard du Saphir - Saisie",
    page_icon="🎱",
    layout="wide"
)

# Fichiers de données
BACKUP_FILE = "sauvegarde_saisie_secours.json"
HISTORIQUE_FILE = "historique_matchs.json"
CONFIG_EMAIL_FILE = "config_email.json"
EQUIPES_CSV_FILE = "equipes-saphir.csv"

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
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def sauvegarder_donnees(data):
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
        f"Points par joueur — {receveur} (sur 24 pts max) :",
        f"  * {dict_joueurs['j1_rec']['nom']} : {pts_joueurs['j1_rec']} pts",
        f"  * {dict_joueurs['j2_rec']['nom']} : {pts_joueurs['j2_rec']} pts",
        f"  * {dict_joueurs['j3_rec']['nom']} : {pts_joueurs['j3_rec']} pts",
        f"Points par joueur — {visiteur} (sur 24 pts max) :",
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

        gagnant = ja if sa > sb else (jb if sb > sa else "Égalité")
        lignes_texte.append(f"Manche {num} : {label_a} ({sa}) vs {label_b} ({sb}) -> Gagnant : {gagnant}")
        lignes_html.append(f"""
            <tr style="border-bottom: 1px solid #ddd; text-align: center;">
                <td style="padding: 8px;"><strong>Manche {num}</strong></td>
                <td style="padding: 8px;">{label_a}</td>
                <td style="padding: 8px; font-weight: bold; color: {'#1b5e20' if sa == 8 else '#333'};">{sa}</td>
                <td style="padding: 8px; font-weight: bold; color: {'#1b5e20' if sb == 8 else '#333'};">{sb}</td>
                <td style="padding: 8px;">{label_b}</td>
                <td style="padding: 8px; font-weight: bold; color: #0d47a1;">{gagnant}</td>
            </tr>
        """)

    texte = "\n".join(lignes_texte)

    absents_html_bloc = ""
    if absents_info:
        absents_html_bloc = f"<p style='color: #d32f2f;'><strong>Joueur(s) absent(s) :</strong> {', '.join(absents_info)}</p>"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222;">
        <h2 style="color: #0b3c5d;">🎱 Ligue de billard du Saphir - Feuille de match officielle</h2>
        <p><strong>Date :</strong> {date_str}</p>
        <div style="background-color: #f4f6f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #1e3d59;">Résultat final du match :</h3>
            <p style="font-size: 18px; margin: 8px 0;">
                <strong>{receveur}</strong> : <span style="font-size: 22px; color: #0d47a1;">{total_rec}</span> pts / 72<br>
                <strong>{visiteur}</strong> : <span style="font-size: 22px; color: #0d47a1;">{total_vis}</span> pts / 72
            </p>
            <p style="font-weight: bold; color: #2e7d32; font-size: 16px;">
                Vainqueur : {receveur if total_rec > total_vis else (visiteur if total_vis > total_rec else "Égalité")}
            </p>
            {absents_html_bloc}
            
            <div style="margin-top: 15px; display: flex; gap: 20px;">
                <div style="flex: 1; background: white; padding: 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 8px 0; color: #0b3c5d;">Points individuels — {receveur} :</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li><strong>{dict_joueurs['j1_rec']['nom']}</strong> : {pts_joueurs['j1_rec']} / 24 pts</li>
                        <li><strong>{dict_joueurs['j2_rec']['nom']}</strong> : {pts_joueurs['j2_rec']} / 24 pts</li>
                        <li><strong>{dict_joueurs['j3_rec']['nom']}</strong> : {pts_joueurs['j3_rec']} / 24 pts</li>
                    </ul>
                </div>
                <div style="flex: 1; background: white; padding: 10px; border-radius: 6px; border: 1px solid #ddd;">
                    <h4 style="margin: 0 0 8px 0; color: #0b3c5d;">Points individuels — {visiteur} :</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li><strong>{dict_joueurs['j1_vis']['nom']}</strong> : {pts_joueurs['j1_vis']} / 24 pts</li>
                        <li><strong>{dict_joueurs['j2_vis']['nom']}</strong> : {pts_joueurs['j2_vis']} / 24 pts</li>
                        <li><strong>{dict_joueurs['j3_vis']['nom']}</strong> : {pts_joueurs['j3_vis']} / 24 pts</li>
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
                    <th style="padding: 10px;">Gagnant</th>
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

def envoyer_courriel(destinataires_str, sujet, texte_brut, html_contenu, config):
    """Envoie un courriel automatique via SMTP selon la configuration chargée."""
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"] = expediteur
    msg["To"] = ", ".join(destinataires)

    part1 = MIMEText(texte_brut, "plain", "utf-8")
    part2 = MIMEText(html_contenu, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

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

# Initialisation des données de secours en session
if "saisie_en_cours" not in st.session_state:
    st.session_state.saisie_en_cours = charger_sauvegarde()

# Chargement de la configuration email au démarrage
config_email = charger_config_email()

# Chargement du fichier équipes CSV
equipes_disponibles = charger_equipes_csv()
noms_equipes = list(equipes_disponibles.keys())

# --- ENTÊTE DU SITE WEB DE RÉFÉRENCE ---
st.title("🎱 Ligue de billard du Saphir")
st.subheader("Application de saisie des résultats - Format 3 contre 3")
st.markdown("*Plateforme officielle de gestion des matchs, de la cédule et des présences.*")
st.divider()

# --- BARRE LATÉRALE : SÉLECTION DU MATCH ET JOUEURS ---
st.sidebar.header("📋 Paramètres du Match")

if noms_equipes:
    options_rec = noms_equipes + ["Autre / Personnalisée"]
    options_vis = noms_equipes + ["Autre / Personnalisée"]
    
    choix_rec = st.sidebar.selectbox("Équipe Receveuse :", options_rec, index=0, key="sel_equipe_rec")
    if choix_rec == "Autre / Personnalisée":
        equipe_receveur = st.sidebar.text_input("Nom équipe receveuse", value="Équipe 1", key="input_custom_rec")
        roster_rec = ["Joueur 1", "Joueur 2", "Joueur 3"]
    else:
        equipe_receveur = choix_rec
        roster_rec = equipes_disponibles[choix_rec]

    default_vis_idx = 1 if len(noms_equipes) > 1 else 0
    choix_vis = st.sidebar.selectbox("Équipe Visiteuse :", options_vis, index=default_vis_idx, key="sel_equipe_vis")
    if choix_vis == "Autre / Personnalisée":
        equipe_visiteur = st.sidebar.text_input("Nom équipe visiteuse", value="Équipe 2", key="input_custom_vis")
        roster_vis = ["Joueur 1", "Joueur 2", "Joueur 3"]
    else:
        equipe_visiteur = choix_vis
        roster_vis = equipes_disponibles[choix_vis]
else:
    equipe_receveur = st.sidebar.text_input("Équipe Receveuse", value="Équipe 1")
    equipe_visiteur = st.sidebar.text_input("Équipe Visiteuse", value="Équipe 2")
    roster_rec = ["Jean-François", "Christian", "Antoine"]
    roster_vis = ["Michel", "Nicolas", "Guy"]

saved_joueurs = st.session_state.saisie_en_cours.get("joueurs", {})

# --- SÉLECTION DES JOUEURS : ÉQUIPE RECEVEUSE ---
st.sidebar.markdown(f"### 👥 Joueurs — {equipe_receveur}")

# Joueur 1 (Sélection)
col_j1_r1, col_j1_r2 = st.sidebar.columns([3, 2])
options_j1_rec = list(roster_rec) + ["Remplaçant..."]
sel_j1_rec = col_j1_r1.selectbox("Sélection Joueur 1 :", options_j1_rec, index=0, key="sel_j1_rec")
if sel_j1_rec == "Remplaçant...":
    j1_rec = st.sidebar.text_input("Nom Joueur 1 (Remplaçant)", value="Remplaçant 1", key="cust_j1_rec")
else:
    j1_rec = sel_j1_rec
j1_rec_pres_def = saved_joueurs.get("j1_rec", {}).get("present", True)
j1_rec_pres = col_j1_r2.toggle("Présent", value=j1_rec_pres_def, key="pres_j1_rec")
j1_rec_pts_def = saved_joueurs.get("j1_rec", {}).get("pts_absent", 0)
if not j1_rec_pres:
    j1_rec_pts = st.sidebar.number_input(
        f"Score par défaut de {j1_rec} (absent) :",
        min_value=0, max_value=7,
        value=j1_rec_pts_def,
        key="pts_j1_rec",
        help=f"Points attribués à {j1_rec} pour chaque manche où il est absent (0 à 7)."
    )
else:
    j1_rec_pts = st.session_state.get("pts_j1_rec", j1_rec_pts_def)

# Joueur 2 (Sélection parmi les joueurs restants)
col_j2_r1, col_j2_r2 = st.sidebar.columns([3, 2])
options_j2_rec = [p for p in roster_rec if p != sel_j1_rec] + ["Remplaçant..."]
sel_j2_rec = col_j2_r1.selectbox("Sélection Joueur 2 :", options_j2_rec, index=0, key="sel_j2_rec")
if sel_j2_rec == "Remplaçant...":
    j2_rec = st.sidebar.text_input("Nom Joueur 2 (Remplaçant)", value="Remplaçant 2", key="cust_j2_rec")
else:
    j2_rec = sel_j2_rec
j2_rec_pres_def = saved_joueurs.get("j2_rec", {}).get("present", True)
j2_rec_pres = col_j2_r2.toggle("Présent", value=j2_rec_pres_def, key="pres_j2_rec")
j2_rec_pts_def = saved_joueurs.get("j2_rec", {}).get("pts_absent", 0)
if not j2_rec_pres:
    j2_rec_pts = st.sidebar.number_input(
        f"Score par défaut de {j2_rec} (absent) :",
        min_value=0, max_value=7,
        value=j2_rec_pts_def,
        key="pts_j2_rec",
        help=f"Points attribués à {j2_rec} pour chaque manche où il est absent (0 à 7)."
    )
else:
    j2_rec_pts = st.session_state.get("pts_j2_rec", j2_rec_pts_def)

# Joueur 3 (Évident / Déduit automatiquement)
col_j3_r1, col_j3_r2 = st.sidebar.columns([3, 2])
restants_rec = [p for p in roster_rec if p != sel_j1_rec and p != sel_j2_rec]
j3_rec = restants_rec[0] if restants_rec else "Joueur 3"
col_j3_r1.markdown(f"**Joueur 3 (défini) :**<br>`{j3_rec}`", unsafe_allow_html=True)
j3_rec_pres_def = saved_joueurs.get("j3_rec", {}).get("present", True)
j3_rec_pres = col_j3_r2.toggle("Présent", value=j3_rec_pres_def, key="pres_j3_rec")
j3_rec_pts_def = saved_joueurs.get("j3_rec", {}).get("pts_absent", 0)
if not j3_rec_pres:
    j3_rec_pts = st.sidebar.number_input(
        f"Score par défaut de {j3_rec} (absent) :",
        min_value=0, max_value=7,
        value=j3_rec_pts_def,
        key="pts_j3_rec",
        help=f"Points attribués à {j3_rec} pour chaque manche où il est absent (0 à 7)."
    )
else:
    j3_rec_pts = st.session_state.get("pts_j3_rec", j3_rec_pts_def)

# --- SÉLECTION DES JOUEURS : ÉQUIPE VISITEUSE ---
st.sidebar.markdown(f"### 👥 Joueurs — {equipe_visiteur}")

# Joueur 1 (Sélection)
col_j1_v1, col_j1_v2 = st.sidebar.columns([3, 2])
options_j1_vis = list(roster_vis) + ["Remplaçant..."]
sel_j1_vis = col_j1_v1.selectbox("Sélection Joueur 1 :", options_j1_vis, index=0, key="sel_j1_vis")
if sel_j1_vis == "Remplaçant...":
    j1_vis = st.sidebar.text_input("Nom Visiteur 1 (Remplaçant)", value="Remplaçant 1", key="cust_j1_vis")
else:
    j1_vis = sel_j1_vis
j1_vis_pres_def = saved_joueurs.get("j1_vis", {}).get("present", True)
j1_vis_pres = col_j1_v2.toggle("Présent", value=j1_vis_pres_def, key="pres_j1_vis")
j1_vis_pts_def = saved_joueurs.get("j1_vis", {}).get("pts_absent", 0)
if not j1_vis_pres:
    j1_vis_pts = st.sidebar.number_input(
        f"Score par défaut de {j1_vis} (absent) :",
        min_value=0, max_value=7,
        value=j1_vis_pts_def,
        key="pts_j1_vis",
        help=f"Points attribués à {j1_vis} pour chaque manche où il est absent (0 à 7)."
    )
else:
    j1_vis_pts = st.session_state.get("pts_j1_vis", j1_vis_pts_def)

# Joueur 2 (Sélection parmi les joueurs restants)
col_j2_v1, col_j2_v2 = st.sidebar.columns([3, 2])
options_j2_vis = [p for p in roster_vis if p != sel_j1_vis] + ["Remplaçant..."]
sel_j2_vis = col_j2_v1.selectbox("Sélection Joueur 2 :", options_j2_vis, index=0, key="sel_j2_vis")
if sel_j2_vis == "Remplaçant...":
    j2_vis = st.sidebar.text_input("Nom Visiteur 2 (Remplaçant)", value="Remplaçant 2", key="cust_j2_vis")
else:
    j2_vis = sel_j2_vis
j2_vis_pres_def = saved_joueurs.get("j2_vis", {}).get("present", True)
j2_vis_pres = col_j2_v2.toggle("Présent", value=j2_vis_pres_def, key="pres_j2_vis")
j2_vis_pts_def = saved_joueurs.get("j2_vis", {}).get("pts_absent", 0)
if not j2_vis_pres:
    j2_vis_pts = st.sidebar.number_input(
        f"Score par défaut de {j2_vis} (absent) :",
        min_value=0, max_value=7,
        value=j2_vis_pts_def,
        key="pts_j2_vis",
        help=f"Points attribués à {j2_vis} pour chaque manche où il est absent (0 à 7)."
    )
else:
    j2_vis_pts = st.session_state.get("pts_j2_vis", j2_vis_pts_def)

# Joueur 3 (Évident / Déduit automatiquement)
col_j3_v1, col_j3_v2 = st.sidebar.columns([3, 2])
restants_vis = [p for p in roster_vis if p != sel_j1_vis and p != sel_j2_vis]
j3_vis = restants_vis[0] if restants_vis else "Joueur 3"
col_j3_v1.markdown(f"**Joueur 3 (défini) :**<br>`{j3_vis}`", unsafe_allow_html=True)
j3_vis_pres_def = saved_joueurs.get("j3_vis", {}).get("present", True)
j3_vis_pres = col_j3_v2.toggle("Présent", value=j3_vis_pres_def, key="pres_j3_vis")
j3_vis_pts_def = saved_joueurs.get("j3_vis", {}).get("pts_absent", 0)
if not j3_vis_pres:
    j3_vis_pts = st.sidebar.number_input(
        f"Score par défaut de {j3_vis} (absent) :",
        min_value=0, max_value=7,
        value=j3_vis_pts_def,
        key="pts_j3_vis",
        help=f"Points attribués à {j3_vis} pour chaque manche où il est absent (0 à 7)."
    )
else:
    j3_vis_pts = st.session_state.get("pts_j3_vis", j3_vis_pts_def)

# Dictionnaire complet des joueurs
dict_joueurs = {
    "j1_rec": {"nom": j1_rec, "present": j1_rec_pres, "pts_absent": j1_rec_pts, "equipe": equipe_receveur},
    "j2_rec": {"nom": j2_rec, "present": j2_rec_pres, "pts_absent": j2_rec_pts, "equipe": equipe_receveur},
    "j3_rec": {"nom": j3_rec, "present": j3_rec_pres, "pts_absent": j3_rec_pts, "equipe": equipe_receveur},
    "j1_vis": {"nom": j1_vis, "present": j1_vis_pres, "pts_absent": j1_vis_pts, "equipe": equipe_visiteur},
    "j2_vis": {"nom": j2_vis, "present": j2_vis_pres, "pts_absent": j2_vis_pts, "equipe": equipe_visiteur},
    "j3_vis": {"nom": j3_vis, "present": j3_vis_pres, "pts_absent": j3_vis_pts, "equipe": equipe_visiteur},
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

# Synchronisation automatique des scores lors d'un changement d'état Présent/Absent ou de score par défaut
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
                    st.session_state[f"s_a_{num_m}"] = 8
                    st.session_state[f"s_b_{num_m}"] = 0

    st.session_state[state_key] = info_j["present"]
    st.session_state[pts_key] = info_j["pts_absent"]

# --- BOUTON DE RÉCUPÉRATION DE SECOURS ---
col_recup1, col_recup2 = st.columns([3, 1])
with col_recup2:
    if st.button("🔄 Restaurer dernière saisie"):
        data_recup = charger_sauvegarde()
        if data_recup:
            st.session_state.saisie_en_cours = data_recup
            for num_m, _, _ in matchs_pairs:
                match_saved = data_recup.get("matchs", {}).get(str(num_m), {})
                if "score_a" in match_saved:
                    st.session_state[f"s_a_{num_m}"] = match_saved["score_a"]
                if "score_b" in match_saved:
                    st.session_state[f"s_b_{num_m}"] = match_saved["score_b"]
            st.success("Données récupérées avec succès !")
            st.rerun()
        else:
            st.warning("Aucune sauvegarde trouvée.")

# Liste des absents pour information
absents_detectes = [f"{j['nom']} ({j['equipe']}) — défaut: {j['pts_absent']} pts" for j in dict_joueurs.values() if not j["present"]]
if absents_detectes:
    st.warning(f"⚠️ **Joueur(s) absent(s) :** {', '.join(absents_detectes)}. Leurs scores de défaut sont automatiquement appliqués dans leurs manches respectives.")

st.markdown("### 🎯 Grille de saisie des 9 manches (Rotation alternée 3 contre 3)")
st.info(
    "📌 **Règle de rotation :** Aucun joueur ne joue deux manches consécutives.\n\n"
    "🎱 **Règle du jeu au 8 :** Le vainqueur obtient **8 points**, le perdant obtient de **0 à 7 points**."
)

# Sauvegarde automatique dynamique au fil de la saisie
donnees_a_sauvegarder = {
    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "receveur": equipe_receveur,
    "visiteur": equipe_visiteur,
    "joueurs": {p_id: {"nom": j["nom"], "present": j["present"], "pts_absent": j["pts_absent"]} for p_id, j in dict_joueurs.items()},
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

    # Titre avec étiquette d'absence
    status_label = ""
    if not a_pres and not b_pres:
        status_label = " ❌ (Forfait double : 2 absents)"
    elif not a_pres:
        status_label = f" ❌ ({joueur_a} absent : {info_a['pts_absent']} pts)"
    elif not b_pres:
        status_label = f" ❌ ({joueur_b} absent : {info_b['pts_absent']} pts)"

    with st.expander(f"Manche {num_manche} : {joueur_a} ({equipe_receveur}) vs {joueur_b} ({equipe_visiteur}){status_label}", expanded=True):
        c1, c2 = st.columns(2)
        
        # Calcul du score par défaut selon absence ou sauvegarde
        saved_scores = st.session_state.saisie_en_cours.get("matchs", {}).get(str(num_manche), {})
        
        if "score_a" in saved_scores and "score_b" in saved_scores:
            def_score_a = saved_scores["score_a"]
            def_score_b = saved_scores["score_b"]
        else:
            if not a_pres and b_pres:
                def_score_a = info_a["pts_absent"]
                def_score_b = 8
            elif not b_pres and a_pres:
                def_score_a = 8
                def_score_b = info_b["pts_absent"]
            elif not a_pres and not b_pres:
                def_score_a = info_a["pts_absent"]
                def_score_b = info_b["pts_absent"]
            else:
                def_score_a = 8
                def_score_b = 0

        with c1:
            label_champ_a = f"Points de {joueur_a}" + (f" (Absent : {info_a['pts_absent']} pts)" if not a_pres else "")
            score_a = st.number_input(
                label_champ_a, 
                0, 8, 
                value=def_score_a,
                key=f"s_a_{num_manche}"
            )
        with c2:
            label_champ_b = f"Points de {joueur_b}" + (f" (Absent : {info_b['pts_absent']} pts)" if not b_pres else "")
            score_b = st.number_input(
                label_champ_b, 
                0, 8, 
                value=def_score_b,
                key=f"s_b_{num_manche}"
            )
        
        # Validation logique du billard au 8
        if score_a == 8 and score_b == 8:
            st.warning("⚠️ Les deux joueurs ne peuvent pas avoir 8 points.")
            manches_invalides.append(num_manche)
        elif score_a < 8 and score_b < 8:
            if not a_pres and not b_pres:
                st.info("ℹ️ Double forfait : aucun joueur n'a atteint 8 points.")
            else:
                st.warning("⚠️ L'un des deux joueurs doit obligatoirement avoir atteint 8 points (le gagnant).")
                manches_invalides.append(num_manche)

        donnees_a_sauvegarder["matchs"][str(num_manche)] = {
            "score_a": score_a,
            "score_b": score_b,
            "joueur_a": joueur_a,
            "joueur_b": joueur_b,
            "joueur_a_absent": not a_pres,
            "joueur_b_absent": not b_pres
        }

# Sauvegarde automatique en arrière-plan à chaque modification
sauvegarder_donnees(donnees_a_sauvegarder)

st.divider()

# --- CALCULS FINAUX ET TOTAUX (PAR ÉQUIPE ET PAR JOUEUR) ---
total_pts_receveur = sum(m["score_a"] for m in donnees_a_sauvegarder["matchs"].values())
total_pts_visiteur = sum(m["score_b"] for m in donnees_a_sauvegarder["matchs"].values())

# Calcul des points individuels par joueur (3 manches par joueur = max 24 pts)
pts_joueurs = {p_id: 0 for p_id in dict_joueurs}
for num_m, id_a, id_b in matchs_pairs:
    m = donnees_a_sauvegarder["matchs"].get(str(num_m), {})
    pts_joueurs[id_a] += m.get("score_a", 0)
    pts_joueurs[id_b] += m.get("score_b", 0)

st.markdown("### 📊 Résultats et Totaux")

# 1. Totaux par équipe
col_res1, col_res2, col_res3 = st.columns(3)
col_res1.metric(label=f"🏆 Total {equipe_receveur}", value=f"{total_pts_receveur} / 72 pts")
col_res2.metric(label=f"🏆 Total {equipe_visiteur}", value=f"{total_pts_visiteur} / 72 pts")

with col_res3:
    st.markdown("### 💾 Sécurité anti-panne")
    st.success("✅ Sauvegarde automatique active.\nEn cas de coupure, cliquez sur **'Restaurer'** en haut.")

# 2. Totaux individuels par joueur
st.markdown("#### 👤 Points individuels par joueur (sur 24 pts max)")

col_rec_pts, col_vis_pts = st.columns(2)

with col_rec_pts:
    st.markdown(f"**🏠 {equipe_receveur}**")
    cr1, cr2, cr3 = st.columns(3)
    p1 = dict_joueurs["j1_rec"]
    p2 = dict_joueurs["j2_rec"]
    p3 = dict_joueurs["j3_rec"]
    cr1.metric(label=f"{p1['nom']}" + (" (Abs.)" if not p1['present'] else ""), value=f"{pts_joueurs['j1_rec']} / 24 pts")
    cr2.metric(label=f"{p2['nom']}" + (" (Abs.)" if not p2['present'] else ""), value=f"{pts_joueurs['j2_rec']} / 24 pts")
    cr3.metric(label=f"{p3['nom']}" + (" (Abs.)" if not p3['present'] else ""), value=f"{pts_joueurs['j3_rec']} / 24 pts")

with col_vis_pts:
    st.markdown(f"**🚗 {equipe_visiteur}**")
    cv1, cv2, cv3 = st.columns(3)
    pv1 = dict_joueurs["j1_vis"]
    pv2 = dict_joueurs["j2_vis"]
    pv3 = dict_joueurs["j3_vis"]
    cv1.metric(label=f"{pv1['nom']}" + (" (Abs.)" if not pv1['present'] else ""), value=f"{pts_joueurs['j1_vis']} / 24 pts")
    cv2.metric(label=f"{pv2['nom']}" + (" (Abs.)" if not pv2['present'] else ""), value=f"{pts_joueurs['j2_vis']} / 24 pts")
    cv3.metric(label=f"{pv3['nom']}" + (" (Abs.)" if not pv3['present'] else ""), value=f"{pts_joueurs['j3_vis']} / 24 pts")

st.divider()

# --- CONFIGURATION ET ENVOI AUTOMATIQUE PAR COURRIEL ---
st.markdown("### 📧 Envoi automatique des résultats par courriel")

dest_actuels = config_email.get("destinataires", "").strip()
if dest_actuels:
    st.info(f"✉️ **Envoi automatique configuré vers :** `{dest_actuels}` (chargé depuis `{CONFIG_EMAIL_FILE}`)")
else:
    st.warning(f"⚠️ **Aucun destinataire configuré dans `{CONFIG_EMAIL_FILE}`.** Ouvrez les paramètres ci-dessous pour renseigner l'adresse courriel.")

with st.expander("⚙️ Modifier et mémoriser la configuration SMTP"):
    smtp_dest = st.text_input("Destinataire(s) (séparés par virgule)", value=config_email.get("destinataires", ""))
    col_c1, col_c2 = st.columns(2)
    smtp_serveur = col_c1.text_input("Serveur SMTP", value=config_email.get("smtp_serveur", "smtp.gmail.com"))
    smtp_port = col_c2.number_input("Port SMTP", value=int(config_email.get("smtp_port", 587)))
    smtp_expediteur = col_c1.text_input("Courriel expéditeur", value=config_email.get("smtp_expediteur", ""))
    smtp_mdp = col_c2.text_input("Mot de passe / Clé d'application", type="password", value=config_email.get("smtp_mdp", ""))
    smtp_ssl = st.checkbox("Utiliser SSL (Port 465)", value=config_email.get("smtp_ssl", False))

    if st.button("💾 Enregistrer la configuration dans le fichier"):
        nouvelle_cfg = {
            "destinataires": smtp_dest,
            "smtp_serveur": smtp_serveur,
            "smtp_port": smtp_port,
            "smtp_expediteur": smtp_expediteur,
            "smtp_mdp": smtp_mdp,
            "smtp_ssl": smtp_ssl
        }
        if sauvegarder_config_email(nouvelle_cfg):
            config_email = nouvelle_cfg
            st.success("Configuration SMTP enregistrée avec succès dans le fichier !")
            st.rerun()
        else:
            st.error("Erreur lors de la sauvegarde du fichier.")

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

col_valid1, col_valid2 = st.columns([2, 1])

with col_valid1:
    if st.button("🚀 Valider et enregistrer la feuille de match officielle", type="primary", use_container_width=True):
        if manches_invalides:
            st.error(f"❌ Impossible d'enregistrer : veuillez corriger les manches suivantes : {', '.join(map(str, sorted(set(manches_invalides))))}.")
        else:
            st.balloons()
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
                    "present": dict_joueurs[p_id]["present"]
                }
                for p_id in dict_joueurs
            }
            donnees_finales["date_enregistrement"] = date_du_match
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
                with st.spinner("Envoi automatique du courriel en cours..."):
                    succes_mail, msg_mail = envoyer_courriel(
                        destinataires_envoi,
                        sujet,
                        texte_resume,
                        html_resume,
                        config_email
                    )
                if succes_mail:
                    st.success(f"✉️ {msg_mail} (Envoyé automatiquement à : `{destinataires_envoi}`)")
                else:
                    st.warning(f"⚠️ {msg_mail}")
                    st.info("💡 Les résultats ont bien été sauvegardés sur l'ordinateur.")

            # Nettoyage du fichier de secours après validation réussie
            if os.path.exists(BACKUP_FILE):
                os.remove(BACKUP_FILE)

with col_valid2:
    dest_mailto = config_email.get("destinataires", "")
    sujet_encoded = urllib.parse.quote(f"Ligue du Saphir : {equipe_receveur} vs {equipe_visiteur}")
    corps_encoded = urllib.parse.quote(texte_resume)
    mailto_url = f"mailto:{dest_mailto}?subject={sujet_encoded}&body={corps_encoded}"
    st.markdown(f"""
        <a href="{mailto_url}" target="_blank" style="text-decoration: none;">
            <button style="width: 100%; padding: 10px; background-color: #f0f2f6; border: 1px solid #d1d5db; border-radius: 8px; cursor: pointer;">
                📨 Ouvrir dans mon application de courriel (Outlook/Mail)
            </button>
        </a>
    """, unsafe_allow_html=True)
