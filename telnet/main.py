from datetime import datetime
import json
import os
import shutil

#TO-DO :
# Il faut revoir toutes les fonctions (dont main) en fonction des dictionnaires voisins et as
# Implémenter les nouvelles fonctions
# Tester les fonctions


def afficher_dico(dico, message=""):
    """Affiche le contenu d'un dictionnaire de manière lisible avec un message optionnel."""
    if message:
        print(message)
    print(json.dumps(dico, indent=4, ensure_ascii=False))

def definir_liens_routeurs(donnees_reseau):
    """
    Définit les liens entre routeurs et génère des adresses IPv6 basées sur le numéro AS, le numéro du lien, et l'extrémité du lien.
    """
    liens = {}
    compteur_lien = 1  # Compteur pour générer des numéros de lien uniques

    # Traitement des routeurs internes à chaque AS
    for as_data in donnees_reseau["AS"]:
        id_as = as_data["id_AS"]

        # Parcours des routeurs dans l'AS
        for routeur in as_data["routeur"]:
            routeur_num = routeur["nom"]
            adresse_as = as_data["prefixe_reseau"]
            protocoles = as_data["protocole_routage"]

            if routeur_num not in liens:
                liens[routeur_num] = []

            # Ajouter une adresse loopback pour le routeur
            adresse_loopback = f"2001:{routeur_num}::1/64"
            liens[routeur_num].append({
                "nom_voisin": routeur_num,
                "interface": "Loopback0",
                "adresse_interface": adresse_loopback,
                "AS": id_as,
                "adresse_AS": adresse_as,
                "protocole_routage": protocoles
            })

            for interface, voisin in routeur["connecte"].items():
                if voisin:  # Si une connexion existe
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
                    if not lien_existe:
                        adresse_lien_source = f"2001:100:{id_as}:{compteur_lien}::1/64"
                        adresse_lien_dest = f"2001:100:{id_as}:{compteur_lien}::2/64"
                        compteur_lien += 1

                        # Ajouter le lien pour le routeur source
                        liens[routeur_num].append({
                            "nom_voisin": voisin,
                            "interface": interface,  # Interface correcte du routeur source
                            "adresse_interface": adresse_lien_source,
                            "AS": id_as,
                            "adresse_AS": adresse_as,
                            "protocole_routage": protocoles
                        })

                        # Ajouter le lien pour le routeur voisin avec son interface correcte
                        if voisin not in liens:
                            liens[voisin] = []
                        liens[voisin].append({
                            "nom_voisin": routeur_num,
                            "interface": interface_voisin,  # Interface correcte côté voisin
                            "adresse_interface": adresse_lien_dest,
                            "AS": id_as,
                            "adresse_AS": adresse_as,
                            "protocole_routage": protocoles
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
        for routeur in inter_as["routeur"]:
            routeur_num = routeur["nom"]
            protocoles = []  # Initialisation de la liste des protocoles à vide
            adresse_as = inter_as['prefixe_reseau'].split("::")[0]+":"+str(compteur_lien)+"::"+inter_as['prefixe_reseau'].split("::")[-1]

            # Recherche du protocole de l'AS auquel appartient le routeur -> pourrait se simplifier avec dictionnaire routeurs
            for a in donnees_reseau["AS"]:
                for r in a["routeur"]:
                    if r["nom"] == routeur_num:
                        protocoles = [elt for elt in a["protocole_routage"] if elt == "OSPF" or elt == "RIP" ]

            # Initialise le routeur si il n'est associé à aucune interface
            if routeur_num not in liens:
                liens[routeur_num] = []

            for interface, voisin in routeur["connecte"].items():
                if voisin:  # Si une connexion existe sur cette interface (toujours le cas en inter-as)
                    # Trouver l'interface du voisin correspondant
                    interface_voisin = None
                    for voisin_routeur in donnees_reseau["AS"] + donnees_reseau["interAS"]:
                        for r in voisin_routeur["routeur"]:
                            if r["nom"] == voisin:
                                for iface, voisin_nom in r["connecte"].items():
                                    if voisin_nom == routeur_num:
                                        interface_voisin = iface
                                        break
                    lien_existe = any(
                        lien for lien in liens.get(voisin, []) if lien["nom_voisin"] == routeur_num
                    )
                    if not lien_existe: # Si le voisin n'a pas été défini
                        adresse_lien_source = f"{inter_as['prefixe_reseau'].split('::')[0]}:{compteur_lien}::1/64"
                        adresse_lien_dest = f"{inter_as['prefixe_reseau'].split('::')[0]}:{compteur_lien}::2/64"
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


    # afficher_dico(liens, "Liens et adresses IP des routeurs :")
    return liens


def charger_json(nom_fichier):
    """Renvoie le fichier json en format dictionnaire"""
    with open(nom_fichier, 'r') as file:
        data_loaded = json.load(file)
    return data_loaded

def invariable_debut(txt_routeur):
    txt_routeur = "configure terminal\nno logging buffered\nno logging monitor\nno logging console\nipv6 unicast-routing\nip bgp-community new-format\n"
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
            liste_routeurs.append(r["nom"])
        dic[a["id_AS"]] = liste_routeurs
    return dic

def liste_routeurs_bordure(data):
    liste = []
    for a in data["interAS"]:
        for r in a["routeur"]:
            liste.append(r["nom"])
    return liste

def interface(nom_interface, ip):
    """
    Renvoie la configuration de l'interface
    Paramètres:
    - nom_interface(str): nom de l'interface qui va être configurée
    - ip(str): ip de l'interface
    - txt_routeur(str): texte de configuration du routeur
    """
    txt_routeur=""
    if ip != "":
        txt_routeur = "interface " + nom_interface + "\n"
        txt_routeur += "ipv6 enable\n"
        txt_routeur += "ipv6 address "+ip+"\n"
        txt_routeur += "no sh\nexit\n"

    return txt_routeur
    
def rip(nom_interface):
    """Renvoie la configuration du protocole RIP"""
    txt_routeur = "ipv6 router rip X\nredistribute connected\nexit\n"
    txt_routeur += "interface "+nom_interface+"\n"
    txt_routeur += "ipv6 rip X enable\nexit\n"
    return txt_routeur

def ospf(nom_routeur,nom_interface):
    """Renvoie la configuration du protocole OSPF"""
     # nom_routeur type X.X.X.X avec X le nom du routeur
    adresse = ((nom_routeur + ".")*4)[:-1]
    txt_routeur = "ipv6 router ospf 31\n"
    txt_routeur += "router-id "+ adresse + "\nexit\n"
    txt_routeur += "interface "+str(nom_interface)+" \n"
    txt_routeur += "ipv6 ospf 31 area 0\nno sh\n"
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

    nom_fichier = os.path.join(dossier_config, f"{nom_routeur}-config.txt")
    with open(nom_fichier, 'w') as f:
        f.write(txt_routeur)


def bgp(dico_json, nom_routeur, voisins, routeur_dans_as, nom_as, routeur_bordure):
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
    id_routeur = ((str(nom_routeur)+".")*4)[:-1]
    id_routeur = ((nom_routeur+".")*4)[:-1]
    txt_routeur = "router bgp " + nom_as + "\n"
    txt_routeur += "no bgp default ipv4-unicast\n"
    txt_routeur += "bgp router-id " + id_routeur + "\n"

    # Adresses loopback des routeurs dans l'AS et adresses des voisins ne faisant pas partie de l'AS
    adresses_bgp = []
    adresses_ebgp = []

    for v in voisins[nom_routeur]:
        if v["AS"] == "Inter-AS":
            routeur_voisin = v["nom_voisin"]
            a_ebgp = [dic["adresse_interface"] for dic in voisins[routeur_voisin] if dic["nom_voisin"]==nom_routeur][0]
            adresses_ebgp.append(a_ebgp) # On conserve avec le /64
            a_ebgp = a_ebgp.split("/")[0] # Enlève le /64
            adresses_bgp.append(a_ebgp)
            id_as = [k for k,valeur in routeur_dans_as.items() if v["nom_voisin"] in valeur][0]
            txt_routeur += "neighbor " + a_ebgp + " remote-as " + str(id_as) + "\n"



    # iBGP
    for r in routeur_dans_as[nom_as]:
        if r != nom_routeur: # Evite d'intégrer l'adresse loopback du routeur qu'on configure
            # Récupère l'adresse de loopback qui est dans le dictionnaire voisins, lorsque l'interface est Loopback0
            a_loopback = [elt["adresse_interface"] for elt in voisins[r] if elt["interface"] == "Loopback0"][0]
            a_loopback = a_loopback.split("/")[0] # Enlève le /64
            adresses_bgp.append(a_loopback)
            txt_routeur += "neighbor " + a_loopback + " remote-as " + str(nom_as) + "\n"
            txt_routeur += "neighbor " + a_loopback + " update-source Loopback0\n"

    txt_routeur += "address-family ipv6 unicast\n"

    liste_reseau_voisin = []
    for r in routeur_dans_as[nom_as]:
        for v in voisins[r]:
            adresse = v["adresse_interface"]
            adresse_r = adresse.split("::")[0] + "::/" + adresse.split("/")[-1] # Adresse réseau du loopback du routeur
            if (r==nom_routeur and v["interface"]=="Loopback0" and adresse_r not in liste_reseau_voisin) or (v["AS"] == nom_as and v["nom_voisin"] != "" and adresse_r not in liste_reseau_voisin and v["interface"]!="Loopback0"):
                liste_reseau_voisin.append(adresse_r)
                if (not(routeur_bordure) and r==nom_routeur and v["interface"]=="Loopback0") or routeur_bordure:
                    txt_routeur += "network " + adresse_r + "\n"

    for a in adresses_ebgp:
        adresse_r = a.split("::")[0] + "::/" + a.split("/")[-1] # Adresse réseau du loopback du routeur
        txt_routeur += "network " + adresse_r + "\n"
        txt_routeur+=f"neighbor {a} send-community both\n"

    for a in adresses_bgp:
        txt_routeur += "neighbor " + a + " activate\n"


    return txt_routeur








############ MAIN ##############
def main():
    #dico_json = charger_json("intent_network_reseau_complet.json")
    dico_json = charger_json("intent_network_complet.json")
    #afficher_dico(f"Dico json : \n{dico_json}")
    dico_liens = definir_liens_routeurs(dico_json)
    dic_rout_as = dic_routeurs_par_as(dico_json)
    routeurs_bordure = liste_routeurs_bordure(dico_json)

    # A revoir pour récupérer les valeurs automatiquement (fichier json et/ou terminal)
    chemin_config = "Config"  # Dossier où se trouvent les fichiers de configuration générés


    # Supprimer tout le contenu du dossier Config pour s'assurer qu'il est vide
    if os.path.exists(chemin_config):
        shutil.rmtree(chemin_config)  # Supprime tout le dossier Config
    os.makedirs(chemin_config)  # Recrée le dossier Config

    # Pour chaque routeur, on écrit un fichier de configuration
    for nom_as, liste_rout in dic_rout_as.items():
        for r in liste_rout:
            txt_routeur = invariable_debut("")
            txt_rip = ""
            txt_ospf = ""
            bool_bordure = r in routeurs_bordure

            # Ajout des interfaces et protocoles
            for i in dico_liens[r]:
                txt_routeur += interface(i["interface"], i["adresse_interface"])
                if "RIP" in i["protocole_routage"]:
                    txt_rip += rip(i["interface"])
                if "OSPF" in i["protocole_routage"]:
                    txt_ospf += ospf(r,i["interface"])

            
            txt_routeur += txt_rip + txt_ospf
            
            # Config bgp
            txt_routeur += bgp(dico_json, r, dico_liens, dic_rout_as, nom_as, bool_bordure)


            # Ecriture dans le fichier de config
            ecrire_config(txt_routeur, r)  

    
if __name__ == "__main__":
    main()
