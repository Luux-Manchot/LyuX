#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QColor

from role_detector import get_current_user_info

class LyuxWelcomeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_info = get_current_user_info()
        self.setWindowTitle("Bienvenue sur LyuX — Opération Manchot")
        self.resize(780, 520)
        self.setMinimumSize(700, 480)

        # Style sombre moderne
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E2E;
            }
            QLabel {
                color: #CDD6F4;
                font-family: 'Segoe UI', 'Ubuntu', 'Noto Sans', sans-serif;
            }
            QPushButton {
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475A;
                border-color: #89B4FA;
            }
            QPushButton#PrimaryBtn {
                background-color: #89B4FA;
                color: #11111B;
                border: none;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #B4BEFE;
            }
            QFrame#Sidebar {
                background-color: #181825;
                border-right: 1px solid #313244;
            }
            QCheckBox {
                color: #A6ADC8;
                font-size: 13px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Barre Latérale (Sidebar) ---
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 20)

        logo_label = QLabel("🐧 LyuX")
        logo_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #89B4FA;")
        subtitle_label = QLabel("Opération Manchot")
        subtitle_label.setStyleSheet("font-size: 12px; color: #A6ADC8; margin-bottom: 25px;")

        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addWidget(subtitle_label)

        # Boutons d'étapes dans la sidebar
        self.step_buttons = []
        steps = ["1. Bienvenue", "2. Vos Fichiers", "3. Vos Outils", "4. Assistance"]
        for i, step in enumerate(steps):
            btn = QPushButton(step)
            btn.setStyleSheet("text-align: left; padding: 8px 12px; font-size: 13px; font-weight: normal;")
            btn.clicked.connect(lambda checked, idx=i: self.stacked_widget.setCurrentIndex(idx))
            self.step_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Profil utilisateur en bas de sidebar
        user_badge = QLabel(f"👤 {self.user_info['display_name']}\n🏷️ {self.user_info['role_label']}")
        user_badge.setStyleSheet("font-size: 12px; color: #BAC2DE; background: #313244; padding: 8px; border-radius: 6px;")
        sidebar_layout.addWidget(user_badge)

        main_layout.addWidget(sidebar)

        # --- Contenu Principal (StackedWidget) ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(35, 30, 35, 25)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.create_welcome_page())
        self.stacked_widget.addWidget(self.create_files_page())
        self.stacked_widget.addWidget(self.create_tools_page())
        self.stacked_widget.addWidget(self.create_help_page())
        self.stacked_widget.currentChanged.connect(self.update_nav_buttons)

        content_layout.addWidget(self.stacked_widget)

        # --- Barre de navigation inférieure ---
        bottom_bar = QHBoxLayout()
        self.dont_show_again = QCheckBox("Ne plus afficher au démarrage")
        self.dont_show_again.setChecked(True)
        bottom_bar.addWidget(self.dont_show_again)
        bottom_bar.addStretch()

        self.prev_btn = QPushButton("Précédent")
        self.prev_btn.clicked.connect(self.go_prev)
        bottom_bar.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Suivant")
        self.next_btn.setObjectName("PrimaryBtn")
        self.next_btn.clicked.connect(self.go_next)
        bottom_bar.addWidget(self.next_btn)

        content_layout.addLayout(bottom_bar)
        main_layout.addWidget(content_container)

        self.update_nav_buttons(0)

    def create_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel(f"Bienvenue, {self.user_info['display_name']} !")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #89B4FA; margin-bottom: 10px;")
        
        desc = QLabel(
            "Vous utilisez le nouveau système d'exploitation libre **LyuX** déployé dans tout l'établissement.\n\n"
            "• **Libre et Performant** : Conçu pour votre réussite scolaire et professionnelle.\n"
            "• **Vos données partout** : Vous pouvez vous asseoir à n'importe quel poste du lycée et retrouver vos fichiers intacts.\n"
            "• **Protection de la vie privée** : Système sécurisé et conforme aux normes RGPD de l'Éducation Nationale."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; line-height: 1.5; color: #CDD6F4;")

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def create_files_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("📁 Où sont stockés vos documents ?")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89B4FA; margin-bottom: 10px;")

        desc = QLabel(
            "⚠️ **Règle essentielle :** Vos fichiers ne doivent pas être enregistrés sur le disque local du PC, "
            "car le poste peut être réinstallé à tout moment.\n\n"
            "Vos dossiers sont automatiquement synchronisés avec le serveur central :\n"
            "• 📂 **Espace Personnel** (`~/Espace_Personnel`) : Vos documents privés accessibles sur tous les PC du lycée.\n"
            "• 📚 **Partages Classes** (`~/Partages_Classes`) : Les cours mis à disposition par vos enseignants et les boîtes de dépôt de devoirs."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; line-height: 1.5; color: #CDD6F4;")

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def create_tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("🛠️ Vos Outils de Travail")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89B4FA; margin-bottom: 10px;")

        if self.user_info['role'] == 'enseignant':
            role_text = (
                "En tant qu'**Enseignant**, vous disposez d'outils dédiés :\n\n"
                "• 🖥️ **Veyon Master** : Supervision des écrans des élèves, verrouillage et projection de votre cours.\n"
                "• 🔑 **Réinitialisation Express** : Débloquez le mot de passe d'un élève en 1 clic via le raccourci sur le bureau.\n"
                "• 📝 **Dépôts de devoirs** : Accédez directement aux dossiers de devoirs de vos classes."
            )
        else:
            role_text = (
                "En tant qu'**Élève**, vous disposez de tous les logiciels nécessaires pour vos cours :\n\n"
                "• 📝 **Bureautique** : LibreOffice (Writer, Calc, Impress) pour tous vos rapports et présentations.\n"
                "• 🐍 **Programmation (SNT/NSI)** : Thonny, Python 3, GeoGebra, VS Code.\n"
                "• 🌐 **Navigateur & ENT** : Firefox préconfiguré avec vos favoris lycée et Pronote."
            )

        desc = QLabel(role_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; line-height: 1.5; color: #CDD6F4;")

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def create_help_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("🆘 Un problème ou une question ?")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89B4FA; margin-bottom: 10px;")

        desc = QLabel(
            "Si vous rencontrez un dysfonctionnement (logiciel manquant, problème d'écran, impression bloquée) :\n\n"
            "• Cliquez sur le bouton **« Signaler un problème »** situé dans votre menu ou la barre des tâches.\n"
            "• Le ticket sera automatiquement envoyé aux administrateurs réseau avec les détails techniques du poste."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; line-height: 1.5; color: #CDD6F4;")

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def update_nav_buttons(self, index):
        self.prev_btn.setEnabled(index > 0)
        if index == self.stacked_widget.count() - 1:
            self.next_btn.setText("Terminer")
        else:
            self.next_btn.setText("Suivant")

        for i, btn in enumerate(self.step_buttons):
            if i == index:
                btn.setStyleSheet("text-align: left; padding: 8px 12px; font-size: 13px; font-weight: bold; background-color: #45475A; color: #89B4FA; border-left: 3px solid #89B4FA;")
            else:
                btn.setStyleSheet("text-align: left; padding: 8px 12px; font-size: 13px; font-weight: normal; background-color: transparent; color: #CDD6F4; border: none;")

    def go_prev(self):
        current = self.stacked_widget.currentIndex()
        if current > 0:
            self.stacked_widget.setCurrentIndex(current - 1)

    def go_next(self):
        current = self.stacked_widget.currentIndex()
        if current < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(current + 1)
        else:
            self.finish()

    def finish(self):
        if self.dont_show_again.isChecked():
            config_dir = Path.home() / ".config" / "lyux"
            config_dir.mkdir(parents=True, exist_ok=True)
            marker = config_dir / ".welcomed"
            marker.write_text("1")
        self.close()

def main():
    app = QApplication(sys.argv)
    window = LyuxWelcomeWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
