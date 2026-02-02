from tours.models import Artist
names = [
"ANOTR","Tujamo","Kura","Dubdogz","KlangKuenstler","Tungevaag","Joseph Capriati","ZHANGYE","22Bullets","Mathame","Danny Avila","Azyr","Argy","Julian Jordan","Holy Priest","Cat Dealers","Marco Carola","Rezz","Chase & Status","KI/KI","999999999","Adam Beyer","Dennis Cruz","DJ Bliss","Brennan Heart","Naeleck","Alan Shirahama","Hot Since 82","Fatboy Slim","Wade","OGUZ","Anfisa Letyago","Alexander Popov","Sonny Fodera","Blasterjaxx","Diego Miranda","Marco Carola","Jonas Blue","Sammy Virji","KAKA","Miss K8","AVA CROWN","Josh Baker","Illenium","Green Velvet","BLOND:ISH","Kettama","Luca Testa","Aryue","Ben Hemsley"
]
unique = []
seen = set()
for name in names:
    if name not in seen:
        seen.add(name)
        unique.append(name)
created = 0
for name in unique:
    obj, was_created = Artist.objects.get_or_create(name=name, defaults={"genre": "DJ"})
    if was_created:
        created += 1
print(f"created={created} total_in_list={len(unique)}")
