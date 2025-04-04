from datetime import datetime
import json
import os
import shutil
import sys

def afficher_dico(dico, message=""):
    """Affiche le contenu d'un dictionnaire de manière lisible avec un message optionnel."""
    if message:
        print(message)
    print(json.dumps(dico, indent=4, ensure_ascii=False))

def definir_liens_routeurs(donnees_reseau):
    """
    Transforme le JSON pour pouvoir générer les adresses IPv6.
    Paramètres :
    - donnees_reseau(dict): dictionnaire json du fichier d'intention
    Return(dict): dictionnaire qui pour chaque routeur renvoie ses voisins avec son numéro d'AS,
    le protocole de communication, son adresse IP et son interface
    """
    liens = {}
    compteur_lien = 1  # Compteur pour générer des numéros de lien uniques

    # Traitement des routeurs internes à chaque AS
    for as_data in donnees_reseau["AS"]:
        id_as = as_data["id_AS"]
        prefixe_reseau = as_data["prefixe_reseau"]

        # Parcours des routeurs dans l'AS
        for routeur in as_data["routeur"]:
            routeur_num = routeur["id_routeur"]
            adresse_as = as_data["prefixe_reseau"]
            protocoles = as_data["protocole_routage"]
            masque = as_data["masque_reseau"]

            # Si le routeur n'a aucun voisin, on l'initialise
            if routeur_num not in liens:
                liens[routeur_num] = []

            # Ajouter une adresse loopback pour le routeur
            adresse_loopback = f"{routeur_num}.{routeur_num}.{routeur_num}.{routeur_num}"
            liens[routeur_num].append({
                "nom_voisin": routeur_num,
                "interface": "Loopback0",
                "adresse_interface": adresse_loopback,
                "AS": id_as,
                "adresse_AS": adresse_as,
                "protocole_routage": protocoles,
                "masque": "255.255.255.255" # toutes les adresses loopback sont en /32
            })

            # On regarde pour tous les routeurs de l'AS
            for interface, voisin in routeur["connecte"].items():
                if voisin:  # Si il y a connexion sur l'interface
                    # Trouver l'interface du voisin correspondant
                    interface_voisin = None
                    for voisin_routeur in donnees_reseau["AS"] + donnees_reseau["interAS"]:
                        for r in voisin_routeur["routeur"]:
                            if r["nom"] == voisin:
                                for iface, voisin_nom in r["connecte"].items():
                                    if voisin_nom == routeur_num:
                                        interface_voisin = iface
                                        break

                    if not interface_voisin:
                        continue  # Si l'interface du voisin n'est pas trouvée, on passe

                    # Vérifier si le lien existe déjà
                    lien_existe = any(
                        lien for lien in liens.get(voisin, []) if lien["nom_voisin"] == routeur_num
                    )
                    # Si il n'existe pas, on génère l'adresse ip pour le routeur et son voisin
                    if not lien_existe:
                        adresse_lien_source = f"{prefixe_reseau}.{compteur_lien}.1"
                        adresse_lien_dest = f"{prefixe_reseau}.{compteur_lien}.2"
                        compteur_lien += 1

                        # Ajouter le lien pour le routeur source
                        liens[routeur_num].append({
                            "nom_voisin": voisin,
                            "interface": interface,
                            "adresse_interface": adresse_lien_source,
                            "AS": id_as,
                            "adresse_AS": adresse_as,
                            "protocole_routage": protocoles,
                            "masque": masque
                        })

                        # Ajouter le lien pour le routeur voisin
                        if voisin not in liens:
                            liens[voisin] = []
                        liens[voisin].append({
                            "nom_voisin": routeur_num,
                            "interface": interface_voisin,
                            "adresse_interface": adresse_lien_dest,
                            "AS": id_as,
                            "adresse_AS": adresse_as,
                            "protocole_routage": protocoles,
                            "masque": masque
                        })

                else:
                    if routeur_num not in liens:
                            liens[routeur_num] = []
                    liens[routeur_num].append({
                        "nom_voisin": "",
                        "interface": interface,
                        "adresse_interface": "",
                        "AS": id_as,
                        "adresse_AS": adresse_as,
                        "protocole_routage": []
                        })
    
    # Traitement des connexions inter-AS
    compteur_lien = 1
    for inter_as in donnees_reseau["interAS"]:
        prefixe_reseau = inter_as["prefixe_reseau"]
        for routeur in inter_as["routeur"]:
            routeur_num = routeur["id_routeur"]
            protocoles = []  # Initialisation de la liste des protocoles à vide
            adresse_as = f"{prefixe_reseau}.{compteur_lien}.1"

            # Recherche du protocole de l'AS auquel appartient le routeur -> pourrait se simplifier avec dictionnaire routeurs
            for a in donnees_reseau["AS"]:
                for r in a["routeur"]:
                    if r["id_routeur"] == routeur_num:
                        protocoles.extend([elt for elt in a["protocole_routage"] if elt == "OSPF"])

            # Initialise le routeur si il n'est associé à aucune interface
            if routeur_num not in liens:
                liens[routeur_num] = []

            for interface, voisin in routeur["connecte"].items():
                if voisin:  # Si une connexion existe sur cette interface (toujours le cas en inter-as)
                    # Trouver l'interface du voisin correspondant
                    interface_voisin = None
                    for voisin_routeur in donnees_reseau["AS"] + donnees_reseau["interAS"]:
                        for r in voisin_routeur["routeur"]:
                            if r["id_routeur"] == voisin:
                                for iface, voisin_nom in r["connecte"].items():
                                    if voisin_nom == routeur_num:
                                        interface_voisin = iface
                                        break
                    lien_existe = any(
                        lien for lien in liens.get(voisin, []) if lien["nom_voisin"] == routeur_num
                    )
                    if not lien_existe: # Si le voisin n'a pas été défini
                        adresse_lien_source = f"{prefixe_reseau}.{compteur_lien}.1"
                        adresse_lien_dest = f"{prefixe_reseau}.{compteur_lien}.2"
                        compteur_lien += 1

                        # Ajouter la nouvelle connexion de routeur_num aux précédentes
                        liens[routeur_num].append({
                            "nom_voisin": voisin,
                            "interface": interface,
                            "adresse_interface": adresse_lien_source,
                            "AS": "Inter-AS",
                            "adresse_AS": adresse_as,
                            "protocole_routage": inter_as['protocole_routage'],  # Ajout correct des protocoles
                        })

                        # Ajouter le lien pour le routeur voisin
                        if voisin not in liens:
                            liens[voisin] = []
                        liens[voisin].append({
                            "nom_voisin": routeur_num,
                            "interface": interface_voisin,
                            "adresse_interface": adresse_lien_dest,
                            "AS": "Inter-AS",
                            "adresse_AS": adresse_as,
                            "protocole_routage": inter_as['protocole_routage'],
                        })
                    else:
                        # On met à jour les protocoles correctement dans chaque lien existant
                        for lien in liens[routeur_num]:
                            if lien["nom_voisin"] == voisin:
                                lien["protocole_routage"].extend(protocoles)

    afficher_dico(liens, "Liens et adresses IP des routeurs :")
    return liens

