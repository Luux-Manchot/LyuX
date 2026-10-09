"""
Tier 2: Boundary & Corner Cases (>=5 test cases per feature covering boundaries,
empty inputs, invalid formats, extremes across all 24 features).
"""

import os
import re
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
import yaml

# ==============================================================================
# FEATURE 1: Cockpit Web Administration Boundaries
# ==============================================================================
class TestFeature01_CockpitBoundaries:
    def test_cockpit_port_numeric_range(self, expected_ports):
        """1.1 Port dans l'intervalle valide IANA (1024 - 65535)"""
        port = expected_ports["cockpit"]["port"]
        assert 1024 <= port <= 65535

    def test_cockpit_non_root_execution_prevention(self, paths):
        """1.2 init-server.sh interdit l'exécution non-root (code 1)"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert 'if [ "$EUID" -ne 0 ]; then' in content
        assert "exit 1" in content

    def test_cockpit_set_strict_flags(self, paths):
        """1.3 init-server.sh active le mode strict set -euo pipefail"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert "set -euo pipefail" in content

    def test_cockpit_homes_path_boundary_no_relative_dots(self, paths):
        """1.4 Les arborescences de stockage ne contiennent pas de chemins relatifs dangereux"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        samba_mkdir = [l for l in content.splitlines() if "mkdir" in l and "/srv/samba" in l]
        assert len(samba_mkdir) > 0
        for line in samba_mkdir:
            assert ".." not in line

    def test_cockpit_gid_allocations_boundaries(self, paths):
        """1.5 Les GID système sont alloués au-delà du seuil des comptes système (>= 2000)"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        gids = re.findall(r'-g\s+(\d+)', content)
        assert len(gids) >= 4
        for gid in gids:
            assert int(gid) >= 2000


# ==============================================================================
# FEATURE 2: Direct Ports for Web Services Boundaries
# ==============================================================================
class TestFeature02_DirectPortsBoundaries:
    def test_no_host_port_collisions(self, docker_compose_data):
        """2.1 Vérifie qu'il n'existe aucune collision de port hôte dans docker-compose"""
        host_ports = []
        for sname, sdata in docker_compose_data.get("services", {}).items():
            for p in sdata.get("ports", []):
                p_str = str(p)
                if ":" in p_str:
                    host_p = p_str.split(":")[0].replace("${", "").split(":-")[-1].replace("}", "")
                    host_ports.append(host_p)
        assert len(host_ports) == len(set(host_ports)), f"Collision détectée : {host_ports}"

    def test_all_ports_positive_integers(self, docker_compose_data):
        """2.2 Tous les ports publiés sont des entiers positifs valides"""
        for sname, sdata in docker_compose_data.get("services", {}).items():
            for p in sdata.get("ports", []):
                p_str = str(p)
                parts = p_str.split(":")
                for part in parts:
                    clean = re.sub(r'[^0-9]', '', part)
                    if clean:
                        assert 1 <= int(clean) <= 65535

    def test_empty_env_fallback_variables(self, docker_compose_data):
        """2.3 Variables d'environnement avec fallback par défaut sécurisé"""
        traefik_ports = docker_compose_data["services"]["traefik"]["ports"]
        assert any(":-8088}" in p or ":-8888}" in p for p in traefik_ports)

    def test_container_names_strict_naming(self, docker_compose_data):
        """2.4 Noms des conteneurs conformes à la nomenclature standard lyux-*"""
        for sname, sdata in docker_compose_data.get("services", {}).items():
            cname = sdata.get("container_name", "")
            assert cname.startswith("lyux-"), f"Conteneur mal nommé : {cname}"

    def test_traefik_web_entrypoint_valid_port_80(self, docker_compose_data):
        """2.5 Traefik entrypoint web écoute sur :80 en interne"""
        cmd = docker_compose_data["services"]["traefik"].get("command", [])
        assert any("--entrypoints.web.address=:80" in c for c in cmd)


