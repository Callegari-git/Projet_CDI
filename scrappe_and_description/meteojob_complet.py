from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse
import time
import random
import os
import re

# --- TES PARAMÈTRES ---
MOTS_CLES = os.getenv("MON_SCRAPER_MOTS_CLES", "data")
VILLE = "Paris"
MAX_PAGES = 1 # Mis à 1 pour vos tests
DOSSIER_CACHE = "offres_scrapees" 

os.makedirs(DOSSIER_CACHE, exist_ok=True)
# ------------------------------

liste_offres = []

with sync_playwright() as p:
    print("🚀 Lancement du navigateur robot pour Meteojob...")
    
    navigateur = p.chromium.launch(headless=False)
    context = navigateur.new_context()
    page = context.new_page()

    mots_cles_enc = urllib.parse.quote(MOTS_CLES)
    ville_enc = urllib.parse.quote(VILLE)

    url_base = f"https://www.meteojob.com/jobs?what={mots_cles_enc}&where={ville_enc}"

    page.goto(f"{url_base}&page=1")
    
    # --- 🍪 GESTION DES COOKIES (Recherche) ---
    try:
        page.get_by_role("button", name="Tout accepter").click(timeout=3000)
        print("🍪 Cookies acceptés sur la page de recherche !")
    except:
        pass 
    
    # --- ÉTAPE 1 : SCRAPING DES PAGES DE RÉSULTATS ---
    for numero_page in range(1, MAX_PAGES + 1):
        print(f"\n📄 Analyse de la page {numero_page}...")

        if numero_page > 1:
            url_page = f"{url_base}&page={numero_page}"
            page.goto(url_page)

            try:
                page.wait_for_selector('article.cc-job-offer-list-item__card', timeout=15000)
                page.wait_for_timeout(random.randint(3000, 5000))
            except:
                print("⚠️ Temps d'attente dépassé.")

        code_html = page.content()
        soup = BeautifulSoup(code_html, "html.parser")

        cartes_offres = soup.find_all("article", class_=lambda c: c and "cc-job-offer-list-item__card" in c)
        offres_trouvees = 0
        
        for carte in cartes_offres:
            lien_tag = carte.find("a", class_=lambda c: c and "cc-job-offer-list-item__link" in c)
            if not lien_tag:
                continue
                
            offres_trouvees += 1

            href = lien_tag.get("href", "")
            lien_offre = "https://www.meteojob.com" + href if href.startswith("/") else href
            titre = lien_tag.text.strip()

            entreprise = "Non renseigné"
            balise_entreprise = carte.find("p", id=lambda x: x and "company-name" in x)
            if balise_entreprise:
                entreprise = balise_entreprise.text.strip()

            date_publication = "Récente"
            lieu = "Non renseigné"
            contrat = "Non renseigné"
            
            textes_bruts = list(carte.stripped_strings)
            mots_a_ignorer = [titre, entreprise, "place", "Voir l'offre", "Sauvegarder", "Postuler", "Nouveau"]
            textes_utiles = [t for t in textes_bruts if t not in mots_a_ignorer and len(t) > 1]
            
            for texte in textes_utiles:
                if any(mot in texte for mot in ["Il y a", "Aujourd'hui", "Hier"]):
                    date_publication = texte
                elif any(c in texte.upper() for c in ["CDI", "CDD", "STAGE", "ALTERNANCE", "INTERIM", "FREELANCE"]):
                    contrat = texte
                elif "€" in texte or "par an" in texte or "mois" in texte:
                    continue
                elif lieu == "Non renseigné":
                    lieu = texte

            liste_offres.append({
                "Plateforme": "Meteojob",
                "Intitulé du poste": titre,
                "Entreprise": entreprise,
                "Lieu": lieu,
                "Date de publication": date_publication,
                "Type de contrat": contrat,
                "Lien de l'offre": lien_offre,
                "Fichier_Description": ""
            })

        if offres_trouvees == 0:
            print("🛑 Fin des résultats.")
            break

    print(f"\n✅ {len(liste_offres)} liens récupérés sur Meteojob. Début du téléchargement...")

    # --- ÉTAPE 2 : VISITER CHAQUE OFFRE POUR LA DESCRIPTION ---
    page_offre = context.new_page()
    premier_passage_offre = True
    
    for offre in liste_offres:
        lien = offre["Lien de l'offre"]
        titre = offre["Intitulé du poste"]
        entreprise = offre["Entreprise"]
        
        entreprise_clean = str(entreprise).replace(" ", "_").replace("/", "-")
        titre_clean = str(titre).replace(" ", "_").replace("/", "-")[:30]
        
        nom_fichier = f"Meteojob_{entreprise_clean}_{titre_clean}.txt"
        chemin_fichier = os.path.join(DOSSIER_CACHE, nom_fichier)
        
        offre['Fichier_Description'] = chemin_fichier
        
        if os.path.exists(chemin_fichier):
            print(f"⏩ Déjà en cache : {nom_fichier}")
            continue
            
        print(f"📥 Téléchargement : {titre} chez {entreprise}...")
        
        try:
            page_offre.goto(lien, timeout=15000)
            
            # --- NOUVEAUTÉ 1 : Attendre activement que la page soit prête ---
            # Au lieu d'un temps aléatoire aveugle, on attend jusqu'à 5 secondes maximum 
            # que l'une des balises de description apparaisse sur l'écran.
            try:
                page_offre.wait_for_selector('.cc-job-offer-description, [data-test="job-description"]', timeout=5000)
            except:
                pass # Si au bout de 5s ça n'apparaît pas, on continue quand même
                
            # --- 🍪 GESTION DES COOKIES ---
            if premier_passage_offre:
                try:
                    page_offre.get_by_role("button", name="Tout accepter").click(timeout=3000)
                except:
                    pass
                premier_passage_offre = False
            
            html_offre = page_offre.content()
            soup_offre = BeautifulSoup(html_offre, "html.parser")
            
            # --- NOUVEAUTÉ 2 : Détection Anti-Bot ---
            titre_page = soup_offre.title.string.lower() if soup_offre.title else ""
            if "captcha" in titre_page or "accès refusé" in titre_page or "access denied" in titre_page or "datadome" in html_offre:
                print(f"🛑 Meteojob a bloqué le robot sur cette offre ! (Anti-bot)")
                time.sleep(5) # On fait une longue pause pour calmer le jeu
                continue # On passe à l'offre suivante
            
            # --- STRATÉGIE D'EXTRACTION METEOJOB (Cascade) ---
            
            # Plan A, B, C (Les balises qu'on a vues sur vos captures)
            zone_description = (
                soup_offre.find("article", class_=lambda c: c and "cc-job-offer-description" in c) or
                soup_offre.find("div", attrs={"data-test": "job-description"}) or
                soup_offre.find("section", class_=lambda c: c and "cc-job-offer-details" in c)
            )
            
            # PLAN D (Le filet de sécurité) : 
            # Si les développeurs de Meteojob ont changé le nom des classes aujourd'hui,
            # on cherche un titre h2 ou h3 qui contient le mot "Description" ou "Missions"
            if not zone_description:
                titre_desc = soup_offre.find(lambda t: t.name in ['h2', 'h3'] and any(m in t.get_text().lower() for m in ["description", "mission", "profil"]))
                if titre_desc:
                    # On aspire le grand bloc qui contient ce titre
                    zone_description = titre_desc.find_parent("section") or titre_desc.find_parent("div")
            
            # PLAN E (Force brute) : On prend le contenu principal de la page
            if not zone_description:
                zone_description = soup_offre.find("main")
            
            if zone_description:
                description_complete = zone_description.get_text(separator='\n', strip=True)
                
                # Nettoyage de fin
                match_fin = re.search(r"(Postuler|Sauvegarder|Signaler cette offre|Découvrez l'entreprise)", description_complete, re.IGNORECASE)
                if match_fin:
                    description_complete = description_complete[:match_fin.start()].strip()

                with open(chemin_fichier, "w", encoding="utf-8") as f:
                    f.write(f"URL: {lien}\n")
                    f.write(f"ENTREPRISE: {entreprise}\n")
                    f.write(f"TITRE: {titre}\n")
                    f.write("-" * 50 + "\n\n")
                    f.write(description_complete)
            else:
                print(f"⚠️ Impossible de trouver le texte, même en force brute pour : {lien}")
                
        except Exception as e:
             print(f"❌ Erreur lors du chargement : {e}")
             
        time.sleep(random.uniform(1.5, 3.0))

    navigateur.close()

# --- ÉTAPE 3 : SAUVEGARDE DU CSV ---
df_meteojob = pd.DataFrame(liste_offres)

if not df_meteojob.empty:
    df_meteojob = df_meteojob.drop_duplicates(subset=["Lien de l'offre"])
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier_csv = f"TABLEAU_DE_BORD_METEOJOB_{date_str}.csv"
    
    df_meteojob.to_csv(nom_fichier_csv, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"\n🎉 Succès ! Les descriptions sont dans le dossier '{DOSSIER_CACHE}'.")
else:
    print("\n❌ Échec : Aucune offre récupérée.")