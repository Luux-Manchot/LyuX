# Project: Opération Manchot (LyuX)

## Architecture
Opération Manchot (LyuX) is a production-grade, modular, standardized Linux ecosystem engineered for secondary schools (Lycées). It replaces fragile ad-hoc scripts with established enterprise open-source solutions:
- **Server Infrastructure (`projects/lyux-server-infra`)**:
  - Cockpit Project (port 9090) for web system administration and storage management.
  - Samba-AD Domain Controller / LDAP for centralized user management (OUs: Eleves, Enseignants, Direction, Vie-Scolaire).
  - LDAP Account Manager (LAM) on port 8082 for web-based directory administration and self-service password resets.
  - GLPI on port 8085 for IT asset inventory and incident ticketing.
  - Uptime Kuma on port 3001 for infrastructure health checks.
  - Shared storage CIFS/NFS: `/homes/<user>` and `/classes/<salle>/` with segregated Distribution (read-only student) and Dépôt (write-only student) directories.
  - LyuX Server API on port 8000 (FastAPI) providing machine enrollment OTPs and central dashboard.
- **Client Workstation (`projects/lyux-ansible`, `lyux-enrollment`, `lyux-station`)**:
  - Debian 12 base with KDE Plasma 5/6 running under X11 for full Veyon screen scraping compatibility.
  - SDDM display manager with French locale (`fr_FR.UTF-8`) and AZERTY keyboard (`pc105`, `latin9`).
  - Automated deployment via Calamares installer and OEM First-Boot wizard (`lyux-enrollment`).
  - Seamless domain authentication via SSSD / realmd.
  - Dynamic user storage mounting at login via `pam_mount` (`~/Espace_Personnel`, `~/Partages_Classes`).
  - Disciplinary software profiles: NSI/Maths (Thonny, VS Code, Python, GeoGebra) and Sciences (Avogadro, Tracker, Stellarium, LibreOffice).
- **Pedagogical Supervision (`projects/lyux-ansible`, `lyux-station`)**:
  - Veyon 4.8+ with asymmetric key authentication (`teacher/key`).
  - Veyon Master on teacher stations (`b204-prof`, `s102-prof`).
  - Veyon Service on student stations (`b204-pc01`, `b204-pc02`, `s102-pc01`, `s102-pc02`).
  - Real-time classroom monitoring, remote screen locking, and broadcast messaging.
- **Virtual Lab & Automation (`projects/lyux-lab-vm`, `tests`)**:
  - VirtualBox unattended installation scripts without manual blue textual prompts.
  - E2E multi-tier automated test harness validating network ports, services, authentication, and Veyon supervision.

---

