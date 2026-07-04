from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse
import os
# --- TES PARAMÈTRES AVANCÉS ---
MOTS_CLES = os.getenv("MON_SCRAPER_MOTS_CLES", "data")
VILLE = "Paris"
TYPE_CONTRAT = os.getenv("MON_SCRAPER_CONTRAT", "CDI")    # (CDI, CDD, ALTERNANCE, STAGE)
SALAIRE_MIN = "45000"   # Sans espace
RAYON = "20"            # En kilomètres
MAX_PAGES = 3
# ------------------------------

liste_offres = []

with sync_playwright() as p:
    print("🚀 Lancement du navigateur pour HelloWork...")
    navigateur = p.chromium.launch(headless=False) 
    page = navigateur.new_page()

    # Encodage pour transformer les espaces/accents pour le format Web
    mots_cles_enc = urllib.parse.quote(MOTS_CLES)
    ville_enc = urllib.parse.quote(VILLE)

    # On construit l'URL de base avec tous tes critères précis
    url_base = (
        f"https://www.hellowork.com/fr-fr/emploi/recherche.html?"
        f"k={mots_cles_enc}&k_autocomplete=&"
        f"l={ville_enc}&l_autocomplete=&"
        f"st=relevance&c={TYPE_CONTRAT}&msa={SALAIRE_MIN}&ray={RAYON}&d=all"
    )

    for numero_page in range(1, MAX_PAGES + 1):
        print(f"📄 Analyse de la page {numero_page}...")

        # On ajoute le numéro de page à la fin de ton URL de base
        url_page = f"{url_base}&p={numero_page}"
        page.goto(url_page)

        if numero_page == 1:
            try:
                # Acceptation des cookies si la bannière est présente
                page.get_by_role("button", name="Tout accepter").click(timeout=3000)
            except:
                pass 

        # On attend 4 secondes pour que HelloWork charge les offres
        page.wait_for_timeout(4000) 

        # --- LECTURE ET DÉCOUPAGE ROBUSTE DU CODE HTML ---
        code_html = page.content()
        soup = BeautifulSoup(code_html, "html.parser")

        # NOUVELLE STRATÉGIE : Au lieu de chercher des titres, on cherche directement 
        # tous les liens <a> dont l'adresse (href) contient "/emplois/"
        liens_offres = soup.find_all("a", href=lambda href: href and "/emplois/" in href)

        offres_trouvees = 0
        
        for lien_tag in liens_offres:
            offres_trouvees += 1
            
            # 1. Reconstitution de l'URL absolue de l'offre
            href = lien_tag["href"]
            if href.startswith("/"):
                lien_offre = "https://www.hellowork.com" + href
            else:
                lien_offre = href

            # 2. Extraction du Titre et de l'Entreprise (Basée sur ton extrait HTML)
            titre = "Non renseigné"
            entreprise = "Non renseigné"
            
            # On cherche les balises <p> à l'intérieur de notre lien <a>
            balises_p = lien_tag.find_all("p")
            
            if len(balises_p) >= 1:
                titre = balises_p[0].text.strip()
            if len(balises_p) >= 2:
                entreprise = balises_p[1].text.strip()
                
            # Sécurité de secours : si jamais les <p> n'existent pas, 
            # on regarde si l'attribut "title" de ton lien <a> est renseigné
            if titre == "Non renseigné" and lien_tag.has_attr("title"):
                titre = lien_tag["title"].strip()

            # 3. Extraction du Lieu
            # Le lieu est généralement écrit juste à côté du lien, dans le conteneur parent
            carte_offre = lien_tag.find_parent("li") or lien_tag.find_parent("article") or lien_tag.parent
            lieu = "Non renseigné"

            if carte_offre:
                # On aspire tous les textes du bloc
                textes_bruts = list(carte_offre.stripped_strings)
                # On filtre pour enlever le titre et l'entreprise qu'on a déjà trouvés
                textes_propres = [t for t in textes_bruts if t not in [titre, entreprise] and len(t) > 2]
                
                if len(textes_propres) > 0:
                    # Le premier élément restant est 90% du temps la ville sur HelloWork
                    lieu = textes_propres[0]

            liste_offres.append({
                "Plateforme": "HelloWork",
                "Intitulé du poste": titre,
                "Entreprise": entreprise,
                "Lieu": lieu,
                "Date de publication": "Récente",
                "Type de contrat": TYPE_CONTRAT, 
                "Lien de l'offre": lien_offre
                
            })

        if offres_trouvees == 0:
            print("🛑 Fin des résultats. (Il n'y a plus d'offres ou un système anti-bot a bloqué l'affichage)")
            break

    navigateur.close()

# --- SAUVEGARDE ET NETTOYAGE ---
df_hellowork = pd.DataFrame(liste_offres)

if not df_hellowork.empty:
    df_hellowork = df_hellowork.drop_duplicates(subset=['Lien de l\'offre'])
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier = f"hellowork_{MOTS_CLES.lower().replace(' ', '_')}_{date_str}.csv"
    df_hellowork.to_csv(nom_fichier, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"\n🎉 Succès ! {len(df_hellowork)} offres extraites et sauvegardées dans {nom_fichier}")
else:
    print("\n❌ Échec : Aucune offre récupérée.")