import pandas as pd
import glob

clear = glob.glob("./gifs/clear/*")
blacked = glob.glob("./gifs/blacked/*")
names = [p.split('\\')[1].replace('.gif', '').lower() for p in blacked]
# lista descrizioni
with open("descriptions.txt", 'r', encoding='utf-8') as f:
    lines = f.readlines()
    descriptions = {}
    for l in lines:
        name = l.split('|')[0].strip().lower()
        desc = l.split('|')[1].strip()
        if  desc != "":
            descriptions[name] = desc

data_list = []
for p in names:
    row = {}
    row['name'] = p
    row['clear_path'] = "./gifs/clear/"+p+'.gif'
    row['blacked_path'] = "./gifs/blacked/"+p+'.gif'
    try:
        row['description'] = descriptions[p]
    except :
        row['description'] = " "
    data_list.append(row)

df = pd.DataFrame(data_list)
df.set_index(inplace=True, keys='name', drop=True)
df.to_csv("pokemon_data.csv")
pass
