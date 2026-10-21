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
    if os.path.exists(CONFIG_EMAIL_FILE):
        try:
            with open(CONFIG_EMAIL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def sauvegarder_config_email(cfg):
    try:
        with open(CONFIG_EMAIL_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def generer_resume_match(receveur, visiteur, matchs, total_rec, total_vis, date_str, absents_info=None):
    """Génère le résumé en texte brut et en HTML."""
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

        label_a = f"{ja} (Absent)" if ja_abs else ja
        label_b = f"{jb} (Absent)" if jb_abs else jb

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
            <h3 style="margin: 0; color: #1e3d59;">Résultat final :</h3>
            <p style="font-size: 18px; margin: 8px 0;">
                <strong>{receveur}</strong> : <span style="font-size: 22px; color: #0d47a1;">{total_rec}</span> pts / 72<br>
                <strong>{visiteur}</strong> : <span style="font-size: 22px; color: #0d47a1;">{total_vis}</span> pts / 72
            </p>
            <p style="font-weight: bold; color: #2e7d32; font-size: 16px;">
                Vainqueur du match : {receveur if total_rec > total_vis else (visiteur if total_vis > total_rec else "Égalité")}
            </p>
            {absents_html_bloc}
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
    """Envoie un courriel via SMTP selon la configuration spécifiée."""
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

# Configuration email sauvegardée
config_email_actuelle = charger_config_email()

# --- ENTÊTE DU SITE WEB DE RÉFÉRENCE ---
st.title("🎱 Ligue de billard du Saphir")
st.subheader("Application de saisie des résultats - Format 3 contre 3")
st.markdown("*Plateforme officielle de gestion des matchs, de la cédule et des présences.*")
st.divider()

# --- BARRE LATÉRALE : SÉLECTION DU MATCH ET JOUEURS ---
st.sidebar.header("📋 Paramètres du Match")
equipe_receveur = st.sidebar.text_input(
    "Équipe Receveuse",
    value=st.session_state.saisie_en_cours.get("receveur", "Équipe 1")
)
equipe_visiteur = st.sidebar.text_input(
    "Équipe Visiteuse",
    value=st.session_state.saisie_en_cours.get("visiteur", "Équipe 2")
)

st.sidebar.markdown("### ⚙️ Règle des Absences")
pts_forfait_defaut = st.sidebar.number_input(
    "Pointage par défaut pour un joueur absent :",
    min_value=0,
    max_value=7,
    value=0,
    help="Points attribués au joueur absent dans ses manches. L'adversaire présent reçoit quant à lui automatiquement 8 points."
)

st.sidebar.markdown(f"### 👥 Joueurs — {equipe_receveur}")

# Joueur 1 Receveur
col_j1_r1, col_j1_r2 = st.sidebar.columns([3, 2])
j1_rec = col_j1_r1.text_input("Receveur 1", value="Jean-François", key="nom_j1_rec")
j1_rec_pres = col_j1_r2.toggle("Présent", value=True, key="pres_j1_rec")
j1_rec_pts = pts_forfait_defaut
if not j1_rec_pres:
    j1_rec_pts = st.sidebar.number_input(f"Points de {j1_rec} (Absent)", 0, 7, value=pts_forfait_defaut, key="pts_j1_rec")

# Joueur 2 Receveur
col_j2_r1, col_j2_r2 = st.sidebar.columns([3, 2])
j2_rec = col_j2_r1.text_input("Receveur 2", value="Christian", key="nom_j2_rec")
j2_rec_pres = col_j2_r2.toggle("Présent", value=True, key="pres_j2_rec")
j2_rec_pts = pts_forfait_defaut
if not j2_rec_pres:
    j2_rec_pts = st.sidebar.number_input(f"Points de {j2_rec} (Absent)", 0, 7, value=pts_forfait_defaut, key="pts_j2_rec")

# Joueur 3 Receveur
col_j3_r1, col_j3_r2 = st.sidebar.columns([3, 2])
j3_rec = col_j3_r1.text_input("Receveur 3", value="Antoine", key="nom_j3_rec")
j3_rec_pres = col_j3_r2.toggle("Présent", value=True, key="pres_j3_rec")
j3_rec_pts = pts_forfait_defaut
if not j3_rec_pres:
    j3_rec_pts = st.sidebar.number_input(f"Points de {j3_rec} (Absent)", 0, 7, value=pts_forfait_defaut, key="pts_j3_rec")

st.sidebar.markdown(f"### 👥 Joueurs — {equipe_visiteur}")

# Joueur 1 Visiteur
col_j1_v1, col_j1_v2 = st.sidebar.columns([3, 2])
j1_vis = col_j1_v1.text_input("Visiteur 1", value="Michel", key="nom_j1_vis")
j1_vis_pres = col_j1_v2.toggle("Présent", value=True, key="pres_j1_vis")
j1_vis_pts = pts_forfait_defaut
if not j1_vis_pres:
    j1_vis_pts = st.sidebar.number_input(f"Points de {j1_vis} (Absent)", 0, 7, value=pts_forfait_defaut, key="pts_j1_vis")

# Joueur 2 Visiteur
col_j2_v1, col_j2_v2 = st.sidebar.columns([3, 2])
j2_vis = col_j2_v1.text_input("Visiteur 2", value="Nicolas", key="nom_j2_vis")
j2_vis_pres = col_j2_v2.toggle("Présent", value=True, key="pres_j2_vis")
j2_vis_pts = pts_forfait_defaut
if not j2_vis_pres:
    j2_vis_pts = st.sidebar.number_input(f"Points de {j2_vis} (Absent)", 0, 7, value=pts_forfait_defaut, key="pts_j2_vis")

# Joueur 3 Visiteur
col_j3_v1, col_j3_v2 = st.sidebar.columns([3, 2])
j3_vis = col_j3_v1.text_input("Visiteur 3", value="Guy", key="nom_j3_vis")
j3_vis_pres = col_j3_v2.toggle("Présent", value=True, key="pres_j3_vis")
j3_vis_pts = pts_forfait_defaut
if not j3_vis_pres:
    j3_vis_pts = st.sidebar.number_input(f"Points de {j3_vis} (Absent)", 0, 7, value=pts_forfait_defaut, key="pts_j3_vis")

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

# Synchronisation automatique des scores lors d'un changement de présence ou de points forfait
for p_id in dict_joueurs:
    info_j = dict_joueurs[p_id]
    state_key = f"prev_state_{p_id}"
    pts_key = f"prev_pts_{p_id}"
    
    presence_changed = (state_key in st.session_state and st.session_state[state_key] != info_j["present"])
    pts_changed = (pts_key in st.session_state and st.session_state[pts_key] != info_j["pts_absent"])

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
absents_detectes = [f"{j['nom']} ({j['equipe']})" for j in dict_joueurs.values() if not j["present"]]
if absents_detectes:
    st.warning(f"⚠️ **Joueur(s) absent(s) détecté(s) :** {', '.join(absents_detectes)}. Leurs pointages par défaut ont été automatiquement préremplis.")

st.markdown("### 🎯 Grille de saisie des 9 manches (Rotation alternée 3 contre 3)")
st.info(
    "📌 **Règle de rotation :** Aucun joueur ne joue deux manches consécutives.\n\n"
    "🎱 **Règle du jeu au 8 :** Le vainqueur obtient **8 points**, le perdant obtient de **0 à 7 points** (selon le nombre de boules empochées ou la règle de forfait)."
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
        status_label = f" ❌ ({joueur_a} absent)"
    elif not b_pres:
        status_label = f" ❌ ({joueur_b} absent)"

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
            label_champ_a = f"Points de {joueur_a}" + (" (Absent)" if not a_pres else "")
            score_a = st.number_input(
                label_champ_a, 
                0, 8, 
                value=def_score_a,
                key=f"s_a_{num_manche}"
            )
        with c2:
            label_champ_b = f"Points de {joueur_b}" + (" (Absent)" if not b_pres else "")
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

# --- CALCULS FINAUX ET TOTAUX ---
total_pts_receveur = sum(m["score_a"] for m in donnees_a_sauvegarder["matchs"].values())
total_pts_visiteur = sum(m["score_b"] for m in donnees_a_sauvegarder["matchs"].values())

col_res1, col_res2, col_res3 = st.columns(3)
col_res1.metric(label=f"Total {equipe_receveur}", value=f"{total_pts_receveur} / 72 pts")
col_res2.metric(label=f"Total {equipe_visiteur}", value=f"{total_pts_visiteur} / 72 pts")

with col_res3:
    st.markdown("### 💾 Sécurité anti-panne")
    st.success("✅ Sauvegarde automatique active.\nEn cas de coupure, cliquez sur **'Restaurer'** en haut.")

st.divider()

# --- OPTION D'ENVOI PAR COURRIEL ---
st.markdown("### 📧 Envoi des résultats par courrier électronique")

col_mail1, col_mail2 = st.columns([2, 1])

with col_mail1:
    envoyer_email = st.checkbox(
        "Activer l'envoi automatique des résultats par courriel lors de la validation",
        value=config_email_actuelle.get("activer_envoi", False)
    )
    destinataires_email = st.text_input(
        "Destinataire(s) (séparer par une virgule pour plusieurs adresses) :",
        value=config_email_actuelle.get("destinataires", "")
    )

with col_mail2:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚙️ Configuration du compte d'envoi (SMTP)"):
        smtp_serveur = st.text_input("Serveur SMTP", value=config_email_actuelle.get("smtp_serveur", "smtp.gmail.com"))
        smtp_port = st.number_input("Port SMTP", value=int(config_email_actuelle.get("smtp_port", 587)))
        smtp_expediteur = st.text_input("Courriel expéditeur", value=config_email_actuelle.get("smtp_expediteur", ""))
        smtp_mdp = st.text_input("Mot de passe / Clé d'application", type="password", value=config_email_actuelle.get("smtp_mdp", ""))
        smtp_ssl = st.checkbox("Utiliser SSL (Port 465)", value=config_email_actuelle.get("smtp_ssl", False))

        if st.button("💾 Mémoriser ces paramètres d'envoi"):
            sauvegarder_config_email({
                "activer_envoi": envoyer_email,
                "destinataires": destinataires_email,
                "smtp_serveur": smtp_serveur,
                "smtp_port": smtp_port,
                "smtp_expediteur": smtp_expediteur,
                "smtp_mdp": smtp_mdp,
                "smtp_ssl": smtp_ssl
            })
            st.success("Configuration d'envoi mémorisée avec succès !")

st.divider()

# --- VALIDATION FINALE DU MATCH ---
date_du_match = datetime.now().strftime("%d/%m/%Y à %H:%M")
texte_resume, html_resume = generer_resume_match(
    equipe_receveur,
    equipe_visiteur,
    donnees_a_sauvegarder["matchs"],
    total_pts_receveur,
    total_pts_visiteur,
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
            donnees_finales["date_enregistrement"] = date_du_match
            historique.append(donnees_finales)

            with open(HISTORIQUE_FILE, "w", encoding="utf-8") as f:
                json.dump(historique, f, ensure_ascii=False, indent=4)

            st.success(f"✅ Le match entre **{equipe_receveur}** ({total_pts_receveur} pts) et **{equipe_visiteur}** ({total_pts_visiteur} pts) a été archivé avec succès !")

            # Envoi du courriel si activé
            if envoyer_email:
                if not destinataires_email.strip():
                    st.warning("⚠️ L'envoi par courriel est activé, mais aucun destinataire n'a été spécifié.")
                else:
                    sujet = f"🎱 Ligue du Saphir : {equipe_receveur} ({total_pts_receveur}) vs {equipe_visiteur} ({total_pts_visiteur}) - {date_du_match}"
                    cfg_envoi = {
                        "smtp_serveur": smtp_serveur,
                        "smtp_port": smtp_port,
                        "smtp_expediteur": smtp_expediteur,
                        "smtp_mdp": smtp_mdp,
                        "smtp_ssl": smtp_ssl
                    }
                    with st.spinner("Envoi du courriel en cours..."):
                        succes_mail, msg_mail = envoyer_courriel(
                            destinataires_email,
                            sujet,
                            texte_resume,
                            html_resume,
                            cfg_envoi
                        )
                    if succes_mail:
                        st.success(f"✉️ {msg_mail} (Envoyé à : {destinataires_email})")
                    else:
                        st.warning(f"⚠️ {msg_mail}")
                        st.info("💡 Les résultats sont néanmoins sauvegardés sur l'ordinateur.")

            # Nettoyage du fichier de secours après validation réussie
            if os.path.exists(BACKUP_FILE):
                os.remove(BACKUP_FILE)

with col_valid2:
    sujet_encoded = urllib.parse.quote(f"Ligue du Saphir : {equipe_receveur} vs {equipe_visiteur}")
    corps_encoded = urllib.parse.quote(texte_resume)
    mailto_url = f"mailto:{destinataires_email}?subject={sujet_encoded}&body={corps_encoded}"
    st.markdown(f"""
        <a href="{mailto_url}" target="_blank" style="text-decoration: none;">
            <button style="width: 100%; padding: 10px; background-color: #f0f2f6; border: 1px solid #d1d5db; border-radius: 8px; cursor: pointer;">
                📨 Ouvrir dans mon application de courriel (Outlook/Mail)
            </button>
        </a>
    """, unsafe_allow_html=True)
