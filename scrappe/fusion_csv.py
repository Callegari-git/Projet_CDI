import pandas as pd
import glob
import os
from datetime import datetime

print("🔄 Démarrage du Fusionneur d'Offres d'Emploi 🔄\n")
print("=" * 60)

# 1. On cherche tous les fichiers CSV dans le dossier actuel
tous_les_csv = glob.glob("*.csv")

# On filtre pour ne prendre que les CSV générés par nos robots
prefixes_valides = ("hellowork_", "jobteaser_", "linkedin", "meteojob_", "wttj_")
fichiers_a_fusionner = [f for f in tous_les_csv if f.lower().startswith(prefixes_valides)]

if not fichiers_a_fusionner:
    print("⚠️ Aucun fichier CSV provenant de tes robots n'a été trouvé dans ce dossier.")
    print("Lance d'abord ton 'Maître d'Orchestre' pour générer les données !")
    exit()

print(f"📁 {len(fichiers_a_fusionner)} fichiers trouvés pour la fusion :")
for f in fichiers_a_fusionner:
    print(f"   - {f}")

liste_dataframes = []

# 2. Lecture et compilation de tous les fichiers
for fichier in fichiers_a_fusionner:
    try:
        # On lit chaque CSV (en gérant nos séparateurs et encodages spécifiques)
        df = pd.read_csv(fichier, sep=';', encoding='utf-8-sig')
        liste_dataframes.append(df)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de {fichier} : {e}")

if liste_dataframes:
    # 3. La grande fusion !
    print("\n🧬 Fusion des données en cours...")
    df_global = pd.concat(liste_dataframes, ignore_index=True)
    
    total_initial = len(df_global)
    print(f"📊 Nombre total d'offres aspirées : {total_initial}")

    # 4. Le Grand Nettoyage (Dédoublonnage)
    # Règle A : Suppression des liens strictement identiques (cas de bugs de scraping)
    df_global = df_global.drop_duplicates(subset=["Lien de l'offre"])
    
    # Règle B : Dédoublonnage croisé ! 
    # Si le même "Intitulé" est proposé par la même "Entreprise", c'est un doublon inter-plateformes.
    df_global = df_global.drop_duplicates(subset=["Intitulé du poste", "Entreprise"])
    
    total_final = len(df_global)
    doublons_supprimes = total_initial - total_final
    
    print(f"🧹 Nettoyage terminé : {doublons_supprimes} doublons supprimés.")
    print(f"🎯 Nombre final d'offres uniques : {total_final}")

    # 5. Création du fichier CSV global
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    nom_fichier_csv = f"TABLEAU_DE_BORD_OFFRES_{date_str}.csv"
    
    try:
        # On exporte en vrai format CSV
        df_global.to_csv(nom_fichier_csv, index=False, sep=';', encoding='utf-8-sig')
        print("\n" + "=" * 60)
        print(f"🎉 SUCCÈS TOTAL ! Ton fichier global {nom_fichier_csv} est prêt ! 🎉")
        print("=" * 60)
        
        # 🔥 LA MODIFICATION EST ICI : Suppression des fichiers sources après succès 🔥
        print("\n🧹 Nettoyage du dossier : Suppression des fichiers CSV de chaque plateforme...")
        for fichier in fichiers_a_fusionner:
            try:
                os.remove(fichier)
                print(f"   🗑️ Supprimé : {fichier}")
            except Exception as e:
                print(f"   ⚠️ Impossible de supprimer {fichier} : {e}")
        print("✨ Dossier nettoyé ! Seul ton fichier global mis à jour a été conservé.")

    except Exception as e:
        print(f"\n❌ Erreur lors de la création du fichier CSV global : {e}")
        print("⚠️ Par sécurité, aucun fichier source n'a été supprimé.")