# 🎱 Ligue de billard Boule en main — Salle Le Saphir

Application web officielle développée avec [Streamlit](https://streamlit.io/) pour la gestion complète de la **Ligue de billard Boule en main (Salle Le Saphir)** : portail d'accueil multi-rôles (**Spectateur**, **Marqueur**, **Administrateur**), saisie en direct des feuilles de matchs réguliers (**3 contre 3**), **Scanner IA de feuilles de match manuscrites par photo (Gemini Vision)** avec **viseur Portrait vertical (3:4)** et multi-déclencheurs, **transmission automatique officielle vers le site Saphir (`saphirbillard.com`)**, **détection des doublons & scans partiels**, **Statistiques avancées, Progression, Face-à-Face & Projections de fin de saison (Joueurs & Équipes)**, organisation de **tournois officiels** (Simple 1v1 & Double 2v2) avec **Mode Téléviseur / Casting TV auto-actualisé**, **Passerelle Sentinelle SMS native Android (`SaphirSMS.apk` v1.1.7) avec Pub/Sub instantané (Supabase Realtime Broadcast)**, verrou atomique anti-doublon, format compact GSM 7-bit mono-segment (< 150 car.) et **convocations automatiques de tournois aux tables**, **Administration sécurisée** et **Persistance Cloud Hybride (Supabase PostgreSQL Prioritaire + GitHub)** avec **bouclier anti-veille et fusion intelligente**.

---

## ✨ Fonctionnalités principales de l'application

### 1. 🚪 Portail d'ouverture & Niveaux d'accès (3 rôles + Documentation intégrée)
Dès l'ouverture de l'application, la page d'accueil présente trois modes d'accès distincts ainsi que la documentation officielle :

1. **👁️ Accès Spectateur (affiché en premier — sans mot de passe) :**
   * Accès immédiat en un clic (`👁️ Entrer en mode Spectateur`) en **lecture seule**.
   * Permet de suivre en direct la feuille de match en cours, les classements de la saison, les statistiques et projections des équipes et joueurs, ainsi que l'arborescence des tournois.
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
L'application intègre un module de pointe basé sur l'IA de vision de Google (**Gemini 2.5 / 3.1 Flash**) capable de lire, corréler et retranscrire automatiquement des feuilles de match papier manuscrites :

* **Ergonomie de prise de vue & Viseur Portrait vertical (3:4) par défaut :**
  * **Viseur calibré par défaut en Mode Portrait vertical (`3:4`) :** Résolution vidéo haute définition verticale (`1080 × 1440`) épousant naturellement le format vertical d'une feuille de match papier, sans déformation.
  * **Bouton de bascule d'orientation en 1 clic :** Commutateur instantané `📱 Format : Portrait vertical (3:4)` ↔ `💻 Format : Paysage (16:9)` pour s'adapter à toutes les prises de vue.
  * **Aperçu haute visibilité de la capture :** La photo prise s'affiche avec un cadre contrasté vert émeraude et un bandeau lumineux d'état sous le viseur pour confirmer immédiatement la qualité de la prise de vue.
  * **3 modes de déclenchement ergonomiques** pour prendre la photo facilement :
    1. **Tap direct sur l'image vidéo** (un toucher n'importe où sur l'aperçu caméra déclenche la photo).
    2. **Gros bouton de capture (`📸 PRENDRE LA PHOTO`)** placé **au-dessus** du viseur.
    3. **Gros bouton vert de capture (`58px`)** placé **en dessous** du viseur.
  * **Contrôles matériels en direct :** Sélecteur de **zoom numérique (`1x`, `1.25x`, `1.5x`, `2x`)** et activation de la **torche / flash LED (`🔦 Torche LED`)** sur les appareils compatibles.
  * **Barre d'outils de retouche rapide après capture (en 1 clic) :** Rotation **↺ 90° Gauche**, **↻ 90° Droite**, **↕️ 180°**, et **✨ Netteté & Contraste Auto** (optimise la lisibilité des chiffres manuscrits au crayon ou stylo pâle avant l'analyse IA).
  * **Alternative universelle :** Prise de photo via l'application **Appareil photo natif** du téléphone ou téléversement par glisser-déposer (`JPG`, `PNG`, `WebP`).
* **Optimisation et vitesse éclair (2 à 3 secondes) :**
  * Redimensionnement et compression automatique en mémoire vive par Pillow (PIL) avant transmission, garantissant une analyse ultrarapide sans latence.
* **Extraction exhaustive, Corrélation intelligente & Totaux par joueur :**
  * Détection automatique de la **date du match**, des **équipes receveuse et visiteuse**, et des **6 joueurs alignés** (avec rapprochement flou sur `equipes-saphir.csv`).
  * **Déduction automatique de l'équipe :** Si le nom d'une équipe est illisible ou absent sur la feuille papier, l'application identifie automatiquement l'équipe officielle à partir des 3 joueurs détectés et empêche tout doublon de joueur au sein d'un même trio.
  * **Alignement sur la grille officielle des 9 manches :** Réconciliation automatique des 9 duels individuels selon l'ordre officiel de rotation et calcul du **total individuel (`/24`)** ainsi que du bilan **`V-D`** de chaque joueur dans le résumé et le tableau récapitulatif.
* **Vérification automatique de l'historique, Scans partiels & Diagnostic d'incertitudes :**
  * **🛑 Détection des matchs déjà archivés (Doublons) :** Dès la fin du scan, l'application vérifie si la rencontre existe déjà dans `historique_matchs.json` (même affiche et même date, ou mêmes scores). Si le match existe déjà :
    * Les boutons d'injection et d'archivage direct sont verrouillés pour éviter tout doublon.
    * Une alerte invite l'utilisateur à utiliser la fonction **`⚙️ Administration → ✏️ Rectifications`** (avec bouton d'accès direct pré-sélectionnant le match pour les administrateurs) et propose un bouton **`🔙 Retour à la saisie du match`**.
  * **⏳ Prise en charge des scans partiels (match en cours) :** Si seules quelques manches sont complétées sur la feuille (`X / 9 manches jouées`), le scanner affiche le détail des manches jouées vs manches à venir, bloque l'archivage direct d'un match incomplet et autorise **`📥 Injecter dans la saisie en direct`** pour poursuivre la soirée dans l'application.
  * **🔍 Diagnostic de confiance & Incertitudes :** Signalement automatique des doutes de lecture manuscrite relevés par l'IA, des manches sans gagnant à 8 points, des écarts arithmétiques entre la somme des manches et le total inscrit au bas de la feuille, et des joueurs remplaçants hors liste officielle.
