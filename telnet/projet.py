from gns3fy import Gns3Connector,Project,Node
from netmiko import ConnectHandler


server=Gns3Connector("http://localhost:3080")


# Liste des projets existants
print(server.get_projects())

"""
project=Project(name="Projet final", connector=server)
project.get()


i=1
#telnet
for node in project.nodes:
    node.get()

    print(f"Console Node address: {node.console}")

    # Connexion Telnet à un périphérique Cisco dans GNS3 via Netmiko
    device = {
        'device_type': 'cisco_ios_telnet',  # Le type de périphérique pour Telnet
        'host': '127.0.0.1',  # Utiliser localhost comme hôte (127.0.0.1)
        'port': node.console,  # Le port auquel le périphérique écoute pour Telnet
        'username': '',  # Laisser vide si aucun mot de passe n'est configuré
        'password': '',  # Laisser vide si aucun mot de passe n'est configuré
    }

    try:
        # Connexion Telnet via Netmiko
        net_connect = ConnectHandler(**device)
        
        # Passer en mode privilégié (enable)
        net_connect.enable()

        with open('Config/'+str(i)+'-config.txt', 'r') as file:
            config_commands = file.read().splitlines()

        
        net_connect.send_config_set(config_commands)


        # Fermer la connexion Netmiko
        net_connect.disconnect()

    except Exception as e:
        print(f"Erreur de connexion avec Netmiko : {e}")
    
    i+=1
"""