## Feature Inventory
Every feature identified during Phase 0 Survey is mapped to a definitive milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Cockpit Web Administration | Deploy Cockpit on standard port 9090 with system, storage, and network modules enabled, UFW allowed. | M1 | Survey 1 & 2 / R1 |
| 2 | Direct Ports for Web Services | Expose direct host ports for GLPI (8085), LAM (8082), Uptime Kuma (3001), API (8000) to ensure reliable access. | M1 | Survey 2 / R1 |
| 3 | GLPI Asset & Incident Tracking | Configure GLPI with MariaDB backend, asset inventory, and ticketing interface. | M1 | Survey 1 & 2 / R1 |
| 4 | Uptime Kuma Service Monitoring | Monitor Cockpit, Samba, LAM, GLPI, and Veyon endpoints on port 3001 with active probes. | M1 | Survey 2 / R1 |
| 5 | Samba-AD Domain Controller | Provision Samba-AD DC mode with domain `LYUX.LAN`, Kerberos realm, and organizational units (OUs). | M2 | Survey 2 / R1 |
| 6 | LDAP Account Manager (LAM) Configuration | Provide official `lyux.conf` profile for LAM connected to Samba-AD LDAP tree with OU mapping. | M2 | Survey 2 / R1 |
| 7 | Mandatory Test Accounts Provisioning | Import and provision the 7 required test accounts (Lucas Martin, Emma Bernard, Hugo Dubois, Léa Thomas, M. Durand, Mme Leroy, Claire Vie-Sco) with groups and passwords. | M2 | Survey 1 & 2 / Acceptance Criteria |
| 8 | Shared Storage CIFS/NFS Architecture | Configure `/homes/<user>` and `/classes/<salle>/` with separate Distribution (RO) and Dépôt (WO) shares and ACLs. | M2 | Survey 2 / R1 |
| 9 | Disk Quotas Enforcement | Implement quota limits (5 GB eleves, 20 GB profs) on user shares via Samba/filesystem. | M2 | Survey 2 / R1 |
| 10 | KDE Plasma Desktop Base | Debian/KDE Plasma graphical environment running on X11 backend for display stability and Veyon hooks. | M3 | Survey 3 / R2 |
| 11 | Locale & AZERTY Keyboard Standard | Enforce `fr_FR.UTF-8` and `pc105 / fr(latin9)` across SDDM, KDE, console, and installer. | M3 | Survey 3 / R2 |
| 12 | Calamares & OEM First-Boot Installer | Configure graphical Calamares installer and OEM First-Boot wizard (`lyux-enrollment`) with server discovery. | M3 | Survey 1 & 3 / R2 |
| 13 | SSSD / Realmd Domain Integration | Configure SSSD and PAM (`pam-auth-update`) for transparent domain login and Kerberos authentication. | M3 | Survey 3 / R2 |
| 14 | Dynamic Network Shares Mount via pam_mount | Configure `/etc/security/pam_mount.conf.xml` to dynamically mount `~/Espace_Personnel` and `~/Partages_Classes` on SDDM login. | M3 | Survey 1 & 3 / R2 |
| 15 | Disciplinary Profile: NSI / Maths | Ansible profile installing Thonny, VS Code, Python 3, GeoGebra, Jupyter, Git, Scilab. | M3 | Survey 1 & 3 / R2 |
| 16 | Disciplinary Profile: Sciences | Ansible profile installing Avogadro, Tracker, Stellarium, LibreOffice, GIMP. | M3 | Survey 1 & 3 / R2 |
| 17 | Veyon Architecture & Asymmetric Keys | Generate and deploy Veyon RSA key pair: private key (`teacher/key`) restricted to profs, public key on all clients. | M4 | Survey 3 / R3 |
| 18 | Veyon Master & Service Deployment | Install Veyon Master on teacher stations, Veyon Service on student stations, with network object directory. | M4 | Survey 3 / R3 |
| 19 | Pedagogical Classroom Supervision | Support live monitoring, screen locking, and teacher messaging for pilot rooms B204 and S102. | M4 | Survey 1 & 3 / R3 |
| 20 | Pilot Rooms Definition (B204 & S102) | Configure network mapping and inventory for Salle B204 (`b204-prof`, `b204-pc01/02`) and S102 (`s102-prof`, `s102-pc01/02`). | M4 | Survey 1 & 3 / R3 |
| 21 | VirtualBox Non-Textual Automated Lab | PowerShell and unattended scripts launching VirtualBox VMs with graphical splash, zero manual blue text prompts. | M5 | Survey 1 & 2 / R4 |
| 22 | Automated Lab Test Runner Script | Automated test script to spin up lab components, run connectivity checks, and report status. | M5 | Survey 2 / R4 |
| 23 | Comprehensive E2E Test Suite (Tiers 1-4) | Opaque-box requirement-driven test suite with >=11*N test cases verifying all features. | M6 | E2E Testing Track |
| 24 | Adversarial Hardening (Tier 5) | White-box stress testing, failure mode recovery, edge case validation. | M6 | Final Verification |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Server Stack & Cockpit Integration | Features 1, 2, 3, 4: Cockpit port 9090, docker direct port publishing for GLPI & LAM, Uptime Kuma monitoring, UFW firewall rules. | None | DONE |
| M2 | Samba-AD DC, LAM Profile & Storage | Features 5, 6, 7, 8, 9: Samba-AD domain provisioning, LAM `lyux.conf`, test user accounts import, `/homes` & `/classes` shares, ACLs, quotas. | M1 | DONE |
| M3 | Client KDE, Calamares & Session | Features 10, 11, 12, 13, 14, 15, 16: KDE Plasma X11 session, SDDM config, Calamares & OOBE installer, SSSD/realmd join, pam_mount, disciplinary profiles. | M2 | PLANNED |
| M4 | Veyon Classroom Supervision | Features 17, 18, 19, 20: Veyon key pair management, Veyon Master & Service configs, pilot classrooms B204 & S102, remote locking & monitoring. | M3 | PLANNED |
| M5 | Virtual Lab Automation & Scripts | Features 21, 22: VirtualBox non-textual automated setup and lab validation scripts. | M4 | PLANNED |
| M6 | Final Verification & Hardening | Features 23, 24: Pass 100% of E2E test suite (Tiers 1-4) and Tier 5 adversarial hardening with zero integrity violations. | M1, M2, M3, M4, M5, TEST_READY | PLANNED |

---

## Interface Contracts