* **Feuille officielle A4 HTML & Transmission automatique par courriel aux administrateurs :**
  * Dès l'analyse terminée, la **feuille de match officielle HTML (format A4)** est générée automatiquement (consultable, téléchargeable et imprimable immédiatement).
  * **Envoi automatique par courriel SMTP** aux administrateurs incluant en pièces jointes la **photo originale scannée** et la **feuille de match officielle HTML** (avec verrou anti-doublon par empreinte SHA-1).
* **✏️ Mini-éditeur de correction rapide intégré aux résultats du Scanner IA :**
  * Permet d'ajuster directement la date, les équipes, l'alignement des 6 joueurs (`J1`, `J2`, `J3`) ou n'importe lequel des 9 pointages (`M1` à `M9`) sur la page du scan avant l'injection ou l'archivage, avec recalcul automatique en 1 clic des totaux par joueur (`/24`), du score d'équipe (`/72`) et de la feuille officielle A4.
  * Tableaux récapitulatifs rendus en **HTML natif 100 % compatible Android / iOS** (zéro erreur de chargement de module dynamique `DataFrame` sur téléphone mobile).
* **Deux modes d'action en un clic :**
  * **`📥 Injecter dans la saisie du match en direct` :** Pré-remplit automatiquement les équipes, les 6 joueurs et les pointages des 9 manches dans le formulaire principal avec confirmation de sécurité si une saisie était déjà en cours.
  * **`💾 Archiver directement dans l'historique officiel` :** Sauvegarde instantanément la rencontre dans `historique_matchs.json`, enregistre dans le Cloud (Supabase PostgreSQL / GitHub), expédie le rapport officiel par courriel SMTP **ET transmet automatiquement les résultats au site officiel `https://saphirbillard.com/` via requête HTTP POST sécurisée**.

---

### 3. 📝 Feuille de Match Officielle (3 contre 3 — Jeu au 8) & Ergonomie Mobile Ultra-Rapide
* **Bandeau « Sticky Live Scoreboard » épinglé en haut de l'écran lors du défilement :**
  * Affichage permanent en temps réel du score global (**Équipe Receveuse vs Équipe Visiteuse**), de l'écart en cours et de la progression des **9 manches** (`X / 9 manches complétées`), qui reste visible au sommet de l'écran sur téléphone même en faisant défiler jusqu'aux manches 6 à 9.
* **📱 Choix rapide des 4 matchs de la semaine & Alignement mobile (`J1 ↔ J2 ↔ J3`) :**
  * **Sélecteur 1-clic des 4 rencontres programmées de la semaine :** Affiche les 4 matchs officiels de la semaine (`🏠 Alpha vs 🚗 Bravo`, etc.) sous forme de boutons rapides en haut de la feuille de match et dans la barre latérale afin que chaque table puisse charger ses 2 équipes, ses 6 joueurs et leurs moyennes officielles en un seul toucher.
  * **Permutation rapide sur mobile (`🔀 J1 ↔ J2`, `🔀 J2 ↔ J3`, `🔀 J1 ↔ J3`) et Présences :** Permet d'inverser l'ordre d'entrée des joueurs ou de basculer une absence directement depuis le haut de la feuille de match sans ouvrir le menu latéral sur téléphone.
* **⚡ Barre de contrôle ergonomique & Saisie éclair des 9 manches :**
  * **Filtre d'affichage par Ronde :** `📋 Toutes (1-9)` | `1️⃣ Ronde 1 (M1-M3)` | `2️⃣ Ronde 2 (M4-M6)` | `3️⃣ Ronde 3 (M7-M9)` | `⏳ À jouer` pour réduire le défilement vertical de 70 % sur smartphone.
  * **Logique « ⚡ Auto-8 intelligent » (activée par défaut) :** Dès que le marqueur sélectionne le score du joueur perdant (`1` à `7`), l'application attribue automatiquement **`8 points`** à son adversaire (divisant par deux le nombre de clics nécessaires sur une soirée).
  * **Boutons tactiles rapides 1-clic (`🏆 8 pts — Joueur`) :** Deux boutons rapides au sommet de chaque manche permettent d'attribuer 8 points au vainqueur d'un seul toucher.
  * **Option « 🔽 Replier terminées » :** Replie automatiquement les manches déjà jouées en affichant un bandeau récapitulatif compact (`✅ Manche X terminée : Joueur A (8) — (5) Joueur B • 🏆 Joueur A`).
* **Rotation optimisée des 9 duels & Pointage souple :**
  * Chaque joueur de l'équipe receveuse affronte les 3 joueurs de l'équipe visiteuse selon un ordre officiel garantissant qu'**aucun joueur ne dispute deux manches consécutives**.
  * Saisie libre de **0 à 8 points** par joueur **sans obligation d'un score de 8** pour valider une manche ou enregistrer la feuille de match.
* **Approbation, Impression A4 & Réactivité instantanée :**
  * Double approbation officielle par un représentant de chaque équipe avant archivage et génération paresseuse (*lazy*) de la **feuille de match officielle calibrée pour une seule page A4**.
  * **Cache mémoire haute vitesse sur `mtime`** (`equipes-saphir.csv`, `horaire_saphir.json`, `historique_matchs.json`) et **anti-rebond Cloud (*debounce*)** pour une fluidité immédiate à chaque clic.
