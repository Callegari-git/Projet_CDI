import csv
from datetime import datetime
from jobspy import scrape_jobs
import pandas as pd
import os

# 1. Définir tes critères de recherche
MOTS_CLES = os.getenv("MON_SCRAPER_MOTS_CLES", "data")       # Remplace par tes mots-clés (ex: "Développeur Python", "Alternance Marketing")
LOCALISATION = "Paris, France"   # Ville, Région ou Pays
NOMBRE_OFFRES = 30               # Nombre d'offres max souhaitées par plateforme

print(f"🕵️‍♂️ Lancement de la recherche pour '{MOTS_CLES}' à '{LOCALISATION}'...")

try:
    # 2. Lancement du scraping
    jobs = scrape_jobs(
        site_name=["linkedin"], # Les plateformes à cibler
        search_term=MOTS_CLES,
        location=LOCALISATION,
        results_wanted=NOMBRE_OFFRES,
        hours_old=72,                          # Récupère les offres des 3 derniers jours (Optionnel)
        country_with_domain="france",          # Force la recherche sur les extensions .fr / France
        
        # Le paramètre suivant permet de filtrer les types de contrats (si l'API du site le gère)
        # job_type="fulltime" # Options possibles: fulltime (CDI), parttime, internship (Stage), contract (CDD)
    )

    # 3. Traitement des résultats avec Pandas
    if not jobs.empty:
        # JobSpy renvoie énormément de colonnes, on ne garde que l'essentiel pour ton projet
        colonnes_utiles = [
            'site', 'title', 'company', 'location', 
            'date_posted', 'job_url', 'job_type'
        ]
        
        # On filtre les colonnes existantes pour éviter les erreurs
        colonnes_presentes = [col for col in colonnes_utiles if col in jobs.columns]
        df_filtre = jobs[colonnes_presentes]
        
        # Optionnel : Renommer les colonnes en français pour plus de clarté
        df_filtre = df_filtre.rename(columns={
            'site': 'Plateforme',
            'title': 'Intitulé du poste',
            'company': 'Entreprise',
            'location': 'Lieu',
            'date_posted': 'Date de publication',
            'job_url': 'Lien de l\'offre',
            'job_type': 'Type de contrat'
        })

        # 4. Sauvegarde dans un fichier CSV (lisible sur Excel)
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        nom_fichier = f"linkedin_{MOTS_CLES.lower().replace(' ', '_')}_{date_str}.csv"
        
        df_filtre.to_csv(nom_fichier, index=False, encoding='utf-8-sig', sep=';')
        
        print(f"\n✅ Succès ! {len(df_filtre)} offres trouvées et sauvegardées dans : {nom_fichier}")
        print("\nAperçu des 5 premières offres :")
        print(df_filtre.head())
        
    else:
        print("❌ Aucune offre trouvée pour ces critères.")

except Exception as e:
    print(f"⚠️ Une erreur est survenue lors du scraping : {e}")