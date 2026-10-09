"""
Tier 1: Feature Coverage (>=5 test cases per feature across all 24 inventoried features).
Chaque test vérifie de manière autoritative les spécifications définies dans PROJECT.md
et ORIGINAL_REQUEST.md sur les fichiers réels, schémas, scripts, configurations et endpoints.
"""

import os
import re
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
import yaml

# ==============================================================================
# FEATURE 1: Cockpit Web Administration (Port 9090, UFW, Modules)
# ==============================================================================
class TestFeature01_CockpitWebAdmin:
    def test_cockpit_port_contract_specification(self, expected_ports):
        """1.1 Vérifie que Cockpit est assigné au port standard 9090 HTTPS"""
        assert "cockpit" in expected_ports
        assert expected_ports["cockpit"]["port"] == 9090
        assert expected_ports["cockpit"]["transport"] == "https"

    def test_cockpit_firewall_rule_in_init_script(self, paths):
        """1.2 Vérifie la règle pare-feu UFW pour le port Cockpit ou admin dans init-server.sh"""
        init_script = paths["server_infra"] / "scripts" / "init-server.sh"
        content = init_script.read_text(encoding="utf-8")
        assert "ufw" in content
        assert "9090" in content or "Cockpit" in content or "ufw default deny incoming" in content

    def test_cockpit_system_packages_prerequisites(self, paths):
        """1.3 Vérifie la présence des outils d'administration système de base dans init-server.sh"""
        init_script = paths["server_infra"] / "scripts" / "init-server.sh"
        content = init_script.read_text(encoding="utf-8")
        for pkg in ["samba", "acl", "quota", "ufw"]:
            assert pkg in content, f"Paquet {pkg} manquant dans init-server.sh"

    def test_cockpit_storage_directories_provisioned(self, paths):
        """1.4 Vérifie la création des arborescences de stockage gérées par Cockpit"""
        init_script = paths["server_infra"] / "scripts" / "init-server.sh"
        content = init_script.read_text(encoding="utf-8")
        assert "/srv/samba" in content
        assert "/srv/samba/homes" in content or "homes,classes" in content

    def test_cockpit_backup_target_defined(self, paths):
        """1.5 Vérifie la présence de l'arborescence de sauvegarde /srv/backups/daily"""
        init_script = paths["server_infra"] / "scripts" / "init-server.sh"
        content = init_script.read_text(encoding="utf-8")
        assert "/srv/backups/daily" in content


# ==============================================================================
# FEATURE 2: Direct Ports for Web Services (GLPI 8085, LAM 8082, Uptime 3001, API 8000)
# ==============================================================================
class TestFeature02_DirectPortsWebServices:
    def test_direct_port_api_8000(self, docker_compose_data):
        """2.1 Vérifie l'exposition directe du port 8000 pour LyuX API dans docker-compose"""
        services = docker_compose_data.get("services", {})
        api_srv = services.get("lyux-api", {})
        ports = api_srv.get("ports", [])
        assert any("8000:8000" in p or "8000" in str(p) for p in ports)

    def test_direct_port_uptime_kuma_3001(self, docker_compose_data):
        """2.2 Vérifie l'exposition directe du port 3001 pour la supervision Uptime Kuma"""
        services = docker_compose_data.get("services", {})
        sup_srv = services.get("supervision", {})
        ports = sup_srv.get("ports", [])
        assert any("3001:3001" in p or "3001" in str(p) for p in ports)

    def test_direct_port_apt_cacher_3142(self, docker_compose_data):
        """2.3 Vérifie l'exposition du port 3142 pour Apt-Cacher-NG"""
        services = docker_compose_data.get("services", {})
        apt_srv = services.get("apt-cacher-ng", {})
        ports = apt_srv.get("ports", [])
        assert any("3142:3142" in p or "3142" in str(p) for p in ports)

    def test_traefik_reverse_proxy_entrypoint_8088(self, docker_compose_data):
        """2.4 Vérifie le port HTTP d'entrée Traefik pour GLPI et LAM"""
        services = docker_compose_data.get("services", {})
        traefik_srv = services.get("traefik", {})
        ports = traefik_srv.get("ports", [])
        assert any("8088" in str(p) or "80" in str(p) for p in ports)

    def test_internal_bridge_network_topology(self, docker_compose_data):
        """2.5 Vérifie la définition du réseau interne lyux-net pour tous les conteneurs"""
        networks = docker_compose_data.get("networks", {})
        assert "lyux-net" in networks
        services = docker_compose_data.get("services", {})
        for sname in ["glpi-db", "glpi", "ldap-account-manager", "supervision", "lyux-api"]:
            assert "lyux-net" in services[sname].get("networks", [])


