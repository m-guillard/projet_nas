# projet_nas

## TO-DO
- Ajouter fonctionnalité
    - Revoir adressage ipv4 Loopback/classique
    - eBGP que sur les Loopback des ASBR
    - modifier iBGP
    - RR
    - mpls ip dans les interfaces
    - address-family vpn
    - address-family ipv4/vrf ==> checj avec : PE/CE = si y'a du eBGP, sinon c'est des P, et pour différencier PE et CE : PE a des vrfet pas CE
 

    - attention commentaires de la magouille intersidérale

## Pour tester
- Test effectué avec config_test.zip avec le fichier d'intention intent_network.json

## Erreurs à corriger/Tests effectués
- Ping impossible de PE à CE mais possible de CE à PE
- Ping impossible entre deux CE d'un mm client
- Ping entre les PE et les P
- Erreurs dans terminal : ligne exit-address-family (je comprends pas d'où ça vient)



![image](https://github.com/user-attachments/assets/811c3436-3d74-4b45-89ba-5faec7ea9774)
