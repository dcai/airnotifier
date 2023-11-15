#!/bin/bash

###########################################################
## Script : sauvegarderMongoDB.sh
## But : Sauvegarde sous format dump d'une base de donnees
##       MongoDB.
##   - $1 : Chemin absolu du dossier de dump de
##          sauvegarde
## Options :
##   - -z : Compresser le fichier de sauvegarde.
## Exemples :
##   - ./sauvegarderMongoBD.sh -z /app/data/mongodbbackup
##
###########################################################

cheminLocal=`dirname $0`

# Gestion des options.
compresserFichierSauv=false
while getopts ":z:" options; do
  case $options in
    z)
        compresserFichierSauv=true;
        shift "$((OPTIND-2))"
    ;;
    \?)
        echo "Option invalide : -$OPTARG" >&2;
        exit 1
    ;;
    :)
        echo "Option -$OPTARG requiert un argument." >&2
        exit 1
    ;;
  esac
done

# Appeler les parametres obligatoires.
cheminDossierSauvegarde=$1

# Importer la librairie commune.
. lib.sh

afficheTitre "SCRIPT DE SAUVEGARDE DE BASE DE DONNEES MONGODB"

# Valider que le repertoire de sauvegarde existe.
if [ ! -d "$cheminDossierSauvegarde" ]; then
    echo "Le dossier de sauvegarde fourni n'existe pas."
    exit 1
fi

# Assembler le chemin et le nom du fichier de sauvegarde.
dossierSauvegarde=$cheminDossierSauvegarde"/mongodb-"`eval date +%Y%m%d_%Hh%M`

echo "Dossier de sauvegarde : $dossierSauvegarde"

echo -e "\nSauvegarde en cours..."

mongodump --uri=mongodb://${MONGO_SERVER}:${MONGO_PORT} -o $dossierSauvegarde
checkCodeRetour

# Compression du fichier de sauvegarde.
if $compresserFichierSauv; then
    echo -e "Compression du fichier de sauvegarde en cours..."
    archiveSauvegarde=$dossierSauvegarde".tgz"
    tar -zcf $archiveSauvegarde -C $dossierSauvegarde .
    checkCodeRetour
    rm -rf $dossierSauvegarde
fi

echo -e "\nSucces de la sauvegarde de la base de donnees MONGODB"

afficheSousTitre "FIN"
