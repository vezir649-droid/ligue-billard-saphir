# 🎱 Ligue de billard Boule en main — Salle Le Saphir

Application web officielle développée avec [Streamlit](https://streamlit.io/) pour la gestion complète de la **Ligue de billard Boule en main (Salle Le Saphir)** : portail d'accueil multi-rôles (**Spectateur**, **Marqueur**, **Administrateur**), saisie en direct des feuilles de matchs réguliers (**3 contre 3**), **Scanner IA de feuilles de match manuscrites par photo (Gemini Vision)**, organisation de **tournois officiels** (Simple 1v1 & Double 2v2) avec **Mode Téléviseur / Casting TV auto-actualisé**, **Statistiques & Classements**, **Administration sécurisée** et **Synchronisation Cloud GitHub intégrale anti-veille avec fusion intelligente**.

---

## ✨ Fonctionnalités principales de l'application

### 1. 🚪 Portail d'ouverture & Niveaux d'accès (3 rôles + Documentation intégrée)
Dès l'ouverture de l'application, la page d'accueil présente trois modes d'accès distincts ainsi que la documentation officielle :

1. **👁️ Accès Spectateur (affiché en premier — sans mot de passe) :**
   * Accès immédiat en un clic (`👁️ Entrer en mode Spectateur`) en **lecture seule**.
   * Permet de suivre en direct la feuille de match en cours, les classements de la saison, les statistiques des joueurs et l'arborescence des tournois.
2. **🔒 Accès Marqueur / Éditeur (protégé par mot de passe — par défaut : `saphir2026`) :**
   * Permet de saisir les pointages des 9 manches (3 contre 3), de numériser les feuilles papier par photo IA, d'approuver et d'archiver les feuilles de match, et de créer/gérer les tournois (Simple et Double).
   * **Restriction de sécurité :** le Marqueur n'a **pas** accès au volet `⚙️ Administration`.
3. **🛡️ Accès Administrateur (protégé par identifiant/mot de passe — par défaut : `admin2026`) :**
   * Donne accès à l'ensemble des fonctions de marqueur ainsi qu'**en exclusivité au volet `⚙️ Administration`** (édition des équipes, rectification de matchs archivés, nouvelle saison, configuration courriel SMTP, clés d'API IA, mots de passe et synchronisation GitHub).
4. **📖 Documentation de l'application (`README.md`) & Impression A4 :**
   * Consultable directement depuis la page d'ouverture sans connexion requise.
   * Inclut un bouton **« 🖨️ Préparer et lancer l'impression de la documentation »** (mise en page A4 automatique) et un bouton **« ⬇️ Télécharger README.md »**.

---

### 2. 📷 Scanner Intelligent de Feuilles de Match (IA Multimodale Gemini Vision)
L'application intègre un module de pointe basé sur l'IA de vision de Google (**Gemini 3.1 / 3.5 Flash**) capable de lire et de retranscrire automatiquement des feuilles de match papier manuscrites :

* **Prise de vue tout-en-un :**
  * **Sur mobile et tablette :** Utilisation directe de l'appareil photo via `st.camera_input` pour photographier instantanément la feuille au bord de la table.
  * **Sur ordinateur :** Téléversement d'image par glisser-déposer (`st.file_uploader`) acceptant les formats JPG, PNG et WebP.
* **Optimisation et vitesse éclair (2 à 3 secondes) :**
  * Redimensionnement et compression automatique en mémoire vive par Pillow (PIL) avant transmission, garantissant une analyse ultrarapide sans temps de latence.
* **Extraction exhaustive & Contrôle de cohérence :**
  * Détection automatique de la **date du match**, des **équipes receveuse et visiteuse**, et des **6 joueurs alignés**.
  * Déchiffrement de l'écriture manuscrite pour les **9 duels individuels** (scores des manches de 0 à 8 points).
  * Calcul et vérification mathématique des cumuls individuels et des totaux par équipe.
  * Détection des capitaines signataires / approbateurs.
* **Deux modes d'action en un clic :**
  * **`📥 Injecter dans la saisie du match en direct` :** Pré-remplit automatiquement la feuille de match en direct pour vérification, ajustement ou continuation de saisie.
  * **`💾 Archiver directement dans l'historique officiel` :** Sauvegarde instantanément la rencontre dans l'historique JSON, génère la copie `.bak` et déclenche la synchronisation distante vers GitHub sans aucune manipulation manuelle.
* **Points d'accès rapides :**
  * Sélectionnable dans la liste déroulante principale : `📷 Numériser une feuille de match (Scanner IA)`.
  * Raccourci dédié dans la barre latérale : `📷 Numériser une feuille (IA)`.

---

### 3. 📝 Feuille de Match Officielle (3 contre 3 — Jeu au 8)
* **Bandeau « Live Scoreboard » épinglé en haut de page :**
  * Affichage permanent en temps réel du score global (**Équipe Receveuse vs Équipe Visiteuse**), d'une jauge de progression des **9 manches** (`X / 9 manches complétées`) et du statut de verrouillage.
* **Rotation optimisée des 9 duels :**
  * Chaque joueur de l'équipe receveuse affronte les 3 joueurs de l'équipe visiteuse selon un ordre officiel garantissant qu'**aucun joueur ne dispute deux manches consécutives**.
* **Pointage souple des manches & Validation instantanée :**
  * Saisie libre de **0 à 8 points** par joueur **sans obligation d'un score de 8** pour valider une manche ou enregistrer la feuille de match.
  * Indicateurs visuels par manche (`⚪ À jouer`, `✅ Manche — 🏆 Victoire`, `⚖️ Égalité`) et synchronisation immédiate des totaux par équipe et par joueur.
* **Approbation & Impression A4 :**
  * Double approbation officielle par un représentant de chaque équipe avant archivage.
  * Génération d'une **feuille de match officielle calibrée pour l'impression sur une seule page A4**.
* **Compatibilité complète Thème Clair (*Light*) & Thème Sombre (*Dark*) :**
  * Adaptation automatique des contrastes pour les cartes de métriques (`st.metric`), les onglets, les podiums, les cartes de rencontres et les aperçus A4.

---

### 4. 📋 Paramètres du Match (Barre latérale & Contrôles de rencontre)
La barre latérale **« 📋 Paramètres du Match »** regroupe tous les réglages d'avant-match et de gestion en cours de rencontre :

* **Sélection des équipes (`🔵 Équipe Receveuse 🏠` & `🟠 Équipe Visiteuse 🚗`) :**
  * Chargement automatique de la liste officielle des équipes et de leurs joueurs réguliers depuis `equipes-saphir.csv`.
  * Option **« Autre / Personnalisée »** permettant de saisir manuellement le nom d'une équipe hors liste.
* **Alignement et ordre des 3 joueurs (`Joueur 1`, `Joueur 2`, `Joueur 3`) :**
  * **Sélection sans doublon :** Le choix du `Joueur 1` filtre automatiquement la liste déroulante du `Joueur 2`, et le **`Joueur 3`** est déduit automatiquement à partir du troisième joueur régulier de l'équipe.
  * **Impact sur la cédule :** L'ordre sélectionné (`J1`, `J2`, `J3`) alimente automatiquement l'ordre des duels dans les 9 manches afin de respecter la règle de repos entre les manches.
* **Ajout de joueurs remplaçants (`Remplaçant...`) :**
  * Pour chaque équipe, l'option **« Remplaçant... »** dans la liste déroulante ouvre un champ de saisie permettant d'inscrire le nom d'un joueur remplaçant (*Sub*).
* **Gestion des présences (`Présent / Absent`) et calcul automatique du score forfaitaire :**
  * Chaque joueur possède un commutateur individuel **`Présent`** (activé par défaut).
  * Lorsqu'un joueur est marqué **Absent** :
    1. Un champ numérique s'affiche pour saisir sa **moyenne officielle** (acceptée sous forme de ratio décimal, ex. `0.625`, ou de pourcentage, ex. `62.5`).
    2. Le pointage forfaitaire par manche du joueur absent est calculé automatiquement selon la formule officielle de la ligue :
       $$	ext{Score absent} = \min\left(7,\ 	ext{arrondi}\left(rac{	ext{moyenne} 	imes 24}{3}ight)ight)$$
    3. **Attribution automatique dans les manches concernées :**
       * **Un seul joueur absent :** le joueur absent reçoit son score calculé (maximum **7 points** par manche) et son adversaire présent reçoit automatiquement **8 points**.
       * **Forfait double (les 2 joueurs absents) :** chacun des deux joueurs absents reçoit le pointage correspondant à sa propre moyenne.
* **🎵 Jukebox — Musique d'ambiance gratuite (Lecteur Radio Web autonome) :**
  * Intégré en haut de la barre latérale et accessible en tout temps (quel que soit l'onglet ouvert) sans interrompre la musique lors de la saisie des pointages.
  * **Sélection par genre musical (6 ambiances, 3 stations gratuites sans publicité par genre) :**
    * 🎸 **Rock Classique & Blues** (*Radio Paradise Rock*, *Classic Mix*, *FIP Rock*)
    * 🕺 **Hits Rétro 70s / 80s / 90s** (*Underground 80s*, *Left Coast 70s*, *FIP Groove*)
    * 🎷 **Jazz, Blues & Lounge** (*Secret Agent Lounge*, *FIP Jazz*, *Illinois Street Lounge*)
    * 🎧 **Lo-Fi & Chill Beats** (*Groove Salad Chill*, *Mellow Mix*, *FIP Chill*)
    * 🤠 **Country & Rock Sudiste** (*Boot Liquor Country*, *Folk Forward*, *Americana Rock*)
    * ⚡ **Pop / Dance / Groove actuel** (*PopTron Electropop*, *Lush Groove*, *FIP Electro*)
  * **Contrôles instantanés :** Bouton **▶️ Démarrer / ⏹️ Arrêter la musique**, bouton **⏭️ Autre station**, curseur de **🔊 Volume (0 à 100 %)** et mode **🔇 Muet**.
* **Sécurité de saisie & Contrôles de session :**
  * **🔄 Restaurer saisie :** Recharge à tout moment la dernière sauvegarde automatique (`sauvegarde_saisie_secours.json`) en cas de coupure ou de rafraîchissement navigateur.
  * **🗑️ Nouveau match & ↩️ Annuler effacement :** Réinitialise la feuille à `0 - 0` tout en conservant une copie de secours dans la corbeille (`sauvegarde_annulee_secours.json`) pour permettre d'annuler un effacement accidentel en un clic.
  * **🚪 Déconnexion / Accueil :** Sauvegarde automatiquement le match et les tournois en cours sur le disque, libère le verrou exclusif du marqueur et retourne à l'écran d'accueil.

---

### 5. 🏆 Module de Tournois Officiels (Simple 1v1 & Double 2v2) & Mode Téléviseur
* **Deux catégories indépendantes :**
  * **👤 Tournoi en Simple (1 contre 1)** — Joueurs individuels.
  * **👥 Tournoi en Double / Équipes (2 contre 2)** — Duos constitués aléatoirement ou manuellement.
* **Trois formules de compétition prises en charge (avec équilibrage automatique pour 18, 20, 22 et 24 joueurs ainsi que jusqu'à 32 participants) :**
  1. **⚡ Élimination directe (Simple élimination)** : Préliminaires en *2 de 3* (premier à 2 victoires) et Finale en *3 de 5* (premier à 3 victoires) :
     * **Cas spécifiques 18, 20, 22 et 24 joueurs (tous jouent au 1er tour + équilibrage au 2e tour) :**
       * **18 joueurs :** **9 matchs** au 1er tour (tous les 18 joueurs jouent) $ightarrow$ **1 match d'équilibrage** au 2e tour (+ 7 gagnants du 1er tour promus) $ightarrow$ **4 matchs** en Quarts de finale (8 joueurs) $ightarrow$ **2 matchs** en Demi-finales $ightarrow$ **1 Finale**.
       * **20 joueurs :** **10 matchs** au 1er tour (tous les 20 joueurs jouent) $ightarrow$ **2 matchs d'équilibrage** au 2e tour (+ 6 gagnants du 1er tour promus) $ightarrow$ **4 matchs** en Quarts de finale $ightarrow$ **2 matchs** en Demi-finales $ightarrow$ **1 Finale**.
       * **22 joueurs :** **11 matchs** au 1er tour (tous les 22 joueurs jouent) $ightarrow$ **3 matchs d'équilibrage** au 2e tour (+ 5 gagnants du 1er tour promus) $ightarrow$ **4 matchs** en Quarts de finale $ightarrow$ **2 matchs** en Demi-finales $ightarrow$ **1 Finale**.
       * **24 joueurs :** **12 matchs** au 1er tour (tous les 24 joueurs jouent) $ightarrow$ **4 matchs d'équilibrage** au 2e tour (+ 4 gagnants du 1er tour promus) $ightarrow$ **4 matchs** en Quarts de finale $ightarrow$ **2 matchs** en Demi-finales $ightarrow$ **1 Finale**.
     * **Exemple en Double (9, 10, 11 ou 12 duos en 2v2) :** Calcul automatique des passes-droits pour équilibrer les Quarts de finale (**4 matchs**) et Demi-finales (**2 matchs**).
  2. **🛡️ Double élimination — Winner & Loser Bracket (Seconde chance)** :
     * **🟦 Tableau des Gagnants (*Winner Bracket*)** : *2 de 3* — pour **18, 20, 22 et 24 joueurs**, tous les joueurs disputent le 1er tour (**9, 10, 11 ou 12 matchs**), puis le 2e tour d'équilibrage (**1, 2, 3 ou 4 matchs** + gagnants promus) forme les Quarts de finale à **4 matchs (8 joueurs)**.
     * **🟧 Tableau de Repêchage (*Loser Bracket — Seconde chance*)** : *2 de 3* — tout participant perdant un premier match est automatiquement reversé dans le Loser Bracket et **doit obligatoirement jouer contre un adversaire réel (jamais contre un passe-droit)**.
     * **🚫 Règle officielle d'évitement des rematchs (*Anti-Rematch*) :** Les joueurs reversés dans le tableau des perdants (*Loser Bracket*) sont automatiquement croisés et permutés afin de **ne jamais rejouer contre un adversaire déjà affronté dans le tableau des gagnants (*Winner Bracket*)**.
     * **🏆 Grande Finale** : *3 de 5* entre le champion du Winner Bracket et le survivant du Loser Bracket.
* **📺 Mode Téléviseur / Casting TV (16:9 Plein écran & Rafraîchissement automatique en direct) :**
  * **Bouton dédié « 📺 Mode TV » :** Présent au sommet de l'onglet Tournois et dans le dialogue d'arborescence. Ouvre instantanément la vue TV dans un **nouvel onglet** prêt à être projeté (Chromecast, Google Cast, écran secondaire HDMI), permettant de continuer à saisir les scores sur votre ordinateur sans perturber l'affichage des spectateurs.
  * **Thème sombre « Dark Stadium » haute lisibilité :** Design optimisé pour écrans 1080p / 4K avec contrastes renforcés (noms blancs nets, scores en badges vifs, bordures émeraude pour les vainqueurs et encadré d'or pour le Champion), parfaitement lisible à 5–10 mètres de distance dans la salle de billard.
  * **Bandeau dynamique des tables en cours :** Affichage en temps réel des matchs actifs assignés aux tables (ex. *🎱 Table 1 : Tremblay J. (1 - 0) Gagnon M.*).
  * **Rafraîchissement automatique toutes les 20 secondes :** Propulsé par un composant fragment Streamlit (`@st.fragment(run_every=20)`) avec décompte visuel en direct (`🔄 MAJ : 20s`) et horloge numérique (`⏰ HH:MM:SS`). Dès qu'un score est mis à jour sur l'ordinateur du marqueur, le téléviseur s'actualise automatiquement sans aucune manipulation.
  * **Lien direct par URL :** Accessible à tout moment en ajoutant `?view=tv` à l'adresse de l'application (ex. `http://localhost:8501/?view=tv&mode=simple` ou `?view=tv&mode=double`).
  * **Bouton `⛶ Plein écran`** (ou touche `F11`) et boutons de bascule rapide entre **Simple (1v1)** et **Double (2v2)** directement sur l'écran TV.
* **Suivi opérationnel & Diffusion standard :**
  * **Affichage automatique du tournoi actif** et ouverture directe de son arborescence à jour lors de l'accès à l'onglet Tournois.
  * **Barre de progression globale** (`matchs terminés / total`) et panneau **« 🎱 En direct / Prochains matchs prêts à appeler aux tables »** avec numéro de table et horaire estimé.
  * **Arborescence visuelle interactive & Impression A4 :** Affichage grand format et impression officielle **A4 Paysage** avec code couleur par tableau (Bleu Gagnants, Ambre Seconde chance, Or Grande Finale).
  * **📧 Envoi de l'arborescence officielle par courriel :**
    * Option accessible en un clic dans la boîte de dialogue d'arborescence, dans la barre de commandes du tournoi actif et dans l'historique des tournois archivés.
    * Génère et attache la **page HTML complète de l'arborescence** ainsi que le fichier `historique_tournois.json` en pièces jointes.
  * Gestion des **passes-droits en cours de tournoi** (`🎟️ Passe-droit`) pour promouvoir un joueur ou un duo au tour suivant.

---

### 6. 👁️ Mode Spectateur & Gestion de la Main (Verrouillage multi-utilisateurs)
* **Accès Spectateur sans mot de passe :**
  * Consultation en direct des scores de la feuille de match (par équipe, par joueur et manche par manche), des classements et de l'arborescence des tournois.
  * Rafraîchissement automatique (toutes les 5s / 15s / 30s) ou manuel en un clic.
* **Contrôle exclusif du Marqueur / Administrateur :**
  * Un seul éditeur détient la main active à la fois (`session_lock.json`) afin d'éviter tout conflit d'écriture.
  * Boutons **« 🤝 Céder la main »** (avec sauvegarde automatique préalable sur le disque) et **« ⚡ Prendre la main »** (avec rechargement automatique de la dernière sauvegarde).

---

### 7. 📊 Statistiques, Podiums & Historiques
* **Podiums Visuels Top 3 (`🥇 1er`, `🥈 2e`, `🥉 3e`) :**
  * Cartes podium en haut des classements **Équipes** et **Joueurs** mettant en valeur les 3 meilleurs performeurs de la saison.
* **Tableaux statistiques complets :**
  * **Classement des équipes :** Matchs joués (PJ), Victoires, Défaites, Égalités, Points Pour, Points Contre, Différentiel, Moyenne pts/match, % Victoires et **Points au classement**.
  * **Classement individuel des joueurs :** Manches jouées, Manches gagnées (score de 8), % Victoires, Points cumulés et **Moyenne officielle sur 8**.
  * **Consultation et réimpression A4** de toutes les feuilles de matchs archivées et de tous les tournois passés.

---

### 8. ⚙️ Espace Administration, API Saphir & Persistance Cloud GitHub Sécurisée
Le volet **`⚙️ Administration`** (réservé exclusivement à l'accès **`🛡️ Administrateur`**) regroupe les outils avancés de gestion de la ligue, de persistance des données, d'interconnexion API et de maintenance du système.

* **Onglets et modules du volet Administration :**
  * **👥 Équipes (`equipes-saphir.csv`) :** Tableau interactif modifiable en direct, ajout rapide d'équipes et de joueurs réguliers, import/export CSV et validation instantanée.
  * **📝 Match passé (Saisie de matchs antérieurs ou en retard) :** Formulaire complet permettant d'enregistrer rétroactivement une rencontre disputée avec sélection de la date/heure, composition des équipes et scores des 9 manches selon la rotation officielle alternée.
  * **✏️ Rectifications (Correction ou suppression de matchs archivés) :** 
    * Correction ciblée des scores de manche, des présences ou des alignements avec motif officiel et régénération immédiate de la feuille officielle.
    * **🗑️ Suppression d'un match de l'historique :** Option sécurisée avec confirmation, sauvegarde `.bak` horodatée et synchronisation GitHub automatique.
  * **🗓️ Saison (Gestion des cycles de compétition) :** Initialisation d'une nouvelle saison, archivage des statistiques précédentes et remise à zéro sécurisée des classements actifs.
  * **💾 Sauvegardes & Restauration fiabilisée (Nettoyage JSON pur) :**
    * **Nettoyage et allègement JSON pur :** Suppression complète du code HTML verbeux et des images base64 dans `historique_matchs.json`. Le fichier passe de ~448 Ko à ~56 Ko (réduction de plus de **88 %**), accélérant les synchronisations réseau.
    * **Exports & Envois par courriel :** Téléchargement direct des bases JSON et envoi automatisé des bilans par courriel SMTP avec pièces jointes.
  * **🌐 Test POST Saphir (`billardImport`) :**
    * Module interactif d'interconnexion avec l'API officielle de la Salle Le Saphir (`POST https://saphirbillard.com/index.php?eID=billardImport`).
    * En-têtes HTTP `Content-Type: application/json` et `X-API-Key: ...` avec test de latence et coloration syntaxique de la réponse serveur.
  * **📧 SMTP (Notifications et bilans officiels) :** Configuration du serveur d'expédition courriel, test d'envoi en direct et routage des alertes administratives.
  * **🔑 Sécurité (Gestion des accès, Clés API & Secrets) :**
    * Modification sécurisée des mots de passe Marqueur et Administrateur avec hachage cryptographique SHA-256 dans `config_auth.json`.
    * **Gestion des clés d'API IA :** Configuration de la clé **Google Gemini API** (`gemini_api_key`) pour la numérisation des photos de feuilles de scores.
    * **Protection stricte des identifiants sensibles :** Intégration transparente de `st.secrets` (`.streamlit/secrets.toml`) pour stocker en lieu sûr le jeton GitHub, la clé Gemini et les mots de passe SMTP.

* **☁️ Synchronisation automatique GitHub intégrale avec Fusion Intelligente (Anti-écrasement) :**
  * **Bouclier anti-écrasement :** Le système de synchronisation au réveil compare l'horodatage des fichiers et n'écrase jamais une sauvegarde locale plus récente par un commit distant plus ancien.
  * **Fusion automatique (Merge) :** Si un match a été saisi localement (ou via le scanner photo), il est automatiquement conservé et fusionné avec les données distantes par sa clé unique (`receveur + visiteur + date`), interdisant toute perte accidentelle de match.
  * **Dès qu'un fichier est modifié :** Poussée automatique vers GitHub pour **tous les fichiers .json et .csv** (validation de match, numérisation photo, tournois, équipes CSV, mots de passe).
  * **Écritures atomiques & Sauvegardes `.bak` :** Toutes les écritures locales sont atomiques avec copies de sauvegarde de secours `.bak` pour une résilience absolue.

---

## 📦 Installation et démarrage local

### 1. Prérequis
* Python 3.10 ou supérieur

### 2. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 3. Lancement de l'application
```bash
streamlit run app.py
```

L'application est alors accessible dans votre navigateur à l'adresse `http://localhost:8501`.

### 4. Configuration des secrets Streamlit (Local & Streamlit Cloud)
Créez un fichier `.streamlit/secrets.toml` (ou renseignez les variables dans le panneau **Settings → Secrets** sur Streamlit Cloud) :
```toml
# Synchronisation automatique GitHub
[github]
token = "ghp_votre_jeton_personnel_github"
repo = "vezir649-droid/ligue-billard-saphir"
branch = "main"

# Intelligence Artificielle (Scanner photo Gemini Vision)
[gemini]
api_key = "AIzaSy_votre_cle_gemini_vision"

# Administration & Mots de passe
[admin]
mot_de_passe = "saphir2026"
mot_de_passe_admin = "admin2026"

# Notifications SMTP (optionnel)
[email]
smtp_expediteur = "votre_adresse@gmail.com"
smtp_mdp = "votre_mot_de_passe_application"
smtp_serveur = "smtp.gmail.com"
smtp_port = 587
smtp_ssl = false
```

---

## 🗂️ Structure des fichiers principaux

| Fichier | Rôle |
| :--- | :--- |
| `app.py` | Code source principal de l'application Streamlit (Saisie, Scanner IA, Tournois, Stats, Admin, Mode TV) |
| `README.md` | Documentation officielle complète (affichée et imprimable depuis la page d'ouverture) |
| `.streamlit/secrets.toml` | Stockage sécurisé des clés d'accès (jeton GitHub, clé Gemini Vision, mots de passe SMTP et Admin) |
| `equipes-saphir.csv` | Liste officielle des équipes et de leurs 3 joueurs réguliers (synchronisée sur GitHub) |
| `historique_matchs.json` | Base de données JSON allégée (100 % JSON pur, sans HTML) des feuilles 3v3 validées (synchronisée sur GitHub) |
| `historique_tournois.json` | Historique officiel complet des tournois Simples & Doubles (synchronisé sur GitHub) |
| `tournois_data.json` | État en temps réel des tournois actifs (synchronisé sur GitHub) |
| `sauvegarde_saisie_secours.json` | Sauvegarde temps réel de la feuille de match 3v3 en cours de saisie (synchronisée sur GitHub) |
| `sauvegarde_annulee_secours.json` | Corbeille de secours permettant d'annuler un « Nouveau match » |
| `session_lock.json` | Verrouillage multi-utilisateurs de la main active (Marqueur / Administrateur) |
| `config_auth.json` | Empreintes SHA-256 des mots de passe Marqueur et Administrateur |
| `config_email.json` | Paramètres SMTP pour l'envoi automatique des rapports et sauvegardes (synchronisé sur GitHub) |
| `config_admin.json` | Configuration administrative locale de la synchronisation GitHub et clé Gemini |

---

## 📄 Licence
Projet développé pour la **Ligue de billard Boule en main — Salle Le Saphir**. Libre d'utilisation et d'adaptation (Licence MIT).
