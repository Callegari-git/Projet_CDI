import requests
import json
import re
import csv
import time
import urllib3

# Désactive les alertes de sécurité si Proxyman est allumé
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ⚙️ CONFIGURATION ---
RECHERCHE = "data analyst"
LIEU = "Paris"
FICHIER_CSV = "offres_indeed.csv"

# Headers minimums pour passer pour un iPhone
HEADERS_SEARCH = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Indeed App 316.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Cookie": "NOMOB=1; CTK=1jsmpcmhn276g001" 
}

# Headers API récupérés via ton interception
HEADERS_GRAPHQL = {
    "Host": "apis.indeed.com",
    "indeed-api-key": "161092c2017b5bbab13edb12461a62d5a833871e7cad6d9d475304573de67ac8",
    "indeed-ctk": "1jsmpcmhn276g001",
    "Accept": "application/json",
    "indeed-locale": "fr-FR",
    "Content-Type": "application/json",
    "User-Agent": "Indeed Jobs/43217 CFNetwork/3860.600.12 Darwin/25.5.0",
    "Indeed-App-Info": "appv=316.0.0; appid=com.indeed.jobsearch; osv=26.5.1; os=ios; dtype=phone",
}

def get_job_keys(query, location):
    """ Étape 1 : Récupérer la liste des identifiants (Job Keys) """
    url = f"https://fr.indeed.com/m/jobs?q={query.replace(' ', '+')}&l={location.replace(' ', '+')}"
    print(f"🔎 1. Recherche des offres sur : {url}")
    
    response = requests.get(url, headers=HEADERS_SEARCH, verify=False)
    
    if response.status_code == 200:
        # On aspire tous les codes de 16 caractères hexadécimaux qui suivent "jk=" dans le code source
        cles_brutes = re.findall(r'jk=([0-9a-fA-F]{16})', response.text)
        
        # On utilise set() pour enlever les doublons (Indeed affiche souvent la même clé plusieurs fois)
        cles_uniques = list(set(cles_brutes))
        print(f"✅ {len(cles_uniques)} offres uniques trouvées !")
        return cles_uniques
    else:
        print(f"❌ Erreur lors de la recherche : Code {response.status_code}")
        return []

def get_job_details(job_key):
    """ Étape 2 : Récupérer les détails d'une offre précise via GraphQL """
    url = "https://apis.indeed.com/graphql"
    
    payload = {
        "variables": {
            "input": job_key,
            "isLoggedIn": False,
            "detailsInput": {} 
        },
        "query": """query Viewjob($input: ID!) {
            viewjob(input: $input) {
                job {
                    title
                    sourceEmployerName
                    location { formatted { long } }
                    compensation { formattedText }
                }
            }
        }"""
    }

    response = requests.post(url, headers=HEADERS_GRAPHQL, json=payload, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        try:
            # On va chercher l'objet job
            job_data = data.get("data", {}).get("viewjob", {}).get("job")
            
            # 🚨 LE GILET DE SAUVETAGE EST ICI :
            if not job_data:
                print(f"   ⚠️ L'offre {job_key} n'est plus disponible (vide ou expirée). On passe à la suivante.")
                return None
            
            # Si job_data existe, on continue normalement
            titre = job_data.get("title", "N/A")
            entreprise = job_data.get("sourceEmployerName", "N/A")
            
            lieu = "N/A"
            if job_data.get("location") and job_data["location"].get("formatted"):
                lieu = job_data["location"]["formatted"].get("long", "N/A")
                
            salaire = "Non spécifié"
            if job_data.get("compensation") and job_data["compensation"].get("formattedText"):
                salaire = job_data["compensation"]["formattedText"]
                
            return {
                "job_key": job_key,
                "titre": titre,
                "entreprise": entreprise,
                "lieu": lieu,
                "salaire": salaire,
                "url": f"https://fr.indeed.com/voir-emploi?jk={job_key}"
            }
        except Exception as e:
            print(f"   ⚠️ Erreur de lecture des données pour {job_key} : {e}")
            return None
    else:
        print(f"   ❌ Erreur API {response.status_code} pour {job_key}")
        return None
    
def main():
    job_keys = get_job_keys(RECHERCHE, LIEU)
    
    if not job_keys:
        print("Fin du programme (aucune offre trouvée).")
        return
        
    print(f"💾 2. Création du fichier '{FICHIER_CSV}' et extraction des détails...")
    
    # On ouvre le fichier CSV en écriture. Le délimiteur ';' est meilleur pour Excel en France.
    with open(FICHIER_CSV, mode='w', newline='', encoding='utf-8-sig') as fichier_csv:
        champs = ['job_key', 'titre', 'entreprise', 'lieu', 'salaire', 'url']
        writer = csv.DictWriter(fichier_csv, fieldnames=champs, delimiter=';')
        
        writer.writeheader()
        
        for idx, key in enumerate(job_keys, start=1):
            print(f"   [{idx}/{len(job_keys)}] Extraction de l'offre : {key}...")
            details = get_job_details(key)
            
            if details:
                writer.writerow(details)
            
            # 🚨 SÉCURITÉ ANTI-BAN : Ne jamais bombarder un serveur !
            # On attend 1,5 seconde entre chaque appel d'offre.
            time.sleep(1.5) 
            
    print(f"🎉 Terminé ! Ouvre le fichier '{FICHIER_CSV}' avec Excel.")

if __name__ == "__main__":
    main()