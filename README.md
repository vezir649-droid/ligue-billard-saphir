# 🎱 Ligue de billard Boule en main — Salle Le Saphir

Application web officielle développée avec [Streamlit](https://streamlit.io/) pour la gestion complète de la **Ligue de billard Boule en main (Salle Le Saphir)** : saisie en direct des feuilles de matchs réguliers (**3 contre 3**), organisation de **tournois officiels** (Simple 1v1 & Double 2v2), suivi **Spectateur en temps réel**, **Statistiques & Classements** et **Administration**.

---

## ✨ Nouveautés & Fonctionnalités principales

### 1. 📝 Feuille de Match Officielle (3 contre 3 — Jeu au 8)
* **Bandeau « Live Scoreboard » épinglé en haut de page :**
  * Affichage permanent en temps réel du score global (**Équipe Receveuse vs Équipe Visiteuse**), d'une jauge de progression des **9 manches** (`X / 9 manches complétées`) et du statut de verrouillage.
* **Rotation optimisée des 9 duels :**
  * Chaque joueur de l'équipe receveuse affronte les 3 joueurs de l'équipe visiteuse selon un ordre officiel garantissant qu'**aucun joueur ne dispute deux manches consécutives**.
* **Règles officielles du Billard au 8 & Validation instantanée :**
  * Le vainqueur d'une manche marque **8 points** ; l'adversaire marque ses boules empochées (**0 à 7 points**).
  * Indicateurs visuels par manche (`⏳ À jouer`, `✅ Manche validée — Vainqueur`, `⚠️ Score incomplet ou invalide`) et synchronisation immédiate des totaux par équipe et par joueur.
* **Gestion des effectifs, présences et remplaçants (Sub) :**
  * Cartes latérales structurées par équipe (**🔵 Équipe Receveuse** et **🟠 Équipe Visiteuse**) avec chargement automatique depuis `equipes-saphir.csv`.
  * Commutateur individuel *Présent / Absent* avec attribution automatique du pointage forfaitaire (moyenne du joueur absent arrondie au point supérieur, et **8 points** pour l'adversaire présent).
  * Ajout rapide d'un **joueur remplaçant (Sub)** avec saisie de sa moyenne.
* **Approbation & Impression A4 :**
  * Double approbation officielle par un représentant de chaque équipe avant archivage.
  * Génération d'une **feuille de match officielle calibrée pour l'impression sur une seule page A4**.

---

### 2. 🏆 Module de Tournois Officiels (Simple 1v1 & Double 2v2)
* **Deux catégories indépendantes :**
  * **👤 Tournoi en Simple (1 contre 1)** — Joueurs individuels.
  * **👥 Tournoi en Double / Équipes (2 contre 2)** — Duos constitués aléatoirement ou manuellement.
* **Trois formules de compétition prises en charge :**
  1. **⚡ Élimination directe (Simple élimination)** : Préliminaires en *2 de 3* (premier à 2 victoires) et Finale en *3 de 5* (premier à 3 victoires), avec calcul automatique des **passes-droits (byes)** au 1er tour pour obtenir une puissance de 2 parfaite au 2e tour.
  2. **🛡️ Double élimination — Winner & Loser Bracket (Seconde chance)** :
     * **🟦 Tableau des Gagnants (*Winner Bracket*)** : *2 de 3*.
     * **🟧 Tableau de Repêchage (*Loser Bracket — Seconde chance*)** : *2 de 3* — tout participant perdant un premier match est automatiquement reversé dans le Loser Bracket et conserve toutes ses chances d'atteindre la Grande Finale.
     * **🏆 Grande Finale** : *3 de 5* entre le champion du Winner Bracket et le survivant du Loser Bracket.
  3. **🔄 Championnat Round-Robin (Tous contre tous)** : Classement en direct (Points, Victoires, Défaites, Manches Pour/Contre, Différence).
* **Suivi opérationnel en direct :**
  * **Affichage automatique du tournoi actif** et ouverture directe de son arborescence à jour lors de l'accès à l'onglet Tournois.
  * **Barre de progression globale** (`matchs terminés / total`) et panneau **« 🎱 En direct / Prochains matchs prêts à appeler aux tables »** avec numéro de table et horaire estimé.
  * **Arborescence visuelle interactive** (plein écran et impression officielle **A4 Paysage**) avec code couleur par tableau (Bleu Gagnants, Ambre Seconde chance, Or Grande Finale).
  * Gestion des **passes-droits en cours de tournoi** (`🎟️ Passe-droit`) pour promouvoir un joueur ou un duo au tour suivant.

---

### 3. 👁️ Mode Spectateur & Gestion de la Main (Verrouillage multi-utilisateurs)
* **Accès Spectateur sans mot de passe :**
  * Consultation en direct des scores de la feuille de match (par équipe, par joueur et manche par manche), des classements et de l'arborescence des tournois.
  * Rafraîchissement automatique (toutes les 15s / 30s) ou manuel en un clic.
* **Contrôle exclusif du Marqueur Officiel :**
  * Un seul marqueur détient la main active à la fois (`session_lock.json`) afin d'éviter tout conflit d'écriture.
  * Boutons **« 🤝 Céder la main »** (avec sauvegarde automatique préalable sur le disque) et **« ⚡ Prendre la main »** (avec rechargement automatique de la dernière sauvegarde).

---

### 4. 📊 Statistiques, Podiums & Historiques
* **Podiums Visuels Top 3 (`🥇 1er`, `🥈 2e`, `🥉 3e`) :**
  * Cartes podium en haut des classements **Équipes** et **Joueurs** mettant en valeur les 3 meilleurs performeurs de la saison.
* **Tableaux statistiques complets :**
  * **Classement des équipes :** Matchs joués (PJ), Victoires, Défaites, Égalités, Points Pour, Points Contre, Différentiel, Moyenne pts/match, % Victoires et **Points au classement**.
  * **Classement individuel des joueurs :** Manches jouées, Manches gagnées (score de 8), % Victoires, Points cumulés et **Moyenne officielle sur 8**.
  * **Consultation et réimpression A4** de toutes les feuilles de matchs archivées et de tous les tournois passés.

---

### 5. ⚙️ Espace Administration & Persistance Sécurisée
* **Onglet dédié `⚙️ Administration` (réservé aux marqueurs/administrateurs) :**
  * **👥 Édition des équipes & joueurs (`equipes-saphir.csv`) :** Tableau interactif modifiable, ajout rapide d'équipe, import et export CSV.
  * **✏️ Rectification officielle d'un match archivé :** Correction des scores ou joueurs avec motif obligatoire, bandeau de rectification sur la feuille officielle et sauvegarde de sécurité horodatée.
  * **📤 Export & Sauvegarde JSON :** Envoi du bilan complet par courriel SMTP (avec `historique_matchs.json` ou `historique_tournois.json` en pièce jointe) + **téléchargement et restauration directe des fichiers JSON** en un clic.
  * **🗓️ Nouvelle saison, 📧 Configuration SMTP & 🔑 Mot de passe d'accès.**
* **Écriture atomique & Copies de secours (`.bak`) :**
  * Toutes les écritures dans `historique_matchs.json`, `historique_tournois.json` et `tournois_data.json` sont effectuées de manière atomique avec création automatique d'une copie `.bak` et récupération transparente en cas d'interruption.

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

---

## 🗂️ Structure des fichiers principaux

| Fichier | Rôle |
| :--- | :--- |
| `billard_app.py` / `app.py` | Code source principal de l'application Streamlit |
| `equipes-saphir.csv` | Liste officielle des équipes et de leurs 3 joueurs réguliers |
| `historique_matchs.json` | Base de données JSON des feuilles de matchs 3v3 validées |
| `historique_tournois.json` | Historique officiel complet des tournois (Simples & Doubles) |
| `tournois_data.json` | État en temps réel des tournois actifs et synchronisation d'historique |
| `sauvegarde_saisie_secours.json` | Sauvegarde temps réel de la feuille de match 3v3 en cours de saisie |
| `config_email.json` | Paramètres SMTP pour l'envoi automatique des rapports et sauvegardes |

---

## 📄 Licence
Projet développé pour la **Ligue de billard Boule en main — Salle Le Saphir**. Libre d'utilisation et d'adaptation (Licence MIT).
