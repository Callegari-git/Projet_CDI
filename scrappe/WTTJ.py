from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
# --- TES PARAMÈTRES ---
EMAIL = "sebastien.callegari@gadz.org"
MOT_DE_PASSE = os.getenv("MOT_DE_PASSE_WTTJ")
MOTS_CLES = os.getenv("MON_SCRAPER_MOTS_CLES", "data") # Tu peux ajouter la ville directement ici !
MAX_PAGES = 3
# ----------------------

liste_offres = []

# Notre mouchard réseau (Intact, il écoute en silence)
def intercepter_reponse(reponse):
    if "api/v3/" in reponse.url and "jobs" in reponse.url and reponse.request.method == "GET" and reponse.status == 200:
        try:
            donnees_json = reponse.json()
            offres = donnees_json.get("data", [])
            
            if offres:
                print(f"🟢 {len(offres)} offres interceptées !")
                
            for offre in offres:
                entreprise_slug = offre.get("organization", {}).get("slug", "")
                offre_slug = offre.get("slug", "")
                
                liste_offres.append({
                    "Plateforme": "Welcome to the Jungle",
                    "Intitulé du poste": offre.get("name", "Non renseigné"),
                    "Entreprise": offre.get("organization", {}).get("name", "Non renseigné"),
                    "Lieu": offre.get("office", {}).get("city", "Non renseigné"),
                    "Date de publication": str(offre.get("published_at", "Non renseigné"))[:10],
                    "Lien de l'offre": f"https://www.welcometothejungle.com/fr/companies/{entreprise_slug}/jobs/{offre_slug}",
                    "Type de contrat": offre.get("contract_type", "Non renseigné")
                })
        except Exception:
            pass

with sync_playwright() as p:
    print("🚀 Lancement du robot Playwright...")
    navigateur = p.chromium.launch(headless=False) 
    page = navigateur.new_page()
    page.on("response", intercepter_reponse)
    
    # --- ÉTAPE 1 : CONNEXION ---
    print("🔑 Connexion en cours...")
    page.goto("https://www.welcometothejungle.com/fr/authenticate/signin?redirect=%2Ffr")
    
    try:
        page.get_by_role("button", name="Tout accepter").click(timeout=3000)
    except:
        pass

    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', MOT_DE_PASSE)
    page.click('button[type="submit"]')
    page.wait_for_timeout(5000) 
    
    # --- ÉTAPE 2 : RECHERCHE VIA LE MENU DE GAUCHE ---
    print(f"\n🕵️‍♂️ Modification des préférences pour '{MOTS_CLES}'...")
    
    page.goto("https://www.welcometothejungle.com/fr/jobs-matches?published_since=last_3d")
    page.wait_for_selector("text=Modifier les préférences", timeout=10000)
    
    try:
        # On repère la zone de texte
        champ_poste = page.locator('label:has-text("Intitulé de poste")').locator('xpath=..').locator('input').first
        if not champ_poste.is_visible():
            champ_poste = page.get_by_label("Intitulé de poste").first

        # L'ASTUCE EST ICI : Si le champ est toujours caché, on clique sur "Rôle" !
        if not champ_poste.is_visible():
            print("🔓 Ouverture du menu déroulant 'Rôle'...")
            page.locator('text="Rôle"').first.click()
            page.wait_for_timeout(1000) # On laisse 1 seconde pour l'animation visuelle d'ouverture
            
        champ_poste.click()
        
        # On efface et on remplit
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        
        print(f"⌨️ Saisie de '{MOTS_CLES}' dans le menu de gauche...")
        champ_poste.fill(MOTS_CLES)
        # 🔥 LA CORRECTION EST ICI 🔥
        # On vide la liste des fausses offres qui ont été chargées à l'ouverture de la page
        liste_offres.clear()
        print("🧹 Nettoyage des offres parasites par défaut...")
        
        page.keyboard.press("Enter")
        
        # On laisse le temps à la page 1 de se charger et d'être interceptée
        page.wait_for_timeout(4000) 
        
    except Exception as e:
        print("⚠️ Impossible de trouver le champ 'Intitulé de poste' ou le menu 'Rôle'.")
        print("Erreur technique :", e)
    
    # --- ÉTAPE 3 : PAGINATION AUTOMATIQUE PAR URL ---
    print("\n⏩ Lancement de la pagination rapide...")
    
    for numero_page in range(2, MAX_PAGES + 1):
        print(f"📄 Passage à la page {numero_page}...")
        
        url_suivante = f"https://www.welcometothejungle.com/fr/jobs-matches?published_since=last_3d&page={numero_page}"
        page.goto(url_suivante)
        
        page.wait_for_timeout(4000)

    navigateur.close()

# --- SAUVEGARDE ET NETTOYAGE ---
df_wttj = pd.DataFrame(liste_offres)

if not df_wttj.empty:
    traduction_contrats = {"full_time": "CDI", "internship": "Stage", "temporary": "CDD", "apprenticeship": "Alternance"}
    if "Type de contrat" in df_wttj.columns:
        df_wttj["Type de contrat"] = df_wttj["Type de contrat"].replace(traduction_contrats)

    df_wttj = df_wttj.drop_duplicates(subset=['Lien de l\'offre'])
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier = f"wttj_complet_{date_str}.csv"
    df_wttj.to_csv(nom_fichier, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"\n🎉 Mission accomplie ! {len(df_wttj)} offres propres et uniques exportées dans {nom_fichier}")
else:
    print("\n❌ Échec : Aucune offre récupérée.")