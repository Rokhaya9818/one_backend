import csv
import sys
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine
from models import MalariaRegional
import re

def clean_region_name(name):
    """Nettoyer et normaliser les noms de régions"""
    if not name or name == "Location":
        return None
    
    # Enlever les préfixes comme ".."
    name = name.replace("..", "").strip()
    
    # Enlever les suffixes de date
    name = re.sub(r'\s*\([\d>-]+\)', '', name)
    
    # Mapping des noms de régions
    region_mapping = {
        "Nord et Est": "Matam",
        "Nord": "Saint-Louis",
        "Ouest": "Dakar",
        "Centre": "Kaolack",
        "Sud": "Ziguinchor",
        "Saint Louis": "Saint-Louis",
    }
    
    return region_mapping.get(name, name)

def import_malaria_data():
    db = SessionLocal()
    
    try:
        # Supprimer les données existantes
        db.query(MalariaRegional).delete()
        db.commit()
        print("✓ Données malaria existantes supprimées")
        
        malaria_data = {}
        
        # Lire malaria-parasitemia_subnational_sen.csv
        print("\n📊 Lecture de malaria-parasitemia_subnational_sen.csv...")
        with open('/home/ubuntu/upload/malaria-parasitemia_subnational_sen.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Sauter les lignes de métadonnées
                if row['Location'] == 'Location' or row['Location'].startswith('#'):
                    continue
                    
                region = clean_region_name(row['Location'])
                if not region:
                    continue
                
                indicator = row['Indicator']
                value = row['Value']
                year = row['SurveyYear']
                
                if not value or value == '':
                    continue
                
                try:
                    year_int = int(year)
                except:
                    continue
                    
                key = f"{region}_{year}"
                if key not in malaria_data:
                    malaria_data[key] = {
                        'region': region,
                        'annee': year_int,
                        'prevalence_rdt': 0,
                        'prevalence_microscopy': 0,
                        'cas_confirmes': 0,
                        'deces': 0
                    }
                
                try:
                    val = float(value)
                    if 'RDT' in indicator:
                        malaria_data[key]['prevalence_rdt'] = val
                    elif 'microscopy' in indicator:
                        malaria_data[key]['prevalence_microscopy'] = val
                except:
                    pass
        
        # Lire select-malaria-indicators_subnational_sen.csv
        print("📊 Lecture de select-malaria-indicators_subnational_sen.csv...")
        with open('/home/ubuntu/upload/select-malaria-indicators_subnational_sen.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Sauter les lignes de métadonnées
                if row['Location'] == 'Location' or row['Location'].startswith('#'):
                    continue
                    
                region = clean_region_name(row['Location'])
                if not region:
                    continue
                
                indicator = row['Indicator']
                value = row['Value']
                year = row['SurveyYear']
                
                if not value or value == '':
                    continue
                
                try:
                    year_int = int(year)
                except:
                    continue
                    
                key = f"{region}_{year}"
                if key not in malaria_data:
                    malaria_data[key] = {
                        'region': region,
                        'annee': year_int,
                        'prevalence_rdt': 0,
                        'prevalence_microscopy': 0,
                        'cas_confirmes': 0,
                        'deces': 0
                    }
                
                try:
                    val = float(value)
                    # On peut ajouter d'autres indicateurs ici si nécessaire
                except:
                    pass
        
        # Insérer dans la base de données
        print(f"\n💾 Insertion de {len(malaria_data)} enregistrements...")
        count = 0
        for data in malaria_data.values():
            malaria = MalariaRegional(
                region=data['region'],
                annee=data['annee'],
                cas_confirmes=int(data['prevalence_rdt'] * 100),  # Estimation basée sur la prévalence
                deces=data['deces'],
                prevalence_rdt=data['prevalence_rdt'],
                prevalence_microscopie=data['prevalence_microscopy']
            )
            db.add(malaria)
            count += 1
        
        db.commit()
        print(f"✅ {count} enregistrements malaria importés avec succès!")
        
        # Afficher un résumé
        print("\n📈 Résumé par région:")
        result = db.execute(text("""
            SELECT region, COUNT(*) as count, SUM(cas_confirmes) as total_cas
            FROM malaria_regional
            GROUP BY region
            ORDER BY total_cas DESC
        """))
        for row in result:
            print(f"  - {row[0]}: {row[1]} années, {row[2]} cas estimés")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_malaria_data()
