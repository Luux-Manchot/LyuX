# Migration d'un lycée vers Linux : dossier complet

🐧 **Opération Manchot**

Le projet de migration (le chantier global)

🐧 **LyuX**

Le système cible (la distribution installée sur les postes)

*Document de référence : infrastructure, usages par profil, logiciels compatibles et non compatibles, plan de migration.*

> **À lire d'abord.** Les versions de logiciels, les durées de support des distributions et la disponibilité des versions Linux des logiciels éditeurs changent régulièrement. Ce document donne une base solide, mais **chaque point marqué « à tester » ou « à vérifier » doit être validé sur une salle pilote** avant tout déploiement général.

## 1. Objectif et principes directeurs

L'objectif est que **chaque élève, enseignant et agent administratif** puisse s'asseoir à n'importe quel poste du lycée, ouvrir sa session avec son propre compte, retrouver ses fichiers et utiliser les logiciels dont il a besoin pour travailler.

Cinq principes guident toutes les décisions :

1. **Un compte par personne**, géré de façon centralisée (jamais de comptes créés poste par poste).
2. **Les données sur le serveur, pas sur le poste** : un PC en panne ne doit faire perdre aucun fichier.
3. **Des postes identiques et remplaçables** : on doit pouvoir réinstaller un PC en quelques minutes.
4. **Tout ce qui est répétitif est automatisé** (création de comptes, installation de logiciels, mises à jour).
5. **La migration est d'abord humaine** : la plupart des échecs viennent du manque de formation et d'accompagnement, pas de la technique.

## 2. Vue d'ensemble de l'architecture

Voici comment les briques s'articulent. Chaque ligne est détaillée dans les sections suivantes.

| Brique | Rôle | Outils proposés |
| --- | --- | --- |
| Postes clients | Ce que les utilisateurs manipulent | Linux + KDE Plasma |
| Annuaire | Liste centrale des comptes et des groupes | OpenLDAP ou Samba-AD |
| Serveur de fichiers | Stocke les dossiers personnels et partagés | Samba ou NFS |
| Déploiement | Installer et cloner les postes | PXE + FOG ou Clonezilla |
| Configuration automatique | Appliquer les réglages à tous les postes | Ansible |
| Réseau | Adresses, noms, Wi-Fi | DHCP, DNS, bornes Wi-Fi |
| Filtrage web | Obligation légale et protection des mineurs | Proxy (Squid, SquidGuard ou équivalent) |
| Impression | Imprimantes partagées | CUPS |
| Outils de classe | Supervision par l'enseignant | Veyon |
| Sauvegarde | Protéger les données | Sauvegardes automatiques chiffrées |
| Supervision | Savoir quand quelque chose tombe en panne | Zabbix ou équivalent |

**Raccourci possible :** la distribution **Debian Edu (Skolelinux)** embarque déjà annuaire, serveur de fichiers, impression, proxy et postes préconfigurés avec KDE Plasma. Elle réduit fortement le travail d'intégration. En France, la solution **EOLE** du ministère de l'Éducation nationale est une autre piste à étudier, notamment si votre académie la propose ou la soutient.

## 3. Choix du système : distribution et bureau

### 3.1 Distribution (la base du système)

| Option | Avantages | Inconvénients | Quand la choisir |
| --- | --- | --- | --- |
| **Debian Edu** | Infrastructure scolaire prête à l'emploi, très stable, KDE par défaut | Logiciels plus anciens | Peu de temps technique, besoin de fiabilité |
| **Kubuntu LTS** | Logiciels récents, paquets éditeurs fournis en priorité pour Ubuntu | Support LTS des « saveurs » plus court que celui d'Ubuntu standard (**à vérifier** sur le site du projet) | Besoin de logiciels récents (NSI, Packet Tracer) |
| **Debian Stable + Plasma** | Contrôle total, stabilité maximale | Plus de travail d'intégration | Équipe technique expérimentée |

**À éviter** pour un établissement : Fedora et Ubuntu non-LTS (cycles de 6 mois, trop de changements), Arch et Tumbleweed (mises à jour en continu, trop imprévisibles pour des centaines de postes).

### 3.2 Environnement de bureau : KDE Plasma

L'environnement de bureau est la partie que l'utilisateur voit (menu, barre, fenêtres). **KDE Plasma** est recommandé pour les raisons suivantes :

