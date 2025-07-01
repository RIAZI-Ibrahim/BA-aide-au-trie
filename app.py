import streamlit as st
import pandas as pd
import unicodedata
import re
from PIL import Image
import numpy as np
import easyocr
import pytesseract

# =========================================
# CONFIG
# =========================================
st.set_page_config(page_title="Gestion des tournées", layout="wide")
st.title("🚚 Aide au tri pour chauffeurs - Transport BA Aquitaine")

# =========================================
# DONNÉES
# =========================================
# Ton mapping des tournées
tournee_mapping = {
    1: "intersport",
    2: "monoprix",
    3: "grand theatre",
    4: "#",
    5: "chartron",
    6: "GRAND PARC",
    7: "VERDUN",
    8: "AUCHAN LAC - 1",
    9: "QUAI DE BACALAN",
    10: "AUCHAN LAC - 2",
    11: "BACALAN ZONE",
    13: "CAUDERAN - 1",
    14: "CAUDERAN - 2",
    15: "HOPITAL",
    16: "MERIADEK",
    17: "ST GENES",
    18: "FONDUDAUGE",
    19: "LA GARE - 1",
    20: "LA GARE - 2"
}

# Filtrer uniquement les tournées qui ont un nom valide
tournee_mapping = dict(sorted(
    (k, v) for k, v in tournee_mapping.items() if v.strip() and v != "#"
))

# Lire le CSV des adresses avec l'ordre
data_csv = pd.read_csv("data/livraisons_traitees.csv")

# =========================================
# FONCTIONS
# =========================================

@st.cache_data
def charger_data():
    return data_csv.copy()

def normaliser(texte):
    if pd.isnull(texte):
        return ""
    texte = texte.lower()
    texte = unicodedata.normalize('NFD', texte).encode('ascii', 'ignore').decode('utf-8')
    texte = re.sub(r'[^a-z0-9\s]', ' ', texte)
    texte = re.sub(r'\s+', ' ', texte).strip()
    return texte

def extraire_nom_rue(adresse):
    adresse = normaliser(adresse)
    adresse_sans_numero = re.sub(r'^\d+\s+', '', adresse)
    return adresse_sans_numero

reader = easyocr.Reader(['fr'], gpu=False)

def extraire_texte_image(image_file):
    try:
        # Ouvre l'image
        image = Image.open(image_file)
        # Convertit en format utilisable par easyocr
        image = image.convert('RGB')
        largeur, hauteur = image.size
        # Découper la zone en haut, par exemple 20% de la hauteur de l’image
        p = .1
        results = ""
        while not results and p <=1: 
            hauteur_zone = int(hauteur * p)
            zone_haute = image.crop((0, 0, largeur, hauteur_zone))
            zone_haute = zone_haute.convert('RGB')
            # OCR avec EasyOCR
            results = reader.readtext(np.array(zone_haute), detail=0, paragraph=True)
            p = p+0.1
        # Concatène tous les résultats
        text = "\n".join(results)
        return text.strip()
    except Exception as e:
        return ""


def chercher_adresse(adresse, tournee_numero):
    nom_rue = extraire_nom_rue(adresse)
    
    subset = data[data['Tournée livraison'] == tournee_numero]
# plus besoin de recalculer Rue_normalisee ici

    match_ligne = subset[subset['Rue_normalisee'] == nom_rue]
    
    if not match_ligne.empty:
        ordre = match_ligne.iloc[0]['Ordre']
        # Vérifier s'il y a la même rue dans d'autres tournées
        autres_tournees = data[
            (data['Rue_normalisee'] == nom_rue) & (data['Tournée livraison'] != tournee_numero)
        ]
        autres = [
            (int(r['Tournée livraison']), tournee_mapping.get(int(r['Tournée livraison']), 'Inconnu'))
            for _, r in autres_tournees.iterrows()
        ]
        return True, ordre, autres
    else:
        # Vérifier si l'adresse existe dans une autre tournée
        data['Rue_normalisee'] = data['Rue destinataire'].apply(extraire_nom_rue)
        autres = data[data['Rue_normalisee'] == nom_rue]
        if not autres.empty:
            other_tournee = autres.iloc[0]['Tournée livraison']
            return False, (other_tournee, tournee_mapping.get(other_tournee, 'Inconnu')), []
        else:
            return False, None, []

# =========================================
# CHARGEMENT
# =========================================
data = charger_data()
data['Rue_normalisee'] = data['Rue destinataire'].apply(extraire_nom_rue)


if 'adresses_ajoutees' not in st.session_state:
    st.session_state.adresses_ajoutees = []

# =========================================
# SELECTION DE LA TOURNEE
# =========================================
st.sidebar.header("🗺️ Sélection de la tournée")
selected_tournee = st.sidebar.selectbox(
    "Choisissez votre tournée",
    options=sorted(tournee_mapping.keys()),
    format_func=lambda x: f"{x} - {tournee_mapping[x]}"
)

