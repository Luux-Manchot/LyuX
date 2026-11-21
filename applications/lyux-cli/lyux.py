#!/usr/bin/env python3
"""
LyuX CLI — Outil d'administration en ligne de commande pour le système LyuX (Opération Manchot).
Permet de piloter l'ensemble du système en SSH ou terminal local :
  - lyux status
  - lyux user list | reset-password | import-csv
  - lyux room list | lock | unlock
  - lyux enroll new | list
"""

import sys
import os
import argparse
import json
import urllib.request
import urllib.error

API_URL_DEFAULT = os.environ.get("LYUX_API_URL", "http://127.0.0.1:8000")

def _request(endpoint, method="GET", data=None, base_url=API_URL_DEFAULT):
    url = f"{base_url.rstrip('/')}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "LyuX-CLI/1.0")

    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data=payload, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return {}
    except urllib.error.URLError as e:
        print(f"\033[91m[ERREUR]\033[0m Impossible de joindre l'API LyuX ({url}) : {e}", file=sys.stderr)
        sys.exit(1)

def cmd_status(args):
    print("\033[1;36m=== État Général du Système LyuX ===\033[0m")
    health = _request("/health", base_url=args.api_url)
    status_icon = "🟢" if health.get("status") == "ok" else "🔴"
    print(f"API LyuX : {status_icon} {health.get('status', 'inconnu').upper()} (v{health.get('version', '1.0')})")

    # Salles
    rooms = _request("/api/v1/rooms", base_url=args.api_url)
    print(f"\n\033[1mSalles configurées ({len(rooms)}) :\033[0m")
    for r in rooms:
        print(f"  • Salle \033[33m{r.get('id', r.get('name'))}\033[0m : {r.get('name')} ({r.get('total_pcs', 0)} postes)")

    # Machines
    machines = _request("/api/v1/machines", base_url=args.api_url)
    print(f"\n\033[1mMachines enregistrées ({len(machines)}) :\033[0m")
    for m in machines[:10]:
        st = "🟢" if m.get("status") in ["online", "active"] else "⚪"
        print(f"  {st} \033[32m{m.get('hostname')}\033[0m (Salle: {m.get('room', 'N/A')}, IP: {m.get('ip', 'N/A')})")
    if len(machines) > 10:
        print(f"  ... et {len(machines) - 10} autre(s) machine(s)")

def cmd_user_list(args):
    users = _request("/api/v1/users", base_url=args.api_url)
    print(f"\033[1;36m=== Utilisateurs LyuX ({len(users)}) ===\033[0m")
    print(f"{'Identifiant':<20} {'Nom Complet':<25} {'Groupe':<15} {'Salle / Classe'}")
    print("-" * 75)
    for u in users:
        print(f"{u.get('username', ''):<20} {u.get('full_name', ''):<25} {u.get('role', u.get('group', '')): <15} {u.get('room', u.get('class', ''))}")

def cmd_user_reset_password(args):
    data = {
        "username": args.username,
        "new_password": args.password
    }
    res = _request("/api/v1/control/reset-password", method="POST", data=data, base_url=args.api_url)
    if res.get("status") in ["password_updated", "ok", "success"]:
        print(f"\033[92m[OK]\033[0m Mot de passe de \033[1m{args.username}\033[0m réinitialisé avec succès.")
    else:
        print(f"\033[93m[INFO]\033[0m Réponse serveur : {res}")

def cmd_room_list(args):
    rooms = _request("/api/v1/rooms", base_url=args.api_url)
    print("\033[1;36m=== Salles Pédagogiques ===\033[0m")
    for r in rooms:
        locked_badge = "🔴 Verrouillée" if r.get("locked") else "🟢 Active"
        print(f"• \033[1;33m{r.get('id', r.get('name'))}\033[0m : {r.get('name')} [{locked_badge}] — {r.get('total_pcs', 0)} postes")

def cmd_room_lock(args):
    data = {
        "room": args.room,
        "lock": True,
        "message": args.message or "Écrans verrouillés par l'administrateur."
    }
    res = _request("/api/v1/control/lock-room", method="POST", data=data, base_url=args.api_url)
    print(f"\033[92m[OK]\033[0m Salle \033[1m{args.room}\033[0m verrouillée : {res.get('message', 'Écrans bloqués')}")

def cmd_room_unlock(args):
    data = {
        "room": args.room,
        "lock": False,
        "message": ""
    }
    res = _request("/api/v1/control/lock-room", method="POST", data=data, base_url=args.api_url)
    print(f"\033[92m[OK]\033[0m Salle \033[1m{args.room}\033[0m déverrouillée.")

def cmd_enroll_new(args):
    data = {"role": "admin"}
    res = _request("/api/v1/enroll/generate-otp", method="POST", data=data, base_url=args.api_url)
    otp = res.get("otp", "N/A")
    exp = res.get("expires_in_minutes", 10)
    print(f"\033[1;32m✔ Nouveau code OTP d'enrôlement : \033[1;33m{otp}\033[0m")
    print(f"  Valable pendant {exp} minutes pour intégrer un nouveau poste.")

def main():
    parser = argparse.ArgumentParser(
        prog="lyux",
        description="LyuX CLI — Outil d'administration simple et direct pour le parc informatique LyuX."
    )
    parser.add_argument("--api-url", default=API_URL_DEFAULT, help="URL de l'API LyuX (par défaut: http://127.0.0.1:8000)")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Afficher l'état du système, des salles et des machines")
    p_status.set_defaults(func=cmd_status)

    # user
    p_user = subparsers.add_parser("user", help="Gestion des utilisateurs")
    user_subs = p_user.add_subparsers(dest="user_command", required=True)
    
    p_user_list = user_subs.add_parser("list", help="Lister les utilisateurs")
    p_user_list.set_defaults(func=cmd_user_list)
    
    p_user_reset = user_subs.add_parser("reset-password", help="Réinitialiser le mot de passe d'un utilisateur")
    p_user_reset.add_argument("username", help="Identifiant de l'élève ou prof (ex: lucas.martin)")
    p_user_reset.add_argument("password", help="Nouveau mot de passe")
    p_user_reset.set_defaults(func=cmd_user_reset_password)

    # room
    p_room = subparsers.add_parser("room", help="Gestion et supervision des salles")
    room_subs = p_room.add_subparsers(dest="room_command", required=True)

    p_room_list = room_subs.add_parser("list", help="Lister les salles et leur statut")
    p_room_list.set_defaults(func=cmd_room_list)

    p_room_lock = room_subs.add_parser("lock", help="Verrouiller tous les écrans d'une salle")
    p_room_lock.add_argument("room", help="Code de la salle (ex: B204, S102)")
    p_room_lock.add_argument("--message", default=None, help="Message à afficher sur les écrans élèves")
    p_room_lock.set_defaults(func=cmd_room_lock)

    p_room_unlock = room_subs.add_parser("unlock", help="Déverrouiller les écrans d'une salle")
    p_room_unlock.add_argument("room", help="Code de la salle (ex: B204, S102)")
    p_room_unlock.set_defaults(func=cmd_room_unlock)

    # enroll
    p_enroll = subparsers.add_parser("enroll", help="Gestion de l'enrôlement des machines")
    enroll_subs = p_enroll.add_subparsers(dest="enroll_command", required=True)

    p_enroll_new = enroll_subs.add_parser("new", help="Générer un nouveau code OTP d'enrôlement")
    p_enroll_new.set_defaults(func=cmd_enroll_new)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