### 1. Network Ports & Protocols
| Service | Port / Protocol | Transport | Accessibility | Purpose |
|---------|-----------------|-----------|---------------|---------|
| Cockpit | 9090/TCP | HTTPS | Admin Subnet | Web system management |
| LyuX API | 8000/TCP | HTTP | All Subnets | Machine enrollment & status |
| LAM | 8082/TCP | HTTP | Admin & Staff | LDAP account administration |
| GLPI | 8085/TCP | HTTP | All Subnets | Helpdesk & IT inventory |
| Uptime Kuma | 3001/TCP | HTTP | Admin Subnet | Service health monitoring |
| Samba AD / LDAP | 389/TCP, 636/TCP | LDAP/LDAPS | All Clients | Domain directory service |
| Samba Kerberos | 88/TCP, 88/UDP | KRB5 | All Clients | Ticket granting & auth |
| Samba CIFS | 445/TCP | SMB | All Clients | Shared network folders |
| Veyon Service | 11100/TCP | Veyon | Classroom LAN | Remote desktop monitoring |
| Veyon Feature | 11200/TCP | Veyon | Classroom LAN | Input locking, messaging |
| Veyon Demo | 11400/TCP | Veyon | Classroom LAN | Teacher screen broadcast |

### 2. File Paths & Shared Directories
- User Homes: `//server.lyux.lan/homes/%(USER)` mounted to `~/Espace_Personnel` (Mode 0700).
- Class Shares: `//server.lyux.lan/classes` mounted to `~/Partages_Classes` (Mode 0755).
  - Subfolder `1G1_B204/Distribution` (Teacher: RW, Student: RO).
  - Subfolder `1G1_B204/Depot` (Teacher: RW, Student: WO).
  - Subfolder `1G2_S102/Distribution` (Teacher: RW, Student: RO).
  - Subfolder `1G2_S102/Depot` (Teacher: RW, Student: WO).
- Veyon Keys:
  - Private key: `/etc/veyon/keys/private/teacher/key` (Mode 0440, root:enseignants, present on `*-prof` only).
  - Public key: `/etc/veyon/keys/public/teacher/key` (Mode 0444, root:root, present on all workstations).

### 3. Test Accounts Contract
| Username | Full Name | Group / Role | Default Password | Assigned Room / Class |
|----------|-----------|--------------|------------------|-----------------------|
| `lucas.martin` | Lucas Martin | `eleves` | `LyuX@2026!` | 1G1 (Salle B204) |
| `emma.bernard` | Emma Bernard | `eleves` | `LyuX@2026!` | 1G1 (Salle B204) |
| `hugo.dubois` | Hugo Dubois | `eleves` | `LyuX@2026!` | 1G2 (Salle S102) |
| `lea.thomas` | Léa Thomas | `eleves` | `LyuX@2026!` | 1G2 (Salle S102) |
| `thomas.durand` | M. Thomas Durand | `enseignants` | `Prof@2026!` | Salle B204 (NSI/Maths) |
| `sophie.leroy` | Mme Sophie Leroy | `enseignants` | `Prof@2026!` | Salle S102 (Sciences) |
| `claire.viesco` | Claire Dupont | `viesco` | `VieSco@2026!` | Administration |
| `alain.direction` | Alain Delon | `direction` | `Direct@2026!` | Direction |

---

## Code Layout & Write Boundaries
To ensure strict isolation between concurrent subagents:
- **Milestone 1 (Server Stack & Cockpit)**:
  - Exclusive ownership: `projects/lyux-server-infra/docker-compose.yml`, `projects/lyux-server-infra/scripts/init-server.sh`, `projects/lyux-server-infra/configs/cockpit/*`
- **Milestone 2 (Samba-AD, LAM, Shares)**:
  - Exclusive ownership: `projects/lyux-server-infra/configs/samba/*`, `projects/lyux-server-infra/configs/lam/*`, `projects/lyux-server-infra/scripts/import-users-csv.py`, `projects/lyux-server-infra/configs/utilisateurs-test.csv`, `projects/lyux-server-infra/scripts/setup-shares.sh`
- **Milestone 3 (Client KDE, Calamares, Session)**:
  - Exclusive ownership: `projects/lyux-ansible/roles/lyux-base/*`, `projects/lyux-ansible/roles/lyux-profile-salles/*`, `projects/lyux-ansible/roles/lyux-kiosk/*`, `projects/lyux-iso-builder/calamares/*`
- **Milestone 4 (Veyon Supervision)**:
  - Exclusive ownership: `projects/lyux-ansible/roles/lyux-profile-prof/*`, `projects/lyux-ansible/roles/lyux-profile-eleve/*`, `projects/lyux-ansible/configs/veyon/*`, `projects/lyux-station/src/veyon_manager.py`
- **Milestone 5 (Lab Automation)**:
  - Exclusive ownership: `projects/lyux-lab-vm/scripts/*`, `projects/lyux-lab-vm/configs/*`
- **E2E Testing Track**:
  - Exclusive ownership: `tests/e2e/*`, `tests/conftest.py`, `TEST_INFRA.md`, `TEST_READY.md`
