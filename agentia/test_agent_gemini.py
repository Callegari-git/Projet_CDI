import os
import glob
import time
from google import genai # --- NOUVEL IMPORT ICI ---
from dotenv import load_dotenv
load_dotenv()
# ==========================================
# CONFIGURATION
# ==========================================
# Remplace par ta vraie clé API
API_KEY = "API_KEY_GEMINI"

DOSSIER_OFFRES = "descriptions_linkedin"
DOSSIER_RESULTATS = "resultats"
FICHIER_CV = "cv_lettre/mon_cv_base.txt"
FICHIER_LM = "cv_lettre/ma_lettre_base.txt"

# --- NOUVELLE CONFIGURATION DU CLIENT ---
client = genai.Client(api_key=API_KEY)

# ==========================================
# FONCTIONS UTILES
# ==========================================
def lire_fichier(chemin):
    with open(chemin, 'r', encoding='utf-8') as file:
        return file.read()

def sauvegarder_fichier(chemin, contenu):
    with open(chemin, 'w', encoding='utf-8') as file:
        file.write(contenu)

# ==========================================
# SCRIPT PRINCIPAL
# ==========================================
def main():
    # 1. Vérification et création du dossier de résultats
    if not os.path.exists(DOSSIER_RESULTATS):
        os.makedirs(DOSSIER_RESULTATS)

    # 2. Chargement des documents de base
    print("Chargement du CV et de la Lettre de motivation de base...")
    try:
        cv_base = lire_fichier(FICHIER_CV)
        lm_base = lire_fichier(FICHIER_LM)
    except FileNotFoundError:
        print("Erreur : Le fichier CV ou Lettre de motivation est introuvable. Vérifie les noms.")
        return

    # 3. Lister toutes les offres d'emploi (.txt) dans le dossier 'offres'
    fichiers_offres = glob.glob(os.path.join(DOSSIER_OFFRES, "*.txt"))
    
    if not fichiers_offres:
        print("Aucune offre trouvée dans le dossier 'descriptions_linkedin'.")
        return

    print(f"{len(fichiers_offres)} offre(s) d'emploi trouvée(s). Début du traitement...\n")

    # 4. Boucle sur chaque offre d'emploi
    for chemin_offre in fichiers_offres:
        nom_fichier = os.path.basename(chemin_offre)
        nom_offre_sans_ext = os.path.splitext(nom_fichier)[0]
        
        print(f"-> Traitement de l'offre : {nom_fichier}")
        description_offre = lire_fichier(chemin_offre)

        # 5. Construction du prompt (les instructions pour l'IA)
        prompt = f"""
        Tu es un assistant de reformatage de texte automatisé et extrêmement strict. Ton unique but est de réécrire un texte existant en respectant des règles absolues.

        RÈGLES DE SÉCURITÉ VITALES (Si tu les enfreins, le processus échouera) :
        1. AUCUNE INVENTION : Tu ne dois sous AUCUN PRÉTEXTE ajouter une expérience professionnelle. Le candidat n'a JAMAIS travaillé pour l'entreprise cible.
        2. AUCUN PROJET FICTIF : Ne crée aucun faux projet académique pour correspondre à l'offre.
        3. RÈGLE DU CONTRAT : L'offre définit le contrat. Si le mot "Alternance" est dans l'offre, le mot "Stage" est formellement interdit dans toute ta réponse.
        4. AUCUN COMMENTAIRE : Ne génère aucun texte explicatif, ni aucune consigne entre crochets [ ].

        --- TEXTES SOURCES ---
        OFFRE D'EMPLOI :
        {description_offre}

        CV RÉEL DU CANDIDAT (Reformule légèrement les phrases pour faire ressortir l'analyse de données, MAIS N'AJOUTE AUCUNE COMPÉTENCE NI EXPÉRIENCE) :
        {cv_base}

        LETTRE RÉELLE (Adapte-la à l'offre en restant factuel) :
        {lm_base}
        ----------------------

        Tu dois répondre STRICTEMENT en utilisant les balises XML suivantes. N'écris absolument rien en dehors de ces balises :

        <score>
        Donne un score sur 100 et une seule phrase factuelle d'explication.
        </score>

        <ecarts>
        Liste à puces des compétences de l'offre absentes du CV.
        </ecarts>

        <cv>
        Insère le CV réécrit ici. Il doit contenir UNIQUEMENT Zenpark, Enedis, Professeur et tes vrais diplômes.
        </cv>

        <lettre>
        Insère la lettre de motivation ici. Rédigée professionnellement, en utilisant le bon type de contrat.
        </lettre>
        """

        try:
            # 6. Appel à l'IA --- NOUVELLE SYNTAXE ICI ---
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt
            )
            
            # 7. Sauvegarde du résultat
            chemin_resultat = os.path.join(DOSSIER_RESULTATS, f"candidature_{nom_offre_sans_ext}.txt")
            sauvegarder_fichier(chemin_resultat, response.text)
            print(f"   Succès ! Fichier sauvegardé sous : {chemin_resultat}")
            
            # Pause de 4 secondes pour éviter de surcharger l'API gratuite (Rate Limiting)
            time.sleep(4) 
            
        except Exception as e:
            print(f"   Erreur lors du traitement de {nom_fichier} : {e}")

    print("\nTerminé ! Toutes les candidatures ont été générées.")

if __name__ == "__main__":
    main()