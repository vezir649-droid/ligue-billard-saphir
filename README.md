# 🎱 Ligue de billard Boule en main — Salle Le Saphir

Application web officielle développée avec [Streamlit](https://streamlit.io/) pour la gestion complète de la **Ligue de billard Boule en main (Salle Le Saphir)** : portail d'accueil multi-rôles (**Spectateur**, **Marqueur**, **Administrateur**), saisie en direct des feuilles de matchs réguliers (**3 contre 3**), organisation de **tournois officiels** (Simple 1v1 & Double 2v2), **Statistiques & Classements**, **Administration sécurisée** et **Synchronisation Cloud GitHub anti-veille**.

---

## ✨ Fonctionnalités principales de l'application

### 1. 🚪 Portail d'ouverture & Niveaux d'accès (3 rôles + Documentation intégrée)
Dès l'ouverture de l'application, la page d'accueil présente trois modes d'accès distincts ainsi que la documentation officielle :

1. **👁️ Accès Spectateur (affiché en premier — sans mot de passe) :**
   * Accès immédiat en un clic (`👁️ Entrer en mode Spectateur`) en **lecture seule**.
   * Permet de suivre en direct la feuille de match en cours, les classements de la saison, les statistiques des joueurs et l'arborescence des tournois.
2. **🔒 Accès Marqueur / Éditeur (protégé par mot de passe — par défaut : `saphir2026`) :**
   * Permet de saisir les pointages des 9 manches (3 contre 3), d'approuver et d'archiver les feuilles de match, et de créer/gérer les tournois (Simple et Double).
   * **Restriction de sécurité :** le Marqueur n'a **pas** accès au volet `⚙️ Administration`.
3. **🛡️ Accès Administrateur (protégé par identifiant/mot de passe — par défaut : `admin2026`) :**
   * Donne accès à l'ensemble des fonctions de marqueur ainsi qu'**en exclusivité au volet `⚙️ Administration`** (édition des équipes, rectification de matchs archivés, nouvelle saison, configuration courriel SMTP, mots de passe et synchronisation GitHub).
4. **📖 Documentation de l'application (`README.md`) & Impression A4 :**
   * Consultable directement depuis la page d'ouverture sans connexion requise.
   * Inclut un bouton **« 🖨️ Préparer et lancer l'impression de la documentation »** (mise en page A4 automatique) et un bouton **« ⬇️ Télécharger README.md »**.

---

### 2. 📝 Feuille de Match Officielle (3 contre 3 — Jeu au 8)
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

### 3. 📋 Paramètres du Match (Barre latérale & Contrôles de rencontre)
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
       $$\text{Score absent} = \min\left(7,\ \text{arrondi}\left(\frac{\text{moyenne} \times 24}{3}\right)\right)$$
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

### 4. 🏆 Module de Tournois Officiels (Simple 1v1 & Double 2v2)
* **Deux catégories indépendantes :**
  * **👤 Tournoi en Simple (1 contre 1)** — Joueurs individuels.
  * **👥 Tournoi en Double / Équipes (2 contre 2)** — Duos constitués aléatoirement ou manuellement.
* **Trois formules de compétition prises en charge (avec équilibrage automatique pour 18, 20, 22 et 24 joueurs ainsi que jusqu'à 32 participants) :**
  1. **⚡ Élimination directe (Simple élimination)** : Préliminaires en *2 de 3* (premier à 2 victoires) et Finale en *3 de 5* (premier à 3 victoires) :
     * **Cas spécifiques 18, 20, 22 et 24 joueurs (tous jouent au 1er tour + équilibrage au 2e tour) :**
       * **18 joueurs :** **9 matchs** au 1er tour (tous les 18 joueurs jouent) $\rightarrow$ **1 match d'équilibrage** au 2e tour (+ 7 gagnants du 1er tour promus) $\rightarrow$ **4 matchs** en Quarts de finale (8 joueurs) $\rightarrow$ **2 matchs** en Demi-finales $\rightarrow$ **1 Finale**.
       * **20 joueurs :** **10 matchs** au 1er tour (tous les 20 joueurs jouent) $\rightarrow$ **2 matchs d'équilibrage** au 2e tour (+ 6 gagnants du 1er tour promus) $\rightarrow$ **4 matchs** en Quarts de finale $\rightarrow$ **2 matchs** en Demi-finales $\rightarrow$ **1 Finale**.
       * **22 joueurs :** **11 matchs** au 1er tour (tous les 22 joueurs jouent) $\rightarrow$ **3 matchs d'équilibrage** au 2e tour (+ 5 gagnants du 1er tour promus) $\rightarrow$ **4 matchs** en Quarts de finale $\rightarrow$ **2 matchs** en Demi-finales $\rightarrow$ **1 Finale**.
       * **24 joueurs :** **12 matchs** au 1er tour (tous les 24 joueurs jouent) $\rightarrow$ **4 matchs d'équilibrage** au 2e tour (+ 4 gagnants du 1er tour promus) $\rightarrow$ **4 matchs** en Quarts de finale $\rightarrow$ **2 matchs** en Demi-finales $\rightarrow$ **1 Finale**.
     * **Exemple en Double (9, 10, 11 ou 12 duos en 2v2) :** Calcul automatique des passes-droits pour équilibrer les Quarts de finale (**4 matchs**) et Demi-finales (**2 matchs**).
  2. **🛡️ Double élimination — Winner & Loser Bracket (Seconde chance)** :
     * **🟦 Tableau des Gagnants (*Winner Bracket*)** : *2 de 3* — pour **18, 20, 22 et 24 joueurs**, tous les joueurs disputent le 1er tour (**9, 10, 11 ou 12 matchs**), puis le 2e tour d'équilibrage (**1, 2, 3 ou 4 matchs** + gagnants promus) forme les Quarts de finale à **4 matchs (8 joueurs)**.
     * **🟧 Tableau de Repêchage (*Loser Bracket — Seconde chance*)** : *2 de 3* — tout participant perdant un premier match est automatiquement reversé dans le Loser Bracket et **doit obligatoirement jouer contre un adversaire réel (jamais contre un passe-droit)**.
     * **🚫 Règle officielle d'évitement des rematchs (*Anti-Rematch*) :** Les joueurs reversés dans le tableau des perdants (*Loser Bracket*) sont automatiquement croisés et permutés afin de **ne jamais rejouer contre un adversaire déjà affronté dans le tableau des gagnants (*Winner Bracket*)**.
     * **🏆 Grande Finale** : *3 de 5* entre le champion du Winner Bracket et le survivant du Loser Bracket.
* **Suivi opérationnel en direct & Diffusion :**
  * **Affichage automatique du tournoi actif** et ouverture directe de son arborescence à jour lors de l'accès à l'onglet Tournois.
  * **Barre de progression globale** (`matchs terminés / total`) et panneau **« 🎱 En direct / Prochains matchs prêts à appeler aux tables »** avec numéro de table et horaire estimé.
  * **Arborescence visuelle interactive & Impression A4 :** Affichage plein écran et impression officielle **A4 Paysage** avec code couleur par tableau (Bleu Gagnants, Ambre Seconde chance, Or Grande Finale).
  * **📧 Envoi de l'arborescence officielle par courriel :**
    * Option accessible en un clic dans la boîte de dialogue d'arborescence, dans la barre de commandes du tournoi actif et dans l'historique des tournois archivés.
    * Génère et attache la **page HTML complète de l'arborescence** (prête pour affichage sur mobile/tablette ou impression A4) ainsi que le fichier `historique_tournois.json` en pièces jointes.
    * Permet l'envoi vers les administrateurs SMTP par défaut ou vers n'importe quelle adresse courriel saisie manuellement.
  * Gestion des **passes-droits en cours de tournoi** (`🎟️ Passe-droit`) pour promouvoir un joueur ou un duo au tour suivant.

---

### 5. 👁️ Mode Spectateur & Gestion de la Main (Verrouillage multi-utilisateurs)
* **Accès Spectateur sans mot de passe :**
  * Consultation en direct des scores de la feuille de match (par équipe, par joueur et manche par manche), des classements et de l'arborescence des tournois.
  * Rafraîchissement automatique (toutes les 5s / 15s / 30s) ou manuel en un clic.
* **Contrôle exclusif du Marqueur / Administrateur :**
  * Un seul éditeur détient la main active à la fois (`session_lock.json`) afin d'éviter tout conflit d'écriture.
  * Boutons **« 🤝 Céder la main »** (avec sauvegarde automatique préalable sur le disque) et **« ⚡ Prendre la main »** (avec rechargement automatique de la dernière sauvegarde).

---

### 6. 📊 Statistiques, Podiums & Historiques
* **Podiums Visuels Top 3 (`🥇 1er`, `🥈 2e`, `🥉 3e`) :**
  * Cartes podium en haut des classements **Équipes** et **Joueurs** mettant en valeur les 3 meilleurs performeurs de la saison.
* **Tableaux statistiques complets :**
  * **Classement des équipes :** Matchs joués (PJ), Victoires, Défaites, Égalités, Points Pour, Points Contre, Différentiel, Moyenne pts/match, % Victoires et **Points au classement**.
  * **Classement individuel des joueurs :** Manches jouées, Manches gagnées (score de 8), % Victoires, Points cumulés et **Moyenne officielle sur 8**.
  * **Consultation et réimpression A4** de toutes les feuilles de matchs archivées et de tous les tournois passés.

---

### 7. ⚙️ Espace Administration, API Saphir & Persistance Cloud GitHub (Anti-veille Streamlit)
Le volet **`⚙️ Administration`** (réservé exclusivement à l'accès **`🛡️ Administrateur`**) regroupe les outils avancés de gestion de la ligue, de persistance des données, d'interconnexion API et de maintenance du système. Son ergonomie a été spécialement optimisée avec des libellés d'onglets compacts et un bandeau de navigation d'accès direct pour garantir une visibilité totale de tous les modules sans défilement masqué.

* **Onglets et modules du volet Administration :**
  * **👥 Équipes (`equipes-saphir.csv`) :** Tableau interactif modifiable en direct, ajout rapide d'équipes et de joueurs réguliers, import/export CSV et validation instantanée.
  * **📝 Match passé (Saisie de matchs antérieurs ou en retard) :** Formulaire complet permettant d'enregistrer rétroactivement une rencontre disputée avec sélection de la date/heure, composition des équipes et scores des 9 manches selon la rotation officielle alternée. Met immédiatement à jour les classements, les statistiques cumulées et déclenche la synchronisation cloud.
  * **✏️ Rectifications (Correction ou suppression de matchs archivés) :** 
    * Correction ciblée des scores de manche, des présences ou des alignements avec saisie obligatoire d'un motif officiel et régénération immédiate de la feuille officielle.
    * **🗑️ Suppression d'un match de l'historique :** Option sécurisée (accessible dans l'Administration et directement lors de la consultation d'une feuille archivée) avec confirmation, création d'une copie de sauvegarde `.bak` horodatée et synchronisation GitHub automatique.
  * **🗓️ Saison (Gestion des cycles de compétition) :** Initialisation d'une nouvelle saison, archivage des statistiques précédentes et remise à zéro sécurisée des classements actifs.
  * **💾 Sauvegardes & Restauration fiabilisée (Nettoyage JSON pur) :**
    * **Nettoyage et allègement JSON pur :** Suppression complète du code HTML verbeux et des images base64 dans `historique_matchs.json`. Le fichier passe de ~448 Ko à ~56 Ko (réduction de plus de **88 %**), éliminant toute redondance et accélérant les synchronisations réseau. Le rendu visuel HTML officiel et l'impression A4 sont désormais générés dynamiquement à la volée de façon 100 % autonome et fidèle.
    * **Restauration d'historique fiabilisée :** Prise en charge universelle des fichiers JSON téléversés (formats liste de matchs ou dictionnaire avec clé `"matchs"`), gestion robuste des encodages UTF-8 standard et UTF-8 avec BOM (`utf-8-sig`), calcul automatique des totaux de scores manquants (`score_total_receveur` / `score_total_visiteur`), déduplication des identifiants et **rafraîchissement immédiat de toutes les listes déroulantes de consultation et de rectification sans conflit d'index**.
    * **Exports & Envois par courriel :** Téléchargement direct des bases JSON et envoi automatisé des bilans par courriel SMTP avec pièces jointes.
  * **🌐 Test POST Saphir (`billardImport`) :**
    * Module interactif d'interconnexion avec l'API officielle de la Salle Le Saphir, également accessible en raccourci direct depuis la vue Saphir de la feuille de match.
    * **Point de terminaison officiel :** `POST https://saphirbillard.com/index.php?eID=billardImport`
    * **Authentification sécurisée :** En-têtes HTTP `Content-Type: application/json` et `X-API-Key: UNE_CLE_DEBILEMENT_LONGUE` avec champ de saisie masqué.
    * **Charge utile JSON structurée :** Modèle prérempli et éditeur en direct validant les données d'importation (saison, semaine, prénom, nom, pointage) :
      ```json
      [
        {
          "saison": 4,
          "semaine": 21,
          "prenom": "Sylvain",
          "nom": "Derasp",
          "pointage": 89
        }
      ]
      ```
    * **Outils d'inspection et de diagnostic :** Validation de syntaxe JSON en direct, génération instantanée de la commande `cURL` équivalente pour exécution en ligne de commande, mesure précise du temps de latence en millisecondes (ms), statut HTTP (`200 OK`, etc.), inspection détaillée des en-têtes et coloration syntaxique de la réponse retournée par le serveur.
  * **📧 SMTP (Notifications et bilans officiels) :** Configuration du serveur d'expédition courriel, test d'envoi en direct et routage des alertes administratives.
  * **🔑 Sécurité (Gestion des accès) :** Modification sécurisée des mots de passe Marqueur et Administrateur avec hachage cryptographique SHA-256 dans `config_auth.json`.

* **☁️ Synchronisation automatique GitHub intégrale (.json & .csv) & Protection anti-veille :**
  * **Au démarrage / Réveil de l'application :** Récupération et restauration automatiques de **tous les fichiers de données JSON et CSV** depuis GitHub (`historique_matchs.json`, `historique_tournois.json`, `tournois_data.json`, `sauvegarde_saisie_secours.json`, `equipes-saphir.csv`, `config_email.json`, `config_admin.json`). Fusion intelligente sans doublon et prise en compte des dernières modifications horodatées.
  * **Lors des sauvegardes :** Envoi automatique vers GitHub de **tous les fichiers .json et .csv** dès qu'une sauvegarde est déclenchée (validation de match, mise à jour ou clôture de tournoi, modification des équipes CSV, configuration email SMTP, mots de passe, cession de main et saisie de secours).
  * **Sécurité & Optimisation des flux :** Masquage automatique des jetons d'accès dans `config_admin.json` avant tout envoi pour prévenir les alertes GitHub Secret Scanning, et comparaison par hash SHA1 Git blob pour éviter tout commit redondant inutile.
  * **Écriture atomique locale & Copies `.bak` :** Toutes les écritures locales sont atomiques avec copies de sauvegarde de secours `.bak` pour une résilience absolue.

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
streamlit run billard_app.py
```
*(ou `streamlit run app.py`)*

L'application est alors accessible dans votre navigateur à l'adresse `http://localhost:8501`.

### 4. Configuration de la persistance GitHub sur Streamlit Cloud (optionnel mais recommandé)
Dans le tableau de bord Streamlit Cloud de votre application (**Settings → Secrets**), ajoutez :
```toml
GITHUB_TOKEN = "ghp_votre_jeton_personnel_github"
GITHUB_REPO = "vezir649-droid/ligue-billard-saphir"
GITHUB_BRANCH = "main"
```

---

## 🗂️ Structure des fichiers principaux

| Fichier | Rôle |
| :--- | :--- |
| `billard_app.py` / `app.py` | Code source principal de l'application Streamlit |
| `README.md` | Documentation officielle (affichée et imprimable depuis la page d'ouverture) |
| `equipes-saphir.csv` | Liste officielle des équipes et de leurs 3 joueurs réguliers |
| `historique_matchs.json` | Base de données JSON allégée (100 % JSON pur, sans HTML) des feuilles de matchs 3v3 validées (synchronisée sur GitHub) |
| `historique_tournois.json` | Historique officiel complet des tournois Simples & Doubles (synchronisé sur GitHub) |
| `tournois_data.json` | État en temps réel des tournois actifs et synchronisation d'historique |
| `sauvegarde_saisie_secours.json` | Sauvegarde temps réel de la feuille de match 3v3 en cours de saisie |
| `sauvegarde_annulee_secours.json` | Corbeille de secours permettant d'annuler un « Nouveau match » |
| `session_lock.json` | Verrouillage multi-utilisateurs de la main active (Marqueur / Administrateur) |
| `config_auth.json` | Empreintes SHA-256 des mots de passe Marqueur et Administrateur |
| `config_email.json` | Paramètres SMTP pour l'envoi automatique des rapports et sauvegardes |
| `config_github.json` | Configuration locale de la synchronisation automatique GitHub |

---

## 📄 Licence
Projet développé pour la **Ligue de billard Boule en main — Salle Le Saphir**. Libre d'utilisation et d'adaptation (Licence MIT).
