import pandas as pd
from datetime import datetime
import csv 

# Chemin vers ton fichier Excel
fichier_excel = "données.xlsx"

# Lire la feuille correcte (remplace 'Feuil1' si besoin)
df = pd.read_excel(fichier_excel, sheet_name=0)

# Vérifie les colonnes
print(df.columns)

# Suppose que les colonnes s'appellent comme suit :
# 'Rue destinataire', 'Date', 'Heure'
colonnes_interet = ['Tournée livraison', 'Rue destinataire', 'Date', 'Heure']

# Filtrage des lignes valides
df_clean = df[colonnes_interet].dropna()

# Retirer "Total pour" ou autres
df_clean = df_clean[~df_clean['Rue destinataire'].str.startswith("Total pour", na=False)]

# Résultat
print(df_clean)

# Configure pandas pour tout afficher
pd.set_option('display.max_rows', None)      # affiche toutes les lignes
pd.set_option('display.max_columns', None)   # affiche toutes les colonnes
pd.set_option('display.width', None)         # ajuste la largeur pour ne pas couper
pd.set_option('display.max_colwidth', None)  # pas de limite sur la largeur des colonnes

# Affiche le DataFrame complet
print(df_clean)

# Sauvegarde en CSV
df_clean.to_csv("db.csv", index=False)

print("✅ Fichier CSV 'resultat_livraisons.csv' créé avec succès !")



##:::::::::::::::::::::::::::::::::


import csv
from datetime import datetime, time
import pandas as pd
import os

# Dictionnaire de correspondance des noms de tournées
noms_tournees = {
    '1': "intersport",
    '2': "monoprix",
    '3': "grand theatre",
    '4': "#",
    '5': "chartron",
    '6': "GRAND PARC",
    '7': "VERDUN",
    '8': "AUCHAN LAC - 1",
    '9': "QUAI DE BACALAN",
    '10': "AUCHAN LAC - 2",
    '11': "BACALAN ZONE",
    '13': "CAUDERAN - 1",
    '14': "CAUDERAN - 2",
    '15': "HOPITAL",
    '16': "MERIADEK",
    '17': "ST GENES",
    '18': "FONDUDAUGE",
    '19': "LA GARE - 1",
    '20': "LA GARE - 2"
}

# Fonction pour convertir une chaîne en objet datetime
def convertir_datetime(date_str, heure_str):
    formats_datetime = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M'
    ]
    
    datetime_str = f"{date_str.strip()} {heure_str.strip()}"
    
    for fmt in formats_datetime:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    
    formats_date = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    for fmt in formats_date:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return datetime.min

# 1. Lire les données du fichier CSV
donnees = []
input_file = 'db.csv'
output_file = 'livraisons_traitees.csv'

with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for ligne in reader:
        ligne_clean = {k: v.strip() for k, v in ligne.items()}
        donnees.append(ligne_clean)

# 2. Supprimer les doublons en conservant la date la plus ancienne
adresses_dict = {}
doublons_supprimes = 0

for livraison in donnees:
    adresse = livraison['Rue destinataire']
    tournee = livraison['Tournée livraison']
    cle = (tournee, adresse)
    dt = convertir_datetime(livraison['Date'], livraison['Heure'])
    
    if cle not in adresses_dict:
        livraison['datetime'] = dt
        adresses_dict[cle] = livraison
    else:
        doublons_supprimes += 1
        if dt < adresses_dict[cle]['datetime']:
            livraison['datetime'] = dt
            adresses_dict[cle] = livraison

donnees_dedoublonnees = list(adresses_dict.values())

# 3. Extraire l'heure pour le tri
for livraison in donnees_dedoublonnees:
    livraison['heure_tri'] = livraison['datetime'].time()

# 4. Trier par tournée et heure
donnees_triees = sorted(
    donnees_dedoublonnees,
    key=lambda x: (x['Tournée livraison'], x['heure_tri'])
)

# 5. Ajouter ordre de passage et nom de tournée
compteur_tournees = {}
for livraison in donnees_triees:
    tournee_raw = livraison['Tournée livraison'].strip()
    
    # Normalisation : supprimer éventuel ".0"
    try:
        tournee_normalisee = str(int(float(tournee_raw)))
    except ValueError:
        tournee_normalisee = tournee_raw
    
    if tournee_normalisee not in compteur_tournees:
        compteur_tournees[tournee_normalisee] = 0
    
    compteur_tournees[tournee_normalisee] += 1
    livraison['Ordre'] = compteur_tournees[tournee_normalisee]
    
    livraison['Nom tournée'] = noms_tournees.get(tournee_normalisee, "")
    livraison['Tournée livraison'] = tournee_normalisee

# 6. DataFrame pandas
df = pd.DataFrame(donnees_triees)
df = df[['Tournée livraison', 'Nom tournée', 'Rue destinataire', 'Date', 'Heure', 'Ordre']]

# 7. Sauvegarde CSV
df.to_csv(output_file, index=False, encoding='utf-8')

# 8. Rapport
print("\n" + "="*50)
print("TRAITEMENT TERMINÉ AVEC SUCCÈS")
print("="*50)
print(f"Fichier d'entrée: {input_file}")
print(f"Fichier de sortie: {output_file}")
print(f"Nombre initial de livraisons: {len(donnees)}")
print(f"Nombre de livraisons après dédoublonnage: {len(donnees_dedoublonnees)}")
print(f"Doublons supprimés: {doublons_supprimes}")
print(f"Nombre de tournées traitées: {len(compteur_tournees)}")
print("\nStructure du fichier de sortie:")
print(df.head(3).to_string(index=False))
print("\nLes résultats ont été enregistrés avec succès dans le fichier CSV.")
