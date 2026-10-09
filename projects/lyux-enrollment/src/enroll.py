#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

# Fix universel d'encodage pour Windows et Linux
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent))

import argparse
import subprocess
import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from hardware import get_hardware_fingerprint
from discovery import discover_lyux_server

console = Console(highlight=False)

def run_enrollment(server_url: str, otp_code: str, room_id: str, is_teacher: bool = False):
    console.print(Panel.fit(
        "[bold cyan]🐧 LyuX Enrollment — Initialisation du Poste Client[/bold cyan]\n"
        "[dim]Opération Manchot — Système d'installation piloté par serveur[/dim]",
        border_style="cyan"
    ))

    # 1. Collecte matérielle
    console.print("\n[yellow]🔍 Étape 1/4 : Collecte des caractéristiques de la machine...[/yellow]")
    hw = get_hardware_fingerprint()
    console.print(f"  • Adresse MAC : [bold]{hw['mac_address']}[/bold]")
    console.print(f"  • Mémoire RAM : [bold]{hw['ram_mb']} Mo[/bold]")

    # 2. Interrogation de l'API Serveur
    console.print(f"\n[yellow]🌐 Étape 2/4 : Validation auprès du serveur LyuX ({server_url})...[/yellow]")
    payload = {
        "otp_code": otp_code,
        "room_id": room_id,
        "mac_address": hw["mac_address"],
        "serial_number": hw["serial_number"],
        "cpu_info": hw["cpu_info"],
        "ram_mb": hw["ram_mb"],
        "is_teacher_pc": is_teacher
    }

    try:
        resp = requests.post(f"{server_url}/api/v1/enroll/validate-otp", json=payload, timeout=10)
        if resp.status_code != 200:
            console.print(f"[bold red]❌ Erreur d'enrôlement ({resp.status_code}) : {resp.text}[/bold red]")
            sys.exit(1)
        data = resp.json()
    except Exception as e:
        console.print(f"[bold red]❌ Impossible de contacter le serveur LyuX : {e}[/bold red]")
        sys.exit(1)

    hostname = data["hostname"]
    profile = data["room_profile"]
    console.print(f"  ✅ Validation réussie !")
    console.print(f"  • Nom attribué : [bold green]{hostname}[/bold green]")
    console.print(f"  • Profil de salle : [bold magenta]{profile}[/bold magenta]")

    # 3. Application du nom d'hôte local
    console.print("\n[yellow]💻 Étape 3/4 : Configuration de l'identité système locale...[/yellow]")
    try:
        subprocess.run(["hostnamectl", "set-hostname", hostname], check=True)
        console.print(f"  • Nom d'hôte appliqué : {hostname}")
    except Exception:
        console.print(f"  ℹ️ (Mode simulation hôte : nom d'hôte virtuel = {hostname})")

    # 4. Déclenchement d'Ansible
    console.print("\n[yellow]⚙️ Étape 4/4 : Déploiement des logiciels et configuration (Ansible)...[/yellow]")
    console.print(f"  • Exécution du profil : [bold]{profile}[/bold]...")
    
    cmd = f"ansible-pull -U {data['ansible_pull_url']} playbooks/enroll.yml --extra-vars 'lyux_room_profile={profile}'"
    console.print(f"  • Commande : [dim]{cmd}[/dim]")

    # 5. Clôture de l'enrôlement et désactivation du service de démarrage
    try:
        os.makedirs("/etc/lyux", exist_ok=True)
        with open("/etc/lyux/enrolled.json", "w", encoding="utf-8") as f:
            json.dump({
                "hostname": hostname,
                "room_id": room_id,
                "profile": profile,
                "is_teacher_pc": is_teacher
            }, f, indent=2)
        subprocess.run(["systemctl", "disable", "lyux-enrollment.service"], check=False)
    except Exception:
        pass

    console.print(Panel.fit(
        f"[bold green]🎉 Enrôlement terminé avec succès pour {hostname} ![/bold green]\n"
        f"Le poste est configuré et prêt à l'emploi.",
        border_style="green"
    ))

def interactive_mode():
    console.print(Panel.fit("[bold cyan]Assistant d'enrôlement LyuX[/bold cyan]", border_style="cyan"))
    found, disc_url, _ = discover_lyux_server()
    default_url = disc_url if found else "http://127.0.0.1:8000"
    if found:
        console.print(f"  [green]🔍 Serveur LyuX découvert automatiquement : {default_url}[/green]")

    server_url = Prompt.ask("Adresse du serveur LyuX", default=default_url)
    otp_code = Prompt.ask("Code OTP d'enrôlement temporaire", default="LYUX-DEMO-2026")
    room_id = Prompt.ask("Identifiant de la salle", default="B204")
    is_teacher = Confirm.ask("S'agit-il du poste enseignant principal de la salle ?", default=False)
    run_enrollment(server_url, otp_code, room_id, is_teacher)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LyuX Machine Enrollment Tool")
    parser.add_argument("--server", help="URL du serveur LyuX")
    parser.add_argument("--otp", help="Code OTP temporaire")
    parser.add_argument("--room", help="Identifiant de la salle (ex: B204)")
    parser.add_argument("--teacher", action="store_true", help="Poste enseignant")

    args = parser.parse_args()

    if args.server and args.otp and args.room:
        run_enrollment(args.server, args.otp, args.room, args.teacher)
    else:
        interactive_mode()
