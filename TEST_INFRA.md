# TEST_INFRA.md — Infrastructure & Méthodologie des Tests E2E LyuX (Opération Manchot)

## 1. Introduction & Périmètre

Le présent document définit l'architecture de test, la méthodologie de qualification, les contrats d'interface et la matrice de vérification E2E (End-to-End) pour le projet **Opération Manchot (LyuX)**.

LyuX déploie un écosystème Linux complet et standardisé pour les lycées (Debian 12, KDE Plasma, Samba-AD, Cockpit, LAM, GLPI, Uptime Kuma, Veyon), remplaçant les scripts fragiles par des composants ouverts standardisés de l'industrie.

Le banc de test E2E applique une approche en **4 Niveaux (Tiers)** rigoureuse et automatisée, exécutable en environnement local, CI/CD ou lab VirtualBox :
- **Tier 1 — Couverture Fonctionnelle** : >= 5 cas de test par fonctionnalité pour l'intégralité des 24 fonctionnalités du catalogue `PROJECT.md`.
- **Tier 2 — Limites, Formats & Cas d'Extrémité (Boundary & Corner Cases)** : >= 5 cas de test par fonctionnalité testant les valeurs limites, payloads corrompus, injection de caractères, dépassements de quotas et résilience.
- **Tier 3 — Combinaisons & Interactions Multi-Composants (Cross-Feature Pairwise)** : Validation des chaînes d'intégration croisées (ex: Authentification SDDM -> pam_mount -> quotas Samba, Enrôlement OTP -> inventaire Ansible -> supervision Veyon, Signalement GLPI -> API -> notification).
- **Tier 4 — Scénarios Applicatifs Réels (Workloads Lycée)** : Simulations de flux réels de salles de classe et d'administration (Rentrée NSI en B204, TP Physique-Chimie en S102, Incident panne matériel GLPI, Panne réseau & reprise, Examen sous verrouillage Veyon).

---

## 2. Contrats d'Interface & Sources de Vérité Autoritatives

Toutes les assertions de test dérivent exclusivement des spécifications formelles définies dans `PROJECT.md`, `ORIGINAL_REQUEST.md` et des standards de l'industrie :

### 2.1 Matrice des Ports & Services Réseau
| Service | Port / Protocole | Transport | Source Spécification | Comportement Attendu |
| :--- | :--- | :--- | :--- | :--- |
| **Cockpit** | 9090 / TCP | HTTPS | `PROJECT.md` § 1, R1 | Interface Web d'administration système, UFW autorisé |
| **LyuX Control API** | 8000 / TCP | HTTP | `PROJECT.md` § 1, R1 | API FastAPI d'enrôlement OTP, monitoring et actions rapides |
| **LDAP Account Manager (LAM)** | 8082 / TCP | HTTP | `PROJECT.md` § 1, R1 | Gestion des comptes Samba-AD via profils web standardisés |
| **GLPI** | 8085 / TCP | HTTP | `PROJECT.md` § 1, R1 | Inventaire de parc et helpdesk tickets d'incidents |
| **Uptime Kuma** | 3001 / TCP | HTTP | `PROJECT.md` § 1, R1 | Dashboard supervision et sondes de liveness |
| **Samba AD / LDAP** | 389, 636 / TCP | LDAP / LDAPS | RFC 4511 / Samba 4 | Annuaire centralisé, OUs `eleves`, `enseignants`, `viesco`, `direction` |
| **Samba Kerberos** | 88 / TCP & UDP | KRB5 | RFC 4120 / Samba-AD | Billetterie TGT/TGS pour authentification unifiée |
| **Samba CIFS** | 445 / TCP | SMB2/3 | RFC 7111 / POSIX | Partages réseau utilisateurs (`homes`) et pédagogiques (`classes`) |
| **Veyon Service** | 11100 / TCP | TCP Veyon | Veyon Core 4.8+ | Écoute poste élève pour scraping d'écran et commandes |
| **Veyon Feature** | 11200 / TCP | TCP Veyon | Veyon Core 4.8+ | Contrôle distant, verrouillage écran, diffusion de message |
| **Veyon Demo Server** | 11400 / TCP | TCP Veyon | Veyon Core 4.8+ | Diffusion de l'écran enseignant vers les postes élèves |
| **Apt-Cacher-NG** | 3142 / TCP | HTTP Proxy | Debian Mirroring | Proxy-cache local des paquets deb pour éviter la saturation WAN |

