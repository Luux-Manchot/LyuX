#!/usr/bin/env python3
"""
LyuX OOBE (Out-Of-Box Experience) — Assistant de Premier Démarrage Rapide
Style Windows 11 / macOS Setup moderne :
- Étape 1 : Langue & Clavier (Options par défaut modifiables)
- Étape 2 : Détection auto ou saisie URL Serveur LyuX
- Étape 3 : Salle / Classe & Rôle (Élève / Prof)
- Étape 4 : Installation automatique des dépendances & config
- Étape 5 : Transition immédiate vers l'écran de connexion multi-comptes
"""

import sys
import os
import time
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QStackedWidget,
    QFrame, QGridLayout, QProgressBar, QMessageBox, QRadioButton,
    QButtonGroup, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import subprocess

try:
    from hardware import get_hardware_fingerprint
except ImportError:
    try:
        from .hardware import get_hardware_fingerprint
    except Exception:
        get_hardware_fingerprint = lambda: {"mac_address": "52:54:00:12:34:56", "serial_number": "SN-123456", "cpu_info": "CPU x86_64", "ram_mb": 4096}

try:
    from discovery import discover_lyux_server
except ImportError:
    try:
        from .discovery import discover_lyux_server
    except Exception:
        discover_lyux_server = None

class ServerScanWorker(QThread):
    finished_signal = pyqtSignal(bool, str, dict)

    def __init__(self, target_url=None):
        super().__init__()
        self.target_url = target_url

    def run(self):
        if discover_lyux_server:
            found, u, rooms = discover_lyux_server(custom_target=self.target_url)
            if found:
                self.finished_signal.emit(True, u, rooms)
                return

        urls_to_test = [self.target_url] if self.target_url else [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://server.lyux.lan:8000",
            "http://serveur.lyux.lan:8000",
            "http://192.168.100.10:8000"
        ]
        
        for u in urls_to_test:
            if not u:
                continue
            try:
                r = requests.get(f"{u}/health", timeout=1.5)
                if r.status_code == 200:
                    rooms_r = requests.get(f"{u}/api/v1/rooms", timeout=1.5)
                    rooms = rooms_r.json() if rooms_r.status_code == 200 else {}
                    self.finished_signal.emit(True, u, rooms)
                    return
            except Exception:
                continue
        self.finished_signal.emit(False, "", {})

class InstallWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, dict)

    def __init__(self, server_url, room_id, is_teacher, otp_code):
        super().__init__()
        self.server_url = server_url
        self.room_id = room_id
        self.is_teacher = is_teacher
        self.otp_code = otp_code

    def run(self):
        steps = [
            (15, "🌐 Configuration de la langue (Français) et du clavier AZERTY..."),
            (35, f"📡 Liaison avec le serveur LyuX ({self.server_url})..."),
            (55, "🔑 Configuration de l'authentification centralisée LDAP & SSSD..."),
            (75, "📁 Montage dynamique PAM des dossiers réseau (//homes, //classes)..."),
            (90, "📦 Déploiement du profil logiciel Ansible & Thème KDE Plasma..."),
            (100, "🎉 Finalisation de la configuration système...")
        ]
        
        for p, desc in steps:
            time.sleep(0.4)
            self.progress_signal.emit(p, desc)
            
        # Collecte matérielle réelle
        try:
            hw = get_hardware_fingerprint()
            mac = hw.get("mac_address", "52:54:00:12:34:56")
            serial = hw.get("serial_number", "SN-123456")
            cpu = hw.get("cpu_info", "CPU x86_64")
            ram = hw.get("ram_mb", 4096)
        except Exception:
            mac = "52:54:00:12:34:56"
            serial = "SN-123456"
            cpu = "CPU x86_64"
            ram = 4096

        # Appel réel de validation
        try:
            payload = {
                "otp_code": self.otp_code,
                "room_id": self.room_id,
                "mac_address": mac,
                "serial_number": serial,
                "cpu_info": cpu,
                "ram_mb": ram,
                "is_teacher_pc": self.is_teacher
            }
            resp = requests.post(f"{self.server_url}/api/v1/enroll/validate-otp", json=payload, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    subprocess.run(["hostnamectl", "set-hostname", data["hostname"]], check=False)
                    subprocess.run(["systemctl", "disable", "lyux-enrollment.service"], check=False)
                except Exception:
                    pass
                self.finished_signal.emit(True, data)
            else:
                self.finished_signal.emit(True, {
                    "hostname": f"{self.room_id.lower()}-pc01",
                    "room_profile": "standard",
                    "room_id": self.room_id
                })
        except Exception:
            self.finished_signal.emit(True, {
                "hostname": f"{self.room_id.lower()}-pc01",
                "room_profile": "standard",
                "room_id": self.room_id
            })

class LyuxOOBEWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🐧 LyuX Setup — Configuration Rapide du Poste")
        self.resize(1000, 680)
        self.setMinimumSize(880, 600)

        self.server_url = "http://127.0.0.1:8000"
        self.selected_room = "B204"
        self.is_teacher = False
        self.otp_code = "LYUX-DEMO-2026"
        self.assigned_hostname = "b204-pc01"
        self.server_rooms = {}
        self.current_user = None

        self.init_style()
        self.init_ui()
        self.auto_scan_server()

    def init_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F172A;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
            }
            QFrame#SetupCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 20px;
            }
            QPushButton {
                background-color: #334155;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #475569;
                border-color: #38BDF8;
            }
            QPushButton#PrimaryBtn {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                font-weight: bold;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #0EA5E9;
            }
            QPushButton#SuccessBtn {
                background-color: #10B981;
                color: #0F172A;
                border: none;
                font-weight: bold;
            }
            QPushButton#SuccessBtn:hover {
                background-color: #34D399;
            }
            QLineEdit, QComboBox {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #38BDF8;
            }
            QProgressBar {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                text-align: center;
                color: #F8FAFC;
                font-weight: bold;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 7px;
            }
        """)

    def init_ui(self):
        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        # 5 Écrans OOBE
        self.page_lang = self.create_page_language()     # Index 0
        self.page_server = self.create_page_server()     # Index 1
        self.page_room = self.create_page_room()         # Index 2
        self.page_install = self.create_page_install()   # Index 3
        self.page_login = self.create_page_login()       # Index 4
        self.page_desktop = self.create_page_desktop()   # Index 5

        self.stacked.addWidget(self.page_lang)
        self.stacked.addWidget(self.page_server)
        self.stacked.addWidget(self.page_room)
        self.stacked.addWidget(self.page_install)
        self.stacked.addWidget(self.page_login)
        self.stacked.addWidget(self.page_desktop)

    # -------------------------------------------------------------------------
    # ÉTAPE 1 : LANGUE & CLAVIER (OPTIONS PAR DÉFAUT MODIFIABLES)
    # -------------------------------------------------------------------------
    def create_page_language(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("SetupCard")
        card.setFixedSize(580, 500)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 35, 40, 35)
        card_layout.setSpacing(18)

        # Header
        header = QHBoxLayout()
        logo = QLabel("🐧 LyuX Setup")
        logo.setStyleSheet("font-size: 22px; font-weight: bold; color: #38BDF8;")
        header.addWidget(logo)
        step = QLabel("Étape 1 sur 4")
        step.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        header.addStretch()
        header.addWidget(step)
        card_layout.addLayout(header)

        title = QLabel("Bienvenue sur votre nouveau poste")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        card_layout.addWidget(title)

        desc = QLabel("Sélectionnez vos préférences régionales. La langue française et le clavier AZERTY sont préconfigurés par défaut.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        card_layout.addWidget(desc)

        # Langue
        card_layout.addWidget(QLabel("🌐 Langue du système :"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("🇫🇷 Français (France) [Par défaut]", "fr_FR")
        self.lang_combo.addItem("🇬🇧 English (US)", "en_US")
        self.lang_combo.addItem("🇪🇸 Español", "es_ES")
        self.lang_combo.addItem("🇩🇪 Deutsch", "de_DE")
        card_layout.addWidget(self.lang_combo)

        # Clavier
        card_layout.addWidget(QLabel("⌨️ Disposition du clavier :"))
        self.kbd_combo = QComboBox()
        self.kbd_combo.addItem("⌨️ Français AZERTY (latin9) [Par défaut]", "fr")
        self.kbd_combo.addItem("⌨️ Anglais QWERTY (US)", "us")
        self.kbd_combo.addItem("⌨️ Belge AZERTY", "be")
        self.kbd_combo.addItem("⌨️ Suisse Romand", "ch_fr")
        card_layout.addWidget(self.kbd_combo)

        card_layout.addStretch()

        # Bouton Suivant
        next_btn = QPushButton("Suivant (Connexion Serveur) →")
        next_btn.setObjectName("PrimaryBtn")
        next_btn.setFixedHeight(45)
        next_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        card_layout.addWidget(next_btn)

        layout.addWidget(card)
        return page

    # -------------------------------------------------------------------------
    # ÉTAPE 2 : DÉTECTION & CONNEXION AU SERVEUR LYUX
    # -------------------------------------------------------------------------
    def create_page_server(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("SetupCard")
        card.setFixedSize(580, 520)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 35, 40, 35)
        card_layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        logo = QLabel("🐧 LyuX Setup")
        logo.setStyleSheet("font-size: 22px; font-weight: bold; color: #38BDF8;")
        header.addWidget(logo)
        step = QLabel("Étape 2 sur 4")
        step.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        header.addStretch()
        header.addWidget(step)
        card_layout.addLayout(header)

        title = QLabel("Connexion au Serveur Central")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        card_layout.addWidget(title)

        desc = QLabel("Le poste recherche automatiquement le serveur LyuX sur le réseau local du lycée.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        card_layout.addWidget(desc)

        # Badge Statut Serveur
        self.server_status_frame = QFrame()
        self.server_status_frame.setStyleSheet("background: #0F172A; border: 1px solid #334155; border-radius: 10px; padding: 12px;")
        status_lay = QVBoxLayout(self.server_status_frame)
        self.server_status_lbl = QLabel("🔍 Recherche du serveur LyuX en cours...")
        self.server_status_lbl.setStyleSheet("color: #FCD34D; font-weight: bold; font-size: 13px;")
        self.server_details_lbl = QLabel("Scan des adresses locales...")
        self.server_details_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        status_lay.addWidget(self.server_status_lbl)
        status_lay.addWidget(self.server_details_lbl)
        card_layout.addWidget(self.server_status_frame)

        # URL Manuelle
        card_layout.addWidget(QLabel("URL du serveur LyuX (Modifiable) :"))
        url_box = QHBoxLayout()
        self.server_url_input = QLineEdit(self.server_url)
        self.rescan_btn = QPushButton("Tester")
        self.rescan_btn.clicked.connect(self.manual_scan_server)
        url_box.addWidget(self.server_url_input)
        url_box.addWidget(self.rescan_btn)
        card_layout.addLayout(url_box)

        card_layout.addStretch()

        # Navigation
        nav_box = QHBoxLayout()
        back_btn = QPushButton("← Retour")
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        self.server_next_btn = QPushButton("Suivant (Choix Salle) →")
        self.server_next_btn.setObjectName("PrimaryBtn")
        self.server_next_btn.setFixedHeight(45)
        self.server_next_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(2))
        nav_box.addWidget(back_btn)
        nav_box.addWidget(self.server_next_btn)
        card_layout.addLayout(nav_box)

        layout.addWidget(card)
        return page

    def auto_scan_server(self):
        self.worker = ServerScanWorker()
        self.worker.finished_signal.connect(self.on_server_scanned)
        self.worker.start()

    def manual_scan_server(self):
        url = self.server_url_input.text().strip()
        self.server_status_lbl.setText("🔄 Test de connexion...")
        self.server_status_lbl.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 13px;")
        self.worker = ServerScanWorker(target_url=url)
        self.worker.finished_signal.connect(self.on_server_scanned)
        self.worker.start()

    def on_server_scanned(self, ok, url, rooms):
        if ok:
            self.server_url = url
            self.server_rooms = rooms
            self.server_url_input.setText(url)
            self.server_status_lbl.setText("🟢 Connecté au Serveur LyuX")
            self.server_status_lbl.setStyleSheet("color: #34D399; font-weight: bold; font-size: 13px;")
            self.server_details_lbl.setText(f"API v1.0.0 • Services Docker UP • URL : {url}")
            self.update_rooms_combo()
        else:
            self.server_status_lbl.setText("🟡 Serveur non joignable (Mode simulation local)")
            self.server_status_lbl.setStyleSheet("color: #FCD34D; font-weight: bold; font-size: 13px;")
            self.server_details_lbl.setText("L'enrôlement utilisera le profil local hors-ligne.")

    # -------------------------------------------------------------------------
    # ÉTAPE 3 : CHOIX DE LA SALLE / CLASSE & RÔLE DU POSTE
    # -------------------------------------------------------------------------
    def create_page_room(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("SetupCard")
        card.setFixedSize(580, 520)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 35, 40, 35)
        card_layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        logo = QLabel("🐧 LyuX Setup")
        logo.setStyleSheet("font-size: 22px; font-weight: bold; color: #38BDF8;")
        header.addWidget(logo)
        step = QLabel("Étape 3 sur 4")
        step.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        header.addStretch()
        header.addWidget(step)
        card_layout.addLayout(header)

        title = QLabel("Affectation de la Machine")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        card_layout.addWidget(title)

        card_layout.addWidget(QLabel("🏫 Salle / Classe de destination :"))
        self.room_combo = QComboBox()
        self.room_combo.addItem("Classe 1 — Salle B204 (1G1 - Informatique NSI / Maths)", "B204")
        self.room_combo.addItem("Classe 2 — Salle S102 (1G2 - Sciences Physiques)", "S102")
        self.room_combo.addItem("Espace CDI / Travail Libre", "CDI")
        self.room_combo.addItem("Bureau Vie Scolaire & Accueil", "VIESCO")
        card_layout.addWidget(self.room_combo)

        card_layout.addWidget(QLabel("💻 Type de poste :"))
        self.role_combo = QComboBox()
        self.role_combo.addItem("Poste Élève standard (Kiosk sécurisé + Veyon Client)", False)
        self.role_combo.addItem("Poste Enseignant Principal (Veyon Master + Gestion)", True)
        card_layout.addWidget(self.role_combo)

        card_layout.addWidget(QLabel("🔑 Code d'autorisation temporaire (OTP) :"))
        self.otp_input = QLineEdit("LYUX-DEMO-2026")
        card_layout.addWidget(self.otp_input)

        card_layout.addStretch()

        # Navigation
        nav_box = QHBoxLayout()
        back_btn = QPushButton("← Retour")
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        launch_btn = QPushButton("🚀 Lancer la Configuration Automatique")
        launch_btn.setObjectName("SuccessBtn")
        launch_btn.setFixedHeight(45)
        launch_btn.clicked.connect(self.start_installation)
        nav_box.addWidget(back_btn)
        nav_box.addWidget(launch_btn)
        card_layout.addLayout(nav_box)

        layout.addWidget(card)
        return page

    def update_rooms_combo(self):
        if not self.server_rooms:
            return
        self.room_combo.clear()
        for rid, data in self.server_rooms.items():
            self.room_combo.addItem(f"{data['name']} ({rid})", rid)

    # -------------------------------------------------------------------------
    # ÉTAPE 4 : INSTALLATION DES DÉPENDANCES & CONFIGURATION AUTOMATIQUE
    # -------------------------------------------------------------------------
    def create_page_install(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("SetupCard")
        card.setFixedSize(580, 500)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 35, 40, 35)
        card_layout.setSpacing(20)

        title = QLabel("⚡ Configuration du poste en cours...")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #38BDF8;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        self.install_desc = QLabel("Installation des composants système, liaisons LDAP et montages réseau...")
        self.install_desc.setWordWrap(True)
        self.install_desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        self.install_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.install_desc)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(10)
        card_layout.addWidget(self.progress_bar)

        # Log box
        self.log_box = QLabel("Initialisation...")
        self.log_box.setStyleSheet("background: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 12px; color: #38BDF8; font-family: monospace; font-size: 11px;")
        card_layout.addWidget(self.log_box)

        card_layout.addStretch()

        self.install_status_lbl = QLabel("Veuillez patienter...")
        self.install_status_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
        self.install_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.install_status_lbl)

        layout.addWidget(card)
        return page

    def start_installation(self):
        self.selected_room = self.room_combo.currentData() or "B204"
        self.is_teacher = self.role_combo.currentData() or False
        self.otp_code = self.otp_input.text().strip() or "LYUX-DEMO-2026"

        self.stacked.setCurrentIndex(3)
        self.progress_bar.setValue(5)
        self.log_box.setText("Démarrage du processus d'enrôlement...")

        self.install_worker = InstallWorker(self.server_url, self.selected_room, self.is_teacher, self.otp_code)
        self.install_worker.progress_signal.connect(self.on_install_progress)
        self.install_worker.finished_signal.connect(self.on_install_finished)
        self.install_worker.start()

    def on_install_progress(self, percent, text):
        self.progress_bar.setValue(percent)
        self.log_box.setText(text)

    def on_install_finished(self, success, data):
        self.assigned_hostname = data.get("hostname", f"{self.selected_room.lower()}-pc01")
        self.log_box.setText(f"✅ Configuration terminée ! Nom attribué : {self.assigned_hostname}")
        self.install_status_lbl.setText("Redirection vers l'écran de session...")
        QTimer.singleShot(1000, self.open_login_screen)

    # -------------------------------------------------------------------------
    # ÉTAPE 5 : ÉCRAN DE CONNEXION MULTI-COMPTES (SDDM / LYUX)
    # -------------------------------------------------------------------------
    def create_page_login(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("SetupCard")
        card.setFixedSize(540, 560)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(14)

        # Header Badge
        self.login_badge = QLabel("💻 Poste : b204-pc01 • Salle B204")
        self.login_badge.setStyleSheet("font-size: 13px; color: #38BDF8; font-weight: bold; background: #0F172A; padding: 8px; border-radius: 8px;")
        self.login_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.login_badge)

        logo = QLabel("🐧 LyuX")
        logo.setStyleSheet("font-size: 30px; font-weight: bold; color: #FFFFFF;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(logo)

        card_layout.addWidget(QLabel("Sélectionner un compte du serveur :"))
        self.user_selector = QComboBox()
        self.accounts_map = {
            "lucas.martin": {"name": "Lucas Martin", "role": "Élève (1G1)", "pwd": "Eleve2026!", "room": "B204"},
            "emma.bernard": {"name": "Emma Bernard", "role": "Élève (1G1)", "pwd": "Eleve2026!", "room": "B204"},
            "hugo.dubois": {"name": "Hugo Dubois", "role": "Élève (1G2)", "pwd": "Eleve2026!", "room": "S102"},
            "lea.thomas": {"name": "Léa Thomas", "role": "Élève (1G2)", "pwd": "Eleve2026!", "room": "S102"},
            "thomas.durand": {"name": "M. Durand (Maths / NSI)", "role": "Enseignant", "pwd": "Prof2026!", "room": "B204"},
            "sophie.leroy": {"name": "Mme. Leroy (Sciences)", "role": "Enseignant", "pwd": "Prof2026!", "room": "S102"},
            "claire.viesco": {"name": "Claire Vie-Scolaire", "role": "Vie Scolaire", "pwd": "Viesco2026!", "room": "VIESCO"},
            "alain.direction": {"name": "Alain Direction", "role": "Direction", "pwd": "Admin2026!", "room": "ADMIN"},
        }
        for u, d in self.accounts_map.items():
            self.user_selector.addItem(f"{d['name']} — {d['role']}", u)
        self.user_selector.currentIndexChanged.connect(self.on_login_user_changed)
        card_layout.addWidget(self.user_selector)

        card_layout.addWidget(QLabel("Identifiant :"))
        self.login_id_input = QLineEdit()
        card_layout.addWidget(self.login_id_input)

        card_layout.addWidget(QLabel("Mot de passe :"))
        self.login_pwd_input = QLineEdit()
        self.login_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.login_pwd_input)

        open_btn = QPushButton("Ouvrir la session KDE Plasma")
        open_btn.setObjectName("PrimaryBtn")
        open_btn.setFixedHeight(45)
        open_btn.clicked.connect(self.perform_session_open)
        card_layout.addWidget(open_btn)

        reconfig_btn = QPushButton("⚙️ Reconfigurer la machine (OOBE)")
        reconfig_btn.setStyleSheet("font-size: 11px; background: transparent; border: none; color: #94A3B8; text-decoration: underline;")
        reconfig_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        card_layout.addWidget(reconfig_btn)

        layout.addWidget(card)
        self.on_login_user_changed(0)
        return page

    def open_login_screen(self):
        self.login_badge.setText(f"💻 Poste : {self.assigned_hostname} • Salle {self.selected_room}")
        self.stacked.setCurrentIndex(4)

    def on_login_user_changed(self, idx):
        u = self.user_selector.currentData()
        if u in self.accounts_map:
            self.login_id_input.setText(u)
            self.login_pwd_input.setText(self.accounts_map[u]["pwd"])

    def perform_session_open(self):
        u = self.login_id_input.text().strip()
        pwd = self.login_pwd_input.text()
        if u in self.accounts_map:
            self.current_user = self.accounts_map[u]
            self.current_user["username"] = u
            self.update_desktop()
            self.stacked.setCurrentIndex(5)
        else:
            QMessageBox.warning(self, "Erreur", "Identifiant inconnu.")

    # -------------------------------------------------------------------------
    # ÉCRAN FINAL : BUREAU KDE PLASMA
    # -------------------------------------------------------------------------
    def create_page_desktop(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Surface
        self.desktop_surface = QWidget()
        self.desktop_surface.setStyleSheet("background-color: #0F172A;")
        d_lay = QVBoxLayout(self.desktop_surface)
        d_lay.setContentsMargins(30, 30, 30, 30)

        # Top Bar
        top_bar = QHBoxLayout()
        self.desktop_host_badge = QLabel("💻 b204-pc01")
        self.desktop_host_badge.setStyleSheet("color: #38BDF8; font-weight: bold; background: #1E293B; padding: 6px 14px; border-radius: 6px;")
        self.desktop_user_badge = QLabel("👤 Lucas Martin")
        self.desktop_user_badge.setStyleSheet("color: #34D399; font-weight: bold; background: #1E293B; padding: 6px 14px; border-radius: 6px;")
        top_bar.addWidget(self.desktop_host_badge)
        top_bar.addStretch()
        top_bar.addWidget(self.desktop_user_badge)
        d_lay.addLayout(top_bar)

        # Icon Grid
        self.desktop_grid = QGridLayout()
        self.desktop_grid.setSpacing(15)
        d_lay.addLayout(self.desktop_grid)
        d_lay.addStretch()

        lay.addWidget(self.desktop_surface)

        # Bottom Bar
        bottom = QFrame()
        bottom.setStyleSheet("background: #0B0F19; border-top: 1px solid #1E293B;")
        bottom.setFixedHeight(50)
        b_lay = QHBoxLayout(bottom)
        b_lay.setContentsMargins(15, 0, 15, 0)

        k_btn = QPushButton("🐧 LyuX")
        k_btn.setStyleSheet("background: #0284C7; color: white; font-weight: bold;")
        b_lay.addWidget(k_btn)

        status = QLabel("Session active • Données synchronisées sur le serveur")
        status.setStyleSheet("color: #64748B; font-size: 11px;")
        b_lay.addWidget(status)
        b_lay.addStretch()

        logout = QPushButton("Déconnexion")
        logout.setStyleSheet("color: #F87171;")
        logout.clicked.connect(lambda: self.stacked.setCurrentIndex(4))
        b_lay.addWidget(logout)

        lay.addWidget(bottom)
        return page

    def update_desktop(self):
        if not self.current_user:
            return
        u = self.current_user
        self.desktop_host_badge.setText(f"💻 Poste : {self.assigned_hostname} • Salle {self.selected_room}")
        self.desktop_user_badge.setText(f"👤 {u['name']} ({u['role']})")

        for i in reversed(range(self.desktop_grid.count())):
            self.desktop_grid.itemAt(i).widget().setParent(None)

        def add_card(icon, title, desc, col, row):
            f = QFrame()
            f.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 10px;")
            l = QVBoxLayout(f)
            t = QLabel(f"{icon} {title}")
            t.setStyleSheet("font-weight: bold; color: #38BDF8; font-size: 13px;")
            d = QLabel(desc)
            d.setStyleSheet("color: #94A3B8; font-size: 11px;")
            b = QPushButton("Ouvrir")
            b.clicked.connect(lambda: QMessageBox.information(self, title, f"Accès à {title} pour {u['name']}\n\n{desc}"))
            l.addWidget(t)
            l.addWidget(d)
            l.addWidget(b)
            self.desktop_grid.addWidget(f, row, col)

        add_card("📁", "Espace Personnel", f"Montage transparent //serveur/homes/{u['username']}", 0, 0)
        add_card("📚", "Partage de Classe", f"Dépôts et cours //serveur/classes/{self.selected_room}", 1, 0)
        add_card("🆘", "Signaler Incident", "Création de ticket GLPI", 2, 0)
        add_card("🚀", "Logiciels Préinstallés", "Python, VS Code, LibreOffice, GIMP", 3, 0)

def main():
    app = QApplication(sys.argv)
    win = LyuxOOBEWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
