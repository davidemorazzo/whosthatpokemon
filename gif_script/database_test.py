import pandas as pd
import glob
import os

gif_folder = 'gifs/'
pokemon_data = pd.read_csv('pokemon_data1.csv', index_col='name')
descriptions = pd.read_csv('descriptions.csv', index_col='name')
VERBOSE = True

# Name translation missing
print("## => Name translation test:")
success = True
for lang in ['de','fr','jp','ko','zh','en']:
	missing_transl = list(pokemon_data[pokemon_data[lang].isna()].index)
	if len(missing_transl) != 0:
		success = False

	if VERBOSE:
		print(f"	- {lang} missing translations: ",missing_transl)

if success:
	print('--- PASS ---')
else:
	print('--- FAIL ---')


# Index matching
print('\n## => Index matching test:')
pokemon_data_idx = set(pokemon_data.index)
descriptions_idx = set(descriptions.index)
diff = (pokemon_data_idx - descriptions_idx) | (descriptions_idx - pokemon_data_idx)
diff = list(diff)
if len(diff) == 0:
	print('--- PASS ---')
else:
	print('--- FAIL ---')
	if VERBOSE:
		print(f"	MISHMATCHES: {diff}") 


# Description translation missing:
print('\n## => Description translation test:')
success = True
for lang in ['de','fr','jp','ko','zh','en']:
	missing_transl = list(descriptions[descriptions[lang].isna()].index)
	if len(missing_transl) != 0:
		success = False
		if VERBOSE:
			print(f"	- {lang} missing translations: ",missing_transl)

if success:
	print('--- PASS ---')
else:
	print('--- FAIL ---')


# gifs path matching
print('\n## => Gifs path matching test:')
success = True
fname_clear = glob.glob(gif_folder + 'clear/*.gif')
fname_clear = [os.path.normpath(i) for i in fname_clear]
fname_blacked = glob.glob(gif_folder + 'blacked/*.gif')
fname_blacked = [os.path.normpath(i) for i in fname_blacked]
errors = set([])
for idx in pokemon_data.index:
	if (not pd.isna(pokemon_data.loc[idx, 'clear_path'])) and\
		 os.path.normpath(pokemon_data.loc[idx, 'clear_path']) not in fname_clear:
		success = False
		errors.add(idx)
	if (not pd.isna(pokemon_data.loc[idx, 'blacked_path'])) and\
		os.path.normpath(pokemon_data.loc[idx, 'blacked_path']) not in fname_blacked:
		success = False
		errors.add(idx)

if success:
	print('--- PASS ---')
else:
	if VERBOSE:
		print(f"	FILES NOT FOUND: {list(errors)}")
		print('number of errors: ', len(errors))
	print('--- FAIL ---')