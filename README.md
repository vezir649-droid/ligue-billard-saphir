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
  * Indicateurs visuels par manche (`⏳ À jouer`, `✅ Manche terminée — Victoire`, `⚠️ Score incomplet ou invalide`) et synchronisation immédiate des totaux par équipe et par joueur.
* **Approbation & Impression A4 :**
  * Double approbation officielle par un représentant de chaque équipe avant archivage.
  * Génération d'une **feuille de match officielle calibrée pour l'impression sur une seule page A4**.
* **Compatibilité complète Thème Clair (*Light*) & Thème Sombre (*Dark*) :**
  * Adaptation automatique des contrastes pour les cartes de métriques (`st.metric`), les onglets, les podiums, les cartes de rencontres et les aperçus A4.

---

### 2. 📋 Paramètres du Match (Barre latérale & Contrôles de rencontre)
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
* **Sécurité de saisie & Contrôles de session :**
  * **🔄 Restaurer saisie :** Recharge à tout moment la dernière sauvegarde automatique (`sauvegarde_saisie_secours.json`) en cas de coupure ou de rafraîchissement navigateur.
  * **🗑️ Nouveau match & ↩️ Annuler effacement :** Réinitialise la feuille à `0 - 0` tout en conservant une copie de secours dans la corbeille (`sauvegarde_annulee_secours.json`) pour permettre d'annuler un effacement accidentel en un clic.
  * **🚪 Déconnexion / Accueil :** Sauvegarde automatiquement le match et les tournois en cours sur le disque, libère le verrou exclusif du marqueur et retourne à l'écran d'accueil.

---

### 3. 🏆 Module de Tournois Officiels (Simple 1v1 & Double 2v2)
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

### 4. 👁️ Mode Spectateur & Gestion de la Main (Verrouillage multi-utilisateurs)
* **Accès Spectateur sans mot de passe :**
  * Consultation en direct des scores de la feuille de match (par équipe, par joueur et manche par manche), des classements et de l'arborescence des tournois.
  * Rafraîchissement automatique (toutes les 5s / 15s / 30s) ou manuel en un clic.
* **Contrôle exclusif du Marqueur Officiel :**
  * Un seul marqueur détient la main active à la fois (`session_lock.json`) afin d'éviter tout conflit d'écriture.
  * Boutons **« 🤝 Céder la main »** (avec sauvegarde automatique préalable sur le disque) et **« ⚡ Prendre la main »** (avec rechargement automatique de la dernière sauvegarde).

---

### 5. 📊 Statistiques, Podiums & Historiques
* **Podiums Visuels Top 3 (`🥇 1er`, `🥈 2e`, `🥉 3e`) :**
  * Cartes podium en haut des classements **Équipes** et **Joueurs** mettant en valeur les 3 meilleurs performeurs de la saison.
* **Tableaux statistiques complets :**
  * **Classement des équipes :** Matchs joués (PJ), Victoires, Défaites, Égalités, Points Pour, Points Contre, Différentiel, Moyenne pts/match, % Victoires et **Points au classement**.
  * **Classement individuel des joueurs :** Manches jouées, Manches gagnées (score de 8), % Victoires, Points cumulés et **Moyenne officielle sur 8**.
  * **Consultation et réimpression A4** de toutes les feuilles de matchs archivées et de tous les tournois passés.

---

### 6. ⚙️ Espace Administration & Persistance Sécurisée
* **Accès exclusif Administrateur (`🛡️ Accès Administrateur` sur la page de démarrage) :**
  * **🔒 Accès Marqueur / Éditeur** (mot de passe par défaut : `saphir2026`) : permet la saisie des manches 3v3, la validation officielle des matchs et la gestion des tournois, **sans accès au volet Administration**.
  * **🛡️ Accès Administrateur** (mot de passe par défaut : `admin2026`) : donne accès à toutes les fonctionnalités de saisie ainsi qu'**en exclusivité à l'onglet `⚙️ Administration`**.
* **Onglet dédié `⚙️ Administration` (réservé uniquement à l'Administrateur) :**
  * **👥 Édition des équipes & joueurs (`equipes-saphir.csv`) :** Tableau interactif modifiable, ajout rapide d'équipe, import et export CSV.
  * **✏️ Rectification officielle d'un match archivé :** Correction des scores ou joueurs avec motif obligatoire, bandeau de rectification sur la feuille officielle et sauvegarde de sécurité horodatée.
  * **📤 Export & Sauvegarde JSON :** Envoi du bilan complet par courriel SMTP (avec `historique_matchs.json` ou `historique_tournois.json` en pièce jointe) + **téléchargement et restauration directe des fichiers JSON** en un clic.
  * **🗓️ Nouvelle saison, 📧 Configuration SMTP & 🔑 Gestion séparée des mots de passe Marqueur et Administrateur.**
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
| `sauvegarde_annulee_secours.json` | Corbeille de secours permettant d'annuler un « Nouveau match » |
| `config_email.json` | Paramètres SMTP pour l'envoi automatique des rapports et sauvegardes |

---

## 📄 Licence
Projet développé pour la **Ligue de billard Boule en main — Salle Le Saphir**. Libre d'utilisation et d'adaptation (Licence MIT).
