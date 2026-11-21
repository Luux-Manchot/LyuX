# 🎓 LyuX Import Siècle (`lyux-import-siecle`)

Ce module assure l'importation et la synchronisation des données scolaires depuis les exports XML/CSV ministériels **Siècle (BEE / Sconet)** et les ENT académiques vers l'annuaire OpenLDAP / Samba-AD de LyuX.

## Fonctionnalités
- Parsing des fichiers d'export XML des élèves, responsables et professeurs.
- Génération automatique des identifiants normalisés (`prenom.nom`).
- Création et affectation automatique des groupes de classes (`1G1`, `TG2`, etc.).
- Création automatique des arborescences de partages Samba et quotas disques.
