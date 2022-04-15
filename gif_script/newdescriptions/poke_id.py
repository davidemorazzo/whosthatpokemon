import pandas as pd
import glob

POKEDEX = 'pokemon_data.csv'
pokemon_data = pd.read_csv(POKEDEX)
files = glob.glob('gif_script\\newdescriptions\\name_transl\\*.txt')
for fname in files:
	with open(fname, 'r', encoding='UTF-8') as f:
		a = fname.split('\\')[-1].removesuffix('.txt')
		names_df = pd.read_csv(f, sep=',', header=None)
		names_df.index = names_df[0]
		names_df[a] = names_df[3]
		names_df[a] = names_df[a].str.lower()
		names_df[a] = names_df[a].str.replace('_', ' ')
		pokemon_data = pd.merge_ordered(pokemon_data, names_df[a], left_on='pokedex_num', right_on=0)
		pokemon_data[a] = pokemon_data[a].fillna(pokemon_data['name'])

	
pokemon_data['en'] = pokemon_data['name'].str.lower()
pokemon_data['en'] = pokemon_data['en'].str.replace('-', ' ')
pokemon_data.tier = 0
pokemon_data.to_csv('gif_script\\newdescriptions\\pokemon_names.csv', index=False)