# ==============================================================================
# Script de preparation et lancement de l'installation automatique (Unattended)
# ==============================================================================

$VBox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$candidateIso = Join-Path $PSScriptRoot "..\iso\debian-netinst.iso"
$IsoPath = if (Test-Path $candidateIso) { (Resolve-Path $candidateIso).Path } else { (Get-ChildItem -Path (Resolve-Path "$PSScriptRoot\..\..") -Filter "*netinst.iso" -Recurse | Select-Object -First 1).FullName }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Configuration Unattended des Clients LyuX (Sans Question)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Configuration Unattended pour le Client Prof
Write-Host "[*] Configuration automatique de LyuX-Client-Prof..." -ForegroundColor Yellow
& $VBox unattended install "LyuX-Client-Prof" `
    --iso=$IsoPath `
    --user="lyux-admin" `
    --user-password="LyuxDeploy2026!" `
    --country="FR" `
    --time-zone="Europe/Paris" `
    --hostname="b204-prof.lyux.lan" `
    --install-additions

# Configuration Unattended pour le Client Eleve
Write-Host "[*] Configuration automatique de LyuX-Client-Eleve..." -ForegroundColor Yellow
& $VBox unattended install "LyuX-Client-Eleve" `
    --iso=$IsoPath `
    --user="lyux-admin" `
    --user-password="LyuxDeploy2026!" `
    --country="FR" `
    --time-zone="Europe/Paris" `
    --hostname="b204-01.lyux.lan" `
    --install-additions

Write-Host ""
Write-Host "[+] Pret ! Les machines s'installeront en pilote automatique complet." -ForegroundColor Green
