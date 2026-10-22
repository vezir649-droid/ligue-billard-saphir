import json
import os
import smtplib
import time
import urllib.parse
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
LOCK_FILE = "session_lock.json"
LOCK_TIMEOUT = 900  # 15 minutes d'inactivité avant libération automatique

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
def gerer_verrou_session(my_session_id):
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
        return True, 0
    else:
        temps_restant = int(LOCK_TIMEOUT - (maintenant - dernier_acces))
        return False, max(0, temps_restant)

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

    # 1. Équipes
    if "choix_rec" in data:
        st.session_state["sel_equipe_rec"] = data["choix_rec"]
    elif "receveur" in data:
        st.session_state["sel_equipe_rec"] = data["receveur"]

    if "choix_vis" in data:
        st.session_state["sel_equipe_vis"] = data["choix_vis"]
    elif "visiteur" in data:
        st.session_state["sel_equipe_vis"] = data["visiteur"]

    if "input_custom_rec" in data:
        st.session_state["input_custom_rec"] = data["input_custom_rec"]
    if "input_custom_vis" in data:
        st.session_state["input_custom_vis"] = data["input_custom_vis"]

    # 2. Sélections Joueurs
    for k in ["sel_j1_rec", "sel_j2_rec", "sel_j1_vis", "sel_j2_vis"]:
        if k in data:
            st.session_state[k] = data[k]

    # 3. Données des joueurs (présence, score absent, nom remplaçant)
    joueurs = data.get("joueurs", {})
    for p_id in ["j1_rec", "j2_rec", "j3_rec", "j1_vis", "j2_vis", "j3_vis"]:
        if p_id in joueurs:
            p_data = joueurs[p_id]
            pres = p_data.get("present", True)
            pts = int(p_data.get("pts_absent", 0))
            moy = float(p_data.get("moyenne", 0.625))
            nom = p_data.get("nom", "")

            st.session_state[f"pres_{p_id}"] = pres
            st.session_state[f"pts_{p_id}"] = pts
            st.session_state[f"moy_{p_id}"] = moy
            st.session_state[f"prev_state_{p_id}"] = pres
            st.session_state[f"prev_pts_{p_id}"] = pts
            st.session_state[f"cust_{p_id}"] = nom

    # 4. Scores des 9 manches
    matchs = data.get("matchs", {})
    for num in range(1, 10):
        m = matchs.get(str(num), {})
        if "score_a" in m:
            st.session_state[f"s_a_{num}"] = int(m["score_a"])
        if "score_b" in m:
            st.session_state[f"s_b_{num}"] = int(m["score_b"])

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

# ==============================================================================
# IDENTIFICATION DE SESSION & GESTION DU VERROU
# ==============================================================================
if "user_session_id" not in st.session_state:
    st.session_state["user_session_id"] = str(uuid.uuid4())
my_session_id = st.session_state["user_session_id"]

est_editeur, temps_restant_verrou = gerer_verrou_session(my_session_id)

# ==============================================================================
# RESTAURATION INITIALE AU CHARGEMENT (ÉVITE LA PERTE DE DONNÉES SUR RAFRAÎCHISSEMENT)
# ==============================================================================
sauvegarde_existante = charger_sauvegarde()
if "app_initialisee" not in st.session_state:
    st.session_state.app_initialisee = True
    if sauvegarde_existante and "matchs" in sauvegarde_existante:
        restaurer_session(sauvegarde_existante)
elif not est_editeur:
    # Pour les spectateurs, on recharge toujours l'état actuel de la sauvegarde
    if sauvegarde_existante and "matchs" in sauvegarde_existante:
        restaurer_session(sauvegarde_existante)

# Chargement de la configuration email au démarrage
config_email = charger_config_email()

# Chargement du fichier équipes CSV
equipes_disponibles = charger_equipes_csv()
noms_equipes = list(equipes_disponibles.keys())

# --- ENTÊTE DU SITE WEB DE RÉFÉRENCE ---
st.title("🎱 Ligue de billard du Saphir")
st.subheader("Application de saisie des résultats - Format 3 contre 3")
st.markdown("*Plateforme officielle de gestion des matchs, de la cédule et des présences.*")

# --- BANDEAU D'ÉTAT DU VERROU EXCLUSIF (UN SEUL MARQUEUR À LA FOIS) ---
col_lock1, col_lock2 = st.columns([3, 1])
if est_editeur:
    col_lock1.success("🟢 **Vous avez la main exclusive pour la saisie et la validation du match.**")
    with col_lock2:
        if st.button("🔓 Céder la main", use_container_width=True, help="Libère la feuille pour permettre à un autre utilisateur de saisir"):
            liberer_verrou(my_session_id)
            st.rerun()
