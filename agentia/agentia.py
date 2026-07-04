import subprocess
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import os
import glob

# Initialisation du client LLM (ex: OpenAI avec votre clé API)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- VOS TEMPLATES DE BASE ---
CV_TEMPLATE = """
[Insérez ici le texte brut de votre CV générique]
Expériences : ...
Compétences : Python, Data Analysis...
"""

LETTRE_TEMPLATE = """
Madame, Monsieur,
Actuellement à la recherche de nouvelles opportunités en tant que [Poste], 
je suis très intéressé par l'entreprise [Entreprise].
[Insérez le reste de votre lettre générique]
"""
def trouver_dernier_csv(dossier="."):
    """Cherche le fichier .csv le plus récemment créé/modifié dans le dossier."""
    print("🔎 Recherche du dernier fichier CSV généré...")
    
    # Cherche tous les fichiers qui se terminent par .csv dans le dossier indiqué
    chemin_recherche = os.path.join(dossier, "*.csv")
    fichiers_csv = glob.glob(chemin_recherche)
    
    if not fichiers_csv:
        print("❌ Erreur : Aucun fichier CSV trouvé dans le dossier.")
        return None
        
    # Trouve le fichier avec la date de modification la plus récente
    dernier_fichier = max(fichiers_csv, key=os.path.getmtime)
    print(f"📂 Fichier trouvé : {dernier_fichier}")
    
    return dernier_fichier

def etape_1_lancer_scrapers():
    print("🚀 Lancement des scripts de web-scraping...")
    # Remplacez par le nom de votre script
    subprocess.run(["python", "scrapping.py"])
    print("✅ Scraping terminé.")

def etape_2_lire_csv(fichier_csv):
    print(f"📄 Lecture du fichier {fichier_csv}...")
    # D'après votre exemple, le séparateur est un point-virgule ';'
    df = pd.read_csv(fichier_csv, sep=';')
    # On filtre uniquement sur les CDI si besoin
    df_cdi = df[df['Type de contrat'].str.contains('CDI', na=False)]
    return df_cdi

def etape_3_scraper_description(url):
    print(f"🔍 Récupération de la description pour l'offre : {url}")
    try:
        # Ajout d'un header (User-Agent) pour éviter d'être bloqué par le site
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        reponse = requests.get(url, headers=headers)
        soup = BeautifulSoup(reponse.text, 'html.parser')
        
        # Astuce : On extrait tout le texte de la page (vous pourrez affiner avec des balises spécifiques)
        texte_complet = soup.get_text(separator=' ', strip=True)
        return texte_complet
    except Exception as e:
        print(f"❌ Erreur lors du scraping de {url}: {e}")
        return ""

def etape_4_generer_candidature(entreprise, intitule, description_offre):
    print(f"✍️ Génération des documents pour {entreprise} - {intitule}...")
    
    prompt = f"""
    Tu es un expert en recrutement. Voici la description d'une offre d'emploi pour le poste de {intitule} chez {entreprise} :
    "{description_offre[:3000]}" # On limite un peu la taille pour le contexte
    
    Voici mon CV actuel :
    "{CV_TEMPLATE}"
    
    Voici mon modèle de lettre de motivation :
    "{LETTRE_TEMPLATE}"
    
    TA MISSION :
    1. Identifie les 5 mots-clés principaux de l'offre (compétences, valeurs de l'entreprise).
    2. Réécris légèrement la partie "Compétences" ou "Accroche" de mon CV pour intégrer subtilement ces mots-clés, SANS inventer d'expériences que je n'ai pas.
    3. Adapte le modèle de lettre de motivation pour mentionner {entreprise}, le poste de {intitule}, et fais le lien entre mes compétences du CV et leurs besoins exprimés dans l'offre.
    
    Format de sortie souhaité :
    --- MOTS CLES ---
    ...
    --- CV ADAPTE ---
    ...
    --- LETTRE DE MOTIVATION ADAPTEE ---
    ...
    """

    response = client.chat.completions.create(
        model="gpt-4o", # ou gpt-3.5-turbo
        messages=[
            {"role": "system", "content": "Tu es un assistant carrière précis et professionnel."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content

def agent_candidature_autonome():
    # 1. Lancer le scraping (qui va générer le nouveau fichier CSV)
    etape_1_lancer_scrapers()
    
    # 2. Trouver AUTOMATIQUEMENT le fichier qui vient d'être créé
    fichier_csv = trouver_dernier_csv()
    
    # Sécurité : on arrête tout si aucun fichier n'a été trouvé
    if not fichier_csv:
        print("Arrêt de l'agent.")
        return
    
    # 3. Lire les résultats du fichier détecté
    offres_df = etape_2_lire_csv(fichier_csv)
    
    # Créer un dossier pour sauvegarder les résultats
    os.makedirs("candidatures_generees", exist_ok=True)
    
    # 4. Boucler sur les offres
    for index, row in offres_df.iterrows():
        entreprise = row['Entreprise']
        intitule = row['Intitulé du poste']
        lien = row["Lien de l'offre"]
        
        description = etape_3_scraper_description(lien)
        
        if description:
            resultat_llm = etape_4_generer_candidature(entreprise, intitule, description)
            
            # Sauvegarde
            nom_fichier = f"candidatures_generees/{entreprise}_{intitule}.txt".replace("/", "-")
            with open(nom_fichier, "w", encoding="utf-8") as f:
                f.write(resultat_llm)
            print(f"✅ Fichier sauvegardé : {nom_fichier}\n")

# --- LANCEMENT DE L'AGENT ---
if __name__ == "__main__":
    agent_candidature_autonome()