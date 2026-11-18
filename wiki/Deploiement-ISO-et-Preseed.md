# 💿 Déploiement ISO & Installation Zéro Invite — LyuX

LyuX fournit une expérience d'installation rapide et sans friction grâce à un système **Debian Preseed 100% autonome**.

---

## 1. L'Objectif : Zéro Écran Bleu Textuel

Lors d'un déploiement sur un poste ou une VM, l'installateur standard Debian Netinst pose habituellement de nombreuses questions interactives (choix de langue, partitionnement, fuseau horaire, miroir de paquets, création d'utilisateurs).

Dans LyuX, **toutes les réponses sont pré-configurées** :
1. **Zéro invite manuelle** : L'installeur démarre avec `priority=critical`.
2. **Partitionnement automatique** : Le disque est partitionné de manière optimale (`atomic` / ext4) sans demande de confirmation.
3. **Locale & Clavier français** : Système configuré en `fr_FR.UTF-8` avec disposition de clavier AZERTY (`fr-latin9`).
4. **Bureau KDE Plasma sous X11** : Installation directe du bureau léger KDE Plasma, de SDDM et des outils requis (`sssd`, `cifs-utils`, `libpam-mount`, `python3-pyqt6`).

---

## 2. Configuration Réseau Unattended (Multi-cartes)

Pour éviter les blocages de sélection d'interface réseau ou d'échec de miroir :
* La carte réseau connectée à Internet (NAT ou réseau d'établissement) est ciblée explicitement (`netcfg/choose_interface select enp0s8` ou carte active).
* Les options DHCP parasites sont neutralisées pendant la phase de bootstrap.
* Le miroir Debian officiel `deb.debian.org` est contacté directement pour installer les paquets à jour.

---

## 3. Post-Installation Automatique (`late_command`)

À la fin de la décompression du système, le script `late_command` du preseed exécute automatiquement les étapes de finalisation :
1. Ajout de l'administrateur local `lyux-admin` au groupe `sudo`.
2. Verrouillage du clavier AZERTY pour la console et le serveur X11.
3. Activation de la cible graphique (`systemctl set-default graphical.target`).
4. Éjection du support d'installation et redémarrage automatique.

Au premier démarrage sur disque, la machine arrive directement sur l'écran d'accueil **SDDM**.
