from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import random
import os
import subprocess # <-- AJOUT : Pour lancer des commandes Windows

# --- TES PARAMÈTRES ---
MAX_PAGES = 3
Type_contrat = os.getenv("MON_SCRAPER_CONTRAT", "CDI")
MOTS_CLES = os.getenv("MON_SCRAPER_MOTS_CLES", "data")
URL_RECHERCHE = f"https://www.jobteaser.com/fr/job-offers?contract={Type_contrat}&lat=48.853495&lng=2.348391&localized_location=Paris&localized_location=+France&location=France%3A%3A%C3%8Ele-de-France%3A%3AParis%3A%3AParis%3A%3A_bG9jYWxpdHk6ZnI6Y2l0eTpmemVIZnJnZDJQekhETTNCZXE0NlUyL3pFMG89&radius=30&q={MOTS_CLES}"
# ----------------------

# --- CHEMINS CHROME ---
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFIL_DIR = r"C:\ChromeDevProfile"

liste_offres = []

# 🔥 ÉTAPE 1 : Lancement automatique de Chrome en mode Debug
print("⚙️ Démarrage automatique de Chrome...")
try:
    # Python lance la commande PowerShell à ta place
    subprocess.Popen([
        CHROME_EXE,
        "--remote-debugging-port=9222",
        f"--user-data-dir={PROFIL_DIR}"
    ])
    # On fait une pause de 3 secondes pour laisser le temps à Chrome de s'ouvrir
    time.sleep(3) 
except Exception as e:
    print(f"❌ Erreur lors du lancement de Chrome : {e}")
    exit()

# 🔥 ÉTAPE 2 : Connexion de Playwright au Chrome qu'on vient d'ouvrir
with sync_playwright() as p:
    print("🚀 Connexion de Playwright au navigateur...")
    
    try:
        navigateur = p.chromium.connect_over_cdp("http://localhost:9222")
    except Exception as e:
        print("❌ ERREUR: Impossible de se connecter à Chrome.")
        exit()

    # On récupère l'onglet actuellement ouvert (celui qui vient de s'ouvrir)
    contexte = navigateur.contexts[0]
    
    # S'il y a déjà une page ouverte au démarrage, on l'utilise, sinon on en crée une
    if len(contexte.pages) > 0:
        page = contexte.pages[0]
    else:
        page = contexte.new_page()
    
    page.goto(URL_RECHERCHE)
    
    try:
        page.locator('button:has-text("Accepter"), button:has-text("Ok pour moi !")').first.click(timeout=3000)
    except:
        pass

    # --- ÉTAPE 3 : SCRAPING DES PAGES ---
    for numero_page in range(1, MAX_PAGES + 1):
        print(f"📄 Analyse de la page {numero_page}...")

        url_page = f"{URL_RECHERCHE}&page={numero_page}"
        page.goto(url_page)
        
        # Petite pause pour laisser les offres charger
        page.wait_for_timeout(random.randint(3000, 5000))

        # Lecture du HTML
        code_html = page.content()
        soup = BeautifulSoup(code_html, "html.parser")

        # Recherche de tous les liens d'offres
        liens_offres = soup.find_all("a", href=lambda href: href and "/job-offers/" in href and "?" not in href)
        offres_trouvees = 0

        for lien_tag in liens_offres:
            titre = lien_tag.text.strip()
            
            if not titre:
                continue
                
            offres_trouvees += 1
            
            href = lien_tag["href"]
            if href.startswith("/"):
                lien_offre = "https://www.jobteaser.com" + href
            else:
                lien_offre = href

            date_publication = "Récente"
            carte_offre = lien_tag.parent
            
            for _ in range(6):
                if carte_offre is None:
                    break
                balise_temps = carte_offre.find("time")
                if balise_temps:
                    date_publication = balise_temps.text.strip()
                    break 
                carte_offre = carte_offre.parent

            if not balise_temps:
                carte_offre = lien_tag.find_parent("div", class_=lambda c: c and "Card" in c) or lien_tag.parent.parent

            entreprise = "Non renseigné"
            lieu = "Paris" 
            
            if carte_offre:
                textes_bruts = list(carte_offre.stripped_strings)
                
                mots_a_ignorer = [
                    "CDI", "Stage", "Alternance", "CDD", "Nouveau", "Urgent", "Temps plein", 
                    "Sauvegarder", "...", titre, date_publication
                ]
                
                textes_utiles = [t for t in textes_bruts if t not in mots_a_ignorer]
                
                if len(textes_utiles) > 0:
                    entreprise = textes_utiles[0]
                if len(textes_utiles) > 1:
                    lieu = textes_utiles[1]

            liste_offres.append({
                "Plateforme": "JobTeaser",
                "Intitulé du poste": titre,
                "Entreprise": entreprise,
                "Lieu": lieu,
                "Date de publication": date_publication,
                "Type de contrat": Type_contrat, # J'ai corrigé "CDI" en dur ici par ta variable Type_contrat
                "Lien de l'offre": lien_offre
            })
        
        if offres_trouvees == 0:
            print("🛑 Aucune offre trouvée sur cette page.")
            break

    # Déconnexion (laisse Chrome ouvert)
    navigateur.close()

# --- SAUVEGARDE ET NETTOYAGE ---
df_jobteaser = pd.DataFrame(liste_offres)

if not df_jobteaser.empty:
    df_jobteaser = df_jobteaser.drop_duplicates(subset=['Lien de l\'offre'])
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier = f"jobteaser_data_{date_str}.csv"
    df_jobteaser.to_csv(nom_fichier, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n🎉 Succès ! {len(df_jobteaser)} offres JobTeaser extraites dans {nom_fichier}")
else:
    print("\n❌ Échec : Aucune offre récupérée.")