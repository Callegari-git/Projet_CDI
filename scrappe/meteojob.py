from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse
import time
import random
import os

# --- TES PARAMÈTRES ---
MOTS_CLES = os.getenv("MON_SCRAPER_MOTS_CLES", "data")
VILLE = "Paris"
MAX_PAGES = 3
# ------------------------------

liste_offres = []

with sync_playwright() as p:
    print("🚀 Lancement du navigateur robot...")
    
    # On lance un navigateur classique, bien visible à l'écran
    navigateur = p.chromium.launch(headless=False) 
    page = navigateur.new_page()

    # Encodage pour le format Web (remplace les espaces par des %20 etc.)
    mots_cles_enc = urllib.parse.quote(MOTS_CLES)
    ville_enc = urllib.parse.quote(VILLE)

    # URL de base Meteojob
    url_base = f"https://www.meteojob.com/jobs?what={mots_cles_enc}&where={ville_enc}"

    # On charge la première page pour déclencher la sécurité
    page.goto(f"{url_base}&page=1")
    
    # --- ÉTAPE 2 : SCRAPING DES PAGES ---
    for numero_page in range(1, MAX_PAGES + 1):
        print(f"📄 Analyse de la page {numero_page}...")

        if numero_page > 1:
            url_page = f"{url_base}&page={numero_page}"
            page.goto(url_page)

            # On attend spécifiquement l'apparition d'une carte d'offre (<article>)
            try:
                page.wait_for_selector('article.cc-job-offer-list-item__card', timeout=15000)
                page.wait_for_timeout(random.randint(3000, 5000))
            except:
                print("⚠️ Temps d'attente dépassé (Meteojob a peut-être bloqué la suite).")

        # --- LECTURE ET DÉCOUPAGE HTML (Technique de la Boîte) ---
        code_html = page.content()
        soup = BeautifulSoup(code_html, "html.parser")

        # 1. On attrape toutes les boîtes (les <article> de chaque offre)
        cartes_offres = soup.find_all("article", class_=lambda c: c and "cc-job-offer-list-item__card" in c)

        offres_trouvees = 0
        
        for carte in cartes_offres:
            # On cherche le lien exact à l'intérieur de CETTE carte
            lien_tag = carte.find("a", class_=lambda c: c and "cc-job-offer-list-item__link" in c)
            
            if not lien_tag:
                continue
                
            offres_trouvees += 1

            # 2. Extraction du Lien
            href = lien_tag.get("href", "")
            if href.startswith("/"):
                lien_offre = "https://www.meteojob.com" + href
            else:
                lien_offre = href

            # 3. Extraction du Titre
            titre = lien_tag.text.strip()

            # 4. Extraction de l'Entreprise (Grâce à l'ID magique)
            entreprise = "Non renseigné"
            balise_entreprise = carte.find("p", id=lambda x: x and "company-name" in x)
            if balise_entreprise:
                entreprise = balise_entreprise.text.strip()

            # --- 5 & 6. NOUVELLE EXTRACTION INTELLIGENTE (Lieu, Date, Contrat) ---
            date_publication = "Récente"
            lieu = "Non renseigné"
            contrat = "Non renseigné"
            
            # On découpe TOUT le texte de la carte en petits morceaux
            textes_bruts = list(carte.stripped_strings)
            
            # On crée une liste noire des mots à jeter à la poubelle
            mots_a_ignorer = [
                titre, entreprise, "place", "Voir l'offre", 
                "Sauvegarder", "Postuler", "Nouveau"
            ]
            
            # On nettoie notre liste de textes
            textes_utiles = [t for t in textes_bruts if t not in mots_a_ignorer and len(t) > 1]
            
            # Maintenant, on analyse les survivants un par un !
            for texte in textes_utiles:
                # Est-ce que ce texte ressemble à une date ?
                if any(mot in texte for mot in ["Il y a", "Aujourd'hui", "Hier"]):
                    date_publication = texte
                    
                # Est-ce que ce texte ressemble à un type de contrat ?
                elif any(c in texte.upper() for c in ["CDI", "CDD", "STAGE", "ALTERNANCE", "INTERIM", "FREELANCE"]):
                    contrat = texte
                    
                # Est-ce que c'est le salaire ? (ex: "80 000 € - 100 000 € par an")
                # On l'ignore pour éviter qu'il ne se retrouve dans la colonne "Lieu"
                elif "€" in texte or "par an" in texte or "mois" in texte:
                    continue
                    
                # Si on arrive ici et qu'on n'a pas encore de lieu, c'est forcément la ville !
                elif lieu == "Non renseigné":
                    lieu = texte

            liste_offres.append({
                "Plateforme": "Meteojob",
                "Intitulé du poste": titre,
                "Entreprise": entreprise,
                "Lieu": lieu,
                "Date de publication": date_publication,
                "Type de contrat": contrat,
                "Lien de l'offre": lien_offre
            })

        if offres_trouvees == 0:
            print("🛑 Fin des résultats ou système anti-bot déclenché.")
            break

    navigateur.close()

# --- SAUVEGARDE ET NETTOYAGE ---
df_meteojob = pd.DataFrame(liste_offres)

if not df_meteojob.empty:
    df_meteojob = df_meteojob.drop_duplicates(subset=['Lien de l\'offre'])
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier = f"meteojob_{MOTS_CLES.lower().replace(' ', '_')}_{date_str}.csv"
    df_meteojob.to_csv(nom_fichier, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"\n🎉 Succès ! {len(df_meteojob)} offres extraites et sauvegardées dans {nom_fichier}")
else:
    print("\n❌ Échec : Aucune offre récupérée.")