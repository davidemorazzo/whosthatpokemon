import glob
import os
import pandas as pd

pokemon_data = pd.read_csv('pokemon_data.csv', index_col='name')
files_clear = glob.glob('gif_script\\gifWorkspace\\*.gif')
fname_clear = [set(os.path.basename(x).removesuffix('.gif').split('-')) for x in files_clear]
files_black = glob.glob('gif_script\\gifWorkspace\\blacked\\*.gif')
fname_black = [set(os.path.basename(x).removesuffix('.gif').split('-')) for x in files_black]

for idx in pokemon_data.loc[pokemon_data['clear_path'].isna()].index:
	if  set(idx.lower().split('-')) in fname_clear and \
		set(idx.lower().split('-')) in fname_black:

		pokemon_data.loc[idx, 'clear_path'] = './gifs/clear/' + idx + '.gif'
		pokemon_data.loc[idx, 'blacked_path'] = './gifs/blacked/' + idx + '.gif'
	
	else:
		print(idx + ' not found')

pokemon_data.to_csv('pokemon_data1.csv')