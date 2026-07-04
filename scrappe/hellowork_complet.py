from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse
import os
import time

# --- PARAMÈTRES AVANCÉS ---
MOTS_CLES = os.getenv("MON_SCRAPER_MOTS_CLES", "data scientist")
VILLE = "Paris"
TYPE_CONTRAT = os.getenv("MON_SCRAPER_CONTRAT", "CDI")    # (CDI, CDD, ALTERNANCE, STAGE)
SALAIRE_MIN = "45000"   # Sans espace
RAYON = "20"            # En kilomètres
MAX_PAGES = 1           # (Mis à 1 pour vos tests, à augmenter plus tard)
DOSSIER_CACHE = "offres_scrapees" # Le dossier où on va stocker les descriptions pour l'IA

# Créer le dossier s'il n'existe pas
os.makedirs(DOSSIER_CACHE, exist_ok=True)

liste_offres = []

with sync_playwright() as p:
    print("🚀 Lancement du navigateur pour HelloWork...")
    navigateur = p.chromium.launch(headless=False)
    context = navigateur.new_context()
    page = context.new_page()

    # --- ÉTAPE 1 : RÉCUPÉRATION DES LIENS ---
    mots_cles_enc = urllib.parse.quote(MOTS_CLES)
    ville_enc = urllib.parse.quote(VILLE)
    url_base = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={mots_cles_enc}&l={ville_enc}&st=relevance&c={TYPE_CONTRAT}&msa={SALAIRE_MIN}&ray={RAYON}&d=all"

    for numero_page in range(1, MAX_PAGES + 1):
        print(f"\n📄 Analyse de la page de résultats {numero_page}...")
        page.goto(f"{url_base}&p={numero_page}")

        if numero_page == 1:
            try:
                page.get_by_role("button", name="Tout accepter").click(timeout=3000)
            except:
                pass 

        page.wait_for_timeout(3000) 

        code_html = page.content()
        soup = BeautifulSoup(code_html, "html.parser")
        liens_offres = soup.find_all("a", href=lambda href: href and "/emplois/" in href)

        for lien_tag in liens_offres:
            href = lien_tag["href"]
            lien_offre = "https://www.hellowork.com" + href if href.startswith("/") else href
            
            balises_p = lien_tag.find_all("p")
            titre = balises_p[0].text.strip() if len(balises_p) >= 1 else "Inconnu"
            entreprise = balises_p[1].text.strip() if len(balises_p) >= 2 else "Inconnu"

            # On aspire également le lieu (comme dans votre premier script)
            carte_offre = lien_tag.find_parent("li") or lien_tag.find_parent("article") or lien_tag.parent
            lieu = "Non renseigné"
            if carte_offre:
                textes_bruts = list(carte_offre.stripped_strings)
                textes_propres = [t for t in textes_bruts if t not in [titre, entreprise] and len(t) > 2]
                if len(textes_propres) > 0:
                    lieu = textes_propres[0]

            liste_offres.append({
                "Plateforme": "HelloWork",
                "Fichier_Description": "" ,# Préparation de la colonne
                "Intitulé du poste": titre,
                "Entreprise": entreprise,
                "Lieu": lieu,
                "Date de publication": "Récente",
                "Type de contrat": TYPE_CONTRAT,
                "Lien de l'offre": lien_offre
            })
            
    print(f"\n✅ {len(liste_offres)} liens d'offres récupérés. Début du téléchargement des descriptions...")

    # --- ÉTAPE 2 : VISITER CHAQUE OFFRE POUR LA DESCRIPTION ---
    page_offre = context.new_page()
    
    for offre in liste_offres:
        # 1. On extrait les variables pour éviter le plantage Python (SyntaxError f-string)
        lien = offre["Lien de l'offre"]
        titre = offre["Intitulé du poste"]
        entreprise = offre["Entreprise"]
        
        entreprise_clean = str(entreprise).replace(" ", "_").replace("/", "-")
        titre_clean = str(titre).replace(" ", "_").replace("/", "-")[:30]
        
        nom_fichier = f"{entreprise_clean}_{titre_clean}.txt"
        chemin_fichier = os.path.join(DOSSIER_CACHE, nom_fichier)
        
        # 2. Mise à jour du dictionnaire avec le chemin du fichier pour le CSV
        offre['Fichier_Description'] = chemin_fichier
        
        # 3. Vérification du cache
        if os.path.exists(chemin_fichier):
            print(f"⏩ Déjà en cache : {nom_fichier}")
            continue
            
        print(f"📥 Téléchargement : {titre} chez {entreprise}...")
        
        try:
            page_offre.goto(lien, timeout=15000)
            page_offre.wait_for_timeout(2000)
            
            html_offre = page_offre.content()
            soup_offre = BeautifulSoup(html_offre, "html.parser")
            
            # --- 1. NETTOYAGE DESTRUCTIF PREALABLE ---
            # On détruit tout ce qui n'est clairement pas la description
            # (menus, pied de page, publicités, scripts invisibles...)
            for element in soup_offre(["nav", "footer", "header", "aside", "script", "style", "button"]):
                element.decompose()
            
            description_complete = None

            # --- 2. STRATÉGIE EN ENTONNOIR ---
            
            # PLAN A : Les balises sémantiques parfaites (Celle qu'on avait avant)
            zone_description = (
                soup_offre.find("section", attrs={"data-cy": "job-description"}) or
                soup_offre.find("div", class_=lambda c: c and "job-description" in c.lower()) or
                soup_offre.find("div", attrs={"itemprop": "description"})
            )
            
            if zone_description:
                description_complete = zone_description.get_text(separator='\n', strip=True)

            # PLAN B : Recherche par mots-clés typiques (Pour votre exemple exact !)
            # Si le plan A échoue, on cherche un titre qui contient "missions" ou "profil recherché"
            if not description_complete:
                titre_cle = soup_offre.find(lambda t: t.name in ['h2', 'h3', 'h4', 'strong', 'p', 'div'] and 
                                           ("missions du poste" in t.get_text(strip=True).lower() or 
                                            "profil recherché" in t.get_text(strip=True).lower() or
                                            "les missions" in t.get_text(strip=True).lower()))
                if titre_cle:
                    # On remonte d'un ou deux crans pour prendre le grand bloc (section, article ou div)
                    # qui contient ce titre.
                    parent = titre_cle.find_parent("section") or titre_cle.find_parent("article") or titre_cle.parent
                    if parent:
                        description_complete = parent.get_text(separator='\n', strip=True)

            # PLAN C : Mode "Force Brute Propre"
            # Si on a vraiment rien trouvé, on prend le contenu principal de la page.
            # Comme on a détruit les menus au début, le texte sera quand même assez propre.
            if not description_complete:
                zone_large = soup_offre.find("main") or soup_offre.find("body")
                if zone_large:
                    texte_brut = zone_large.get_text(separator='\n', strip=True)
                    
                    # --- NOUVEAU : LE NETTOYAGE INTELLIGENT ---
                    import re
                    
                    # 1. Couper le début (enlever les salaires, menus...)
                    # On cherche des mots-clés qui annoncent le début de la description
                    match_debut = re.search(r"(Détail du poste|Description de poste|Vos missions|Fonctions et responsabilités|Le profil recherché)", texte_brut, re.IGNORECASE)
                    
                    if match_debut:
                        texte_brut = texte_brut[match_debut.start():]
                        
                    # 2. Couper la fin (enlever les suggestions, pubs, boilerplates d'entreprise)
                    # On cherche des mots-clés de pied de page
                    match_fin = re.search(r"(Ensemble, en tant que propriétaires|La vie chez .* est ancrée|Créez votre compte Hellowork|Ces offres pourraient aussi|Recherches similaires|Publiée le \d{2}/\d{2}/\d{4}|Entreprise .* a été créée en)", texte_brut, re.IGNORECASE)
                    
                    if match_fin:
                        texte_brut = texte_brut[:match_fin.start()]
                        
                    description_complete = texte_brut.strip()

            # --- 3. SAUVEGARDE DU RESULTAT ---
            if description_complete and len(description_complete) > 100:
                with open(chemin_fichier, "w", encoding="utf-8") as f:
                    f.write(f"URL: {lien}\n")
                    f.write(f"ENTREPRISE: {entreprise}\n")
                    f.write(f"TITRE: {titre}\n")
                    f.write("-" * 50 + "\n\n")
                    f.write(description_complete)
            else:
                print(f"⚠️ Impossible de trouver le texte pour {lien} (Même avec le Plan C)")
                
        except Exception as e:
             print(f"❌ Erreur lors du chargement : {e}")
             
        time.sleep(2)

    navigateur.close()

# --- ÉTAPE 3 : SAUVEGARDE DU CSV ---
df_hellowork = pd.DataFrame(liste_offres)

if not df_hellowork.empty:
    df_hellowork = df_hellowork.drop_duplicates(subset=["Lien de l'offre"])
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier_csv = f"hellowork_{MOTS_CLES.lower().replace(' ', '_')}_{date_str}.csv"
    
    df_hellowork.to_csv(nom_fichier_csv, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"\n🎉 Succès ! Les descriptions sont dans le dossier '{DOSSIER_CACHE}'.")
    print(f"📊 Le tableau de bord a été sauvegardé sous : {nom_fichier_csv}")
else:
    print("\n❌ Échec : Aucune offre récupérée.")