def definir_nom_id(dico):
    dico_nom = {}
    for a in dico["AS"]:
        for r in a:
            dico_nom[r["id_routeur"]] = r["nom"]

    return dico_nom

def point_excl(nb):
    """Renvoie nb points d'exclamation avec saut de ligne"""
    return "!\n"*nb

def charger_json(nom_fichier):
    """Renvoie le fichier json en format dictionnaire"""
    with open(nom_fichier, 'r') as file:
        data_loaded = json.load(file)
    return data_loaded

def invariable_debut(nom_routeur, txt_routeur):
    """
    Renvoie la configuration du routeur au début du fichier qui est identique pour tous les routeurs
    Paramètres :
    - nom_routeur(str): nom du routeur à configurer
    - txt_routeur(str): texte de configuration du routeur
    Return(str): texte de configuration à jour
    """
    # Texte de configuration identique dans tous les routeurs
    txt_routeur += point_excl(1)
    date = datetime.now().strftime('%H:%M:%S UTC %a %b %d %Y') # Heure à laquelle on lance le script
    txt_routeur += "\n!\n! Last configuration change at " + date + "\n!\n"
    txt_routeur += "version 15.2\nservice timestamps debug datetime msec\nservice timestamps log datetime msec\n!\n"
    txt_routeur += "hostname R" + nom_routeur + "\n!\n"
    txt_routeur += "boot-start-marker\nboot-end-marker\n" + point_excl(3)
    txt_routeur += "no aaa new-model\nno ip icmp rate-limit unreachable\nip cef\n" + point_excl(1)
    return txt_routeur


