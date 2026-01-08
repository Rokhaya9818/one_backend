import re

# Texte du communiqué (extrait de l'image)
communique_text = """
Point de situation sur les épidémies de Mpox et de Fièvre de la Vallée du Rift (FVR)

Le Ministère de la Santé et de l'Hygiène publique fait le point sur l'évolution des épidémies de la Fièvre
de la Vallée du Rift (FVR) et de la Mpox, à la date du 21 octobre 2025.

1- Fièvre de la Vallée du Rift (FVR)

Depuis le début de l'épidémie, le Sénégal a enregistré 277 cas confirmés, dont 22 décès et 207
guéris. La répartition des cas positifs est la suivante :

Région de Saint-Louis : 240 cas
• District Saint-Louis : 71 cas
• District Richard-Toll : 126 cas
• District Podor : 16 cas
• District Pété : 7 cas
• District Dagana : 20 cas

Région de Matam : 13 cas
• District Thilogne : 8 cas
• District Kanel : 2 cas
• District Ranérou : 1 cas
• District Matam : 2 cas

Région de Louga : 12 cas
• District Linguère : 5 cas
• District Keur Momar Sarr : 2 cas
• District Sakal : 2 cas
• District Dahra : 2 cas

Région de Fatick : 8 cas
• District Fatick : 2 cas
• District Diofior : 6 cas

Région de Dakar : 2 cas
• District Keur Massar : 1 cas
• District Sangalkam : 1 cas

Région de Kaolack : 2 cas
• District Nioro : 1 cas
• District Kaolack : 1 cas
"""

def extract_fvr_data_from_text(text):
    result = {
        "total_cas_confirmes": 0,
        "total_deces": 0,
        "total_gueris": 0,
        "regions": []
    }
    
    # Extraire les statistiques nationales
    stats_pattern = r'(\d+)\s*cas\s+confirmés.*?(\d+)\s*décès.*?(\d+)\s*guéris'
    stats_match = re.search(stats_pattern, text, re.IGNORECASE | re.DOTALL)
    if stats_match:
        result["total_cas_confirmes"] = int(stats_match.group(1))
        result["total_deces"] = int(stats_match.group(2))
        result["total_gueris"] = int(stats_match.group(3))
    
    # Extraire les régions et leurs cas
    region_pattern = r'Région\s+de\s+([^:]+?)\s*:\s*(\d+)\s*cas'
    region_matches = re.finditer(region_pattern, text, re.IGNORECASE)
    
    for region_match in region_matches:
        region_name = region_match.group(1).strip()
        region_total = int(region_match.group(2))
        
        # Trouver les districts de cette région
        region_start = region_match.end()
        next_region = re.search(r'Région\s+de\s+', text[region_start:], re.IGNORECASE)
        
        if next_region:
            region_text = text[region_start:region_start + next_region.start()]
        else:
            next_section = re.search(r'\d+[-\.]?\s*(Mpox|Contact|Pour toute)', text[region_start:], re.IGNORECASE)
            if next_section:
                region_text = text[region_start:region_start + next_section.start()]
            else:
                region_text = text[region_start:region_start + 500]
        
        # Extraire les districts
        district_pattern = r'District\s+([^:]+?)\s*:\s*(\d+)\s*cas'
        district_matches = re.finditer(district_pattern, region_text, re.IGNORECASE)
        
        districts = []
        for district_match in district_matches:
            district_name = district_match.group(1).strip()
            district_cas = int(district_match.group(2))
            districts.append({
                "nom": district_name,
                "cas": district_cas
            })
        
        result["regions"].append({
            "nom": region_name,
            "total_cas": region_total,
            "districts": districts
        })
    
    return result

# Tester l'extraction
print("=== TEST D'EXTRACTION DES DONNÉES FVR ===\n")
data = extract_fvr_data_from_text(communique_text)

print(f"✅ Total cas confirmés: {data['total_cas_confirmes']}")
print(f"✅ Total décès: {data['total_deces']}")
print(f"✅ Total guéris: {data['total_gueris']}")
print(f"\n✅ Nombre de régions extraites: {len(data['regions'])}\n")

for region in data['regions']:
    print(f"📍 {region['nom']}: {region['total_cas']} cas")
    for district in region['districts']:
        print(f"   • {district['nom']}: {district['cas']} cas")
    print()

# Vérification
total_verif = sum(r['total_cas'] for r in data['regions'])
print(f"🔍 Vérification: Somme des régions = {total_verif} (attendu: 277)")
