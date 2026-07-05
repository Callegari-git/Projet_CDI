from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse
import time
import random
import os

# --- TES PARAMÈTRES ---
MOTS_CLES = "Data Analyst"
VILLE = "Paris"
MAX_PAGES = 1  # Restons sur 1 page pour le test (environ 25 offres)
OFFRES_PAR_PAGE = 25
# ------------------------------

liste_offres = []

# On crée automatiquement le dossier pour les fichiers texte s'il n'existe pas
DOSSIER_TXT = "descriptions_linkedin"
os.makedirs(DOSSIER_TXT, exist_ok=True)

with sync_playwright() as p:
    print("Lancement du navigateur robot...")
    navigateur = p.chromium.launch(headless=False) 
    page = navigateur.new_page()

    mots_cles_enc = urllib.parse.quote(MOTS_CLES)
    ville_enc = urllib.parse.quote(VILLE)
    url_base = f"https://www.linkedin.com/jobs/search?keywords={mots_cles_enc}&location={ville_enc}"
    
    # --- ÉTAPE 1 : RÉCUPÉRATION DE LA LISTE DES OFFRES ---
    for numero_page in range(MAX_PAGES):
        print(f"📄 Analyse de la page de recherche {numero_page + 1}...")
        start_val = numero_page * OFFRES_PAR_PAGE
        url_page = f"{url_base}&start={start_val}"

        page.goto(url_page)

        try:
            page.wait_for_selector('div.base-card', timeout=10000)
        except:
            print("⚠️ Pas de cartes d'offres détectées.")
            break

        # Défilement pour forcer le chargement de toutes les cartes (Lazy Loading)
        for _ in range(5):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(600)

        code_html = page.content()
        soup = BeautifulSoup(code_html, "html.parser")
        cartes_offres = soup.find_all("div", class_="base-search-card")

        print(f"{len(cartes_offres)} pré-offres trouvées sur la page. Analyse des détails...")

        # --- ÉTAPE 2 : EXTRACTION DES DÉTAILS ET DU TEXTE ---
        for idx, carte in enumerate(cartes_offres, start=1):
            lien_tag = carte.find("a", class_="base-card__full-link")
            if not lien_tag:
                continue

            lien_offre = lien_tag.get("href", "").split("?")[0]
            
            # Extraction propre du Job ID depuis le lien LinkedIn
            # Exemple : .../view/data-analyst-at-company-4397053388 -> 4397053388
            job_id = lien_offre.split("-")[-1].split("/")[-1]

            titre_tag = carte.find("h3", class_="base-search-card__title")
            titre = titre_tag.text.strip() if titre_tag else "Non renseigné"

            entreprise_tag = carte.find("h4", class_="base-search-card__subtitle")
            entreprise = entreprise_tag.text.strip() if entreprise_tag else "Non renseigné"

            lieu_tag = carte.find("span", class_="job-search-card__location")
            lieu = lieu_tag.text.strip() if lieu_tag else "Non renseigné"

            print(f"   [{idx}/{len(cartes_offres)}] Récupération de la description pour : {titre} ({entreprise})...")

            # ACTION : On navigue sur la page unique de l'offre pour avoir la description complète
            description_texte = "Non récupérée"
            try:
                # URL publique directe de l'offre
                url_directe = f"https://www.linkedin.com/jobs/view/{job_id}"
                page.goto(url_directe, timeout=15000)
                page.wait_for_timeout(1000) # Attente légère que le texte charge
                
                html_offre = page.content()
                soup_offre = BeautifulSoup(html_offre, "html.parser")
                
                # La classe publique standard de la description sur LinkedIn
                balise_desc = soup_offre.find("div", class_=lambda x: x and "show-more-less-html__markup" in x)
                
                if balise_desc:
                    description_texte = balise_desc.get_text(separator="\n").strip()
                    
                    # 💾 SAUVEGARDE DU FICHIER .TXT
                    nom_fichier_txt = f"{DOSSIER_TXT}/offre_{job_id}.txt"
                    with open(nom_fichier_txt, "w", encoding="utf-8") as f_txt:
                        f_txt.write(f"TITRE : {titre}\n")
                        f_txt.write(f"ENTREPRISE : {entreprise}\n")
                        f_txt.write(f"LIEU : {lieu}\n")
                        f_txt.write(f"LIEN : {lien_offre}\n")
                        f_txt.write(f"='='='='='='='='='='='='='='='='='='='='='\n\n")
                        f_txt.write(description_texte)
                else:
                    print(f"      Description introuvable pour l'offre {job_id} (Authwall ou offre expirée).")
                    
            except Exception as e:
                print(f"      Erreur lors de l'ouverture de l'offre {job_id} : {e}")

            # On ajoute l'offre à notre tableau, avec le nom du fichier texte associé
            liste_offres.append({
                "Plateforme": "LinkedIn",
                "ID Offre": job_id,
                "Intitulé du poste": titre,
                "Entreprise": entreprise,
                "Lieu": lieu,
                "Fichier Texte": f"offre_{job_id}.txt",
                "Lien de l'offre": lien_offre
            })

            # SÉCURITÉ ANTI-BOT CRITIQUE
            # LinkedIn bloque TRÈS vite si on enchaîne les pages d'offres.
            # On attend entre 3 et 6 secondes de manière aléatoire entre chaque offre.
            temps_pause = random.uniform(3.0, 6.0)
            time.sleep(temps_pause)

    navigateur.close()

# --- SAUVEGARDE DU FICHIER INDEX (CSV) ---
df_linkedin = pd.DataFrame(liste_offres)

if not df_linkedin.empty:
    df_linkedin = df_linkedin.drop_duplicates(subset=['Lien de l\'offre'])
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier_csv = f"linkedin_{MOTS_CLES.lower().replace(' ', '_')}_{date_str}.csv"
    
    df_linkedin.to_csv(nom_fichier_csv, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n Extraction terminée avec succès !")
    print(f" Fichier CSV d'index créé : {nom_fichier_csv}")
    print(f" Descriptions textuelles enregistrées dans le dossier : '{DOSSIER_TXT}/'")
else:
    print("\n Échec : Aucune donnée n'a pu être extraite.")