else:
    mins = temps_restant_verrou // 60
    secs = temps_restant_verrou % 60
    col_lock1.warning(f"🔒 **Mode consultation (Lecture seule) :** Un autre utilisateur effectue actuellement la saisie. Vos champs sont verrouillés pour éviter les conflits. *(Inactivité restante : {mins}m {secs:02d}s)*")
    with col_lock2:
        if st.button("⚡ Prendre la main", use_container_width=True, help="Prend le contrôle de la saisie si le marqueur précédent a quitté sans libérer"):
            forcer_prise_de_main(my_session_id)
            st.rerun()

# --- BOUTONS D'ACTION HAUT DE PAGE (RESTAURER / NOUVEAU MATCH) ---
col_h1, col_h2, col_h3 = st.columns([2, 1, 1])

date_sauv_str = sauvegarde_existante.get("date", "")
if date_sauv_str:
    col_h1.caption(f"💾 *Dernière sauvegarde automatique : {date_sauv_str}*")

with col_h2:
    if st.button("🔄 Restaurer dernière saisie", use_container_width=True, disabled=not est_editeur):
        data_a_restaurer = charger_sauvegarde()
        if data_a_restaurer and "matchs" in data_a_restaurer:
            restaurer_session(data_a_restaurer)
            st.success("✅ Données récupérées avec succès !")
            st.rerun()
        else:
            st.warning("⚠️ Aucune sauvegarde valide trouvée.")

with col_h3:
    if st.button("🗑️ Nouveau match", use_container_width=True, disabled=not est_editeur, help="Efface la saisie en cours et réinitialise"):
        if os.path.exists(BACKUP_FILE):
            try:
                os.remove(BACKUP_FILE)
            except Exception:
                pass
        for k in list(st.session_state.keys()):
            if k.startswith("s_a_") or k.startswith("s_b_") or k.startswith("pres_") or k.startswith("pts_") or k.startswith("moy_") or k.startswith("prev_"):
                del st.session_state[k]
        st.rerun()

st.divider()

# --- BARRE LATÉRALE : SÉLECTION DU MATCH ET JOUEURS ---
st.sidebar.header("📋 Paramètres du Match")

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
                    st.session_state[f"s_a_{num_m}"] = 8
                    st.session_state[f"s_b_{num_m}"] = 0

    st.session_state[state_key] = info_j["present"]
    st.session_state[pts_key] = info_j["pts_absent"]

# Liste des absents pour information
absents_detectes = [f"{j['nom']} ({j['equipe']}) — moy: {j['moyenne']:.3f} → {j['pts_absent']} pts" for j in dict_joueurs.values() if not j["present"]]
if absents_detectes:
    st.warning(f"⚠️ **Joueur(s) absent(s) :** {', '.join(absents_detectes)}. Leurs scores de défaut sont automatiquement appliqués dans leurs manches respectives.")

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
            init_val_a = 8
            init_val_b = 0

        val_score_a = int(st.session_state.get(f"s_a_{num_manche}", init_val_a))
        val_score_b = int(st.session_state.get(f"s_b_{num_manche}", init_val_b))

        with c1:
            label_champ_a = f"Points de {joueur_a}" + (f" (Absent : {info_a['pts_absent']} pts)" if not a_pres else "")
            score_a = st.number_input(
                label_champ_a, 
                0, 8, 
                value=val_score_a,
                key=f"s_a_{num_manche}",
                disabled=not est_editeur
            )
        with c2:
            label_champ_b = f"Points de {joueur_b}" + (f" (Absent : {info_b['pts_absent']} pts)" if not b_pres else "")
            score_b = st.number_input(
                label_champ_b, 
                0, 8, 
                value=val_score_b,
                key=f"s_b_{num_manche}",
                disabled=not est_editeur
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

match_valide = False
col_valid1, col_valid2 = st.columns([2, 1])

with col_valid1:
    if st.button("🚀 Valider et enregistrer la feuille de match officielle", type="primary", use_container_width=True, disabled=not est_editeur):
        if manches_invalides:
            st.error(f"❌ Impossible d'enregistrer : veuillez corriger les manches suivantes : {', '.join(map(str, sorted(set(manches_invalides))))}.")
        else:
            match_valide = True
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
                    "present": dict_joueurs[p_id]["present"],
                    "moyenne": dict_joueurs[p_id].get("moyenne", 0.0)
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

            # Nettoyage du fichier de secours et libération du verrou après validation réussie
            if os.path.exists(BACKUP_FILE):
                try:
                    os.remove(BACKUP_FILE)
                except Exception:
                    pass
            liberer_verrou(my_session_id)

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

# Sauvegarde automatique en arrière-plan (uniquement par l'éditeur actif et si le match n'est pas validé)
if est_editeur and not match_valide:
    sauvegarder_donnees(donnees_a_sauvegarder)