def invariable2():
    txt_routeur = point_excl(5)
    txt_routeur += "no ip domain lookup\nno ipv6 cef\n" + point_excl(2)
    return txt_routeur

def invariable3():
    txt_routeur = "multilink bundle-name authenticated\n" + point_excl(9)
    txt_routeur += "ip tcp synwait-time 5\n" + point_excl(12)

    return txt_routeur

def invariable_milieu():
    """
    Renvoie la configuration du routeur entre bgp et ospf qui est identique pour tous les routeurs
    Return(str): texte de configuration à jour
    """
    txt_routeur = "ip forward-protocol nd\n"
    txt_routeur += point_excl(2)
    txt_routeur += "no ip http server\nno ip http secure-server\n!\n"
    return txt_routeur

def invariable_fin():
    """
    Renvoie la configuration du routeur à la fin du fichier qui est identique pour tous les routeurs
    Return(str): texte de configuration à jour
    """
    txt_routeur = point_excl(4)
    txt_routeur += "control-plane\n"
    txt_routeur += point_excl(2)
    txt = " exec-timeout 0 0\n privilege level 15\n logging synchronous\n stopbits 1\n"
    txt_routeur += "line con 0\n" + txt
    txt_routeur += "line aux 0\n" + txt
    txt_routeur += "line vty 0 4\n login\n"
    txt_routeur += point_excl(2)
    txt_routeur += "end\n"

    return txt_routeur

def dic_routeurs_par_as(data):
    """
    Transforme le json en dictionnaire qui associe à chaque AS tous les
    routeurs
    Paramètres : data(dict): dictionnaire du fichier json
    Return(dict): dictionnaire qui à chaque AS associe les routeurs
    """
    dic = {}
    for a in data["AS"]:
        liste_routeurs = []
        for r in a["routeur"]:
            liste_routeurs.append(r["id_routeur"])
        dic[a["id_AS"]] = liste_routeurs
    return dic

def liste_routeurs_bordure(data):
    """Liste tous les routeurs de bordures"""
    liste = []
    for a in data["interAS"]:
        for r in a["routeur"]:
            liste.append(r["id_routeur"])
    return liste

def interface(nom_interface, ip, protocole, masque):
    """
    Renvoie la configuration de l'interface
    Paramètres:
    - nom_interface(str): nom de l'interface qui va être configurée
    - ip(str): ip de l'interface
    - protocole(list de str): liste des protocoles appliquée sur l'interface
    Return(str): texte de configuration à jour
    """
    txt_routeur = "interface " + nom_interface + "\n"
    txt_routeur += " no ip address\n"

    if ip == "" and "FastEthernet" not in nom_interface: # L'interface n'est connectée à aucun routeur
        txt_routeur += " shutdown\n"

    if "GigabitEthernet" in nom_interface:
        txt_routeur += " negotiation auto\n"
    elif "FastEthernet" in nom_interface:
        txt_routeur += " duplex full\n"

    if ip != "": # L'interface est connectée à un routeur
        txt_routeur += " ip address " + ip + " " + masque + "\n"

        if "OSPF" in protocole and "eBGP" not in protocole:
            txt_routeur += " ip ospf 1 area 0\n"

    txt_routeur += "!\n"

    return txt_routeur

def communaute():
    return "ip bgp-community new-format\n!\n"

def ospf(nom_routeur):
    """Renvoie la configuration du protocole OSPF"""
    # nom_routeur type X.X.X.X avec X le nom du routeur
    adresse = ((nom_routeur + ".")*4)[:-1]
    txt_routeur = "ipv6 router ospf 1\n"
    txt_routeur += " router-id "+ adresse + "\n"
    return txt_routeur

def ecrire_config(txt_routeur, nom_routeur, dossier_config="Config"):
    """
    Écrit la configuration dans un fichier .cfg dans le dossier spécifié.
    Prend en paramètres :
    - txt_routeur (str) : contenu de la configuration à écrire.
    - nom_routeur (str) : nom du routeur pour le fichier.
    - dossier_config (str) : chemin vers le dossier où sauvegarder les fichiers (par défaut : "Config").
    """
    if not os.path.exists(dossier_config):
        os.makedirs(dossier_config)  # Crée le dossier Config s'il n'existe pas

    nom_fichier = os.path.join(dossier_config, f"i{nom_routeur}_startup-config.cfg")
    with open(nom_fichier, 'w') as f:
        f.write(txt_routeur)


