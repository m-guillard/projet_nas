# Projet NAS - Automatisation du réseau

## Description du projet
Le but de ce projet est d'automatiser la connexion entre les routeurs à partir d'un fichier d'intention. C'est la continuité du projet GNS. En plus, de ce dernier, on fournit des services BGP/MPLS.

## Fontionnalités implémentées
- Adressage automatique en IPV4 (adresse physique et adresse de Loopback)
- Implémentation OSPFv2 au sein de l'AS et de BGP en Inter-AS
- Configuration MP-BGP, LDP
- Configuration des VRF
- Drag and drop automatique des fichiers de configurations
- Route reflection
- Partage de VPN

## Lancer le projet
### Drag and drop automatique
Pour lancer le projet : py main_sans_community.py INTENT_FILE_JSON CHEMIN_PROJET_GNS


## Contributeurs
Anaïs DAGNET, Alice INVERNIZZI et Marion GUILLARD