* **🌐 Transmission automatique officielle vers le site Saphir (`saphirbillard.com`) :**
  * Dans la fenêtre modale d'approbation finale, une option activée par défaut (`🌐 Transmettre automatiquement les résultats au site Saphir`) expédie les pointages de la rencontre par requête `POST` vers `https://saphirbillard.com/index.php?eID=billardImport` avec l'en-tête `X-API-Key`.
  * Calcul dynamique de la saison (`saison`, ex. `S2025-2026`) et du numéro de semaine (`semaine`, ex. `Semaine 1` à `14`) à partir de la date de la rencontre et du calendrier `horaire_saphir.json`.
* **Compatibilité complète Thème Clair (*Light*) & Thème Sombre (*Dark*) :**
  * Adaptation automatique des contrastes pour les cartes de métriques (`st.metric`), les onglets, les podiums, les cartes de rencontres et les aperçus A4.
* **⚡ Composants Streamlit natifs & Rendu mobile ultra-fluide :**
  * Remplacement des anciens blocs HTML bruts et chaînes base64 par des composants Streamlit natifs pour le scoreboard en direct, les cartes de manches et les armoiries, éliminant tout bloc de code parasite et accélérant le rendu sur mobile.
  * Formulaire de saisie et liste déroulante d'historique épurés et fiabilisés.

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

### 5. 🏆 Module de Tournois Officiels (Simple 1v1 & Double 2v2) & Mode Téléviseur
* **Deux catégories indépendantes :**
  * **👤 Tournoi en Simple (1 contre 1)** — Joueurs individuels.
  * **👥 Tournoi en Double / Équipes (2 contre 2)** — Duos constitués aléatoirement ou manuellement.