def bgp(nom_routeur, voisins, routeur_dans_as, nom_as, routeur_bordure):
    """
    Implémente bgp dans la configuration du routeur
    Paramètres :
    - nom_routeur(str) : nom du routeur dont on fait la configuration
    - voisins(dict) : pour chaque routeur donne les voisins avec toutes ses informations
    - routeur_dans_as(dict) : donne tous les routeurs de l'AS
    - nom_as(str) : nom de l'AS
    - routeur_bordure (bool) : True si routeur de bordure, False sinon
    Return : Ne retourne rien
    """
    txt_routeur = "router bgp " + nom_as + "\n"
    id_routeur = ((nom_routeur+".")*4)[:-1]
    txt_routeur += " bgp router-id " + id_routeur + "\n"
    txt_routeur += " bgp log-neighbor-changes\n"
    txt_routeur += " no bgp default ipv4-unicast\n"

    # Adresses loopback des routeurs dans l'AS et adresses des voisins ne faisant pas partie de l'AS
    adresses_bgp = []
    adresses_ebgp = []

    # eBGP
    for v in voisins[nom_routeur]:
        if v["AS"] == "Inter-AS":
            routeur_voisin = v["nom_voisin"]
            a_ebgp = [dic["adresse_interface"] for dic in voisins[routeur_voisin] if dic["nom_voisin"]==nom_routeur][0]
            adresses_ebgp.append(a_ebgp) # On conserve avec le /64
            a_ebgp = a_ebgp.split("/")[0] # Enlève le /64
            adresses_bgp.append(a_ebgp)
            id_as = [k for k,valeur in routeur_dans_as.items() if v["nom_voisin"] in valeur][0]
            txt_routeur += " neighbor " + a_ebgp + " remote-as " + id_as + "\n"
    # iBGP
    for r in routeur_dans_as[nom_as]:
        if r != nom_routeur: # Evite d'intégrer l'adresse loopback du routeur qu'on configure
            # Récupère l'adresse de loopback qui est dans le dictionnaire voisins, lorsque l'interface est Loopback0
            a_loopback = [elt["adresse_interface"] for elt in voisins[r] if elt["interface"] == "Loopback0"][0]
            a_loopback = a_loopback.split("/")[0] # Enlève le /64
            adresses_bgp.append(a_loopback)
            txt_routeur += " neighbor " + a_loopback + " remote-as " + nom_as + "\n"
            txt_routeur += " neighbor " + a_loopback + " update-source Loopback0\n"

    txt_routeur += " !\n address-family ipv4\n exit-address-family\n !\n address-family ipv6\n"

    liste_reseau_voisin = []
    for r in routeur_dans_as[nom_as]:
        for v in voisins[r]:
            adresse = v["adresse_interface"]
            adresse_r = adresse.split("::")[0] + "::/" + adresse.split("/")[-1] # Adresse réseau du loopback du routeur
            if (r==nom_routeur and v["interface"]=="Loopback0" and adresse_r not in liste_reseau_voisin) or (v["AS"] == nom_as and v["nom_voisin"] != "" and adresse_r not in liste_reseau_voisin and v["interface"]!="Loopback0"):
                liste_reseau_voisin.append(adresse_r)
                if (not(routeur_bordure) and r==nom_routeur and v["interface"]=="Loopback0") or routeur_bordure:
                    txt_routeur += "  network " + adresse_r + "\n"

    for a in adresses_ebgp:
        adresse_r = a.split("::")[0] + "::/" + a.split("/")[-1] # Adresse réseau du loopback du routeur
        txt_routeur += "  network " + adresse_r + "\n"


    for a in adresses_bgp:
        txt_routeur += "  neighbor " + a + " activate\n"


    txt_routeur += " exit-address-family\n!\n"    
    return txt_routeur

def mpls():
    return "mpls label protocol ldp\n"

