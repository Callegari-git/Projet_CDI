import subprocess
import sys
import time
import os 

# --- 1. L'INTERFACE UTILISATEUR ---
print("=" * 60)
print("🎯 BIENVENUE DANS TON MULTI-SCRAPER D'OFFRES D'EMPLOI 🎯")
print("=" * 60)

# On pose les questions à l'utilisateur
saisie_mots_cles = input("👉 Quels métiers cherches-tu ? (ex: data analyst, chef de projet) : ")
saisie_contrat = input("👉 Quel type de contrat ? (ex: CDI, STAGE, ALTERNANCE) : ")

# On colle les réponses sur notre "post-it virtuel" (Variables d'environnement)
os.environ["MON_SCRAPER_MOTS_CLES"] = saisie_mots_cles
os.environ["MON_SCRAPER_CONTRAT"] = saisie_contrat

print(f"\n✅ Parfait ! Lancement de la traque pour '{saisie_mots_cles}' en '{saisie_contrat}'...\n")
time.sleep(2)

# --- 2. CONFIGURATION DU DOSSIER ---
# Indique ici le nom du dossier qui contient tes scripts
DOSSIER_SCRIPTS = "scrappe"

# --- 3. LA LISTE DES SCRIPTS ---
SCRIPTS = [
    "hellowork.py",
    "Jobteaser.py",
    "Linkedin2.py",
    "meteojob.py",
    "WTTJ.py",
    "Indeed2.py",
    "fusion_csv.py"
]

def lancer_scraping_global():
    print("🚀 Lancement du Maître d'Orchestre 🚀\n")
    print("-" * 60)

    python_exe = sys.executable

    for script in SCRIPTS:
        # On crée le chemin exact vers le fichier (ex: scrappe/hellowork.py)
        chemin_script = os.path.join(DOSSIER_SCRIPTS, script)

        if script == "fusion_csv.py":
            print("\n" + "=" * 60)
            print("✨ TOUS LES SCRAPERS ONT TERMINÉ. LANCEMENT DE LA FUSION FINALE ✨")
            print("=" * 60)

        print(f"\n▶️ DÉMARRAGE : {chemin_script}...")
        
        # Vérification préventive : on s'assure que le fichier est bien dans le dossier
        if not os.path.exists(chemin_script):
            print(f"\n⚠️ INTROUVABLE : Le fichier {chemin_script} n'a pas été trouvé.")
            print("-" * 60)
            continue # On passe directement au script suivant

        start_time = time.time()

        try:
            # En lançant subprocess avec chemin_script, il va chercher dans le bon dossier
            subprocess.run([python_exe, chemin_script], check=True)
            
            duree = round(time.time() - start_time, 2)
            print(f"\n✅ SUCCÈS : {script} a terminé son travail en {duree} secondes.")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ ERREUR : {script} s'est arrêté prématurément (Code : {e.returncode}).")
            print("Le Maître d'Orchestre passe au script suivant pour ne pas bloquer la chaîne...")
            
        except FileNotFoundError:
            # Gère le cas (rare) où python_exe lui-même n'est pas trouvé par le système
            print(f"\n⚠️ ERREUR CRITIQUE : L'exécutable Python n'a pas été trouvé.")

        print("-" * 60)
        time.sleep(2)

    print("\n🎉 MISSION ACCOMPLIE ! TOUTE LA CHAÎNE EST TERMINÉE ! 🎉")
    print("Vérifie ton dossier : ton fichier global 'TABLEAU_DE_BORD_OFFRES' est prêt.")

if __name__ == "__main__":
    lancer_scraping_global()