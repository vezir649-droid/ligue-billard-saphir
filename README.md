# 🎱 Ligue de billard du Saphir — Application de saisie des résultats

Application web interactive développée avec [Streamlit](https://streamlit.io/) pour la gestion et la saisie des résultats de matchs de billard au format **3 contre 3**.

---

## 🚀 Fonctionnalités principales

* **Rotation optimisée des 9 duels (3 contre 3) :**
  * Chaque joueur de l'équipe receveuse affronte les 3 joueurs de l'équipe visiteuse.
  * **Règle de repos :** Aucun joueur ne dispute deux manches consécutives.
* **Règles du jeu au 8 :**
  * Le vainqueur marque **8 points**.
  * Le perdant marque son nombre de boules empochées (**0 à 7 points**).
  * Contrôle de cohérence automatique en temps réel.
* **Gestion des présences et forfaits :**
  * Commutateur *Présent / Absent* individuel pour chaque joueur.
  * Configuration du pointage forfaitaire par défaut pour joueur absent (l'adversaire présent reçoit automatiquement 8 points).
  * Prise en charge des doubles forfaits.
* **Sécurité anti-panne & Sauvegarde automatique :**
  * Sauvegarde automatique à chaque frappe dans un fichier de secours local.
  * Bouton de restauration rapide de la session active en cas de rafraîchissement inopiné.
* **Historique des rencontres :**
  * Archivage permanent de chaque match validé avec date et horodatage.
* **Envoi des résultats par courriel :**
  * Envoi automatique par SMTP (Gmail, Outlook, etc.) d'un rapport complet au format texte et HTML.
  * Mémorisation sécurisée des paramètres d'envoi.
  * Bouton d'ouverture rapide dans le client de messagerie local (`mailto:`).

---

## 📦 Installation et démarrage

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

L'application sera accessible dans votre navigateur à l'adresse `http://localhost:8501`.

---

## 📄 Licence
Projet sous licence MIT - Libre d'utilisation et d'adaptation.