############### Drag and drop ################
def lister_configs_dossier(chemin_dossier):
    """
    Parcourt un dossier et renvoie la liste complète des chemins de fichiers présents.
    Paramètres :
        - chemin_dossier (str) : chemin vers le dossier contenant les fichiers.
    Retour :
        - (list) : liste des chemins complets des fichiers trouvés.
    """
    if not os.path.exists(chemin_dossier):
        raise Exception(f"Le dossier spécifié n'existe pas : {chemin_dossier}")
    
    fichiers = []
    for nom_fichier in os.listdir(chemin_dossier):
        chemin_complet = os.path.join(chemin_dossier, nom_fichier)
        if os.path.isfile(chemin_complet):  # Vérifie qu'il s'agit bien d'un fichier
            fichiers.append(chemin_complet)
    return fichiers


def trouver_fichier(chemin, nom_config):
    """
    Parcourt l'arborescende du dossier projet GNS pour trouver le
    chemin de la configuration du routeur initiale
    Paramètres :
        - chemin(str): chemin du répertoire projet à parcourir
        - nom_config(str): fichier config à trouver
    Return(str): chemin où copier le nouveau fichier de config
    """
    for racine, repertoires, fichiers in os.walk(chemin):
        for f in fichiers:
            if nom_config == f: # On a trouvé le fichier
                return racine # On renvoie le chemin
    # Si aucun fichier trouvé on lève une exception
    raise Exception("Fichier de config \""+nom_config+"\" non trouve")



############ MAIN ##############
def main():
    # Récupère le nom des fichiers à partir de l'invite de commande
    if len(sys.argv) != 3:
        print("Arguments : <INTENT_FILE.json> <DOSSIER_PROJET_GNS>", file=sys.stderr)
        sys.exit(1)
    fjson, chemin_projet = sys.argv[1], sys.argv[2]

    dico_json = charger_json(fjson)
    dico_nom_id = definir_nom_id(dico_json)
    dico_liens = definir_liens_routeurs(dico_json)
    dic_rout_as = dic_routeurs_par_as(dico_json)
    routeurs_bordure = liste_routeurs_bordure(dico_json)

    chemin_config = "Config"  # Dossier où se trouvent les fichiers de configuration générés

    # Supprimer tout le contenu du dossier Config pour s'assurer qu'il est vide
    if os.path.exists(chemin_config):
        shutil.rmtree(chemin_config)  # Supprime tout le dossier Config
    os.makedirs(chemin_config)  # Recrée le dossier Config

    # Pour chaque routeur, on écrit un fichier de configuration
    for nom_as, liste_rout in dic_rout_as.items():
        for r in liste_rout:
            txt_ospf = ""
            txt_mpls = ""
            txt_vrf = ""
            bool_bordure = r in routeurs_bordure

            # Ajout des interfaces et protocoles
            for i in dico_liens[r]:
                txt_routeur += interface(i["interface"], i["adresse_interface"], i["protocole_routage"], i["masque"])
                if "OSPF" in i["protocole_routage"] and "eBGP" not in i["protocole_routage"]:
                    txt_ospf = ospf(r)
                if "MPLS" in i["protocole_routage"]:
                    txt_mpls = mpls()
                # Voir comment on définit le VRF dans 

            txt_routeur = invariable_debut(dico_nom_id[r], "")
            txt_routeur += txt_vrf
            txt_routeur += invariable2()
            txt_routeur += txt_mpls
            txt_routeur += invariable3()

            # Config bgp
            txt_routeur += bgp(r, dico_liens, dic_rout_as, nom_as, bool_bordure)

            # Ajout sections communes
            txt_routeur += invariable_milieu()
            txt_routeur += txt_ospf
            txt_routeur += invariable_fin()

            # Ecriture dans le fichier de config
            ecrire_config(txt_routeur, r)  

    # Récupère tous les fichiers de configuration dans le dossier Config
    fichiers_config = lister_configs_dossier(chemin_config) 
    # print(fichiers_config)

    # Copie des fichiers de configuration générés
    for chemin_fichier in fichiers_config:
        try:
            nom_fichier = os.path.basename(chemin_fichier)
            nv_ch = trouver_fichier(chemin_projet, nom_fichier)  # Trouve le chemin cible
            print(f"Copie de {nom_fichier} vers {nv_ch}")
            shutil.copy(chemin_fichier, nv_ch)  # Copie du fichier en écrasant si nécessaire
        except Exception as e:
            print(f"Erreur lors de la copie pour le fichier {chemin_fichier}: {e}")


if __name__ == "__main__":
    main()