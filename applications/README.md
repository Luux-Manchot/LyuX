# 🖥️ LyuX Applications (`lyux-applications`)

Suite logicielle et utilitaires graphiques pour les postes clients du projet **LyuX (Opération Manchot)** sous Debian 13 & KDE Plasma 6.

## 📦 Applications incluses
- **`lyux-station`** : Station de travail graphique complète développée en PyQt6 (supervision de classe Veyon, gestionnaire de logiciels, réinitialisation de mot de passe, alertes).
- **`lyux-welcome`** : Écran d'accueil et premier démarrage adaptatif (détecte le rôle élève / enseignant).
- **`lyux-report`** : Boîte à outils de diagnostic matériel et signalement d'incidents informatiques connecté à GLPI.
- **`lyux-enrollment`** : Outil d'appairage express et enrôlement automatique des nouveaux postes dans leur salle via OTP.
- **`lyux-cli`** : Utilitaire CLI d'administration unifiée (`lyux`).

## 🚀 Démarrage rapide
```bash
# Lancer la station de travail
python lyux-station/src/main.py

# Utiliser la CLI
python lyux-cli/lyux.py status
```
