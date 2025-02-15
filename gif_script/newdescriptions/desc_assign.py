import pandas as pd
import itertools
import re
import pandas as pd
import glob


SOURCE = 'gif_script\\newdescriptions\\english.txt'
FILENAME = 'gif_script\\newdescriptions\\descriptions_english.csv'
POKEDEX = 'gif_script\\newdescriptions\\new_database1.csv'

def parse_description_file(src, df = None) -> pd.DataFrame:
	with open(src, 'r', encoding='UTF-8') as f:
		# Read the file and create the dataframe
		col_name = src.split('\\')[-1].removesuffix('.txt')
		print(col_name)
		text = f.read()
		descriptions = re.split(r'\n{2,}', text)
		print("Number of descriptions:", len(descriptions))
		df = pd.DataFrame(descriptions, columns=[col_name])

	new_descr = df
	pokemon_data = pd.read_csv(POKEDEX, index_col='name')

	new_descr = pd.DataFrame(index=pokemon_data.index, columns=[col_name])
	for idx in new_descr.index:
		for description in descriptions:
			# pokemon set to find
			poke_translated = pokemon_data.loc[idx, col_name].replace('-', ' ').split(' ')
			poke_translated = set(poke_translated)
			poke_en = pokemon_data.loc[idx, 'en'].split(' ')
			poke_en = set(poke_en)

			# get words until first parenthesis hoping it is the full pokemon name
			description_pokemon = description.split(' (')[0].lower()
			description_pokemon = description_pokemon.replace('alolan', 'alola')
			description_pokemon = description_pokemon.replace('galarian', 'galar')
			words = description_pokemon.strip().lower().split(' ')
			words = set(words)
			
			
			if poke_translated == words:
				new_descr.loc[idx, col_name] = description
				descriptions.remove(description)
				break
			elif poke_en == words:
				new_descr.loc[idx, col_name] = description
				descriptions.remove(description)
				break

	# new_descr.to_csv('gif_script\\newdescriptions\\descriptions_english_with_pokemon.csv', index=False)
	# print('Pokemons not assigned ', pokemons_idx)
	# print('Descriptions without pokemon: ', len(new_descr[new_descr['pokemon'].isna()]))
	
	return new_descr

if __name__ == '__main__':
	pokemon_data = pd.read_csv(POKEDEX, index_col='name')
	pokemons = list(pokemon_data.index).copy()
	output_df = pd.DataFrame(index=pokemon_data.index)

	# for each file in the folder newdescriptions\source
	for f in glob.glob('gif_script\\newdescriptions\\source\\*.txt'):
		a = f.split('\\')[-1].removesuffix('.txt')
		df = parse_description_file(f)
		# df.drop(columns=['pokemon'], inplace=True)
		# output_df.index = df.index
		# output_df.join(df[f.split('\\')[-1].removesuffix('.txt')])
		# output_df = output_df.merge(df[a], how='right', right_index=True, left_index=True)
		# output_df = pd.concat([output_df[output_df.index.notna()], df[df.index.notna()]], axis=1)
		output_df = pd.merge(output_df, df, left_index=True, right_index=True, how='right')
	
	output_df.to_csv('gif_script\\newdescriptions\\descriptions_english_with_pokemon.csv', index=True)