- **Il ressemble à Windows** (barre en bas, menu, icônes), ce qui réduit le temps d'adaptation des élèves et des enseignants.
- **Il est verrouillable** grâce au système **KDE Kiosk** : on peut interdire de modifier la barre des tâches, de lancer certains programmes, etc. Le poste reste identique chaque matin.
- **Sa configuration est en fichiers texte**, donc déployable sur tous les postes avec Ansible.
- **Il est complet** : gestionnaire de fichiers Dolphin, multi-écrans, accessibilité correcte.

**Points de vigilance :**

- **Wayland ou X11 :** Plasma 6 utilise Wayland par défaut, mais certains outils de classe, **Veyon** en particulier, fonctionnent mieux ou uniquement sous X11. C'est **le premier test à faire** sur la salle pilote.
- **Vieux PC :** en dessous de 4 Go de RAM ou avec un processeur très ancien, préférer **XFCE** ou **LXQt**.
- **Trop configurable :** sans Kiosk, un élève peut dérégler son bureau.

## 4. Annuaire et gestion des comptes

### 4.1 Principe

Quand un utilisateur tape son identifiant et son mot de passe, le PC ne vérifie rien lui-même : il interroge le **serveur d'annuaire** (OpenLDAP ou Samba-AD), qui répond si le couple est valide **et** à quels groupes appartient la personne. Le poste applique ensuite les droits correspondants.

### 4.2 Règles à fixer en amont

- **Identifiants :** format `prenom.nom`, avec une règle pour les homonymes (`prenom.nom2`).
- **Groupes :** élèves (un groupe par classe), enseignants, administration, vie scolaire, techniciens. Les droits sont donnés **aux groupes**, jamais aux individus.
- **Mots de passe :** mot de passe provisoire à la première connexion, changement obligatoire, longueur minimale raisonnable. Éviter les règles trop lourdes : elles poussent à écrire le mot de passe sur un post-it.
- **Cycle de vie :** création des comptes à la rentrée, archivage ou suppression au départ de l'élève. Avec plusieurs centaines d'élèves, cela **doit être automatisé** (import d'un fichier CSV exporté de l'outil de gestion des élèves).
- **Synchronisation avec l'ENT :** si l'ENT existe déjà, synchroniser l'annuaire dessus pour que chacun garde le même identifiant partout (**à vérifier** avec le prestataire de l'ENT).

### 4.3 Mot de passe oublié : trois niveaux de secours

Le but est qu'un oubli ne bloque jamais un cours de 30 élèves.

1. **Réinitialisation par l'enseignant** (droit délégué, limité à ce seul geste) via une petite interface web comme LDAP Account Manager. Le prof génère un mot de passe provisoire, l'élève doit en choisir un nouveau immédiatement. Le prof ne connaît jamais le vrai mot de passe.
2. **Réinitialisation en libre-service** par l'élève via un code envoyé par mail (outil **Self Service Password**). Cela demande une adresse mail valide pour chaque compte.
3. **Compte de dépannage de salle** (ex. `invite-salle1`), très limité : aucun accès aux dossiers des autres, session **effacée à la déconnexion**, travail enregistré sur clé USB ou envoyé par ENT.

**Interdit :** utiliser le compte d'un camarade ou d'un enseignant. Cela casse la séparation des données et la traçabilité.

**Blocage après trop d'essais :** le compte se verrouille temporairement après plusieurs échecs, pour empêcher quelqu'un de deviner un mot de passe. Le déblocage est assuré par la vie scolaire ou l'administrateur réseau, selon une procédure affichée en salle.

## 5. Stockage et sauvegardes

### 5.1 Où sont les fichiers

- **Dossier personnel** (`Documents`, bureau) : stocké sur le serveur de fichiers, accessible depuis n'importe quel poste.
- **Dossiers partagés par classe ou matière :** l'enseignant dépose des documents, les élèves les récupèrent (lecture seule) ou y rendent leur travail (dossier de dépôt).
- **Quotas :** limite d'espace par élève pour éviter qu'un compte sature le serveur.
- **Dossiers des enseignants et de l'administration :** séparés, avec droits distincts. Les données sensibles (notes, dossiers d'élèves) ne sont jamais accessibles aux élèves.

### 5.2 Sauvegardes

