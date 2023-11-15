#!/bin/bash

###########################################################
## Script : lib.sh
## But : Rassembler les fonctions communes aux autres scripts
##
###########################################################

# Verifie si le code de retour n'est pas 0.
function checkCodeRetour() {
   local codeRetour=$?
   if [ $codeRetour != 0 ]; then
      echo ""
      echo "----------------------------"
      echo "===> Code retour = $codeRetour"
      echo "----------------------------"
      echo ""
      exit $codeRetour
   fi
}

# Affiche le titre.
function afficheTitre() {
    local titre="$1"
    local barre=""
    for ((i=1; i<=$((${#titre} + 8)); i++)); do
        barre="$barre#"
    done
    echo ""
    echo $barre
    echo "### $titre ###"
    echo $barre
    echo ""
}

# Affiche un sous-titre.
function afficheSousTitre() {
    local titre="$1"
    echo ""
    echo "=== $titre ==="
    echo ""
}

# Valide que le fichier de configuration est présent.
function valideFichierConfig() {
    local fichier=$1
    local typeServeur=$2
    if [ ! -f "$fichier" ]; then
        echo "Aucun fichier de configuration trouve pour le serveur $typeServeur."
        exit 1
    fi
}

# Valide que le fichier de restauration MySQL est présent.
function valideCheminFichierMySQL() {
    local fichier=$1
    if [ ! -f "$fichier" ]; then
        echo "Le fichier de restauration mysql fourni n'existe pas."
        exit 1
    fi
}

# Valide que l'environnement ne fait pas parti d'une liste d'environnements invalides.
#
# $1 le type de serveur a valider
# $2 La liste des types invalides
function valideTypesEnvironnementsInvalides() {
    local typeServeur=$1
    local types=$2
    for type in $types; do
        if [[ "$type" == "$typeServeur" ]]; then
            echo "Il est interdit d'utiliser ce script avec "
            echo "les types d'environnements suivants :"
            echo $types
            exit 1;
        fi
    done
}

# Extrait et valide les parties de l'url.
#
# $1 l'url a extraire
function extraireURL() {
    local url=$1
    local regex='(https?://([^ /]+))([^ ]*)?/'
    if [[ $url =~ $regex ]]; then
        site="${BASH_REMATCH[1]}"
        domaine="${BASH_REMATCH[2]}"
    else
        echo "l'url fourni n'est pas au bon format."
        exit 1
    fi
}