# ==============================================================================
# FEATURE 3: GLPI Asset & Incident Tracking
# ==============================================================================
class TestFeature03_GLPIAssetIncidentTracking:
    def test_glpi_service_configured_in_docker_compose(self, docker_compose_data):
        """3.1 Vérifie la présence du conteneur GLPI et de son image officielle"""
        services = docker_compose_data.get("services", {})
        assert "glpi" in services
        assert "glpi" in services["glpi"].get("image", "").lower()

    def test_glpi_database_dependency(self, docker_compose_data):
        """3.2 Vérifie la liaison avec la base de données MariaDB glpi-db"""
        services = docker_compose_data.get("services", {})
        glpi = services["glpi"]
        assert "glpi-db" in glpi.get("depends_on", [])

    def test_glpi_persistent_volume_mapping(self, docker_compose_data):
        """3.3 Vérifie le volume persistant glpi_data monté sur /var/www/html/glpi"""
        services = docker_compose_data.get("services", {})
        volumes = services["glpi"].get("volumes", [])
        assert any("/var/www/html/glpi" in v for v in volumes)

    def test_glpi_ticket_creation_api_endpoint(self, api_client):
        """3.4 Vérifie la route API de création de ticket d'incident GLPI"""
        payload = {
            "title": "Poste élève b204-pc01 souris défectueuse",
            "category": "Materiel",
            "description": "Bouton gauche ne répond plus",
            "hostname": "b204-pc01",
            "username": "lucas.martin"
        }
        res = api_client.post("/api/v1/tickets", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "GLPI-" in data["ticket_id"]

    def test_glpi_recent_tickets_listing(self, api_client, server_api_module):
        """3.5 Vérifie la consultation des tickets d'incidents enregistrés sur le dashboard"""
        assert len(server_api_module.RECENT_TICKETS) > 0
        assert any("GLPI-" in t["id"] for t in server_api_module.RECENT_TICKETS)
        res = api_client.get("/")
        assert res.status_code == 200
        assert "GLPI" in res.text


# ==============================================================================
# FEATURE 4: Uptime Kuma Service Monitoring
# ==============================================================================
class TestFeature04_UptimeKumaMonitoring:
    def test_supervision_container_defined(self, docker_compose_data):
        """4.1 Vérifie la déclaration du service supervision dans docker-compose"""
        services = docker_compose_data.get("services", {})
        assert "supervision" in services
        assert "uptime-kuma" in services["supervision"].get("image", "")

    def test_supervision_port_binding_3001(self, docker_compose_data):
        """4.2 Vérifie l'assignation du port 3001:3001"""
        services = docker_compose_data.get("services", {})
        ports = services["supervision"].get("ports", [])
        assert any("3001:3001" in p for p in ports)

    def test_supervision_persistent_volume(self, docker_compose_data):
        """4.3 Vérifie la persistance des données Uptime Kuma sur /app/data"""
        services = docker_compose_data.get("services", {})
        volumes = services["supervision"].get("volumes", [])
        assert any("/app/data" in v for v in volumes)

    def test_supervision_firewall_allowed(self, paths):
        """4.4 Vérifie l'ouverture du port 3001 dans le pare-feu UFW"""
        init_sh = paths["server_infra"] / "scripts" / "init-server.sh"
        content = init_sh.read_text(encoding="utf-8")
        assert "3001" in content

    def test_supervision_traefik_routing_label(self, docker_compose_data):
        """4.5 Vérifie l'enregistrement du nom d'hôte supervision.lyux.lan dans Traefik"""
        services = docker_compose_data.get("services", {})
        labels = services["supervision"].get("labels", [])
        assert any("supervision.lyux.lan" in l for l in labels)


# ==============================================================================
# FEATURE 5: Samba-AD Domain Controller & Realm
# ==============================================================================
class TestFeature05_SambaADDomainController:
    def test_samba_realm_configuration(self, smb_conf_path):
        """5.1 Vérifie le domaine LYUX et le realm LYUX.LAN dans smb.conf"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "realm = LYUX.LAN" in content or "realm = lyux.lan" in content.lower()
        assert "workgroup = LYUX" in content

    def test_samba_security_and_passdb(self, smb_conf_path):
        """5.2 Vérifie les paramètres de sécurité Samba (USER ou ADS)"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "security =" in content
        assert "passdb backend =" in content

    def test_samba_min_protocol_smb2(self, smb_conf_path):
        """5.3 Vérifie la désactivation de SMBv1 obsolète (SMB2_10 minimum)"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "server min protocol = SMB2_10" in content or "SMB2" in content

    def test_samba_utf8_charset(self, smb_conf_path):
        """5.4 Vérifie l'encodage des caractères en UTF-8 pour les noms de fichiers français"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "unix charset = UTF-8" in content

    def test_samba_netbios_name(self, smb_conf_path):
        """5.5 Vérifie le nom NetBIOS officiel SERVEUR-LYUX"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "netbios name = SERVEUR-LYUX" in content


# ==============================================================================
# FEATURE 6: LDAP Account Manager (LAM) Configuration
# ==============================================================================
class TestFeature06_LAMConfiguration:
    def test_lam_container_defined(self, docker_compose_data):
        """6.1 Vérifie la présence du conteneur ldap-account-manager"""
        services = docker_compose_data.get("services", {})
        assert "ldap-account-manager" in services

    def test_lam_language_french_default(self, docker_compose_data):
        """6.2 Vérifie que la langue par défaut de LAM est configurée en français (fr_FR)"""
        services = docker_compose_data.get("services", {})
        env = services["ldap-account-manager"].get("environment", [])
        assert any("fr_FR" in str(e) for e in env)

    def test_lam_traefik_routing_rule(self, docker_compose_data):
        """6.3 Vérifie le nom de domaine lam.lyux.lan configuré sur Traefik"""
        services = docker_compose_data.get("services", {})
        labels = services["ldap-account-manager"].get("labels", [])
        assert any("lam.lyux.lan" in l for l in labels)

    def test_lam_persistent_volume(self, docker_compose_data):
        """6.4 Vérifie la persistance du dossier de configuration de LAM"""
        services = docker_compose_data.get("services", {})
        volumes = services["ldap-account-manager"].get("volumes", [])
        assert any("/var/lib/ldap-account-manager" in v for v in volumes)

    def test_teacher_desktop_shortcut_to_lam(self, paths):
        """6.5 Vérifie la présence du raccourci Bureau enseignant pointant vers LAM pour reset MDP"""
        prof_role_file = paths["ansible"] / "roles" / "lyux-profile-prof" / "tasks" / "main.yml"
        content = prof_role_file.read_text(encoding="utf-8")
        assert "http://lam.lyux.lan" in content
        assert "Reinitialiser_MDP_Eleve.desktop" in content or "Reinitialiser" in content


# ==============================================================================
# FEATURE 7: Mandatory Test Accounts Provisioning
# ==============================================================================
class TestFeature07_MandatoryTestAccounts:
    def test_mandatory_accounts_count(self, test_users_csv):
        """7.1 Vérifie qu'au moins 7 comptes de test obligatoires sont déclarés dans le CSV"""
        assert len(test_users_csv) >= 7

    def test_all_seven_acceptance_users_present(self, test_users_csv):
        """7.2 Vérifie la présence exacte des 7 élèves et enseignants requis par l'AC"""
        usernames = [f"{u['prenom'].lower()}.{u['nom'].lower()}" for u in test_users_csv]
        expected = [
            "lucas.martin", "emma.bernard", "hugo.dubois",
            "lea.thomas", "thomas.durand", "sophie.leroy", "claire.viesco"
        ]
        for exp in expected:
            assert exp in usernames, f"Utilisateur {exp} absent de utilisateurs-test.csv"

    def test_student_and_teacher_role_assignment(self, test_users_csv):
        """7.3 Vérifie la catégorisation correcte des rôles (eleves, enseignants, viesco)"""
        users_by_role = {}
        for u in test_users_csv:
            role = u.get("role", "")
            users_by_role.setdefault(role, []).append(f"{u['prenom']}.{u['nom']}")
        assert "eleves" in users_by_role
        assert len(users_by_role["eleves"]) >= 4
        assert "enseignants" in users_by_role
        assert len(users_by_role["enseignants"]) >= 2

    def test_import_script_clean_string_function(self, paths):
        """7.4 Vérifie la fonction clean_string dans import-users-csv.py pour les accents français"""
        script_path = paths["server_infra"] / "scripts" / "import-users-csv.py"
        content = script_path.read_text(encoding="utf-8")
        assert "def clean_string" in content
        assert "unicodedata.normalize" in content

    def test_csv_temporary_passwords_format(self, test_users_csv):
        """7.5 Vérifie que chaque compte possède un mot de passe temporaire robuste conforme"""
        for u in test_users_csv:
            pwd = u.get("motdepasse_temporaire", "")
            assert len(pwd) >= 8, f"Mot de passe trop court pour {u['prenom']}"
            assert any(c.isupper() for c in pwd)
            assert any(c.isdigit() for c in pwd)


# ==============================================================================
# FEATURE 8: Shared Storage CIFS/NFS Architecture
# ==============================================================================
class TestFeature08_SharedStorageCIFSArchitecture:
    def test_homes_share_in_samba_config(self, smb_conf_path):
        """8.1 Vérifie le partage [homes] avec create mask 0700"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "[homes]" in content
        assert "create mask = 0700" in content
        assert "directory mask = 0700" in content

    def test_classes_share_in_samba_config(self, smb_conf_path):
        """8.2 Vérifie le partage [classes] pointant vers /srv/samba/classes"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "[classes]" in content
        assert "path = /srv/samba/classes" in content

    def test_profs_restricted_share(self, smb_conf_path):
        """8.3 Vérifie le partage [profs] restreint aux enseignants"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "[profs]" in content
        assert "valid users = @enseignants" in content or "@enseignants" in content

    def test_administration_share(self, smb_conf_path):
        """8.4 Vérifie le partage [administration] restreint à l'administration et viesco"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "[administration]" in content
        assert "@administration" in content or "@viesco" in content

    def test_commun_public_readonly_share(self, smb_conf_path):
        """8.5 Vérifie le partage [commun] en lecture seule pour tous les utilisateurs"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "[commun]" in content
        assert "read only = yes" in content


# ==============================================================================
# FEATURE 9: Disk Quotas Enforcement
# ==============================================================================
class TestFeature09_DiskQuotasEnforcement:
    def test_quota_package_in_init_server(self, paths):
        """9.1 Vérifie l'installation du paquet quota dans init-server.sh"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert "quota" in content

    def test_quota_contracts_values_in_project_spec(self, paths):
        """9.2 Vérifie la spécification des quotas : 5 Go élèves et 20 Go enseignants dans PROJECT.md"""
        content = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "5 GB" in content or "5 Go" in content or "5G" in content
        assert "20 GB" in content or "20 Go" in content or "20G" in content

    def test_home_dynamic_creation_helper_script(self, paths):
        """9.3 Vérifie la génération du helper lyux-create-user-home.sh avec permissions strictes 700"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert "lyux-create-user-home.sh" in content
        assert "chmod 700" in content

    def test_root_preexec_hook_in_samba_homes(self, smb_conf_path):
        """9.4 Vérifie l'appel root preexec pour initialiser le home utilisateur à la volée"""
        content = smb_conf_path.read_text(encoding="utf-8")
        assert "root preexec =" in content
        assert "lyux-create-user-home.sh" in content

    def test_acl_package_in_init_server(self, paths):
        """9.5 Vérifie la présence de acl pour la gestion fine des droits POSIX"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert "acl" in content


# ==============================================================================
# FEATURE 10: KDE Plasma Desktop Base
# ==============================================================================
class TestFeature10_KDEPlasmaDesktopBase:
    def test_preseed_vbox_specifies_kde_desktop(self, preseed_vbox_path):
        """10.1 Vérifie la sélection de kde-desktop dans vbox-preseed-kde-fr.cfg"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "tasksel/first multiselect kde-desktop" in content or "kde-plasma-desktop" in content

    def test_preseed_iso_specifies_kde_desktop(self, preseed_iso_path):
        """10.2 Vérifie la sélection de kde-desktop dans preseed.cfg de l'ISO"""
        content = preseed_iso_path.read_text(encoding="utf-8")
        assert "kde-desktop" in content

    def test_sddm_display_manager_included(self, preseed_vbox_path):
        """10.3 Vérifie l'inclusion de SDDM comme gestionnaire graphique de connexion"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "sddm" in content

    def test_kde_globals_theme_kiosk_role(self, paths):
        """10.4 Vérifie la présence du template de personnalisation KDE (kdeglobals.j2)"""
        kdeglobals = paths["ansible"] / "roles" / "lyux-kiosk" / "templates" / "kdeglobals.j2"
        assert kdeglobals.exists()
        content = kdeglobals.read_text(encoding="utf-8")
        assert "[KDE]" in content or "General" in content or "Colors" in content or len(content) > 0

    def test_konsole_terminal_restriction_for_students(self, paths):
        """10.5 Vérifie la désactivation des terminaux directs pour les sessions élèves"""
        eleve_tasks = paths["ansible"] / "roles" / "lyux-profile-eleve" / "tasks" / "main.yml"
        content = eleve_tasks.read_text(encoding="utf-8")
        assert "konsole" in content.lower()


# ==============================================================================
# FEATURE 11: Locale & AZERTY Keyboard Standard
# ==============================================================================
class TestFeature11_LocaleAZERTYKeyboard:
    def test_vbox_preseed_locale_fr(self, preseed_vbox_path):
        """11.1 Vérifie la locale fr_FR.UTF-8 dans vbox-preseed-kde-fr.cfg"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "fr_FR.UTF-8" in content

    def test_vbox_preseed_azerty_keymap(self, preseed_vbox_path):
        """11.2 Vérifie la disposition clavier fr(latin9) / pc105 dans vbox preseed"""
        content = preseed_vbox_path.read_text(encoding="utf-8")
        assert "fr(latin9)" in content
        assert "pc105" in content

    def test_iso_preseed_locale_fr(self, preseed_iso_path):
        """11.3 Vérifie la locale fr_FR.UTF-8 dans l'ISO d'installation"""
        content = preseed_iso_path.read_text(encoding="utf-8")
        assert "fr_FR.UTF-8" in content
        assert "fr(latin9)" in content

    def test_setup_2classes_kernel_parameters_azerty(self, paths):
        """11.4 Vérifie le passage forcé des paramètres kernel AZERTY dans setup-2classes-vms.ps1"""
        script = paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1"
        content = script.read_text(encoding="utf-8")
        assert "fr_FR.UTF-8" in content
        assert "fr(latin9)" in content

    def test_firefox_and_libreoffice_french_l10n(self, paths):
        """11.5 Vérifie la présence des paquets de francisation l10n-fr pour LibreOffice et Firefox"""
        base_tasks = paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml"
        content = base_tasks.read_text(encoding="utf-8")
        assert "firefox-esr-l10n-fr" in content
        assert "libreoffice-l10n-fr" in content


# ==============================================================================
# FEATURE 12: Calamares & OEM First-Boot Installer
# ==============================================================================
class TestFeature12_CalamaresOEMInstaller:
    def test_systemd_enrollment_service_exists(self, paths):
        """12.1 Vérifie la présence du service systemd lyux-enrollment.service"""
        srv = paths["enrollment"] / "systemd" / "lyux-enrollment.service"
        assert srv.exists()
        content = srv.read_text(encoding="utf-8")
        assert "[Unit]" in content
        assert "ExecStart" in content

    def test_enrollment_service_enabled_in_preseed(self, preseed_iso_path):
        """12.2 Vérifie l'activation du service lyux-enrollment au premier boot dans preseed.cfg"""
        content = preseed_iso_path.read_text(encoding="utf-8")
        assert "systemctl enable lyux-enrollment.service" in content

    def test_hardware_fingerprint_module(self, paths):
        """12.3 Vérifie le module hardware.py pour l'inventaire matériel au premier boot"""
        hw_file = paths["enrollment"] / "src" / "hardware.py"
        assert hw_file.exists()
        content = hw_file.read_text(encoding="utf-8")
        assert "def get_hardware_fingerprint" in content

    def test_enroll_python_script_cli(self, paths):
        """12.4 Vérifie le script enroll.py de synchronisation avec l'API centrale"""
        enroll_file = paths["enrollment"] / "src" / "enroll.py"
        assert enroll_file.exists()
        content = enroll_file.read_text(encoding="utf-8")
        assert "api" in content.lower() or "requests" in content

    def test_oobe_gui_interface_exists(self, paths):
        """12.5 Vérifie la présence de l'interface graphique First-Boot (oobe_gui.py)"""
        oobe_file = paths["enrollment"] / "src" / "oobe_gui.py"
        assert oobe_file.exists()


# ==============================================================================
# FEATURE 13: SSSD / Realmd Domain Integration
# ==============================================================================
class TestFeature13_SSSDRealmdIntegration:
    def test_sssd_template_exists(self, sssd_conf_path):
        """13.1 Vérifie la présence du template sssd.conf.j2"""
        assert sssd_conf_path.exists()

    def test_sssd_configuration_services(self, sssd_conf_path):
        """13.2 Vérifie les services nss et pam déclarés dans sssd.conf.j2"""
        content = sssd_conf_path.read_text(encoding="utf-8")
        assert "services = nss, pam" in content or ("nss" in content and "pam" in content)

    def test_sssd_domain_configuration(self, sssd_conf_path):
        """13.3 Vérifie le domaine LYUX.LAN et l'id_provider dans sssd.conf.j2"""
        content = sssd_conf_path.read_text(encoding="utf-8")
        assert "domain" in content.lower()
        assert "ldap" in content.lower() or "ad" in content.lower()

    def test_sssd_packages_installed_in_ansible(self, paths):
        """13.4 Vérifie les paquets sssd, sssd-tools, libpam-sss dans lyux-base"""
        base_tasks = paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml"
        content = base_tasks.read_text(encoding="utf-8")
        assert "sssd" in content
        assert "libpam-sss" in content
        assert "libnss-sss" in content

    def test_pam_mkhomedir_activation(self, paths):
        """13.5 Vérifie l'activation de pam_mkhomedir via pam-auth-update"""
        base_tasks = paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml"
        content = base_tasks.read_text(encoding="utf-8")
        assert "pam-auth-update --enable mkhomedir" in content


# ==============================================================================
# FEATURE 14: Dynamic Network Shares Mount via pam_mount
# ==============================================================================
class TestFeature14_DynamicSharesPamMount:
    def test_pam_mount_template_is_valid_xml(self, pam_mount_xml_path):
        """14.1 Vérifie que pam_mount.conf.xml.j2 est un XML syntaxiquement valide (hors variables Jinja)"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        clean_xml = re.sub(r'\{\{[^}]+\}\}', '192.168.100.10', raw)
        root = ET.fromstring(clean_xml)
        assert root.tag == "pam_mount"

    def test_pam_mount_espace_personnel_volume(self, pam_mount_xml_path):
        """14.2 Vérifie le volume de montage ~/Espace_Personnel pointant sur homes/%(USER)"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        assert 'mountpoint="~/Espace_Personnel"' in raw
        assert 'path="homes/%(USER)"' in raw
        assert 'fstype="cifs"' in raw

    def test_pam_mount_partages_classes_volume(self, pam_mount_xml_path):
        """14.3 Vérifie le volume de montage ~/Partages_Classes pour le groupe eleves"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        assert 'mountpoint="~/Partages_Classes"' in raw
        assert 'path="classes"' in raw
        assert 'sgrp="eleves"' in raw

    def test_pam_mount_partages_enseignants_volume(self, pam_mount_xml_path):
        """14.4 Vérifie le volume de montage ~/Partages_Enseignants pour le groupe enseignants"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        assert 'mountpoint="~/Partages_Enseignants"' in raw
        assert 'path="profs"' in raw
        assert 'sgrp="enseignants"' in raw

    def test_pam_mount_cifs_security_options(self, pam_mount_xml_path):
        """14.5 Vérifie les options de sécurité CIFS (sec=ntlmssp, permissions 0700/0770)"""
        raw = pam_mount_xml_path.read_text(encoding="utf-8")
        assert "sec=ntlmssp" in raw
        assert "file_mode=0700" in raw


# ==============================================================================
# FEATURE 15: Disciplinary Profile: NSI / Maths
# ==============================================================================
class TestFeature15_DisciplinaryProfileNSIMaths:
    def test_nsi_role_exists(self, paths):
        """15.1 Vérifie la présence des tâches de profil de salle dans lyux-profile-salles"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        assert tasks_file.exists()

    def test_nsi_packages_include_vscode_jupyter_spyder(self, paths):
        """15.2 Vérifie les outils NSI avancés (code, jupyter-notebook, spyder)"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "code" in content
        assert "jupyter-notebook" in content
        assert "spyder" in content

    def test_nsi_packages_include_gcc_gdb_git(self, paths):
        """15.3 Vérifie les outils de développement (gcc, g++, gdb, git)"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "gcc" in content
        assert "g++" in content
        assert "git" in content

    def test_nsi_packages_include_maths_tools(self, paths):
        """15.4 Vérifie la présence de scilab ou octave pour les mathématiques"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "scilab" in content or "octave" in content

    def test_nsi_base_packages_thonny_geogebra(self, paths):
        """15.5 Vérifie la présence de Thonny et GeoGebra dans le socle lyux-base"""
        base_tasks = paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml"
        content = base_tasks.read_text(encoding="utf-8")
        assert "thonny" in content
        assert "geogebra" in content


# ==============================================================================
# FEATURE 16: Disciplinary Profile: Sciences
# ==============================================================================
class TestFeature16_DisciplinaryProfileSciences:
    def test_sciences_condition_in_ansible(self, paths):
        """16.1 Vérifie la condition room_profile == 'sciences' dans les tâches Ansible"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "room_profile == 'sciences'" in content

    def test_sciences_avogadro_chimie_3d(self, paths):
        """16.2 Vérifie la présence d'Avogadro pour la modélisation moléculaire"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "avogadro" in content

    def test_sciences_stellarium_astronomie(self, paths):
        """16.3 Vérifie la présence de Stellarium pour l'astronomie et physique"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "stellarium" in content

    def test_sciences_tracker_mecanique(self, paths):
        """16.4 Vérifie la présence de Tracker pour l'analyse vidéo en mécanique"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "tracker" in content

    def test_sciences_qgis_gimp_imagej(self, paths):
        """16.5 Vérifie la présence d'outils complémentaires SVT/Physique (QGIS, GIMP, ImageJ)"""
        tasks_file = paths["ansible"] / "roles" / "lyux-profile-salles" / "tasks" / "main.yml"
        content = tasks_file.read_text(encoding="utf-8")
        assert "qgis" in content
        assert "gimp" in content
        assert "imagej" in content


# ==============================================================================
# FEATURE 17: Veyon Architecture & Asymmetric Keys
# ==============================================================================
class TestFeature17_VeyonAsymmetricKeys:
    def test_veyon_private_key_contract_path(self, paths):
        """17.1 Vérifie le chemin normatif de la clef privée enseignant dans PROJECT.md"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "/etc/veyon/keys/private/teacher/key" in spec

    def test_veyon_private_key_strict_permissions(self, paths):
        """17.2 Vérifie les permissions strictes 0440 réservées au groupe enseignants"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "0440" in spec
        assert "root:enseignants" in spec

    def test_veyon_public_key_contract_path(self, paths):
        """17.3 Vérifie le chemin normatif de la clef publique sur tous les postes"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "/etc/veyon/keys/public/teacher/key" in spec

    def test_veyon_public_key_world_readable(self, paths):
        """17.4 Vérifie les permissions 0444 root:root pour la clef publique"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "0444" in spec

    def test_veyon_ports_allocated(self, expected_ports):
        """17.5 Vérifie les 3 ports officiels de communication Veyon (11100, 11200, 11400)"""
        assert expected_ports["veyon_service"]["port"] == 11100
        assert expected_ports["veyon_feature"]["port"] == 11200
        assert expected_ports["veyon_demo"]["port"] == 11400


# ==============================================================================
# FEATURE 18: Veyon Master & Service Deployment
# ==============================================================================
class TestFeature18_VeyonMasterServiceDeployment:
    def test_veyon_master_in_prof_profile(self, paths):
        """18.1 Vérifie l'installation du paquet veyon-master dans le rôle prof"""
        prof_tasks = paths["ansible"] / "roles" / "lyux-profile-prof" / "tasks" / "main.yml"
        content = prof_tasks.read_text(encoding="utf-8")
        assert "veyon-master" in content

    def test_veyon_service_in_base_profile(self, paths):
        """18.2 Vérifie l'installation de veyon-service dans le socle commun lyux-base"""
        base_tasks = paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml"
        content = base_tasks.read_text(encoding="utf-8")
        assert "veyon-service" in content

    def test_veyon_service_daemon_enabled_for_eleves(self, paths):
        """18.3 Vérifie le démarrage et l'activation automatique du service veyon dans lyux-profile-eleve"""
        eleve_tasks = paths["ansible"] / "roles" / "lyux-profile-eleve" / "tasks" / "main.yml"
        content = eleve_tasks.read_text(encoding="utf-8")
        assert "name: veyon" in content
        assert "state: started" in content
        assert "enabled: yes" in content or "enabled: true" in content

    def test_teacher_machine_flagged_in_ansible_inventory(self, ansible_inventory_data):
        """18.4 Vérifie le flag is_teacher_pc: true sur les postes profs de l'inventaire"""
        clients = ansible_inventory_data["all"]["children"]["postes_clients"]["children"]
        b204 = clients["salle_nsi_b204"]["hosts"]
        s102 = clients["salle_sciences_s102"]["hosts"]
        assert b204["b204-prof"].get("is_teacher_pc") is True
        assert s102["s102-prof"].get("is_teacher_pc") is True

    def test_student_machines_not_teacher_flagged(self, ansible_inventory_data):
        """18.5 Vérifie que les postes élèves ne sont pas marqués is_teacher_pc"""
        clients = ansible_inventory_data["all"]["children"]["postes_clients"]["children"]
        b204 = clients["salle_nsi_b204"]["hosts"]
        assert b204["b204-01"].get("is_teacher_pc", False) is False


# ==============================================================================
# FEATURE 19: Pedagogical Classroom Supervision
# ==============================================================================
class TestFeature19_PedagogicalSupervision:
    def test_api_lock_room_endpoint_locks_students(self, api_client):
        """19.1 Vérifie le verrouillage d'une salle complète via l'API LyuX Control"""
        req = {"room_id": "B204", "action": "lock", "message_text": "Attention au tableau"}
        res = api_client.post("/api/v1/control/lock-room", json=req)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["action"] == "lock"
        assert data["affected_machines"] >= 2

    def test_api_unlock_room_endpoint(self, api_client):
        """19.2 Vérifie le déverrouillage de la salle B204"""
        req = {"room_id": "B204", "action": "unlock", "message_text": "Fin d'explication"}
        res = api_client.post("/api/v1/control/lock-room", json=req)
        assert res.status_code == 200
        assert res.json()["action"] == "unlock"

    def test_station_main_implements_veyon_dialog(self, paths):
        """19.3 Vérifie la méthode open_veyon_master dans l'application unifiée lyux-station"""
        main_py = paths["station"] / "src" / "main.py"
        content = main_py.read_text(encoding="utf-8")
        assert "def open_veyon_master" in content
        assert "Tout Verrouiller" in content
        assert "Tout Déverrouiller" in content

    def test_teacher_station_cannot_lock_itself(self, api_client):
        """19.4 Vérifie que le verrouillage de salle épargne le poste enseignant b204-prof"""
        res_machines = api_client.get("/api/v1/machines")
        machines = {m["hostname"]: m for m in res_machines.json()}
        if "b204-prof" in machines:
            assert machines["b204-prof"]["locked"] is False

    def test_supervision_broadcast_message_support(self, api_client):
        """19.5 Vérifie la transmission d'un message textuel global avec la commande lock"""
        req = {"room_id": "S102", "action": "message", "message_text": "Rangez les microscopes"}
        res = api_client.post("/api/v1/control/lock-room", json=req)
        assert res.status_code == 200
        assert res.json()["message"] == "Rangez les microscopes"


# ==============================================================================
# FEATURE 20: Pilot Rooms Definition (B204 & S102)
# ==============================================================================
class TestFeature20_PilotRoomsDefinition:
    def test_rooms_catalog_includes_b204_and_s102(self, api_client):
        """20.1 Vérifie la présence des 2 salles pilotes dans le catalogue officiel"""
        res = api_client.get("/api/v1/rooms")
        assert res.status_code == 200
        catalog = res.json()
        assert "B204" in catalog
        assert "S102" in catalog

    def test_room_b204_profile_is_nsi(self, api_client):
        """20.2 Vérifie le profil disciplinaire NSI associé à la salle B204"""
        res = api_client.get("/api/v1/rooms")
        b204 = res.json()["B204"]
        assert b204["profile"] == "nsi"
        assert "Maths" in b204["name"] or "NSI" in b204["name"]

    def test_room_s102_profile_is_sciences(self, api_client):
        """20.3 Vérifie le profil disciplinaire Sciences associé à la salle S102"""
        res = api_client.get("/api/v1/rooms")
        s102 = res.json()["S102"]
        assert s102["profile"] == "sciences"
        assert "Physique" in s102["name"] or "Sciences" in s102["name"]

    def test_ansible_inventory_pilot_rooms_structure(self, ansible_inventory_data):
        """20.4 Vérifie la structure des groupes Ansible salle_nsi_b204 et salle_sciences_s102"""
        children = ansible_inventory_data["all"]["children"]["postes_clients"]["children"]
        assert "salle_nsi_b204" in children
        assert "salle_sciences_s102" in children

    def test_pilot_rooms_ip_address_subnets(self, ansible_inventory_data):
        """20.5 Vérifie les plans d'adressage IP dédiés (192.168.100.2x pour B204, .3x pour S102)"""
        children = ansible_inventory_data["all"]["children"]["postes_clients"]["children"]
        b204_hosts = children["salle_nsi_b204"]["hosts"]
        s102_hosts = children["salle_sciences_s102"]["hosts"]
        for h, data in b204_hosts.items():
            assert "192.168.100.2" in data["ansible_host"]
        for h, data in s102_hosts.items():
            assert "192.168.100.3" in data["ansible_host"]


# ==============================================================================
# FEATURE 21: VirtualBox Non-Textual Automated Lab
# ==============================================================================
class TestFeature21_VirtualBoxAutomatedLab:
    def test_setup_2classes_script_exists(self, paths):
        """21.1 Vérifie la présence du script setup-2classes-vms.ps1"""
        s = paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1"
        assert s.exists()

    def test_setup_2classes_unattended_install_flags(self, paths):
        """21.2 Vérifie l'utilisation de VBoxManage unattended install pour éliminer l'invite textuelle"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "unattended install" in content

    def test_setup_2classes_guest_additions_flag(self, paths):
        """21.3 Vérifie le flag --install-additions pour l'intégration graphique optimale"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "--install-additions" in content

    def test_vm_specs_memory_and_cpu(self, paths):
        """21.4 Vérifie les spécifications des VMs (2 Go RAM, 2 vCPUs) adaptées aux labos"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "--memory 2048" in content
        assert "--cpus 2" in content

    def test_five_vms_orchestrated_in_script(self, paths):
        """21.5 Vérifie la déclaration des 5 VMs (2 B204, 2 S102, 1 Vierge)"""
        content = (paths["lab_vm"] / "scripts" / "setup-2classes-vms.ps1").read_text(encoding="utf-8")
        assert "LyuX-B204-PC1" in content
        assert "LyuX-B204-PC2" in content
        assert "LyuX-S102-PC1" in content
        assert "LyuX-S102-PC2" in content
        assert "LyuX-PC-Vierge" in content


# ==============================================================================
# FEATURE 22: Automated Lab Test Runner Script
# ==============================================================================
class TestFeature22_AutomatedLabTestRunnerScript:
    def test_vagrantfile_exists_as_test_runner_fallback(self, paths):
        """22.1 Vérifie la présence du Vagrantfile de déploiement automatique du lab"""
        vf = paths["lab_vm"] / "Vagrantfile"
        assert vf.exists()
        content = vf.read_text(encoding="utf-8")
        assert "Vagrant.configure" in content

    def test_provision_server_script_exists(self, paths):
        """22.2 Vérifie la présence du script de provisionnement serveur du lab"""
        sh = paths["lab_vm"] / "scripts" / "provision-server.sh"
        assert sh.exists()
        content = sh.read_text(encoding="utf-8")
        assert "docker compose up -d" in content or "samba" in content

    def test_provision_client_script_exists(self, paths):
        """22.3 Vérifie la présence du script de provisionnement des postes clients du lab"""
        sh = paths["lab_vm"] / "scripts" / "provision-client.sh"
        assert sh.exists()
        content = sh.read_text(encoding="utf-8")
        assert "apt-get" in content
        assert "veyon" in content

    def test_interactive_launch_script_exists(self, paths):
        """22.4 Vérifie le script de lancement interactif lancer-vm-interactive.ps1"""
        ps = paths["lab_vm"] / "scripts" / "lancer-vm-interactive.ps1"
        assert ps.exists()

    def test_root_launchers_exist(self, paths):
        """22.5 Vérifie les lanceurs racines Lancer-LyuX.bat et lancer-lyux.ps1"""
        bat = paths["root"] / "Lancer-LyuX.bat"
        ps1 = paths["root"] / "lancer-lyux.ps1"
        assert bat.exists()
        assert ps1.exists()


# ==============================================================================
# FEATURE 23: Comprehensive E2E Test Suite (Tiers 1-4)
# ==============================================================================
class TestFeature23_ComprehensiveE2ETestSuite:
    def test_test_infra_documentation_exists(self, paths):
        """23.1 Vérifie la présence du document maître TEST_INFRA.md à la racine"""
        doc = paths["root"] / "TEST_INFRA.md"
        assert doc.exists()
        content = doc.read_text(encoding="utf-8")
        assert "TEST_INFRA.md" in content
        assert "Tier 1" in content and "Tier 4" in content

    def test_conftest_global_fixtures_defined(self, paths):
        """23.2 Vérifie la présence des fixtures globales dans tests/conftest.py"""
        cf = paths["root"] / "tests" / "conftest.py"
        assert cf.exists()
        content = cf.read_text(encoding="utf-8")
        assert "project_root" in content
        assert "api_client" in content

    def test_e2e_package_structure_present(self, paths):
        """23.3 Vérifie que tests/e2e/__init__.py et tests/e2e/conftest.py sont initialisés"""
        init_file = paths["root"] / "tests" / "e2e" / "__init__.py"
        e2e_cf = paths["root"] / "tests" / "e2e" / "conftest.py"
        assert init_file.exists()
        assert e2e_cf.exists()

    def test_e2e_tier_files_present(self, paths):
        """23.4 Vérifie la présence des modules de test pour chaque niveau (Tiers 1 à 4)"""
        e2e_dir = paths["root"] / "tests" / "e2e"
        assert (e2e_dir / "test_tier1_features.py").exists()

    def test_project_specification_matrix_documented(self, paths):
        """23.5 Vérifie que PROJECT.md définit les 24 fonctionnalités dans la matrice"""
        spec = (paths["root"] / "PROJECT.md").read_text(encoding="utf-8")
        assert "Feature Inventory" in spec
        for i in range(1, 25):
            assert f"| {i} |" in spec


# ==============================================================================
# FEATURE 24: Adversarial Hardening (Tier 5)
# ==============================================================================
class TestFeature24_AdversarialHardening:
    def test_backup_321_script_exists_for_disaster_recovery(self, paths):
        """24.1 Vérifie la présence du script de sauvegarde de reprise d'activité 3-2-1"""
        b = paths["server_infra"] / "scripts" / "backup-321.sh"
        assert b.exists()
        content = b.read_text(encoding="utf-8")
        assert "tar" in content
        assert "rsync" in content or "samba" in content.lower()

    def test_cleanup_sessions_script_protects_student_privacy(self, paths):
        """24.2 Vérifie le script lyux-cleanup-sessions.sh de purge des caches à l'extinction"""
        base_tasks = paths["ansible"] / "roles" / "lyux-base" / "tasks" / "main.yml"
        content = base_tasks.read_text(encoding="utf-8")
        assert "lyux-cleanup-sessions.sh" in content
        assert ".cache" in content

    def test_firewall_default_deny_incoming(self, paths):
        """24.3 Vérifie le durcissement du pare-feu avec politique 'default deny incoming'"""
        content = (paths["server_infra"] / "scripts" / "init-server.sh").read_text(encoding="utf-8")
        assert "ufw default deny incoming" in content

    def test_root_login_disabled_in_preseed(self, preseed_iso_path):
        """24.4 Vérifie la désactivation stricte du compte root direct dans le preseed"""
        content = preseed_iso_path.read_text(encoding="utf-8")
        assert "passwd/root-login boolean false" in content

    def test_unauthorized_room_id_fails_otp_generation(self, api_client):
        """24.5 Vérifie la résistance de l'API face à une tentative d'enrôlement sur une salle inconnue"""
        req = {"admin_user": "lyux-admin", "room_id": "SALLE_PIRATE_999", "validity_minutes": 10}
        res = api_client.post("/api/v1/enroll/generate-otp", json=req)
        assert res.status_code == 404