### 2.2 Arborescence des Partages et Droits d'Accès
- **Homes utilisateurs** : `//serveur.lyux.lan/homes/<username>` monté dynamiquement sur `~/Espace_Personnel` via `pam_mount`. Permissions POSIX : `0700`, propriétaire `<username>:<primary_group>`.
- **Espaces Pédagogiques** : `//serveur.lyux.lan/classes` monté dynamiquement sur `~/Partages_Classes`.
  - `1G1_B204/Distribution` : Enseignants = Lecture/Écriture (`0770`), Élèves = Lecture Seule (`0750`).
  - `1G1_B204/Depot` : Enseignants = Lecture/Écriture (`0770`), Élèves = Dépôt Écriture Seule (`0770` avec permissions restrictives).
  - `1G2_S102/Distribution` & `1G2_S102/Depot` : structure symétrique pour la salle de sciences.
- **Espaces Personnels Enseignants** : `//serveur.lyux.lan/profs` monté sur `~/Partages_Enseignants` réservé au groupe `enseignants` (`0770`).
- **Clefs Asymétriques Veyon** :
  - Clef privée : `/etc/veyon/keys/private/teacher/key` (Droits `0440`, propriétaire `root:enseignants`, présente uniquement sur postes profs).
  - Clef publique : `/etc/veyon/keys/public/teacher/key` (Droits `0444`, propriétaire `root:root`, déployée sur tous les postes).

### 2.3 Annuaire des Comptes de Test Requis
| Identifiant | Nom Complet | Groupe Primaire | Salle Assignée | Rôle Pédagogique |
| :--- | :--- | :--- | :--- | :--- |
| `lucas.martin` | Lucas Martin | `eleves` | B204 (1G1) | Élève NSI / Maths |
| `emma.bernard` | Emma Bernard | `eleves` | B204 (1G1) | Élève NSI / Maths |
| `hugo.dubois` | Hugo Dubois | `eleves` | S102 (1G2) | Élève Sciences / SVT |
| `lea.thomas` | Léa Thomas | `eleves` | S102 (1G2) | Élève Sciences / SVT |
| `thomas.durand` | M. Thomas Durand | `enseignants` | B204 | Enseignant Maths & NSI |
| `sophie.leroy` | Mme Sophie Leroy | `enseignants` | S102 | Enseignante Physique-Chimie |
| `claire.viesco` | Claire Dupont | `viesco` | VIESCO | Vie Scolaire / Surveillance |
| `alain.direction` | Alain Delon | `direction` | DIRECTION | Direction / Proviseur |

---

## 3. Architecture du Banc de Test

```
tests/
├── conftest.py                     # Fixtures communes, parseurs de config, mock API client, validateurs de contrats
└── e2e/
    ├── __init__.py
    ├── conftest.py                 # Fixtures E2E spécialisées, chargement dynamique des playbooks, schémas XML/JSON
    ├── test_tier1_features.py      # Tier 1 : Couverture fonctionnelle (Features 1 à 24, >= 5 tests / feature)
    ├── test_tier2_boundaries.py    # Tier 2 : Cas limites, entrées vides, corrompues, dépassements de quotas
    ├── test_tier3_interactions.py  # Tier 3 : Matrice d'interactions croisées pairwise
    └── test_tier4_scenarios.py     # Tier 4 : 5 Scénarios réalistes d'exploitation en établissement scolaire
```

---

## 4. Modalités d'Exécution

### 4.1 Commande d'Exécution Standard
```powershell
pytest -v tests/e2e
```

### 4.2 Exécution Ciblée par Niveau
```powershell
# Tier 1 uniquement
pytest -v tests/e2e/test_tier1_features.py

# Tier 2 uniquement
pytest -v tests/e2e/test_tier2_boundaries.py

# Tier 3 uniquement
pytest -v tests/e2e/test_tier3_interactions.py

# Tier 4 uniquement
pytest -v tests/e2e/test_tier4_scenarios.py
```

### 4.3 Dépendances d'Exécution
- Python 3.10+
- `pytest` (>= 8.0)
- `fastapi` & `httpx` (pour `TestClient`)
- `pyyaml` (pour validation d'inventaires et playbooks Ansible)
- Modules Python natifs : `xml.etree.ElementTree`, `csv`, `configparser`, `ipaddress`, `hashlib`, `pathlib`, `re`

---

## 5. Critères de Réussite & Certification

Le banc de test est déclaré conforme et publie `TEST_READY.md` lorsque :
1. Les 4 fichiers de test `test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_interactions.py`, et `test_tier4_scenarios.py` sont présents et exécutables sans avertissement fatal.
2. 100% des tests réussissent sans tricherie ni bouchon factice (assertions strictes sur fichiers réels, modèles Pydantic réels, configurations réelles, inventaires réels et logique métier).
3. Toutes les 24 fonctionnalités inventoriées dans `PROJECT.md` disposent d'une traçabilité explicite vers leurs cas de tests.
