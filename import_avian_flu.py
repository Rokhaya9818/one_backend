import csv
import psycopg2
import uuid
from datetime import datetime
from collections import defaultdict

# Connexion à PostgreSQL
conn = psycopg2.connect(
    dbname="onehealth",
    user="onehealth_user",
    password="onehealth2025",
    host="localhost"
)
cur = conn.cursor()

# Supprimer les anciennes données
cur.execute("DELETE FROM grippe_aviaire")
conn.commit()
print("Anciennes données supprimées")

# Lire le fichier CSV
data = []
with open('/home/ubuntu/upload/sahel-prediction-death-animals-by-ach-gis4tech.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['country'] == 'Senegal':
            data.append(row)

print(f"Total enregistrements Sénégal: {len(data)}")

# Agréger par département, municipalité et date
aggregated = {}
for row in data:
    date = row['date']
    dept = row['department']
    municipality = row['municipality']
    dead_animals = int(row['dead_animals'])
    prob_death = float(row['prob_dead_animals_1'])
    
    # Créer une clé unique
    key = (date, dept, municipality)
    
    if key not in aggregated:
        aggregated[key] = {
            'date': date,
            'department': dept,
            'municipality': municipality,
            'cases': 0,
            'prob_death': prob_death
        }
    
    # Compter comme cas si dead_animals=1 ou probabilité > 50%
    if dead_animals == 1 or prob_death > 0.5:
        aggregated[key]['cases'] += 1

# Filtrer uniquement les cas confirmés (au moins 1 cas)
confirmed_cases = [v for v in aggregated.values() if v['cases'] > 0]
print(f"Cas confirmés à importer: {len(confirmed_cases)}")

# Insérer dans la base de données
import_count = 0
for case in confirmed_cases:
    try:
        cur.execute("""
            INSERT INTO grippe_aviaire 
            (report_id, date_rapport, region, espece, maladie, cas_confirmes, deces, statut_epidemie)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()),
            case['date'],
            case['department'],
            'Poultry',
            'Influenza A viruses of high pathogenicity',
            case['cases'],
            0,  # Pas de données de décès
            'Active' if datetime.strptime(case['date'], '%Y-%m-%d').year >= 2024 else 'Resolved'
        ))
        import_count += 1
    except Exception as e:
        print(f"Erreur lors de l'insertion: {e}")
        conn.rollback()  # Rollback en cas d'erreur
        break

if import_count > 0:
    conn.commit()
print(f"\n✅ {import_count} cas de grippe aviaire importés avec succès!")

# Statistiques
cur.execute("SELECT COUNT(*) FROM grippe_aviaire")
total = cur.fetchone()[0]
print(f"Total dans la base: {total}")

cur.execute("SELECT SUM(cas_confirmes) FROM grippe_aviaire")
total_cases = cur.fetchone()[0]
print(f"Total cas confirmés: {total_cases}")

cur.close()
conn.close()
