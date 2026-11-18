# 📦 Catalogue de Logiciels Flatpak & Droits par Profil

> **Référence Issue GitHub** : [#7](https://github.com/Luux-Manchot/LyuX/issues/7)  
> **Décisions d'Architecture** : ADR-007

---

## 1. Pourquoi Flatpak plutôt que Snap ? (ADR-007)

Sur les distributions Linux classiques basées sur Ubuntu, les logiciels clés comme Firefox ou Chromium sont imposés sous forme de paquets **Snap**.  
Or, dans un environnement scolaire avec des dossiers réseau montés via `pam_mount` (`~/Espace_Personnel` en CIFS) :
* Les paquets Snap refusent d'accéder aux répertoires réseau à cause des règles strictes de confinement AppArmor.
* Les élèves subissent des erreurs de profil corrompu, et les navigateurs ne peuvent ni télécharger ni enregistrer leurs devoirs.

👉 **LyuX utilise Debian 12 avec Flatpak et Flathub** :
1. **Zéro Snap** : Toutes les applications de base (Firefox ESR, LibreOffice, Python, PyQt) sont en paquets natifs Debian `.deb`.
2. **Applications Pédagogiques Modernes via Flatpak** : Les logiciels plus volumineux ou en évolution rapide (Blender, Godot, Krita, Audacity, MuseScore) sont encapsulés dans le standard universel et ouvert **Flatpak**, 100% compatible avec les partages distants.

---

## 2. Matrice des Droits d'Installation par Profil

Pour éviter que les élèves n'installent des jeux non scolaires ou ne saturent l'espace disque du PC, les autorisations sont strictement définies :

| Fonctionnalité | 👨‍🎓 Élèves | 👩‍🏫 Enseignants / NSI / STI2D | 🛠️ Administrateur |
| :--- | :---: | :---: | :---: |
| **Utilisation des logiciels installés** | ✅ Oui (Toutes les applications approuvées) | ✅ Oui | ✅ Oui |
| **Installation de logiciels Flatpak** | ❌ **Bloquée** (Message de sécurité) | ✅ **Autorisée** (Mode utilisateur `--user` sans mot de passe root) | ✅ **Plein contrôle** (Système entier `--system`) |
| **Accès à KDE Discover** | Mode consultation uniquement | Mode installation actif depuis le catalogue officiel Flathub | Plein contrôle |
| **Ajout de dépôts tiers inconnus** | ❌ Interdit | ❌ Interdit | ✅ Autorisé |

---

## 3. Schéma de Déploiement et Accélération Locale

```mermaid
flowchart TD
    subgraph ADMIN ["Administration Système"]
        LIST["Liste des Flatpaks de Salle (ex: Blender, Godot, GIMP)"]
    end

    subgraph CACHE ["Serveur LyuX Local"]
        APT_C["Cache Local Apt-Cacher-NG / Flathub Proxy (:3142)"]
    end

    subgraph POSTES ["30 Postes de la Salle B204"]
        P1["Poste 01"]
        P2["Poste 02"]
        PN["Poste 30"]
    end

    ADMIN -->|Déploiement en 1 clic| POSTES
    P1 -->|1er téléchargement| CACHE
    CACHE -->|Mise en cache du runtime| CACHE
    P2 & PN -->|Téléchargement local Gigabit (2 sec)| CACHE
```

### Le Rôle Clé du Cache Local (`Apt-Cacher-NG`)
Lorsqu'une salle de 30 PC doit recevoir une suite comme **Blender** (environ 500 Mo) :
* Si chaque poste téléchargeait depuis Internet, la connexion du lycée serait saturée (30 x 500 Mo = 15 Go sur la bande passante externe).
* Avec LyuX, seul le premier PC télécharge l'application ; **les 29 autres la récupèrent directement depuis le cache local du serveur en quelques secondes**, sans impacter la connexion internet du reste du lycée.
