import re
import pandas as pd


df = pd.read_csv("pokemon_data3.csv", index_col="pokedex_num")
pokedex_df = pd.read_csv("pokedex1.txt", index_col='pindex')
for idx, r in pokedex_df.iterrows():
	try:
		# n = int(re.search(r'\d+', df.loc[idx]['description']).group())
		df.loc[int(idx)]
	except :
		try:
			row = pd.Series({'name':r[1], 'clear_index':None, 'blacked_index':None, 'tier':None, 'description':None}, name=int(idx))
			df.loc[int(idx)] = row
		except :
			pass
pass
