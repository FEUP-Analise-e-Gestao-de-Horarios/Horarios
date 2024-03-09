from unidecode import unidecode

import json

with open('dados.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

def remove_accents(data):
    if isinstance(data, str):
        return unidecode(data)
    elif isinstance(data, dict):
        return dict((remove_accents(k), remove_accents(v)) for k, v in data.items())
    elif isinstance(data, list):
        return [remove_accents(item) for item in data]
    else:
        return data

data = remove_accents(data)

result = []
for category, subcategories in data.items():
    if isinstance(subcategories, list):
        result.extend([f"{'Redes'} - {item} - {category}" for item in subcategories])
    else:
        for subcategory, items in subcategories.items():
            result.extend([f"{category} - {item} - {subcategory}" for item in items])

with open('Salas.txt', 'w') as f:
    for item in result:
        f.write(f"{unidecode(item)}\n")