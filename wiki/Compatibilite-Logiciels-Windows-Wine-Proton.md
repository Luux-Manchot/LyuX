# 🍷 Compatibilité Logiciels Windows (Wine, Proton & Bottles)

L'un des freins historiques à l'adoption de Linux dans l'Éducation Nationale est l'existence de logiciels pédagogiques conçus exclusivement pour Windows (notamment en **Physique-Chimie**, en **SVT** et en **Mathématiques**).

**LyuX intègre une couche de compatibilité transparente et sécurisée basée sur Wine, Proton et Bottles**, permettant d'exécuter ces logiciels historiques directement sous Linux comme s'il s'agissait d'applications natives, sans avoir à conserver ou payer des licences Windows.

---

## 1. L'Expérience Utilisateur : Exécution Transparente & "Zéro Bureau Windows"

Pour l'élève et l'enseignant, la transition est totalement invisible :
1. **Lancement en 1 clic** : Le logiciel Windows (ex: *Régressi*, *Cabri 3D*) dispose de sa propre icône intégrée dans le menu des applications de **KDE Plasma**.
2. **Fenêtre native** : Aucun bureau Windows virtuel ne s'affiche. L'application s'ouvre dans sa propre fenêtre flottante avec le thème graphique du système.
3. **Enregistrement direct dans le Home Réseau** : Le lecteur `H:` ou `Mes Documents` de l'application Windows est automatiquement relié au dossier réseau de l'élève (`~/Espace_Personnel`). Tous les graphiques et mesures sont sauvegardés sur le serveur central.

---

## 2. Architecture de Confinement & Sécurité (Sandbox)

Faire tourner des binaires Windows (.exe) sous Linux offre un **gain de sécurité massif** par rapport à un poste Windows classique :

```mermaid
graph TD
    subgraph POSTE_LYUX ["Poste Universel LyuX (Debian 12)"]
        KDE["Bureau KDE Plasma (X11)"]

        subgraph SANDBOX_WINE ["Sandbox Isolée (Préfixe Wine / Bottles)"]
            EXE["Logiciel Pédagogique Windows (ex: Régressi.exe)"]
            DLLS["Bibliothèques de compatibilité (Wine / Proton DXVK)"]
            DRIVE_C["Disque Virtuel C: Fictif (Isolé)"]
            VIRT_COM["Port Série Virtuel COM1"]
        end

        subgraph SYSTEME_HOTE ["Système Hôte Linux Protégé"]
            UDEV["Règles udev USB (/dev/ttyUSB0)"]
            HOME["Partage Réseau CIFS (~/Espace_Personnel)"]
        end
    end

    EXE --> DLLS --> DRIVE_C
    EXE -->|Enregistrement TP| HOME
    UDEV -->|Redirection brute| VIRT_COM --> EXE
    EXE -.->|Infection Malware Windows| DRIVE_C
    DRIVE_C -.x|Bloqué : Impossible d'infecter l'OS Linux| SYSTEME_HOTE
```

### Les Avantages de Sécurité :
* **Immunité aux Virus & Ransomwares Windows** : Si un élève tente de lancer un exécutable infecté ou si un logiciel Windows est vulnérable, l'attaque reste piégée dans le faux disque `C:\` virtuel sans jamais pouvoir compromettre le système d'exploitation Linux ni les fichiers système.
* **Zéro droit administrateur** : L'environnement Windows émulé tourne avec les droits restreints de l'élève.

---

## 3. Matériel de Mesure & Consoles d'Acquisition (SVT / Physique)

L'un des défis majeurs en sciences concerne les **boîtiers d'acquisition de données** branchés en USB sur les paillasses (ex: capteurs de température, d'accélération, de pH, consoles ExAO) :

1. **Règles `udev` dédiées** : Lorsqu'un boîtier de mesure USB est branché, le noyau Linux le détecte et lui attribue une route brute (ex: `/dev/ttyUSB0` ou `/dev/ttyACM0`).
2. **Liaison automatique avec Wine** : LyuX crée un lien symbolique direct dans le préfixe Windows :
   ```bash
   ln -s /dev/ttyUSB0 ~/.wine/dosdevices/com1
   ```
3. **Résultat pour l'enseignant** : Lorsqu'il ouvre son logiciel de mesure Windows sous LyuX, le logiciel voit le port `COM1` comme sous Windows et communique directement avec la console de mesure sans aucune manipulation manuelle.

---

## 4. Matrice de Compatibilité des Logiciels Pédagogiques Français

| Logiciel | Matière | Statut sous LyuX | Technologie Utilisée | Expérience Constatée |
| :--- | :---: | :---: | :--- | :--- |
| **Régressi** | Physique | ✅ **Parfait** | Wine 9.x / Proton | Traitement de données et modélisation graphique 100% fonctionnels. |
| **Atelier Scientifique (Jeulin)** | SVT / Physique | ✅ **Fonctionnel** | Wine + règles udev COM | Reconnaissance des capteurs ExAO via port série émulé. |
| **LatisPro** | Physique | 🟡 **Testé / Validé** | Wine Staging + DLL overrides | Nécessite l'injection des runtimes Visual C++ (automatisée dans LyuX). |
| **Cabri 3D / Cabri II Plus** | Maths | ✅ **Parfait** | Proton / DXVK | Rendu 3D fluide accéléré par la carte graphique via Vulkan. |
| **Chemsketch** | Chimie | ✅ **Parfait** | Wine 9.x | Dessin de molécules et structures chimiques sans aucun ralentissement. |
| **EduPython** | NSI / SNT | 🔄 **Remplacé** | **Thonny / VS Code (Natif)** | Remplacé nativement par Thonny (plus stable, plus rapide et moderne). |
| **Tracker** | Physique | ✅ **Natif** | Java OpenJDK | Analyse vidéo de mouvements (chute libre, trajectoires) 100% native. |
| **Avogadro / Stellarium** | Chimie / SVT | ✅ **Natif** | Paquets officiels Debian | Planétarium et modélisation moléculaire native haute performance. |

---

## 5. Pourquoi Proton et Bottles plutôt que du Wine brut ?

1. **DXVK (DirectX vers Vulkan)** : Proton intègre la couche DXVK qui traduit les appels graphiques Direct3D (DirectX 9, 10, 11) en instructions **Vulkan** natives. Les logiciels de modélisation 3D (ex: Cabri 3D, simulateurs de mécanique) tournent à 60 images par seconde avec une fluidité identique à Windows.
2. **Gestion par "Bouteilles" (Bottles)** : Chaque logiciel spécialisé possède sa propre configuration de dépendances isolée (un logiciel nécessitant .NET 4.8 n'interfère pas avec un logiciel nécessitant d'anciennes bibliothèques VB6 de 2005).
3. **Pré-empaquetage Flatpak** : Ces préfixes Wine sont packagés et déployés automatiquement via notre catalogue Flatpak local sans aucune intervention de l'enseignant.
