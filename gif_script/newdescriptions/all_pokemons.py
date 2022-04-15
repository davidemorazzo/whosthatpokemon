import pandas as pd
import re

POKEDEX = 'pokemon_data.csv'
translation = 'gif_script\\newdescriptions\\pokemon_names.csv'
all_names = 'gif_script\\newdescriptions\\all_pokemons.csv'
new_database = 'gif_script\\newdescriptions\\new_database.csv'

pokemon_data = pd.read_csv(POKEDEX)
translation_data = pd.read_csv(translation)
all_names_data = pd.read_csv(all_names)
new_database_data = pd.read_csv(new_database, index_col=False)

new_database_data.loc[new_database_data['en'].isna(), 'en'] = new_database_data['name'].str.replace('-', ' ')
new_database_data.loc[new_database_data['de'].isna(), 'de'] = new_database_data['en']
new_database_data.loc[new_database_data['fr'].isna(), 'fr'] = new_database_data['en']
new_database_data.loc[new_database_data['jp'].isna(), 'jp'] = new_database_data['en']
new_database_data.loc[new_database_data['ko'].isna(), 'ko'] = new_database_data['en']
new_database_data.loc[new_database_data['zh'].isna(), 'zh'] = new_database_data['en']
new_database_data.to_csv('gif_script\\newdescriptions\\new_database1.csv', index=False)