- **Sauvegarde automatique quotidienne** des serveurs (annuaire, fichiers, configurations).
- **Règle du 3-2-1 :** 3 copies des données, sur 2 supports différents, dont 1 hors du lycée.
- **Test de restauration régulier :** une sauvegarde jamais testée n'est pas une sauvegarde.
- **Postes clients :** non sauvegardés (ils sont remplaçables), puisque les données sont sur le serveur.

## 6. Réseau, filtrage et sécurité

- **DHCP et DNS** : attribution automatique des adresses et des noms.
- **Segmentation du réseau :** séparer les réseaux élèves, enseignants, administration et serveurs. Une faille d'un côté ne doit pas donner accès à tout le reste.
- **Wi-Fi :** authentification individuelle (comptes de l'annuaire), pas un mot de passe unique partagé.
- **Filtrage web avec journalisation :** obligation légale pour un établissement accueillant des mineurs. À mettre en place avec le proxy, en lien avec le référent numérique et la direction.
- **Mises à jour de sécurité** automatisées sur les postes et les serveurs.
- **Comptes d'administration :** peu nombreux, nominatifs, protégés par une authentification renforcée si possible.
- **Protection contre les rançongiciels :** sauvegardes hors ligne et séparation des droits (un compte élève ne doit jamais pouvoir modifier les sauvegardes).

## 7. Déploiement et maintenance des postes

1. **Image modèle :** installer un poste de référence complet, le tester, puis le cloner.
2. **Installation en réseau (PXE)** avec FOG ou Clonezilla : un poste vierge démarre sur le réseau et reçoit l'image automatiquement.
3. **Ansible :** permet d'installer un logiciel, de changer un réglage ou de déployer une mise à jour sur tous les postes (ou seulement une salle) en une commande.
4. **Réparation rapide :** poste défaillant = réinstallation par le réseau, sans perte de données.
5. **Supervision :** un outil (ex. Zabbix) alerte en cas de serveur saturé, de disque presque plein ou de poste hors ligne.
6. **Fenêtre de mise à jour :** les mises à jour majeures se font pendant les vacances, jamais en pleine semaine de cours.

## 8. Outils de classe

| Besoin | Outil | Remarque |
| --- | --- | --- |
| Voir/verrouiller les écrans, projeter l'écran du prof | **Veyon** | À tester avec Wayland/X11 |
| Tableau numérique interactif | **OpenBoard** (libre) ou **ActivInspire** (Promethean) | SMART Notebook n'existe pas sous Linux |
| Impression | **CUPS** | Compatibilité des imprimantes à vérifier avant achat |
| Dépôt et récupération de travaux | ENT, Moodle ou dossiers partagés |  |
| Visioconférence | BigBlueButton, Jitsi, Teams web | Pas de client Teams Linux natif, version web utilisable |

## 9. Ce que chaque profil utilisera

### 9.1 Les élèves

- Session personnelle avec leurs fichiers où qu'ils soient.
- LibreOffice, navigateur web, ENT, Pronote (version web), Moodle.
- Logiciels de discipline (Python, GeoGebra, Scratch, QGIS, etc., voir section 10).
- Pas de droits d'administration, pas d'installation de logiciels.
- Clé USB autorisée selon la politique de l'établissement (à décider avec la direction).
- Accès internet filtré et journalisé.

### 9.2 Les enseignants

- Même environnement que les élèves, avec des droits supplémentaires : supervision de salle (Veyon), réinitialisation des mots de passe élèves, dossiers de dépôt, impression étendue.
- Pronote (web), ENT, outils de TNI, logiciels de leur discipline.
- **Formation indispensable** avant la bascule, avec une fiche d'équivalences « avant/après » (ex. Word, LibreOffice Writer).

### 9.3 Administration et vie scolaire

- **Poste à traiter à part.** Beaucoup de logiciels de gestion (Pronote client administrateur, emplois du temps, comptabilité) sont uniquement Windows ou imposés par l'académie ou la région.
- Dans la plupart des cas, **les postes administratifs restent sous Windows au moins dans un premier temps**, ou passent par un bureau virtuel.
- Données personnelles sensibles : droits d'accès stricts et journalisation.

### 9.4 L'équipe technique

- Comptes d'administration nominatifs.
- Documentation à jour de l'architecture, des procédures et des mots de passe de secours (stockés dans un coffre-fort de mots de passe).
- Au moins **deux personnes** formées : un seul administrateur est un risque majeur.

## 10. Logiciels : compatibilité et remplaçants

**Légende :** ✅ natif Linux · 🌐 dans le navigateur · ☕ multiplateforme (Java, Qt) · 🍷 Wine ou machine virtuelle, à tester · ❌ Windows uniquement

### 10.1 Bureautique et usages généraux

| Logiciel | Statut | Solution sous Linux |
| --- | --- | --- |
| LibreOffice, OnlyOffice | ✅ | Remplacent Office pour la grande majorité des usages |
| Microsoft Office | ❌ | Microsoft 365 en ligne 🌐 ou LibreOffice |
| Access | ❌ | LibreOffice Base (partiel) |
| Acrobat Reader | ❌ | Okular, Evince, navigateur |
| Firefox, Chromium | ✅ |  |
| VLC, Audacity | ✅ |  |
| Zotero, Freeplane | ✅ |  |
| LaTeX, Overleaf | ✅ / 🌐 |  |

### 10.2 Gestion de l'établissement

| Logiciel | Statut | Solution |
| --- | --- | --- |
| Pronote (accès web) | 🌐 | Suffisant pour élèves et enseignants |
| Pronote (client administrateur), Hyperplanning, EDT (conception) | ❌ | Poste Windows ou bureau virtuel |
| ENT, Moodle, Cyclades, Parcoursup | 🌐 |  |
| BCDI (gestion du CDI) | ❌ | PMB 🌐 en alternative libre |
| Sage, Ciel, EBP (comptabilité) | ❌ | Poste Windows ou alternative libre (Dolibarr, Odoo) |

### 10.3 Mathématiques, informatique (SNT, NSI)

| Logiciel | Statut | Solution |
| --- | --- | --- |
| Python, Thonny, Jupyter, Spyder | ✅ |  |
| Capytale, Basthon | 🌐 | Très utilisés au lycée |
| GeoGebra | ✅ / 🌐 |  |
| Xcas, Maxima, SageMath, Scilab, Octave | ✅ |  |
| AlgoBox, MathGraph32, Filius | ☕ | Java requis |
| EduPython | ❌ | Thonny |
| Cabri Géomètre | ❌ | GeoGebra |
| Émulateurs TI-Nspire, Casio | ❌ | Émulateur NumWorks 🌐 |
| Cisco Packet Tracer | ✅ | Compte Cisco requis |
| VS Code, Git, GCC, JDK, Arduino IDE, Wireshark | ✅ |  |

### 10.4 Physique-chimie

| Logiciel | Statut | Solution |
| --- | --- | --- |
| Pymecavideo, Tracker | ✅ / ☕ |  |
| Régressi | ❌ / 🍷 | À tester avec Wine, résultats variables |
| LatisPro, Généris | ❌ | Poste Windows dédié aux TP |
| Cartes d'acquisition (Sysam, Orphy…) | ❌ / 🍷 | **Les pilotes matériels sont le vrai blocage** |
| PhET | 🌐 |  |
| Avogadro, Jmol, Stellarium | ✅ / ☕ |  |
| ChemSketch | ❌ | MarvinSketch (☕), Avogadro |

### 10.5 SVT, histoire-géographie

| Logiciel | Statut | Solution |
| --- | --- | --- |
| Anagène, EduAnat2 | ☕ / 🌐 | Selon la version |
| Mesurim | ❌ / 🍷 | ImageJ ☕ |
| Phylogene, Sismolog, Tectoglob 3D | ❌ / 🍷 | À tester un par un |
| QGIS, Google Earth Pro, GIMP | ✅ |  |
| Philcarto, Cartes & Données | ❌ / 🍷 | QGIS, Magrit 🌐 |
| uMap, Géoportail, Edugéo | 🌐 |  |

### 10.6 Sciences de l'ingénieur, STI2D, filières professionnelles

**C'est le point le plus délicat de toute la migration.**

| Logiciel | Statut | Solution |
| --- | --- | --- |
| SolidWorks, Inventor, AutoCAD, Catia | ❌ | Poste Windows ou bureau virtuel ; FreeCAD, Onshape 🌐 pour l'initiation |
| Fusion 360 | ❌ / 🌐 | Pas de client Linux officiel |
| FreeCAD, SolveSpace, Blender, KiCad | ✅ | Alternatives libres |
| Proteus, Multisim | ❌ | KiCad |
| LTspice | 🍷 | ngspice, Qucs |
| MATLAB/Simulink, LabVIEW | ✅ | Licences payantes |
| TIA Portal, EcoStruxure, Automgen (automates) | ❌ | Windows, liés au matériel industriel |
| Lego Mindstorms / Spike | ❌ / 🌐 | Selon la version |
| Cura, PrusaSlicer | ✅ |  |
| Logiciels de commande numérique, diagnostic automobile, caisse hôtelière, PAO textile | ❌ | Presque toujours Windows et liés à du matériel |

### 10.7 Économie-gestion, arts, musique

| Logiciel | Statut | Solution |
| --- | --- | --- |
| Excel avec macros VBA complexes | ❌ | LibreOffice gère mal les macros VBA complexes |
| Photoshop, Illustrator, InDesign, Premiere, After Effects | ❌ | GIMP, Krita, Inkscape, Scribus, Kdenlive |
| Sibelius, Finale | ❌ | MuseScore |
| Cubase, Ableton, Logic | ❌ | Ardour, LMMS |
| Blender, Darktable | ✅ |  |

### 10.8 Accessibilité

| Logiciel | Statut | Solution |
| --- | --- | --- |
| NVDA, JAWS | ❌ | Orca (lecteur d'écran Linux), compatibilité moindre avec certains logiciels |
| Dragon NaturallySpeaking | ❌ | Pas d'équivalent complet |
| LireCouleur, OpenDyslexic, eSpeak | ✅ |  |

**Règle :** tout outil d'aide à un élève à besoins particuliers doit être **testé avec l'élève et l'équipe de suivi** avant de migrer son poste.

## 11. Ce qui ne pourra pas être remplacé : synthèse et solutions

Trois familles de logiciels n'ont pas d'équivalent satisfaisant :

1. **Logiciels industriels (CAO, automates, commande numérique)** : liés aux référentiels de formation et aux examens.
2. **Logiciels de gestion et de comptabilité** : formats et usages imposés par le monde professionnel.
3. **Logiciels liés à du matériel** (acquisition de physique, diagnostic automobile) : pilotes Windows uniquement.

Quatre stratégies, utilisables ensemble :

| Stratégie | Principe | Limites |
| --- | --- | --- |
| **Salles Windows conservées** | Quelques salles ou postes spécialisés restent sous Windows | Maintenance de deux parcs |
| **Bureau virtuel (VDI)** | Les élèves accèdent à un Windows hébergé sur un serveur depuis leur poste Linux | Serveur puissant, licences, performances graphiques (CAO) |
| **Machines virtuelles locales** | Windows dans une VM sur le poste Linux | Gourmand en ressources ; pilotes USB parfois problématiques |
| **Wine** | Fait tourner certains logiciels Windows directement | Résultats variables, pas de support éditeur, **jamais pour un usage critique sans test** |

La solution réaliste pour un lycée avec filières technologiques ou professionnelles est **mixte** : Linux pour la grande majorité des usages, Windows pour une minorité de postes spécialisés.

## 12. Conformité : RGPD et cadre légal

- **Registre des traitements** : liste de ce qui est collecté (comptes, journaux de connexion, fichiers).
- **Minimisation :** ne conserver que ce qui est nécessaire, pendant une durée définie.
- **Journaux de filtrage web :** conservés selon la durée légale, accessibles seulement aux personnes habilitées.
- **Information des utilisateurs :** charte informatique à signer par élèves (et responsables légaux) et enseignants.
- **Interlocuteurs :** le délégué à la protection des données (DPD) de l'académie ou de la région, et le chef d'établissement. Ce document n'est pas un avis juridique : à valider avec eux.
- **Responsabilités :** la région finance et gère souvent le matériel et les réseaux, l'établissement les usages. **Clarifier qui décide de quoi** avant de commencer.

## 13. Plan de migration par étapes

| Phase | Contenu | Durée indicative |
| --- | --- | --- |
| **0. Cadrage** | Accord de la direction, de la région et de l'académie ; budget ; désignation d'un chef de projet et d'au moins deux techniciens | 1 à 2 mois |
| **1. Inventaire** | Questionnaire aux enseignants et services : logiciels réellement utilisés, matériel connecté, besoins d'accessibilité. Classement avec la légende de la section 10 | 1 mois |
| **2. Infrastructure** | Serveurs, annuaire, fichiers, réseau, filtrage, sauvegardes, supervision | 2 à 3 mois |
| **3. Salle pilote** | Une salle, des enseignants volontaires, les vrais logiciels. Test de Veyon, impression, TNI, périphériques | 1 à 2 mois |
| **4. Correction** | Résoudre les problèmes du pilote, ajuster l'image, rédiger les procédures | 1 mois |
| **5. Formation** | Enseignants, vie scolaire, élèves (courte présentation en début d'année) | En continu |
| **6. Déploiement progressif** | Salle par salle, de préférence pendant les vacances | 1 à 2 trimestres |
| **7. Suivi** | Support de proximité les premières semaines, collecte des retours, amélioration continue | Permanent |

Les durées sont **indicatives** et dépendent des moyens humains disponibles.

**Retour arrière :** garder la possibilité de remettre l'ancien système sur une salle pendant la phase pilote, pour ne pas bloquer les cours en cas de problème grave.

## 14. Formation et accompagnement

- **Enseignants :** ateliers pratiques de 1 à 2 heures, fiche d'équivalences, référent par discipline. C'est le facteur n°1 de réussite.
- **Élèves :** brève présentation (session, enregistrement des fichiers, mot de passe).
- **Vie scolaire et administration :** procédures de déblocage de compte et de dépannage de premier niveau.
- **Support :** un point de contact clair (adresse, ticket ou bureau), avec délai de réponse annoncé. Un outil de tickets simple (GLPI, par exemple) suffit.

## 15. Risques principaux et réponses

| Risque | Conséquence | Réponse |
| --- | --- | --- |
| Logiciel indispensable non compatible | Cours bloqué | Inventaire en amont, postes Windows de repli |
| Pilotes de matériel absents | TP impossibles | Tester le matériel dès le pilote |
| Rejet par les enseignants | Échec du projet | Volontaires d'abord, formation, écoute |
| Un seul administrateur | Arrêt en cas d'absence | Équipe d'au moins deux personnes, documentation |
| Panne de serveur | Plus de connexion possible | Sauvegardes testées, plan de reprise, serveur de secours si possible |
| Wayland/X11 incompatible avec Veyon | Supervision de salle indisponible | Tester dès le début, choisir X11 si nécessaire |
| Mauvaise estimation du temps | Retards | Phases réalistes, déploiement progressif |

## 16. Liste de contrôle finale

**Avant de commencer :**

- [ ] Accord de la direction, de la région et de l'académie
- [ ] Chef de projet et équipe technique désignés (au moins 2 personnes)
- [ ] Inventaire des logiciels et matériels réalisé
- [ ] Âge et état du parc de PC connus

**Infrastructure :**

- [ ] Annuaire installé et import automatique des comptes testé
- [ ] Serveur de fichiers et quotas configurés
- [ ] Sauvegardes automatiques et restauration testée
- [ ] Réseau segmenté, Wi-Fi authentifié, filtrage web journalisé
- [ ] Supervision en place

**Postes :**

- [ ] Image modèle validée
- [ ] Verrouillage KDE Kiosk testé
- [ ] Veyon, impression, TNI fonctionnels
- [ ] Procédures de réinstallation rapide documentées

**Humain :**

- [ ] Enseignants formés, fiche d'équivalences distribuée
- [ ] Procédure « mot de passe oublié » affichée en salle
- [ ] Charte informatique signée
- [ ] Point de support identifié

**Conformité :**

- [ ] Registre des traitements RGPD à jour
- [ ] Durée de conservation des journaux définie
- [ ] Validation par le DPD

## 17. Conclusion

Une migration de lycée vers Linux est **réalisable et durable**, à condition de respecter trois règles : **tester avant de déployer** (salle pilote), **ne pas chercher le 100 % Linux** (conserver quelques postes Windows pour les logiciels industriels et administratifs), et **investir dans l'accompagnement humain**. Avec Debian Edu ou une distribution LTS associée à KDE Plasma, la majeure partie des usages pédagogiques est couverte sans difficulté, et la part de logiciels disponibles dans le navigateur augmente chaque année.

## Annexe A. Installation par clé USB « légère », pilotée par le serveur

Cette annexe décrit un système unique pour tous les types de lycées (général, technologique, professionnel) : **la clé ne contient presque rien, et c'est le serveur de l'établissement qui décide de ce que le poste devient.**

### A.1 Principe : clé minimale, serveur maître

La clé n'embarque que le nécessaire pour démarrer : un système de base, l'assistant d'enrôlement et la liste des serveurs connus. Tout le reste (logiciels, réglages, droits, dépendances) est **téléchargé depuis le serveur choisi**.

**Pourquoi c'est la bonne approche :**

- **Une seule clé pour tous les établissements** : seul le serveur sélectionné change le résultat.
- **Pas de clé à refaire** quand un logiciel change : on modifie le serveur, pas la clé.
- **Sécurité** : une clé perdue ne contient ni mot de passe, ni configuration spécifique à un lycée.
- **Cohérence** : tous les postes d'un établissement reçoivent la même source de vérité.

### A.2 Déroulement de l'enrôlement d'un nouveau poste

1. **Démarrage sur la clé.** Le système de base s'installe sans intervention (fichier de réponses *preseed* ou *autoinstall*).
2. **Choix du serveur.** L'assistant liste les serveurs détectés sur le réseau (ou propose de saisir une adresse). L'administrateur choisit son établissement.
3. **Authentification de l'administrateur.** Identifiant et mot de passe saisis sur le poste, vérifiés par le serveur. Option plus sûre : un **code d'enrôlement à usage unique**, généré par le serveur et valable quelques minutes.
4. **Informations du poste.** Salle (liste proposée par le serveur), nom du poste (proposé automatiquement, ex. `B204-03`), type de salle si nécessaire.
5. **Le serveur prend le relais.** Il envoie au poste son profil : jonction à l'annuaire, liste de logiciels de la salle, règles de droits, paramètres réseau, dépôts de paquets de l'établissement.
6. **Installation des dépendances.** Le poste télécharge et installe tout ce que le serveur déclare, y compris les bibliothèques nécessaires aux logiciels.
7. **Enregistrement dans l'inventaire** (salle, nom, numéro de série, version) puis redémarrage.

**Adresse IP :** les postes la reçoivent automatiquement (DHCP). L'administrateur n'indique que l'adresse du **serveur**, jamais celle du poste.

### A.3 Comment le serveur adapte chaque poste

Le serveur contient un **catalogue de profils** (par exemple géré avec Ansible, en mode *pull* : le poste vient chercher sa configuration). Chaque profil est un ensemble de logiciels et de réglages.

| Élément | Ce que décide le serveur |
| --- | --- |
| **Socle commun** | Installé sur tous les postes : bureautique, navigateur, Python, GeoGebra, Veyon, lecteurs |
| **Profil de salle** | Technologie, physique-chimie, informatique, arts, vie scolaire, administration, etc. |
| **Demandes spécifiques** | Un enseignant ou un service demande un logiciel : l'administrateur l'ajoute au profil concerné (une salle, un groupe de salles ou tout l'établissement) |
| **Dépendances** | Résolues automatiquement par le gestionnaire de paquets, depuis un dépôt local ou miroir du lycée |
| **Paramètres d'établissement** | ENT, proxy, imprimantes, page d'accueil du navigateur, logo |

**Mises à jour continues.** Le poste réapplique son profil périodiquement (par exemple chaque nuit). Ajouter un logiciel demandé par un enseignant revient donc à **modifier le profil sur le serveur** : le logiciel apparaît sur les postes concernés sans aucune intervention physique.

**Bonnes pratiques :**

- Un **dépôt local (miroir)** des paquets sur le serveur : installations plus rapides, moins de bande passante, et possibilité de **valider les versions** avant de les distribuer.
- Un **environnement de test** : tout nouveau profil ou toute mise à jour passe d'abord sur une salle pilote.
- Un **historique** des changements de configuration (gestion de versions de type Git) pour pouvoir revenir en arrière.
- Des **groupes de déploiement** : on applique un changement à une salle, on vérifie, puis on étend.

### A.4 Un poste unique pour tous, des droits selon le compte

Il n'y a **pas de poste « élève » et de poste « professeur »**. Le poste est identique, et trois couches adaptent l'expérience selon le compte :

- **L'annuaire** indique le groupe de la personne.
- **Le serveur de fichiers** applique les droits sur les données.
- **Le poste** adapte le bureau (menus, outils visibles, réglages verrouillés) selon le groupe.

| Capacité | Élève | Enseignant | Vie scolaire / administration | Technicien |
| --- | --- | --- | --- | --- |
| Ouvrir une session sur n'importe quel poste | Oui | Oui | Oui | Oui |
| Logiciels du profil de la salle | Oui | Oui | Oui | Oui |
| Superviser les écrans (Veyon) | Non | Oui | Non | Oui |
| Réinitialiser un mot de passe élève | Non | Oui | Oui | Oui |
| Dossiers de dépôt des classes | Non | Oui | Non | Oui |
| Installer des logiciels, modifier le système | Non | Non | Non | Oui |

**Règle de sécurité essentielle :** un droit refusé doit l'être **côté système ou serveur**, pas seulement par un menu masqué. Cacher un outil est de l'ergonomie ; l'interdire dans la configuration est de la sécurité.

### A.5 Signalement d'un problème depuis le poste

Un bouton **« Signaler un problème »** est présent sur tous les postes :

- le formulaire est **prérempli** (poste, salle, identifiant, heure, informations système) ;
- l'utilisateur choisit une catégorie (écran, logiciel, impression, mot de passe), ajoute une phrase et, s'il le souhaite, une capture d'écran ;
- un **ticket est créé automatiquement** dans l'outil de suivi (par exemple GLPI) vu par l'équipe technique ;
- l'utilisateur reçoit une confirmation et peut suivre l'état de sa demande.

### A.6 Assistant de bienvenue au premier usage

Au premier login d'un compte (détecté par l'absence d'un marqueur dans le dossier personnel), un assistant pas à pas s'ouvre. Il **lit le groupe de l'utilisateur** et adapte son contenu :

1. **Bienvenue** : « Vous êtes enseignant, voici votre bureau. »
2. **Vos fichiers** : où ils sont, comment ils suivent l'utilisateur d'un poste à l'autre.
3. **Votre mot de passe** : choisir le mot de passe définitif.
4. **Vos outils** : ceux de votre profil (supervision de salle, dépôt de documents, impression).
5. **Vos droits** : ce qui est possible et ce qui ne l'est pas (« vous pouvez réinitialiser le mot de passe d'un élève, vous ne pouvez pas installer de logiciel »).
6. **Besoin d'aide** : bouton de signalement, et contact de l'administrateur pour toute demande de droit ou de logiciel.

Le contenu pour un élève est plus court ; celui d'un administrateur rappelle les procédures sensibles. Le bouton « Revoir la présentation » reste disponible.

### A.7 Ce qui existe déjà et ce qu'il faut créer

| Composant | Existant ou à créer |
| --- | --- |
| Installation automatique du système de base | Existant, à configurer |
| Annuaire, serveur de fichiers, impression, filtrage | Existant |
| Installation et mise à jour des logiciels par profil | Existant (Ansible), profils à écrire |
| Inventaire et tickets | Existant (par exemple GLPI) |
| Assistant d'enrôlement (choix du serveur, salle, authentification) | À créer : script avec interface simple |
| Bouton « Signaler un problème » | À créer : petit programme relié à l'outil de tickets |
| Assistant de bienvenue par rôle | À créer : petit programme et contenu rédigé |
| Droits par groupe | Existant (KDE Kiosk, Veyon, serveur de fichiers), règles à définir |

Les trois programmes à créer sont de taille modeste. Le gros du travail est dans la configuration, les profils et les tests.

### A.8 Points de vigilance

- **Disponibilité du serveur :** si le serveur tombe, un nouveau poste ne peut pas s'enrôler, et les postes déjà installés doivent continuer à fonctionner avec leur dernière configuration connue. À tester explicitement.
- **Authenticité du serveur :** l'assistant doit vérifier qu'il parle au vrai serveur de l'établissement (certificat), pour qu'un faux serveur sur le réseau ne puisse pas installer n'importe quoi.
- **Logiciels Windows uniquement :** pour les filières technologiques et professionnelles, les profils ne peuvent pas installer SolidWorks, les automates ou la comptabilité. Prévoir un accès à un bureau Windows virtuel ou des postes dédiés, comme en section 11.
- **Maintenance de la clé :** même minimale, elle doit être versionnée et regénérée régulièrement.
- **Gouvernance :** si le système sert plusieurs établissements, décider qui maintient la clé, les profils de base et les outils (région, académie ou établissement).
