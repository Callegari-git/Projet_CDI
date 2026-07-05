from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse
import time
import random
import os

# --- TES PARAMÈTRES ---
MOTS_CLES = "Data"
VILLE = "Paris"
MAX_PAGES = 3
OFFRES_PAR_PAGE = 25 
# ------------------------------

liste_offres = []

with sync_playwright() as p:
    print("🚀 Lancement du navigateur robot pour LinkedIn...")
    
    # headless=False permet de voir le robot travailler
    navigateur = p.chromium.launch(headless=False) 
    page = navigateur.new_page()

    # Encodage pour le format Web
    mots_cles_enc = urllib.parse.quote(MOTS_CLES)
    ville_enc = urllib.parse.quote(VILLE)

    # 💡 L'URL MAGIQUE : On utilise la version "Guest" de LinkedIn
    url_base = f"https://www.linkedin.com/jobs/search?keywords={mots_cles_enc}&location={ville_enc}"
    
    # --- ÉTAPE 2 : SCRAPING DES PAGES ---
    for numero_page in range(MAX_PAGES):
        print(f"📄 Analyse de la page {numero_page + 1}...")

        # Sur LinkedIn, la pagination ne se fait pas avec page=1,2,3...
        # Elle se fait avec "start=0", "start=25", "start=50"
        start_val = numero_page * OFFRES_PAR_PAGE
        url_page = f"{url_base}&start={start_val}"

        page.goto(url_page)

        # On attend l'apparition d'une carte d'offre publique
        try:
            page.wait_for_selector('div.base-card', timeout=10000)
        except:
            print("⚠️ Temps d'attente dépassé (LinkedIn a bloqué ou il n'y a plus d'offres).")
            break

        # --- ÉTAPE CLÉ SUR LINKEDIN : LE SCROLL ---
        # LinkedIn utilise le "Lazy Loading" (les données ne chargent que si on descend la page)
        for _ in range(6):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(500)

        page.wait_for_timeout(random.randint(2000, 4000)) # Pause humaine anti-bot

        # --- LECTURE ET DÉCOUPAGE HTML ---
        code_html = page.content()
        soup = BeautifulSoup(code_html, "html.parser")

        # 1. On attrape toutes les boîtes d'offres (les classes publiques sont propres)
        cartes_offres = soup.find_all("div", class_="base-search-card")

        offres_trouvees = 0
        
        for carte in cartes_offres:
            offres_trouvees += 1

            # 2. Extraction du Lien
            lien_tag = carte.find("a", class_="base-card__full-link")
            # On nettoie le lien (on enlève tout ce qui est après le "?" de tracking)
            lien_offre = lien_tag.get("href", "").split("?")[0] if lien_tag else "Non renseigné"

            # 3. Extraction du Titre
            titre_tag = carte.find("h3", class_="base-search-card__title")
            titre = titre_tag.text.strip() if titre_tag else "Non renseigné"

            # 4. Extraction de l'Entreprise
            entreprise_tag = carte.find("h4", class_="base-search-card__subtitle")
            entreprise = entreprise_tag.text.strip() if entreprise_tag else "Non renseigné"

            # 5. Extraction du Lieu
            lieu_tag = carte.find("span", class_="job-search-card__location")
            lieu = lieu_tag.text.strip() if lieu_tag else "Non renseigné"

            # 6. Extraction de la Date
            date_tag = carte.find("time", class_="job-search-card__listdate")
            if not date_tag:
                # Parfois la classe change si c'est une offre très récente
                date_tag = carte.find("time", class_="job-search-card__listdate--new")
            date_publication = date_tag.text.strip() if date_tag else "Non renseigné"

            liste_offres.append({
                "Plateforme": "LinkedIn",
                "Intitulé du poste": titre,
                "Entreprise": entreprise,
                "Lieu": lieu,
                "Date de publication": date_publication,
                "Lien de l'offre": lien_offre
            })

        if offres_trouvees == 0:
            print("🛑 Plus aucune offre trouvée sur la page.")
            break

    navigateur.close()

# --- SAUVEGARDE ET NETTOYAGE ---
df_linkedin = pd.DataFrame(liste_offres)

if not df_linkedin.empty:
    # On supprime les doublons éventuels basés sur le lien
    df_linkedin = df_linkedin.drop_duplicates(subset=['Lien de l\'offre'])
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier = f"linkedin_{MOTS_CLES.lower().replace(' ', '_')}_{date_str}.csv"
    
    # utf-8-sig permet à Excel de lire les accents français (é, à) correctement
    df_linkedin.to_csv(nom_fichier, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"\n🎉 Succès ! {len(df_linkedin)} offres extraites et sauvegardées dans {nom_fichier}")
else:
    print("\n❌ Échec : Aucune offre récupérée.")