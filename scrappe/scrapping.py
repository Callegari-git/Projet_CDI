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

# --- 2. LA LISTE DES SCRIPTS ---
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
        if script == "fusion_csv.py":
            print("\n" + "=" * 60)
            print("✨ TOUS LES SCRAPERS ONT TERMINÉ. LANCEMENT DE LA FUSION FINALE ✨")
            print("=" * 60)

        print(f"\n▶️ DÉMARRAGE : {script}...")
        start_time = time.time()

        try:
            # En lançant subprocess, il transmet automatiquement notre "post-it" aux autres scripts !
            subprocess.run([python_exe, script], check=True)
            
            duree = round(time.time() - start_time, 2)
            print(f"\n✅ SUCCÈS : {script} a terminé son travail en {duree} secondes.")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ ERREUR : {script} s'est arrêté prématurément (Code : {e.returncode}).")
            print("Le Maître d'Orchestre passe au script suivant pour ne pas bloquer la chaîne...")
            
        except FileNotFoundError:
            print(f"\n⚠️ INTROUVABLE : Le fichier {script} n'a pas été trouvé dans ce dossier.")

        print("-" * 60)
        time.sleep(2)

    print("\n🎉 MISSION ACCOMPLIE ! TOUTE LA CHAÎNE EST TERMINÉE ! 🎉")
    print("Vérifie ton dossier : ton fichier global 'TABLEAU_DE_BORD_OFFRES' est prêt.")

if __name__ == "__main__":
    lancer_scraping_global()