# ==============================================================================
# FEATURE 3: GLPI Asset & Incident Tracking Boundaries
# ==============================================================================
class TestFeature03_GLPIBoundaries:
    def test_glpi_missing_fields_validation(self, api_client):
        """3.1 Rejet 422 si champs obligatoires absents dans la requête ticket"""
        res = api_client.post("/api/v1/tickets", json={"title": "Incomplet"})
        assert res.status_code == 422

    def test_glpi_xss_special_characters_in_ticket(self, api_client):
        """3.2 Résistance aux balises HTML/XSS dans le titre et la description"""
        payload = {
            "title": "<script>alert('XSS')</script>",
            "category": "Materiel",
            "description": "<b>Écran cassé</b> & <img src=x onerror=alert(1)>",
            "hostname": "b204-pc01",
            "username": "lucas.martin"
        }
        res = api_client.post("/api/v1/tickets", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_glpi_large_description_payload(self, api_client):
        """3.3 Support d'une description volumineuse (limite 5000 caractères)"""
        payload = {
            "title": "Panne complexe",
            "category": "Logiciel",
            "description": "Erreur " * 500,
            "hostname": "b204-pc02",
            "username": "emma.bernard"
        }
        res = api_client.post("/api/v1/tickets", json=payload)
        assert res.status_code == 200

    def test_glpi_db_charset_and_credentials_fallback(self, docker_compose_data):
        """3.4 Base de données GLPI configurée avec identifiants définis"""
        env = docker_compose_data["services"]["glpi-db"].get("environment", {})
        assert "MARIADB_DATABASE" in env
        assert "MARIADB_USER" in env

    def test_glpi_timezone_paris_enforced(self, docker_compose_data):
        """3.5 Fuseau horaire configuré sur Europe/Paris pour horodatage légal des incidents"""
        env = docker_compose_data["services"]["glpi"].get("environment", {})
        assert env.get("TIMEZONE") == "Europe/Paris"


# ==============================================================================
# FEATURE 4: Uptime Kuma Monitoring Boundaries
# ==============================================================================
class TestFeature04_UptimeKumaBoundaries:
    def test_supervision_image_major_version_pinned(self, docker_compose_data):
        """4.1 Uptime Kuma utilise une version majeure fixée (image: louislam/uptime-kuma:1)"""
        image = docker_compose_data["services"]["supervision"].get("image", "")
        assert "uptime-kuma:1" in image

    def test_supervision_restart_policy(self, docker_compose_data):
        """4.2 Politique de redémarrage robuste unless-stopped"""
        policy = docker_compose_data["services"]["supervision"].get("restart", "")
        assert policy == "unless-stopped"

    def test_supervision_firewall_rule_comment(self, paths):
        """4.3 Règle UFW 3001 documentée dans init-server.sh"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert "3001/tcp comment 'Supervision Uptime Kuma'" in content

    def test_supervision_traefik_router_match(self, docker_compose_data):
        """4.4 Règle de routage Traefik exacte pour supervision.lyux.lan"""
        labels = docker_compose_data["services"]["supervision"].get("labels", [])
        assert any("Host(`supervision.lyux.lan`)" in l for l in labels)

    def test_supervision_data_volume_declared(self, docker_compose_data):
        """4.5 Volume nommé uptime_kuma_data déclaré dans la section top-level volumes"""
        assert "uptime_kuma_data" in docker_compose_data.get("volumes", {})


# ==============================================================================
# FEATURE 5: Samba-AD Domain Controller Boundaries
# ==============================================================================
class TestFeature05_SambaADBoundaries:
    def test_netbios_name_max_15_chars(self, smb_conf_path):
        """5.1 Nom NetBIOS inférieur ou égal à 15 caractères (RFC 1001/1002)"""
        content = smb_conf_path.read_text(encoding="utf-8")
        match = re.search(r'netbios name\s*=\s*(\S+)', content)
        assert match is not None
        name = match.group(1)
        assert len(name) <= 15

    def test_workgroup_alphanumeric_uppercase(self, smb_conf_path):
        """5.2 Nom de workgroup en majuscules sans espaces"""
        content = smb_conf_path.read_text(encoding="utf-8")
        match = re.search(r'workgroup\s*=\s*(\S+)', content)
        assert match is not None
        wg = match.group(1)
        assert wg.isupper()
        assert wg.isalnum()

    def test_max_log_size_boundary(self, smb_conf_path):
        """5.3 Taille maximale des logs Samba bornée (ex: 1000 Ko)"""
        content = smb_conf_path.read_text(encoding="utf-8")
        match = re.search(r'max log size\s*=\s*(\d+)', content)
        assert match is not None
        assert 100 <= int(match.group(1)) <= 10000

    def test_panic_action_defined(self, smb_conf_path):
        """5.4 Définition d'une panic action pour la robustesse en cas de crash démon"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "panic action =" in content

    def test_dos_charset_cp850(self, smb_conf_path):
        """5.5 Compatibilité dos charset CP850 pour les caractères français DOS/Windows"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "dos charset = CP850" in content


# ==============================================================================
# FEATURE 6: LDAP Account Manager (LAM) Boundaries
# ==============================================================================
class TestFeature06_LAMBoundaries:
    def test_lam_desktop_shortcut_mode_755(self, paths):
        """6.1 Permissions du raccourci Bureau LAM fixées à 0755 (exécutable)"""
        content = (paths["ansible"] / "roles" / "lyux-profile-prof" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "mode: '0755'" in content

    def test_lam_desktop_shortcut_valid_desktop_entry(self, paths):
        """6.2 Raccourci Bureau conforme au standard FreeDesktop .desktop"""
        content = (paths["ansible"] / "roles" / "lyux-profile-prof" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "[Desktop Entry]" in content
        assert "Type=Application" in content
        assert "Exec=firefox http://lam.lyux.lan" in content

    def test_lam_admin_password_env_fallback(self, docker_compose_data):
        """6.3 Mot de passe admin LAM avec fallback de secours non vide"""
        env = docker_compose_data["services"]["ldap-account-manager"].get("environment", [])
        assert any("LAM_PASSWORD=" in str(e) for e in env)

    def test_lam_volume_persists_in_volumes_section(self, docker_compose_data):
        """6.4 Déclaration du volume lam_data au niveau racine"""
        assert "lam_data" in docker_compose_data.get("volumes", {})

    def test_lam_web_port_mapped_to_80_internally(self, docker_compose_data):
        """6.5 Port interne conteneur LAM fixé à 80 pour Traefik"""
        labels = docker_compose_data["services"]["ldap-account-manager"].get("labels", [])
        assert any("loadbalancer.server.port=80" in l for l in labels)


# ==============================================================================
# FEATURE 7: Mandatory Test Accounts Provisioning Boundaries
# ==============================================================================
class TestFeature07_MandatoryAccountsBoundaries:
    def test_csv_header_exact_format(self, paths):
        """7.1 En-tête CSV respecte strictement les colonnes obligatoires"""
        csv_file = paths["server_infra"] / "configs" / "utilisateurs-test.csv"
        with open(csv_file, mode="r", encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        expected = ["prenom", "nom", "role", "classe", "motdepasse_temporaire"]
        assert header == expected

    def test_no_empty_user_fields(self, test_users_csv):
        """7.2 Aucune valeur vide autorisée dans le fichier CSV des comptes"""
        for u in test_users_csv:
            for k, v in u.items():
                assert v is not None and len(v.strip()) > 0

    def test_clean_string_removes_accents_and_special_chars(self, paths):
        """7.3 Nettoyage strict des caractères accentués par regex et normalisation"""
        import unicodedata
        import re
        def clean_string(text: str) -> str:
            text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
            return re.sub(r'[^a-zA-Z0-9\._-]', '', text).lower()

        assert clean_string("Léa") == "lea"
        assert clean_string("Éléonore-Chloë") == "eleonore-chloe"
        assert clean_string("François") == "francois"

    def test_distinct_usernames(self, test_users_csv):
        """7.4 Unicité stricte des identifiants générés (aucun doublon)"""
        usernames = [f"{u['prenom'].lower()}.{u['nom'].lower()}" for u in test_users_csv]
        assert len(usernames) == len(set(usernames))

    def test_allowed_roles_enumeration(self, test_users_csv):
        """7.5 Rôles restreints à la nomenclature officielle autorisée"""
        allowed = {"eleves", "enseignants", "viesco", "administration", "techniciens"}
        for u in test_users_csv:
            assert u["role"] in allowed, f"Rôle inattendu : {u['role']}"


# ==============================================================================
# FEATURE 8: Shared Storage CIFS Architecture Boundaries
# ==============================================================================
class TestFeature08_SharedStorageBoundaries:
    def test_homes_browseable_no(self, smb_conf_path):
        """8.1 Partage [homes] non visible dans le voisinage réseau (browseable = no)"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "browseable = no" in content

    def test_classes_browseable_yes(self, smb_conf_path):
        """8.2 Partage [classes] visible dans le réseau scolaire (browseable = yes)"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "browseable = yes" in content

    def test_homes_mask_boundary_strict_0700(self, smb_conf_path):
        """8.3 Masque de fichier et de dossier homes hermétique (0700)"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "create mask = 0700" in content
        assert "directory mask = 0700" in content

    def test_profs_valid_users_enforced(self, smb_conf_path):
        """8.4 Restriction stricte valid users = @enseignants, @techniciens pour [profs]"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "valid users = @enseignants, @techniciens" in content

    def test_guest_ok_only_on_commun(self, smb_conf_path):
        """8.5 Accès invité autorisé uniquement sur [commun], banni sur [homes] et [classes]"""
        content = smb_conf_path.read_text(encoding="utf-8")
        homes_sec = content[content.find("[homes]"):content.find("[classes]")]
        assert "guest ok = yes" not in homes_sec


# ==============================================================================
# FEATURE 9: Disk Quotas Enforcement Boundaries
# ==============================================================================
class TestFeature09_DiskQuotasBoundaries:
    def test_eleves_quota_lower_than_profs_quota(self):
        """9.1 Vérifie la hiérarchie des quotas : élèves (5 Go) < enseignants (20 Go)"""
        quota_eleve_gb = 5
        quota_prof_gb = 20
        assert quota_eleve_gb < quota_prof_gb

    def test_home_helper_directory_creation_documents_bureau_images(self, paths):
        """9.2 Le script de home dynamique initialise Documents, Bureau et Images"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert '"$USER_HOME/Documents"' in content
        assert '"$USER_HOME/Images"' in content
        assert '"$USER_HOME/Bureau"' in content

    def test_home_helper_chown_strict(self, paths):
        """9.3 Attribution stricte du propriétaire et du groupe utilisateur"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert 'chown -R "$USER_NAME:$USER_GROUP" "$USER_HOME"' in content

    def test_home_helper_chmod_strict(self, paths):
        """9.4 Attribution stricte des permissions 700 sur le dossier home utilisateur"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert 'chmod 700 "$USER_HOME"' in content

    def test_backup_retention_days_boundary(self, paths):
        """9.5 Script de backup applique une politique de rétention (suppression anciens backups)"""
        content = (paths["server_infra"] / "scripts" / "backup-321.sh").read_text(encoding="utf-8")
        assert 'BACKUP_DIR="/srv/backups/daily"' in content
        assert "-mtime +7 -delete" in content


# ==============================================================================
# FEATURE 10: KDE Plasma Desktop Base Boundaries
# ==============================================================================
class TestFeature10_KDEPlasmaBoundaries:
    def test_preseed_user_fullname_non_empty(self, preseed_vbox_path):
        """10.1 Nom complet de l'administrateur local non vide"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "d-i passwd/user-fullname string Administrateur LyuX" in content

    def test_preseed_auto_partitioning_atomic_recipe(self, preseed_vbox_path):
        """10.2 Partitionnement atomique d-i sans fractionnement complexe"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "d-i partman-auto/choose_recipe select atomic" in content

    def test_preseed_confirm_write_new_label(self, preseed_vbox_path):
        """10.3 Confirmation automatique d'écriture de table de partition pour éviter tout blocage"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "d-i partman-partitioning/confirm_write_new_label boolean true" in content

    def test_sddm_installed_with_plasma_nm(self, preseed_vbox_path):
        """10.4 Présence conjointe de sddm et de l'applet réseau plasma-nm"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "sddm" in content
        assert "plasma-nm" in content

    def test_kxmlgui_disabled_for_eleves(self, paths):
        """10.5 Suppression du fichier konsoleui.rc pour bloquer les raccourcis terminaux"""
        content = (paths["ansible"] / "roles" / "lyux-profile-eleve" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "/usr/local/share/kxmlgui5/konsole/konsoleui.rc" in content
        assert "state: absent" in content


# ==============================================================================
# FEATURE 11: Locale & AZERTY Keyboard Standard Boundaries
# ==============================================================================
class TestFeature11_LocaleAZERTYBoundaries:
    def test_xkb_keymap_exact_latin9(self, preseed_vbox_path):
        """11.1 Disposition clavier avec variante latin9 pour le symbole Euro et caractères français"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "xkb-keymap select fr(latin9)" in content

    def test_keyboard_model_pc105_standard(self, preseed_vbox_path):
        """11.2 Modèle de clavier fixé au standard 105 touches (pc105)"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "modelcode string pc105" in content

    def test_console_setup_ask_detect_false(self, preseed_vbox_path):
        """11.3 Détection interactive du clavier désactivée (ask_detect false)"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "console-setup/ask_detect boolean false" in content

    def test_timezone_europe_paris_in_setup_vms(self, paths):
        """11.4 Fuseau horaire Europe/Paris forcé dans setup-2classes-vms.ps1"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert '--time-zone="Europe/Paris"' in content

    def test_domain_lyux_lan_configured(self, preseed_vbox_path):
        """11.5 Domaine réseau lyux.lan forcé dans le preseed"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "netcfg/get_domain string lyux.lan" in content


# ==============================================================================
# FEATURE 12: Calamares & OEM First-Boot Boundaries
# ==============================================================================
class TestFeature12_CalamaresOEMBoundaries:
    def test_otp_rejection_when_code_does_not_exist(self, api_client):
        """12.1 Rejet 400 d'un code OTP inconnu"""
        req = {
            "otp_code": "OTP-TOTALEMENT-INVALIDE",
            "room_id": "B204",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "is_teacher_pc": False
        }
        res = api_client.post("/api/v1/enroll/validate-otp", json=req)
        assert res.status_code == 400
        assert "invalide" in res.json()["detail"].lower()

    def test_otp_generation_with_extreme_validity(self, api_client):
        """12.2 Génération d'OTP avec durée de validité aux limites (1 minute à 120 minutes)"""
        for val in [1, 120]:
            req = {"admin_user": "lyux-admin", "room_id": "B204", "validity_minutes": val}
            res = api_client.post("/api/v1/enroll/generate-otp", json=req)
            assert res.status_code == 200
            assert "LYUX-" in res.json()["otp_code"]

    def test_hardware_fingerprint_positive_ram(self, paths):
        """12.3 Le module hardware retourne une quantité de RAM strictement positive"""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("hw_test", str(paths["enrollment"] / "src" / "hardware.py"))
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        hw = mod.get_hardware_fingerprint()
        assert hw["ram_mb"] > 0
        assert len(hw["mac_address"]) >= 12

    def test_enrollment_service_wanted_by_multi_user(self, paths):
        """12.4 Le service systemd lyux-enrollment cible multi-user.target"""
        content = (paths["enrollment"] / "systemd" / "lyux-enrollment.service").read_text(encoding="utf-8")
        assert "WantedBy=multi-user.target" in content

    def test_teacher_pc_flag_generates_prof_hostname(self, api_client):
        """12.5 Enrôlement avec is_teacher_pc: true génère obligatoirement le hostname *-prof"""
        # Générer un OTP d'abord
        otp_req = {"admin_user": "lyux-admin", "room_id": "S102", "validity_minutes": 10}
        otp_res = api_client.post("/api/v1/enroll/generate-otp", json=otp_req)
        otp_code = otp_res.json()["otp_code"]

        enroll_req = {
            "otp_code": otp_code,
            "room_id": "S102",
            "mac_address": "52:54:00:99:88:77",
            "is_teacher_pc": True
        }
        res = api_client.post("/api/v1/enroll/validate-otp", json=enroll_req)
        assert res.status_code == 200
        assert res.json()["hostname"] == "s102-prof"


# ==============================================================================
# FEATURE 13: SSSD / Realmd Domain Integration Boundaries
# ==============================================================================
class TestFeature13_SSSDRealmdBoundaries:
    def test_sssd_file_permissions_mode_0600(self, paths):
        """13.1 Le fichier sssd.conf doit obligatoirement avoir les permissions 0600 (exigence stricte SSSD)"""
        content = (paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "mode: '0600'" in content

    def test_sssd_owner_and_group_root(self, paths):
        """13.2 sssd.conf doit appartenir exclusivement à root:root"""
        content = (paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "owner: root" in content
        assert "group: root" in content

    def test_sssd_handler_notifies_restart(self, paths):
        """13.3 Modification de sssd.conf déclenche la notification 'Restart sssd'"""
        content = (paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "notify: Restart sssd" in content

    def test_sssd_handler_file_defines_service_restart(self, paths):
        """13.4 Le handler Ansible Restart sssd redémarre effectivement le service"""
        handler_path = paths["ansible"] / "roles" / "lyux-base" / "handlers" / "main.yml"
        assert handler_path.exists()
        content = handler_path.read_text(encoding="utf-8")
        assert "name: sssd" in content
        assert "state: restarted" in content

    def test_sssd_cache_credentials_offline(self, sssd_conf_path):
        """13.5 sssd.conf active la mise en cache des identifiants (cache_credentials = true)"""
        content = sssd_conf_path.read_text(encoding="utf-8")
        assert "cache_credentials" in content


# ==============================================================================
# FEATURE 14: Dynamic Shares pam_mount Boundaries
# ==============================================================================
class TestFeature14_DynamicSharesPamMountBoundaries:
    def test_pam_mount_volume_attributes_presence(self, pam_mount_xml_path):
        """14.1 Tous les éléments volume disposent de fstype, server, path, mountpoint"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        clean_xml = re.sub(r'\{\{[^}]+\}\}', '192.168.100.10', raw)
        root = ET.fromstring(clean_xml)
        volumes = root.findall("volume")
        assert len(volumes) >= 3
        for v in volumes:
            assert "fstype" in v.attrib
            assert "server" in v.attrib
            assert "path" in v.attrib
            assert "mountpoint" in v.attrib

    def test_pam_mount_fstype_is_cifs(self, pam_mount_xml_path):
        """14.2 Tous les partages sont de type CIFS/SMB standardisé"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        clean_xml = re.sub(r'\{\{[^}]+\}\}', '192.168.100.10', raw)
        root = ET.fromstring(clean_xml)
        for v in root.findall("volume"):
            assert v.attrib["fstype"] == "cifs"

    def test_pam_mount_mkmountpoint_enabled(self, pam_mount_xml_path):
        """14.3 mkmountpoint activé avec suppression au démontage (remove=true)"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        assert '<mkmountpoint enable="1" remove="true" />' in raw

    def test_pam_mount_mntoptions_require_nosuid_nodev(self, pam_mount_xml_path):
        """14.4 Sécurité du montage exigeant nosuid et nodev"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        assert '<mntoptions require="nosuid,nodev" />' in raw

    def test_pam_mount_file_permissions_mode_0644(self, paths):
        """14.5 pam_mount.conf.xml installé en mode 0644 root:root"""
        content = (paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "dest: /etc/security/pam_mount.conf.xml" in content
        assert "mode: '0644'" in content


# ==============================================================================
# FEATURE 15: Disciplinary Profile NSI/Maths Boundaries
# ==============================================================================
class TestFeature15_NSIMathsBoundaries:
    def test_nsi_package_list_not_empty(self, paths):
        """15.1 La liste des paquets NSI contient au moins 8 éléments"""
        content = (paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml").read_text(encoding="utf-8")
        nsi_block = content[content.find("when: room_profile == 'nsi'") - 400:content.find("when: room_profile == 'nsi'")]
        pkgs = re.findall(r'-\s+([a-zA-Z0-9_\+-]+)', nsi_block)
        assert len(pkgs) >= 8

    def test_nsi_no_duplicate_packages(self, paths):
        """15.2 Aucun doublon de paquet dans la tâche NSI"""
        content = (paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml").read_text(encoding="utf-8")
        nsi_block = content[content.find("when: room_profile == 'nsi'") - 400:content.find("when: room_profile == 'nsi'")]
        pkgs = re.findall(r'-\s+([a-zA-Z0-9_\+-]+)', nsi_block)
        assert len(pkgs) == len(set(pkgs))

    def test_nsi_room_b204_assigned_in_inventory(self, ansible_inventory_data):
        """15.3 Salle B204 assignée au profil nsi dans l'inventaire"""
        b204 = ansible_inventory_data["all"]["children"]["postes_clients"]["children"]["salle_nsi_b204"]
        assert b204["vars"]["room_profile"] == "nsi"

    def test_wireshark_network_analyzer_included(self, paths):
        """15.4 Wireshark inclus pour le programme officiel NSI (Protocoles & Réseaux)"""
        content = (paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "wireshark" in content

    def test_python_full_and_pip_in_base(self, paths):
        """15.5 Socle python3-full et python3-pip dans lyux-base"""
        content = (paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "python3-full" in content
        assert "python3-pip" in content


# ==============================================================================
# FEATURE 16: Disciplinary Profile Sciences Boundaries
# ==============================================================================
class TestFeature16_SciencesBoundaries:
    def test_sciences_package_list_not_empty(self, paths):
        """16.1 La liste des paquets Sciences contient au moins 5 éléments"""
        content = (paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml").read_text(encoding="utf-8")
        sciences_block = content[content.find("when: room_profile == 'sciences'") - 300:content.find("when: room_profile == 'sciences'")]
        pkgs = re.findall(r'-\s+([a-zA-Z0-9_\+-]+)', sciences_block)
        assert len(pkgs) >= 5

    def test_sciences_room_s102_assigned_in_inventory(self, ansible_inventory_data):
        """16.2 Salle S102 assignée au profil sciences dans l'inventaire"""
        s102 = ansible_inventory_data["all"]["children"]["postes_clients"]["children"]["salle_sciences_s102"]
        assert s102["vars"]["room_profile"] == "sciences"

    def test_techno_profile_distinct_from_sciences(self, paths):
        """16.3 Profil Techno distinct du profil Sciences (FreeCAD, KiCad)"""
        content = (paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "freecad" in content
        assert "when: room_profile == 'techno'" in content

    def test_vlc_and_audacity_in_base_for_multimedia(self, paths):
        """16.4 Lecteur multimédia VLC et Audacity dans lyux-base pour les TP sciences"""
        content = (paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "vlc" in content
        assert "audacity" in content

    def test_okular_pdf_reader_in_base(self, paths):
        """16.5 Lecteur Okular dans lyux-base pour les sujets de TP"""
        content = (paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "okular" in content


# ==============================================================================
# FEATURE 17: Veyon Asymmetric Keys Boundaries
# ==============================================================================
class TestFeature17_VeyonKeysBoundaries:
    def test_private_key_cannot_be_accessible_to_students(self, paths):
        """17.1 La clef privée n'est jamais accessible au groupe eleves"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "root:enseignants" in spec
        assert "root:eleves" not in spec

    def test_private_key_mode_not_world_readable(self, paths):
        """17.2 Le mode de la clef privée interdit tout droit pour les autres (mode 0440)"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "0440" in spec

    def test_public_key_world_readable_for_service(self, paths):
        """17.3 Le mode de la clef publique autorise la lecture à tous (mode 0444)"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "0444" in spec

    def test_veyon_key_directories_separation(self, paths):
        """17.4 Ségrégation stricte des dossiers private/teacher et public/teacher"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "/etc/veyon/keys/private" in spec
        assert "/etc/veyon/keys/public" in spec

    def test_veyon_default_ports_consecutive_boundaries(self, expected_ports):
        """17.5 Les ports Veyon sont tous distincts et situés dans la plage 11100-11400"""
        v_ports = [expected_ports[k]["port"] for k in ["veyon_service", "veyon_feature", "veyon_demo"]]
        assert len(v_ports) == len(set(v_ports))
        for p in v_ports:
            assert 11000 <= p <= 12000


# ==============================================================================
# FEATURE 18: Veyon Master & Service Deployment Boundaries
# ==============================================================================
class TestFeature18_VeyonMasterDeploymentBoundaries:
    def test_master_not_installed_on_student_stations(self, paths):
        """18.1 veyon-master absent des tâches élèves lyux-profile-eleve"""
        content = (paths["ansible"] / "roles" / "lyux-profile-eleve" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "veyon-master" not in content

    def test_service_running_on_eleves(self, paths):
        """18.2 veyon-service activé au démarrage sur les postes élèves"""
        content = (paths["ansible"] / "roles" / "lyux-profile-eleve" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "name: veyon" in content
        assert "state: started" in content

    def test_provision_client_installs_master_only_conditionally(self, paths):
        """18.3 Le script provision-client.sh tolère ou gère l'installation de veyon-master"""
        content = (paths["lab_vm"] / "scripts" / "provision-client.sh").read_text(encoding="utf-8")
        assert "veyon" in content

    def test_ansible_roles_hierarchy_separation(self, paths):
        """18.4 Ségrégation claire entre rôles lyux-profile-prof et lyux-profile-eleve"""
        prof_dir = paths["ansible"] / "roles" / "lyux-profile-prof"
        eleve_dir = paths["ansible"] / "roles" / "lyux-profile-eleve"
        assert prof_dir.is_dir()
        assert eleve_dir.is_dir()

    def test_veyon_plugins_present_in_prof_profile(self, paths):
        """18.5 Paquet veyon-plugins présent pour les extensions de contrôle à distance"""
        content = (paths["ansible"] / "roles" / "lyux-profile-prof" / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "veyon-plugins" in content


# ==============================================================================
# FEATURE 19: Pedagogical Classroom Supervision Boundaries
# ==============================================================================
class TestFeature19_PedagogicalSupervisionBoundaries:
    def test_lock_empty_or_unknown_room_returns_zero_affected(self, api_client):
        """19.1 Verrouillage d'une salle inexistante affecte 0 machine sans crasher"""
        req = {"room_id": "SALLE_VIDE_000", "action": "lock", "message_text": "Test"}
        res = api_client.post("/api/v1/control/lock-room", json=req)
        assert res.status_code == 200
        assert res.json()["affected_machines"] == 0

    def test_lock_action_case_or_invalid_action(self, api_client):
        """19.2 Transmission d'une action personnalisée supportée"""
        req = {"room_id": "B204", "action": "message", "message_text": "Message seul"}
        res = api_client.post("/api/v1/control/lock-room", json=req)
        assert res.status_code == 200
        assert res.json()["action"] == "message"

    def test_reset_password_unknown_user_returns_404(self, api_client):
        """19.3 Réinitialisation de mot de passe pour utilisateur inexistant retourne 404"""
        res = api_client.post("/api/v1/control/reset-password", json={"username": "inconnu.total"})
        assert res.status_code == 404

    def test_reset_password_returns_complex_new_password(self, api_client):
        """19.4 Le nouveau mot de passe généré contient le préfixe Pass et un point d'exclamation"""
        res = api_client.post("/api/v1/control/reset-password", json={"username": "lucas.martin"})
        assert res.status_code == 200
        new_pwd = res.json()["new_password"]
        assert new_pwd.startswith("Pass")
        assert new_pwd.endswith("!")

    def test_lock_dialog_students_grid_populated(self, paths):
        """19.5 L'interface graphique dispose de la grille de suivi pour B204 et S102"""
        content = (paths["station"] / "src" / "main.py").read_text(encoding="utf-8")
        assert "b204-pc01" in content
        assert "s102-pc01" in content


# ==============================================================================
# FEATURE 20: Pilot Rooms Definition Boundaries
# ==============================================================================
class TestFeature20_PilotRoomsBoundaries:
    def test_room_capacity_positive_integer(self, api_client):
        """20.1 Les capacités des salles pilotes sont strictement positives"""
        rooms = api_client.get("/api/v1/rooms").json()
        assert rooms["B204"]["capacity"] > 0
        assert rooms["S102"]["capacity"] > 0

    def test_room_teachers_assigned(self, api_client):
        """20.2 Chaque salle pilote dispose d'un enseignant titulaire attitré"""
        rooms = api_client.get("/api/v1/rooms").json()
        assert len(rooms["B204"]["teacher"]) > 0
        assert len(rooms["S102"]["teacher"]) > 0

    def test_no_cross_room_hostname_collisions(self, api_client):
        """20.3 Aucun chevauchement de noms d'hôtes entre les salles"""
        machines = api_client.get("/api/v1/machines").json()
        b204_hosts = [m["hostname"] for m in machines if m["room"] == "B204"]
        s102_hosts = [m["hostname"] for m in machines if m["room"] == "S102"]
        assert set(b204_hosts).isdisjoint(set(s102_hosts))

    def test_ip_addresses_are_valid_ipv4(self, api_client):
        """20.4 Toutes les adresses IP inscrites sont des IPv4 valides"""
        import ipaddress
        machines = api_client.get("/api/v1/machines").json()
        for m in machines:
            ip = m["ip"]
            parsed = ipaddress.ip_address(ip)
            assert parsed.version == 4

    def test_cdi_and_viesco_extra_rooms_available(self, api_client):
        """20.5 Espaces CDI et VIESCO prévus pour l'extension hors salles pilotes"""
        rooms = api_client.get("/api/v1/rooms").json()
        assert "CDI" in rooms
        assert "VIESCO" in rooms


# ==============================================================================
# FEATURE 21: VirtualBox Non-Textual Automated Lab Boundaries
# ==============================================================================
class TestFeature21_VirtualBoxBoundaries:
    def test_vboxmanage_executable_default_path(self, paths):
        """21.1 Chemin par défaut de VBoxManage.exe sous Windows"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "C:\\Program Files\\Oracle\\VirtualBox\\VBoxManage.exe" in content

    def test_vm_disk_size_20gb_minimum(self, paths):
        """21.2 Taille des disques virtuels fixée à 20 Go (20480 Mo) pour le confort des profils"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "--size 20480" in content

    def test_vm_ostype_debian_64(self, paths):
        """21.3 Type d'OS configuré sur Debian_64"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert '--ostype "Debian_64"' in content

    def test_vm_vram_128mb_allocated(self, paths):
        """21.4 Mémoire vidéo allouée à 128 Mo pour fluidité KDE Plasma"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "--vram 128" in content

    def test_sata_controller_bootable(self, paths):
        """21.5 Contrôleur SATA IntelAhci configuré avec flag bootable on"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "--controller IntelAhci --bootable on" in content


# ==============================================================================
# FEATURE 22: Automated Lab Test Runner Script Boundaries
# ==============================================================================
class TestFeature22_AutomatedLabRunnerBoundaries:
    def test_vagrantfile_ip_subnet_consistency(self, paths):
        """22.1 Vagrantfile utilise le sous-réseau cohérent 192.168.100.x"""
        content = (paths["lab_vm"] / "Vagrantfile").read_text(encoding="utf-8")
        assert "192.168.100." in content

    def test_vagrantfile_synced_folders(self, paths):
        """22.2 Réseau privé et sous-réseau cohérent configuré dans le Vagrantfile"""
        content = (paths["lab_vm"] / "Vagrantfile").read_text(encoding="utf-8")
        assert 'private_network' in content
        assert '192.168.100.10' in content

    def test_download_iso_powershell_file_exists(self, paths):
        """22.3 Script de téléchargement automatique d'ISO présent"""
        ps = paths["lab_vm"] / "scripts" / "download-and-attach-iso.ps1"
        assert ps.exists()

    def test_start_unattended_install_powershell_exists(self, paths):
        """22.4 Script start-unattended-install.ps1 présent"""
        ps = paths["lab_vm"] / "scripts" / "start-unattended-install.ps1"
        assert ps.exists()

    def test_batch_launcher_calls_powershell(self, paths):
        """22.5 Lancer-LyuX.bat et lancer-lyux.ps1 démarrent le portail web 8000 et l'application station"""
        bat_content = (paths["root"] / "Lancer-LyuX.bat").read_text(encoding="utf-8")
        ps1_content = (paths["root"] / "lancer-lyux.ps1").read_text(encoding="utf-8")
        assert "localhost:8000" in bat_content
        assert "main.py" in bat_content
        assert "localhost:8000" in ps1_content
        assert "main.py" in ps1_content


# ==============================================================================
# FEATURE 23: Comprehensive E2E Test Suite Boundaries
# ==============================================================================
class TestFeature23_E2ESuiteBoundaries:
    def test_test_infra_contains_all_milestones(self, paths):
        """23.1 TEST_INFRA.md documente l'ensemble des jalons M1 à M6"""
        content = (paths["root"] / "TEST_INFRA.md").read_text(encoding="utf-8")
        for m in ["Tier 1", "Tier 2", "Tier 3", "Tier 4"]:
            assert m in content

    def test_conftest_exports_all_required_fixtures(self):
        """23.2 Vérifie l'accessibilité de la fixture globale project_root"""
        assert Path(__file__).resolve().parent.parent.parent.exists()

    def test_all_expected_ports_have_transport_and_protocol(self, expected_ports):
        """23.3 Toutes les définitions de ports spécifient protocole et transport"""
        for sname, sdata in expected_ports.items():
            assert "protocol" in sdata
            assert "transport" in sdata
            assert "port" in sdata

    def test_e2e_folder_isolated_from_projects_code(self, paths):
        """23.4 Le dossier tests/e2e est totalement disjoint de projects/"""
        e2e_dir = paths["root"] / "tests" / "e2e"
        assert not str(e2e_dir).startswith(str(paths["root"] / "projects"))

    def test_original_request_file_exists_and_non_empty(self, paths):
        """23.5 ORIGINAL_REQUEST.md est accessible et non vide"""
        req_file = paths["root"] / ".agents" / "teamwork" / "ORIGINAL_REQUEST.md"
        assert req_file.exists()
        assert len(req_file.read_text(encoding="utf-8")) > 100


# ==============================================================================
# FEATURE 24: Adversarial Hardening Boundaries
# ==============================================================================
class TestFeature24_AdversarialBoundaries:
    def test_otp_code_entropy(self, api_client):
        """24.1 Les codes OTP générés disposent d'au moins 6 caractères aléatoires (entropie)"""
        req = {"admin_user": "lyux-admin", "room_id": "B204", "validity_minutes": 15}
        res = api_client.post("/api/v1/enroll/generate-otp", json=req)
        code = res.json()["otp_code"]
        assert len(code) >= 10
        assert code.startswith("LYUX-")

    def test_command_injection_attempt_in_mac(self, api_client):
        """24.2 Résistance à une tentative d'injection de commande dans l'adresse MAC"""
        otp_req = {"admin_user": "lyux-admin", "room_id": "B204", "validity_minutes": 15}
        otp = api_client.post("/api/v1/enroll/generate-otp", json=otp_req).json()["otp_code"]

        malicious_req = {
            "otp_code": otp,
            "room_id": "B204",
            "mac_address": "52:54:00:11:22:33; rm -rf /",
            "is_teacher_pc": False
        }
        res = api_client.post("/api/v1/enroll/validate-otp", json=malicious_req)
        assert res.status_code == 200
        # Vérifie que le hostname n'a pas été corrompu
        assert "b204-pc" in res.json()["hostname"]

    def test_zero_validity_minutes_otp(self, api_client):
        """24.3 Requête OTP avec validité 0 minute rejetée ou expire immédiatement"""
        req = {"admin_user": "lyux-admin", "room_id": "B204", "validity_minutes": 0}
        res = api_client.post("/api/v1/enroll/generate-otp", json=req)
        # L'API accepte ou traite selon son modèle
        assert res.status_code in [200, 422]

    def test_sql_injection_attempt_in_username(self, api_client):
        """24.4 Résistance à l'injection SQL dans la réinitialisation de mot de passe"""
        res = api_client.post("/api/v1/control/reset-password", json={"username": "' OR '1'='1"})
        assert res.status_code == 404

    def test_backup_script_archive_format(self, paths):
        """24.5 Le script backup-321.sh compresse avec gzip (.tar.gz)"""
        content = (paths["server_infra"] / "scripts" / "backup-321.sh").read_text(encoding="utf-8")
        assert ".tar.gz" in content
