import os
import glob
import ollama
import re

# ==========================================
# CONFIGURATION
# ==========================================
MODELE_OLLAMA = "mistral" # Remplace par "mistral" si tu préfères

DOSSIER_OFFRES = "descriptions_linkedin"
DOSSIER_RESULTATS = "resultats"
FICHIER_CV = "cv_lettre/mon_cv_base.txt"
FICHIER_LM = "cv_lettre/ma_lettre_base.txt"

# ==========================================
# FONCTIONS UTILES
# ==========================================
def lire_fichier(chemin):
    with open(chemin, 'r', encoding='utf-8') as file:
        return file.read()

def sauvegarder_fichier(chemin, contenu):
    with open(chemin, 'w', encoding='utf-8') as file:
        file.write(contenu)

def extraire_balise(texte, balise):
    """Extrait le texte contenu à l'intérieur d'une balise XML spécifique"""
    pattern = f"<{balise}>(.*?)</{balise}>"
    match = re.search(pattern, texte, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

# ==========================================
# SCRIPT PRINCIPAL
# ==========================================
def main():
    if not os.path.exists(DOSSIER_RESULTATS):
        os.makedirs(DOSSIER_RESULTATS)

    print("Chargement des documents de base...")
    try:
        cv_base = lire_fichier(FICHIER_CV)
        lm_base = lire_fichier(FICHIER_LM)
    except FileNotFoundError:
        print("Erreur : Fichier CV ou Lettre introuvable.")
        return

    fichiers_offres = glob.glob(os.path.join(DOSSIER_OFFRES, "*.txt"))
    if not fichiers_offres:
        print("Aucune offre trouvée.")
        return

    print(f"{len(fichiers_offres)} offre(s) trouvée(s). Lancement de l'IA locale ({MODELE_OLLAMA})...\n")

    for chemin_offre in fichiers_offres:
        nom_fichier = os.path.basename(chemin_offre)
        nom_offre_sans_ext = os.path.splitext(nom_fichier)[0]
        
        print(f"-> Analyse de l'offre : {nom_fichier}...")
        description_offre = lire_fichier(chemin_offre)

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
            # Appel à l'API locale d'Ollama
            response = ollama.chat(model=MODELE_OLLAMA, messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
                ], options={
                'temperature': 0.2  # 0 = Très strict/factuel, 1 = Très créatif
            })
            
            contenu_brut = response['message']['content']
            
            score = extraire_balise(contenu_brut, "score")
            ecarts = extraire_balise(contenu_brut, "ecarts")
            cv = extraire_balise(contenu_brut, "cv")
            lettre = extraire_balise(contenu_brut, "lettre")
            
            # Si l'IA a bien respecté les balises, on formate un beau fichier final
            if score and cv and lettre:
                texte_final = f"=== 1. SCORE DE PERTINENCE ===\n{score}\n\n"
                texte_final += f"=== 2. ANALYSE DES ÉCARTS ===\n{ecarts}\n\n"
                texte_final += f"=== 3. CV ADAPTÉ ===\n{cv}\n\n"
                texte_final += f"=== 4. LETTRE DE MOTIVATION ADAPTÉE ===\n{lettre}\n"
            else:
                # Si l'IA a bugué et oublié les balises, on sauvegarde la réponse brute par sécurité
                texte_final = contenu_brut

            chemin_resultat = os.path.join(DOSSIER_RESULTATS, f"candidature_{nom_offre_sans_ext}.txt")
            sauvegarder_fichier(chemin_resultat, texte_final)
            print(f"   [OK] Fichier finalisé : {chemin_resultat}")
            
        except Exception as e:
            print(f"   [ERREUR] Problème avec {nom_fichier} : {e}")

    print("\nProcessus terminé avec succès !")

if __name__ == "__main__":
    main()