* **Trois formules de compétition prises en charge (avec équilibrage automatique pour 18, 20, 22 et 24 joueurs ainsi que jusqu'à 32 participants) :**
  1. **⚡ Élimination directe (Simple élimination)** : Préliminaires en *2 de 3* (premier à 2 victoires) et Finale en *3 de 5* (premier à 3 victoires) :
     * **Cas spécifiques 18, 20, 22 et 24 joueurs (tous jouent au 1er tour + équilibrage au 2e tour) :**
       * **18 joueurs :** **9 matchs** au 1er tour (tous les 18 joueurs jouent) → **1 match d'équilibrage** au 2e tour (+ 7 gagnants du 1er tour promus) → **4 matchs** en Quarts de finale (8 joueurs) → **2 matchs** en Demi-finales → **1 Finale**.
       * **20 joueurs :** **10 matchs** au 1er tour (tous les 20 joueurs jouent) → **2 matchs d'équilibrage** au 2e tour (+ 6 gagnants du 1er tour promus) → **4 matchs** en Quarts de finale → **2 matchs** en Demi-finales → **1 Finale**.
       * **22 joueurs :** **11 matchs** au 1er tour (tous les 22 joueurs jouent) → **3 matchs d'équilibrage** au 2e tour (+ 5 gagnants du 1er tour promus) → **4 matchs** en Quarts de finale → **2 matchs** en Demi-finales → **1 Finale**.
       * **24 joueurs :** **12 matchs** au 1er tour (tous les 24 joueurs jouent) → **4 matchs d'équilibrage** au 2e tour (+ 4 gagnants du 1er tour promus) → **4 matchs** en Quarts de finale → **2 matchs** en Demi-finales → **1 Finale**.
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
* **✏️ Reprise de validation & Correction des matchs validés (`✏️ Reprendre / Corriger`) :**
  * **Accès immédiat sur les rencontres terminées :** Dès qu'un match est validé, un popover ergonomique `✏️ Reprendre / Corriger` apparaît sur la carte de la rencontre pour les éditeurs / marqueurs (les spectateurs visualisent un badge sécurisé `✅ Rencontre terminée et validée`).
  * **1️⃣ Correction directe du score :** Ajustement des manches sans défaire l'arbre du tournoi si le vainqueur reste identique. Si le vainqueur est inversé, la qualification et l'élimination sont automatiquement répercutées dans les tours suivants et dans la Grande Finale.
  * **2️⃣ Reprendre la validation (Dévalider / Remettre en jeu) :** Annule l'état terminé du match, remet la rencontre en attente de score en préremplissant les scores précédents pour accélérer la saisie, et repositionne les cases dépendantes à « À déterminer ». Si le tournoi était clôturé, il repasse automatiquement en statut `en_cours`.
  * **🛡️ Protection anti-corruption de l'arbre :** Détection automatique des matchs descendants déjà disputés avec message d'avertissement et confirmation explicite obligatoire par case à cocher avant toute réinitialisation en cascade.
  * **Prise en charge tous formats :** Fonctionne en Élimination directe, en Double élimination (Winner et Loser Bracket) et en Championnat Round-Robin.
* **🏁 Persistance, Podium & Clôture explicite des tournois terminés :**
  * **Persistance garantie de la Grande Finale :** La saisie et validation du match de finale enregistre le Champion officiel (`vainqueur_final`) et le Finaliste (`finaliste`) sans jamais faire disparaître le tournoi de la grille active ni de l'historique.
  * **Affichage instantané du Podium & Score validé :** Dès la fin de la finale, un bloc de victoire doré s'affiche en tête d'onglet (`🎉 FÉLICITATIONS AU CHAMPION 🎉`, `🥇 Champion`, `🥈 Finaliste`) accompagné du score officiel validé de la finale.
  * **Actions directes sur la finale terminée :** Le marqueur bénéficie de deux actions rapides directement dans le bloc de victoire :
    1. `✏️ Reprendre / Corriger la finale` : permet de rectifier immédiatement un pointage erroné ou d'annuler la validation pour remettre la finale en jeu sans briser l'arbre.
    2. `🏁 Clôturer & Libérer la grille` : libère manuellement la grille active (`td[mode] = None`) une fois la remise des prix terminée, tout en conservant le tournoi archivé avec son podium dans l'historique officiel.
  * **Indicateur d'onglet haute visibilité :** L'onglet actif bascule élégamment de `👤 Tournoi Simple 🟢 (Actif)` à `👤 Tournoi Simple 🏆 (Terminé)` (et de même en Double), garantissant que le tournoi reste identifiable et ouvert.
  * **Bouclier Cloud (Supabase PostgreSQL + GitHub) :** Tout tournoi local en cours ou terminé est strictement protégé contre tout écrasement par une archive distante vide lors du réveil ou des synchronisations d'arrière-plan.
* **🛡️ Étanchéité Simple/Double & Annulation complète sans persistance d'actif :**
  * **Annulation complète garantie (❌ Annulation complète) :** Lorsqu'un tournoi est annulé, il est immédiatement purgé de 	ournois_data.json et de historique_tournois.json. Il ne conserve aucun statut actif et ne s'affiche plus jamais comme 🟢 Actif nulle part (marquage explicite [❌ Annulé] si archivé).
  * **Indépendance totale Simple et Double :** La création, la saisie des scores d'une ronde ou le passage à l'autre catégorie ne peut jamais écraser, effacer ou réinitialiser le tournoi en cours de l'autre mode. Les données du disque sont systématiquement rechargées à chaque écriture pour préserver l'état de chaque catégorie.
  * **Navigation stable entre onglets :** L'ordre des onglets (*Tournoi Simple*, *Tournoi Double*, *Créer un nouveau tournoi*, *Historique*) demeure fixe et immuable sans permutation dynamique pour garantir une consultation fluide sans sauts d'onglets ni désynchronisation.
  * **Protection anti-écrasement Cloud au réveil :** La synchronisation automatique avec Supabase et GitHub préserve systématiquement tout tournoi local en cours.
* **📲 Convocations SMS automatiques à H-30 min (Prochaine demi-heure) & Notifications d'horaire :**
  * **Désactivé par défaut au lancement & Envoi immédiat dès l'activation :** Lors du lancement d'un tournoi, l'envoi de SMS est obligatoirement **désactivé par défaut** afin de permettre à l'organisateur de peaufiner le tableau sans précipitation. Dès que l'interrupteur SMS est activé par le marqueur, des convocations SMS sont immédiatement expédiées aux joueurs cédulés aux tables disponibles.
  * **Convocations ciblées dans la prochaine demi-heure (H-30 min) :** Pour toutes les rencontres ultérieures, l'envoi de SMS ne dépend plus du moment où un match se termine ou est validé à la table. L'application analyse en continu l'horaire prévu de chaque rencontre et expédie automatiquement les textos 30 minutes avant chaque match, permettant aux compétiteurs de se préparer sereinement.
  * **Veille automatique d'arrière-plan (30s) :** Un fragment autonome vérifie périodiquement l'horloge murale toutes les 30 secondes et expédie les convocations dès qu'une partie entre dans la fenêtre des 30 minutes, sans nécessiter d'interaction manuelle.
  * **Badge visuel dynamique `📱 Convoqué` :** Marquage en temps réel sur les cartes de rencontres actives et dans la liste des tables pour identifier immédiatement les joueurs déjà alertés.
  * **Envoi immédiat des convocations SMS lors de la modification d'un horaire ou d'une table :** Dès qu'un organisateur ou marqueur modifie l'heure estimée ou la table assignée d'un match (dans le popover de planification en Élimination directe ou Round-Robin), l'application expédie immédiatement les textos de convocation SMS mis à jour aux joueurs concernés avec la nouvelle heure et la nouvelle table. Si l'option *« Décaler aussi les matchs suivants de ce décalage »* est cochée, les rencontres suivantes décalées sont également mises à jour et leurs convocations SMS sont actualisées instantanément avec mise à jour en temps réel des badges `📱 Convoqué (HH:MM)`.
  * **Avis automatique de changement d'horaire / table (`⏰ TOURNOI_HORAIRE`) :** En cas de reprogrammation d'une heure ou de réattribution de table, les convocations SMS sont automatiquement diffusées aux compétiteurs concernés.
  * **Format ultra-concis GSM 7-bit mono-segment (< 150 car.) :** Raccourcissement intelligent des noms d'équipes et joueurs pour garantir une expédition en un seul segment SMS (mono-segment 160 caractères max).
* **🔒 Validation séquentielle stricte par ronde (Rondes verrouillées jusqu'à complétion) :**
  * **Verrouillage strict des rondes suivantes :** Avant de passer à la saisie ou à la validation des pointages d'une ronde subséquente (ex. Quarts de finale, Demi-finales, Grande Finale), l'ensemble des matchs de la ronde courante/précédente doivent être obligatoirement validés et terminés (`termine == True`).
  * **Indicateurs visuels et contrôles désactivés :** Tout match d'une ronde non prête affiche un bandeau clair d'information (`🔒 Saisie verrouillée : La ronde précédente (...) doit être entièrement validée avant de pouvoir saisir cette ronde (X match(s) en attente)`), les listes déroulantes de pointage sont grisées (`disabled=True`), et le bouton `✅ Valider` ainsi que le bouton de promotion (`🎟️ Passe-droit`) sont bloqués.
  * **Déverrouillage automatique en temps réel :** Dès que le dernier match de la ronde précédente est validé par le marqueur, la ronde suivante se déverrouille instantanément.
  * **Sécurité applicative garantie :** Les fonctions de scoring (`actualiser_score_elimination` et `attribuer_passe_droit_elimination`) vérifient la complétion séquentielle et rejettent formellement toute validation prématurée.
* **📂 Option « Récupérer tournoi en cours » (Reprise instantanée & Anti-perte) :**
  * **Reprise en 1 clic de tout tournoi en cours :** Permet à l'organisateur ou au marqueur de récupérer et de recharger sur la grille active n'importe quel tournoi en cours sauvegardé dans l'historique ou sur disque.
  * **Accès omniprésent :**
    * **Sur la grille active vide :** Lorsqu'aucun tournoi n'est affiché en Simple ou en Double, un conteneur dédié `⚡ Reprendre un tournoi en cours` présente la liste des tournois en cours avec leur progression (ex. *3/7 match(s) joué(s)*) et un bouton `⚡ Reprendre ce tournoi`.
    * **Barre d'outils du tournoi actif :** Un bouton popover `📂 Récupérer` dans la rangée d'actions supérieure permet de changer de tournoi ou de restaurer un tournoi archivé sans perdre le tournoi courant (archivé automatiquement avant bascule).
    * **Onglet Nouveau tournoi :** Un bloc d'alerte `⚡ Tournoi(s) en cours disponible(s) à la reprise` liste les tournois non terminés pour éviter de recréer un tournoi par inadvertance.
    * **Section Historique :** Le bouton `⚡ Reprendre en direct` recharge immédiatement le tournoi sélectionné dans la grille active de sa catégorie.
* **🎯 Saisie des résultats pour les tournois actifs choisis dans la liste :**
  * **Saisie directe depuis la liste déroulante des tournois :** Lorsqu'un tournoi actif est sélectionné dans la liste déroulante (*« 🏆 Choisir un tournoi dans la liste déroulante »*), l'ensemble des rencontres, les cartes de matchs, la saisie des pointages, les boutons de validation (`✅ Valider`), de promotion (`🎟️ Passe-droit`) et de rectification (`✏️ Reprendre / Corriger`) s'affichent immédiatement sous l'arborescence, permettant d'entrer les scores directement sans devoir obligatoirement basculer d'onglet.
  * **Réactivation en 1 clic des tournois en cours :** Pour tout tournoi sauvegardé dont le statut est en cours (`statut == "en_cours"`), un bouton `⚡ Reprendre en direct` permet de le recharger immédiatement comme tournoi actif de sa catégorie pour poursuivre la saisie officielle des résultats.
* **📧 Sauvegarde automatique & Notification par courriel aux administrateurs dès la validation de la finale :**
  * **Clôture et archivage instantanés :** Dès la saisie ou validation du dernier match de la finale (Grande Finale en Double Élimination, Finale en Élimination directe ou dernière rencontre en Round-Robin), le tournoi bascule automatiquement au statut `statut = "termine"`, le Champion (`vainqueur_final`) et le finaliste sont officiellement proclamés et l'état complet est sauvegardé dans `tournois_data.json` et `historique_tournois.json`.
  * **Transmission courriel automatique aux administrateurs :** L'application expédie immédiatement un courriel officiel aux administrateurs définis dans la configuration SMTP. Ce message contient l'annonce officielle du Champion médaillé d'or 🥇, du Finaliste 🥈, les statistiques et horaires de la compétition, et intègre en pièces jointes le fichier complet `historique_tournois.json` ainsi que l'arborescence visuelle HTML du tournoi prêt à imprimer.
  * **Confirmation visuelle à l'écran :** Un bandeau de confirmation informe immédiatement le marqueur que la finale est validée, le podium officiel affiché et la notification courriel délivrée.


---

### 6. 👁️ Mode Spectateur & Gestion de la Main (Verrouillage multi-utilisateurs)
* **Accès Spectateur sans mot de passe :**
  * Consultation en direct des scores de la feuille de match (par équipe, par joueur et manche par manche), des classements, des statistiques de progression et de l'arborescence des tournois.
  * Rafraîchissement automatique (toutes les 5s / 15s / 30s) ou manuel en un clic.
* **Contrôle exclusif du Marqueur / Administrateur :**
  * Un seul éditeur détient la main active à la fois (`session_lock.json`) afin d'éviter tout conflit d'écriture.
  * Boutons **« 🤝 Céder la main »** (avec sauvegarde automatique préalable sur le disque) et **« ⚡ Prendre la main »** (avec rechargement automatique de la dernière sauvegarde).

---

### 7. 📈 Statistiques, Progression, Face-à-Face & Projections (Joueurs & Équipes)
Le module **« 📈 Statistiques & Progression — Joueurs et Équipes »** (accessible depuis le menu principal et dans l'onglet Statistiques) offre une analyse complète en **4 volets spécialisés**, précédés d'un bandeau des records et honneurs de la semaine :

* **🌟 Bandeau « Tableau d'Honneur de la Dernière Semaine & Records de la Saison » :**
  * **⭐ Les 3 Étoiles de la Semaine (Joueurs) :** Mise en lumière automatique des 3 meilleures performances individuelles de la dernière journée (score `/24`, nombre de manches gagnées à 8 points et différentiel $\Delta$ par rapport à l'objectif personnel).
  * **🚀 Équipe de la Semaine :** L'équipe ayant signé le plus haut pointage collectif (`/72`) lors de la dernière semaine.
  * **🏅 4 Records de la Saison :**
    * **Record d'équipe (`/72`)** sur une soirée.
    * **Duel le plus serré** (plus faible écart de points).
    * **Plus large victoire** (écart maximal).
    * **Plus longue série de manches à 8 points consécutives** par un joueur.
* **🏆 Volet 1 — Équipes & Collectif :**
  * **Podium Top 3 & Classement général enrichi** (triable selon le **Total des Points officiel Saphir** ou par **Victoires V-D**) incluant : Matchs joués (`PJ`), `V`, `D`, `É`, **Total Points**, **Moyenne `/72`**, **Différentiel (`+/-`)**, **% Manches gagnées**, bilan **🏠 Receveur vs 🚗 Visiteur**, **Série en cours** (`🔥 3V`, `❄️ 2D`) et **Forme des 5 derniers matchs** (`🟢V 🔴D...`).
  * **📈 Courbe d'évolution cumulée des points** des 8 équipes (`Alpha` à `Hotel`) au fil de la saison.
  * **⚖️ Homogénéité & Répartition du Trio (J1 / J2 / J3 / Remplaçants) :** Part en `%` et moyenne `/24` de chaque membre du trio dans le score de son équipe avec qualification automatique du profil collectif (*⚖️ Trio très homogène*, *🤝 Trio équilibré*, *⭐ Leader prédominant*).
  * **🔄 Performance par Ronde (Début, Milieu et Fin de soirée) :** Analyse comparative de chaque équipe en **1re Ronde (Manches 1–3)**, **2e Ronde (Manches 4–6)** et **3e Ronde (Manches 7–9 — Finition)** avec identification de sa ronde forte.
* **👤 Volet 2 — Joueurs & Individuel :**
  * **Filtre par équipe** et **4 modes de tri** : *Moyenne par manche (`/8`)*, *Total des points cumulés*, *Surperformance vs Objectif ($\Delta$ pts)* et *Indice Clutch (manches serrées 8-6 / 8-7)*.
  * **🎯 Objectif personnel (`/24`) & Indice de Surperformance ($\Delta$ pts) :** Croisement automatique avec `joueurs_stats.csv` pour calculer l'objectif attendu par soirée de chaque joueur et mesurer son écart réel cumulé ($\Delta$ points au-dessus ou en dessous de son standard).
  * **Indicateurs de maîtrise & Constance :**
    * **👑 Soirées parfaites (`24/24`)** (3 victoires de 8 points en 3 manches).
    * **🧹 Blanchissages (`8-0`)** infligés.
    * **🔥 Indice « Clutch » :** Bilan `V-D` et `%` de réussite dans les manches décisives serrées (`8-6` et `8-7`).
    * **📊 Profil de Constance :** Écart-type et fourchette `Plancher – Plafond` classant chaque joueur (*🎯 Métronome*, *⚖️ Régulier*, *⚡ Variable*).
    * **🟢 Assiduité & Points sur table vs Forfait d'absence :** Distinction claire entre les points gagnés queue en main à la table et les points attribués par forfait d'absence.
  * **⚔️ Relations d'adversité individuelles :** Identification automatique pour chaque joueur de son **🟢 Adversaire favori (Proie favorite)** et de sa **🔴 Bête noire**.
  * **📉 Graphique individuel de progression (0 à 24 pts) :** Diagramme par soirée avec barres colorées selon l'atteinte du contrat et **ligne de référence pointillée orange** représentant l'objectif personnel (`/24`).
* **⚔️ Volet 3 — Face-à-Face & Matrice Croisée 8×8 :**
  * **🥊 Comparateur Duel Joueur A vs Joueur B :** Bilan direct des confrontations (manches gagnées, points marqués, moyenne `/8` en face-à-face) et historique détaillé manche par manche.
  * **🏁 Matrice Croisée des Équipes (8×8 — `Alpha` à `Hotel`) :** Tableau synthétique de tous les duels d'équipes (scores aller/retour et bilan particulier).
* **🔮 Volet 4 — Calendrier Restant & Projections de Fin de Saison (14 semaines) :**
  * Croisement automatique entre `historique_matchs.json` et le calendrier officiel `horaire_saphir.json` :
    * **Matchs restants à disputer** et liste des **3 prochains adversaires** (`vs` domicile / `@` extérieur).
    * **Indice de difficulté du calendrier restant (*Strength of Schedule*) :** Moyenne `/72` des adversaires restants avec badge de difficulté (*🟢 Favorable*, *🟡 Équilibré*, *🔴 Relevé*).
    * **Projection de fin de saison (14 semaines) :** Estimation des victoires finales et du total de points projeté au terme des 14 semaines régulières, accompagnée de la **feuille de route détaillée match par match** par équipe.
* **🖨️ Archives & Réimpression A4 :**
  * Consultation et réimpression A4 en un clic de toutes les feuilles de matchs archivées et de tous les tournois passés.

---

### 8. ⚙️ Espace Administration, Transmission API Saphir & Persistance Cloud Hybride (Supabase PostgreSQL + GitHub)
Le volet **`⚙️ Administration`** (réservé exclusivement à l'accès **`🛡️ Administrateur`**) regroupe les outils avancés de gestion de la ligue, de persistance des données, d'interconnexion API et de maintenance du système.

* **Onglets et modules du volet Administration :**
  * **👥 Équipes (`equipes-saphir.csv`) :** Tableau interactif modifiable en direct, ajout rapide d'équipes et de joueurs réguliers, import/export CSV et validation instantanée.
  * **📝 Match passé (Saisie de matchs antérieurs ou en retard) :** Formulaire complet permettant d'enregistrer rétroactivement une rencontre disputée avec sélection de la date/heure, composition des équipes et scores des 9 manches selon la rotation officielle alternée.
  * **✏️ Rectifications (Correction ou suppression de matchs archivés) :**
    * Correction ciblée des scores de manche, des présences ou des alignements avec motif officiel et régénération immédiate de la feuille officielle (accessible aussi directement depuis une alerte de doublon du Scanner IA).
    * **🗑️ Suppression d'un match de l'historique :** Option sécurisée avec confirmation, sauvegarde `.bak` horodatée et synchronisation Cloud automatique.
  * **🗓️ Saison (Gestion des cycles de compétition) :** Initialisation d'une nouvelle saison, archivage des statistiques précédentes et remise à zéro sécurisée des classements actifs.
  * **💾 Sauvegardes & Restauration fiabilisée (Nettoyage JSON pur) :**
    * **Nettoyage et allègement JSON pur :** Suppression complète du code HTML verbeux et des images base64 dans `historique_matchs.json`. Le fichier passe de ~448 Ko à ~56 Ko (réduction de plus de **88 %**), accélérant les synchronisations réseau.
    * **Exports & Envois par courriel :** Téléchargement direct des bases JSON et envoi automatisé des bilans par courriel SMTP avec pièces jointes.
  * **🌐 Module API Saphir (`POST billardImport`) :**
    * Module interactif et automatisé d'interconnexion avec l'API officielle de la Salle Le Saphir (`POST https://saphirbillard.com/index.php?eID=billardImport`).
    * **Transmission automatisée :** Déclenchée sans friction lors de l'approbation d'un match en direct ou lors de l'archivage direct depuis le scanner IA de feuilles de match (avec calcul automatique de la saison et de la semaine).
    * **Banc d'essai administratif :** En-têtes HTTP `Content-Type: application/json` et `X-API-Key: ...` avec test de latence et coloration syntaxique de la réponse serveur pour valider la communication.
  * **📲 Sentinelle SMS (Passerelle Android APK & Termux avec support Pub/Sub ⚡) :**
    * Module de gestion des 24 membres avec leurs numéros de téléphone et consentement SMS dans `joueurs_sms.json` (avec commandes rapides pour **activer ou désactiver tous les consentements en 1 clic** tout en conservant l'ajustement individuel par joueur).
    * **Architecture Pub/Sub instantanée (Supabase Realtime Broadcast) :** Dès qu'un match est archivé, qu'un rappel de tournoi est lancé ou qu'un test est ordonné, un événement WebSocket est diffusé en direct sur le canal `realtime:saphir_sms`. L'application mobile réagit en moins d'une seconde, sans délai d'attente (délai de 5 minutes éliminé) !
    * **Application Android native (`SaphirSMS.apk` v1.1.7 — versionCode 15) :**
      * Projet Android complet (disponible directement à la racine sous `SaphirSMS.apk` et via GitHub Releases) compilé avec `targetSdk 33` / `compileSdk 34`.
      * **Verrou atomique anti-doublon (`AtomicBoolean`) & Dédoublonnage :** Sécurité stricte éliminant tout risque de double expédition SMS lors de la réception simultanée d'un signal Pub/Sub et du cycle de scrutation de sécurité.
      * **Découpage optimisé GSM 7-bit mono-segment (jusqu'à 160 car.) :** Algorithme perfectionné dans `SmsHelper.java` permettant aux textos de 160 caractères ou moins d'être transmis en un unique segment SMS sans découpage prématuré.
      * **Normalisation automatique GSM 7-bit :** Conversion transparente de tous les caractères accentués et spéciaux vers l'alphabet standard GSM 7-bit, garantissant 100 % de compatibilité avec tous les opérateurs mobiles nord-américains sans corruption d'encodage.
      * **Suivi d'expédition modem & Repli indicatif +1 :** Écoute via `PendingIntent` du résultat renvoyé par le modem cellulaire (accusé `RESULT_OK`), consignation explicite des erreurs et tentative de repli automatique avec l'indicatif international `+1` si nécessaire.
      * **Téléversement du Journal en direct (`journal_sentinelle.txt`) :** L'application Android pousse automatiquement ses journaux d'activité vers Supabase en temps réel, permettant aux administrateurs de surveiller le statut du téléphone relais sans quitter l'interface Streamlit.
      * **Protection Android 14 FGS & WakeLock sécurisé :** Service d'arrière-plan permanent (*Foreground Service*) avec notification persistante et maintien d'éveil pour éviter toute mise en veille forcée par le système d'exploitation.
      * Client WebSocket OkHttp connecté 24/7, bouton Démarrer/Arrêter la surveillance, démarrage automatique au démarrage de l'appareil (*boot completed*) et compilation continue via GitHub Actions.
    * **Format ultra-compact GSM (< 150 caractères) pour les résultats de match (`NOUVEAU_MATCH`) :**
      * Synthèse condensée affichant le score global et les points individuels (`J.Nom:Pts`) sur une seule ligne par équipe, garantissant un texto complet tenant sur un seul segment SMS.
    * **Banc d'essai Pub/Sub avec sélection de signal & Modèles types :**
      * Sélecteur de signal intégré avec pré-remplissage du modèle associé :
        1. `⚡ TEST_SMS` : test direct de connectivité de la Sentinelle.
        2. `📢 NOUVEAU_MATCH` : expédition du sommaire officiel d'un match de ligue (format compact).
        3. `🎱 TOURNOI_CONVOCATION` : appel d'un match aux tables de tournoi (heure + table).
        4. `⏰ TOURNOI_HORAIRE` : avis de report ou changement de table en tournoi.
        5. `🔍 CHECK_NOW` : signal Ping / diagnostic forçant le téléversement immédiat du journal `journal_sentinelle.txt`.
        6. `✍️ PERSONNALISE` : saisie libre de message.
      * Compteur de caractères en direct, prévisualisation du rendu GSM 7-bit, estimation des segments et pré-remplissage du numéro administrateur par défaut (`418-872-0836`).
    * **Interrupteur global de service & File d'attente Cloud :** Commutateur marche/arrêt instantané (`sms_actif` dans `config_sms.json` avec diffusion immédiate WebSocket `CONFIG_SMS`) et file d'attente horodatée dans `commandes_sms.json`.
    * **Générateur de script Termux (`saphir_sms_poller.py`) :** Téléchargeable en 1 clic avec clés Supabase pré-remplies pour une exécution instantanée sur Android avec `termux-wake-lock`.
  * **📧 SMTP (Notifications et bilans officiels) :** Configuration du serveur d'expédition courriel (prise en charge robuste TLS port 587 / SSL port 465 avec repli automatique et nettoyage des mots de passe d'application Gmail), test d'envoi en direct et routage des alertes administratives.
  * **🔑 Sécurité (Gestion des accès, Clés API & Secrets) :**
    * Modification sécurisée des mots de passe Marqueur et Administrateur avec hachage cryptographique SHA-256 dans `config_auth.json`.
    * **Gestion des clés d'API IA :** Configuration de la clé **Google Gemini API** (`gemini_api_key`) pour la numérisation des photos de feuilles de scores.
    * **Configuration du Cloud & Sélection du Mode de Persistance :** Renseignement des identifiants Supabase (URL et clé API) et choix du mode actif.
    * **Protection stricte des identifiants sensibles :** Intégration transparente de `st.secrets` (`.streamlit/secrets.toml`) pour stocker en lieu sûr les clés Supabase, le jeton GitHub, la clé Gemini et les mots de passe SMTP.

* **🚀 Mode Cloud Hybride (Supabase PostgreSQL Prioritaire) & Élimination des rechargements intempestifs :**
  * **Pourquoi Supabase PostgreSQL ?** Sur Streamlit Community Cloud, chaque commit git poussé sur la branche `main` déclenche un redémarrage complet du conteneur applicatif, coupant les sessions des marqueurs en direct. L'intégration d'une base relationnelle **Supabase PostgreSQL** via PostgREST résout définitivement ce problème.
  * **Table relationnelle `public.saphir_files` (14 documents vitaux) :**
    * Stockage temps réel des 14 fichiers fondamentaux sous forme d'enregistrements `(filename, content, updated_at)` : `equipes-saphir.csv`, `joueurs_stats.csv`, `horaire_saphir.json`, `historique_matchs.json`, `historique_tournois.json`, `tournois_data.json`, `sauvegarde_saisie_secours.json`, `sauvegarde_annulee_secours.json`, `session_lock.json`, `config_email.json`, `config_admin.json`, `joueurs_sms.json`, `config_sms.json`, `commandes_sms.json` (ainsi que `journal_sentinelle.txt` pour les journaux d'activité en direct).
    * Opérations SQL atomiques optimisées en Upsert (`INSERT ... ON CONFLICT (filename) DO UPDATE`) exécutées en moins de 150 ms sans solliciter Git.
  * **3 modes de persistance au choix dans l'interface (`🔑 Sécurité`) :**
    1. **Mode 1 — Supabase prioritaire (Recommandé en production) :** Sauvegardes instantanées dans Supabase PostgreSQL. **Zéro commit git** pendant les matchs, garantissant une stabilité absolue sans coupure de session.
    2. **Mode 2 — Hybride (Supabase + Backup GitHub) :** Écriture en temps réel dans Supabase avec sauvegarde miroir sur GitHub.
    3. **Mode 3 — GitHub classique :** Persistance exclusive par commits git sur le dépôt distant.
  * **Sauvegarde intégrale automatique déclenchée au clic :** Dès que l'administrateur clique sur `💾 Enregistrer la configuration Cloud`, l'application pousse immédiatement l'ensemble des 14 fichiers locaux vers la table `saphir_files` de Supabase avec confirmation visuelle détaillée.
  * **Restauration intelligente au réveil & Repli automatique (*Fallback*) :**
    * Au réveil du conteneur Streamlit (`restaurer_depuis_cloud_au_reveil`), l'application interroge Supabase en priorité pour recharger la dernière version des données.
    * **Bouclier anti-écrasement (Fusion intelligente) :** Si un match a été saisi localement, il est conservé et fusionné avec les données distantes par sa clé unique (`receveur + visiteur + date`), interdisant toute perte accidentelle.
    * En cas d'indisponibilité ou d'absence de configuration Supabase, repli automatique transparent vers GitHub.
  * **Anti-mise en veille Supabase (Keep-Alive via `cron-job.org`) :**
    * Pour éviter la mise en pause gratuite des projets Supabase inactifs après 7 jours, une tâche cron quotidienne gratuite (`cron-job.org`) effectue une requête `GET` légère sur `https://<projet>.supabase.co/rest/v1/saphir_files?select=filename&limit=1` avec l'en-tête `apikey`, maintenant la base éveillée et réactive en tout temps.

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
# Base de données Cloud Supabase PostgreSQL (Recommandé en production)
[supabase]
url = "https://votre-projet.supabase.co"
key = "votre_cle_supabase_anon_ou_service_role"
mode = "supabase"   # "supabase" (Mode 1), "hybride" (Mode 2), ou "github" (Mode 3)

# Synchronisation miroir GitHub (Mode 2 et 3)
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

| Fichier / Ressource | Rôle |
| :--- | :--- |
| `app.py` | Code source principal de l'application Streamlit (Saisie, Scanner IA, Tournois, Stats & Projections, Admin, Mode TV, Moteur Cloud Hybride) |
| `README.md` | Documentation officielle complète (affichée et imprimable au format A4 depuis la page d'ouverture) |
| `SaphirSMS.apk` | Paquet binaire Android APK prêt à installer (v1.1.7 — versionCode 15) de la passerelle Sentinelle SMS (verrou atomique anti-doublon, Pub/Sub temps réel, découpage mono-segment 160 car., convocations tournois) |
| `public.saphir_files` | Table relationnelle PostgreSQL hébergée sur Supabase stockant en temps réel les 14 fichiers fondamentaux de la ligue |
| `.streamlit/secrets.toml` | Stockage sécurisé des clés d'accès (Supabase, GitHub, Gemini Vision, SMTP et Admin) |
| `equipes-saphir.csv` | Liste officielle des équipes (`Alpha` à `Hotel`) et de leurs 3 joueurs réguliers (synchronisée Cloud) |
| `joueurs_stats.csv` | Statistiques de référence et moyennes officielles des joueurs utilisées pour les objectifs (`/24`) et forfaits d'absence |
| `horaire_saphir.json` | Calendrier officiel des 14 semaines de la saison régulière utilisé pour les projections et le calcul de semaine |
| `historique_matchs.json` | Base de données allégée (100 % JSON pur) des feuilles 3v3 validées (synchronisée Cloud avec fusion intelligente) |
| `historique_tournois.json` | Historique officiel complet des tournois Simples & Doubles (synchronisé Cloud) |
| `tournois_data.json` | État en temps réel des tournois actifs (synchronisé Cloud) |
| `sauvegarde_saisie_secours.json` | Sauvegarde temps réel de la feuille de match 3v3 en cours de saisie (synchronisée Cloud) |
| `sauvegarde_annulee_secours.json` | Corbeille de secours permettant d'annuler un « Nouveau match » |
| `session_lock.json` | Verrouillage multi-utilisateurs de la main active (Marqueur / Administrateur) |
| `joueurs_sms.json` | Répertoire des contacts cellulaires et consentements SMS des membres de la ligue (synchronisé Cloud) |
| `config_sms.json` | Configuration et statut d'activation du service SMS de la ligue (`sms_actif`, synchronisé Cloud) |
| `commandes_sms.json` | File d'attente et historique des commandes d'envoi SMS de résultats et tests (synchronisé Cloud) |
| `android-saphir-sms/` | Code source complet du projet Android natif Saphir SMS v1.1.7 (verrou atomique anti-doublon, WebSocket Pub/Sub temps réel, service FGS Android 14) |
| `config_auth.json` | Empreintes SHA-256 des mots de passe Marqueur et Administrateur |
| `config_email.json` | Paramètres SMTP pour l'envoi automatique des rapports, feuilles scannées et sauvegardes (synchronisé Cloud) |
| `config_admin.json` | Configuration administrative locale de la persistance Cloud (Supabase / GitHub) et clé Gemini |

---

## 📄 Licence
Projet développé pour la **Ligue de billard Boule en main — Salle Le Saphir**. Libre d'utilisation et d'adaptation (Licence MIT).