st.sidebar.markdown("---")
st.sidebar.info(f"Vous avez choisi la tournée **{selected_tournee} - {tournee_mapping[selected_tournee]}**")

# =========================================
# SAISIE OU SCAN
# =========================================
st.subheader("📦 Saisie ou Scan de l'adresse")
col1, col2 = st.columns([2, 1])

#with col1:
    #input_adresse = st.text_input("✍️ Entrez l'adresse manuellement :")

with col2:
    #st.markdown("**📷 Photo directe ou Import**")
    image_uploaded = None
    # Prendre photo en direct
    #photo_capturee = st.camera_input("Prendre une photo")
    if 'show_camera' not in st.session_state:
        st.session_state.show_camera = False

    if st.button("📷 Ouvrir la caméra"):
        st.session_state.show_camera = True

    if st.session_state.show_camera:
        image_uploaded = st.camera_input("Prendre une photo")
    # Ou importer depuis la galerie
    #image_uploaded = st.file_uploader("📷 Prendre une photo / Importer", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")


if image_uploaded:
    ocr_result = extraire_texte_image(image_uploaded)
    if ocr_result:
        # Ici on extrait seulement la première ligne (ou celle qu'on considère comme adresse)
        adresse_extraite = ocr_result.split('\t\n')[0].strip()
        st.success(f"✅ Adresse détectée sur l’étiquette : {adresse_extraite}")
        # Affiche une zone de texte éditable initialisée avec le texte OCR
        input_adresse = st.text_area("✍️ Corrigez si besoin l'adresse détectée :", value=adresse_extraite, height=100)
    else:
        st.error("❌ Impossible de lire l'adresse sur la photo. Veuillez réessayer.")


# =========================================
# AJOUTER L'ADRESSE
# =========================================
if st.button("✅ Ajouter l'adresse"):
    if not input_adresse.strip():
        st.warning("⚠️ Veuillez saisir ou scanner une adresse.")
    else:
        ok, info, autres = chercher_adresse(input_adresse, selected_tournee)
        
        if ok:
            st.session_state.adresses_ajoutees.append({
                'Adresse fournie': input_adresse,
                'Ordre': info,
                'Autres_tournees': autres
            })
            st.success(f"✅ Adresse ajoutée à la tournée {selected_tournee}.")
        else:
            if info is None:
                st.error("❌ Adresse non trouvée dans aucune tournée.")
            else:
                t_num, t_nom = info
                st.error(f"❌ Cette adresse n'est pas dans votre tournée {selected_tournee} - {tournee_mapping[selected_tournee]}.\n"
                         f"Elle correspond à la tournée {t_num} - {t_nom}.")

# =========================================
# AFFICHAGE DU TABLEAU
# =========================================
if st.session_state.adresses_ajoutees:
    st.subheader("📋 Tableau des adresses ajoutées")
    # Filtrer celles qui sont bien dans la tournée sélectionnée
    table = [a for a in st.session_state.adresses_ajoutees if a['Ordre'] is not None]
    table = [a for a in table if chercher_adresse(a['Adresse fournie'], selected_tournee)[0]]
    if table:
        table = sorted(table, key=lambda x: x['Ordre'])

        def highlight_dupes(df):
            # Crée un DataFrame vide de même forme que df, rempli de chaînes vides (pas de style)
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            
            seen_rues = {}
            colors = ["#FFCCCC", "#CCFFCC", "#CCCCFF", "#FFFFCC", "#FFCCFF", "#CCFFFF"]
            color_index = 0

            for i, row in df.iterrows():
                # ici prends la bonne colonne d'adresse
                rue_norm = extraire_nom_rue(row['Adresse saisie'])  # adapter 'Adresse' au nom correct
                
                if rue_norm in seen_rues:
                    color = seen_rues[rue_norm]
                else:
                    color = colors[color_index % len(colors)]
                    seen_rues[rue_norm] = color
                    color_index += 1

                # Appliquer le style couleur de fond à toute la ligne i
                styles.loc[i, :] = f'background-color: {color}'

            return styles

       # Construire d'abord la liste des lignes avec la colonne remplie ou vide
        rows = [{
            'Adresse saisie': a['Adresse fournie'],
            'Ordre': a['Ordre'],
            '⚠️ Aussi dans': ", ".join(
                [f"{num}-{tournee_mapping.get(num,'Inconnu')}" for num, nom in a['Autres_tournees']]
            ) if a['Autres_tournees'] else ""
        } for a in table]

        df_display = pd.DataFrame(rows)

        # Vérifier si la colonne '⚠️ Aussi dans' contient au moins une valeur non vide
        if not df_display['⚠️ Aussi dans'].any():
            # Supprimer la colonne si toutes les valeurs sont vides
            df_display = df_display.drop(columns=['⚠️ Aussi dans'])

        # Afficher le tableau
        st.dataframe(df_display.style.apply(highlight_dupes, axis=None), use_container_width=True)

    else:
        st.info("Aucune adresse valide ajoutée pour la tournée sélectionnée.")
