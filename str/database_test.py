import pandas as pd
import glob
import os
from colorama import init
init() # init colorama
from colorama import Fore, Style

gif_folder = 'gifs/'
pokemon_data = pd.read_csv('str/pokemon_data.csv', index_col='name')
descriptions = pd.read_csv('str/descriptions.csv', index_col='name')
VERBOSE = True
PASS = Fore.GREEN+'--- PASS ---'+Style.RESET_ALL
FAIL = Fore.RED+'--- FAIL ---'+Style.RESET_ALL

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
	print(PASS)
else:
	print(FAIL)


# Index matching
print('\n## => Index matching test:')
pokemon_data_idx = set(pokemon_data.index)
descriptions_idx = set(descriptions.index)
diff = (pokemon_data_idx - descriptions_idx) | (descriptions_idx - pokemon_data_idx)
diff = list(diff)
if len(diff) == 0:
	print(PASS)
else:
	print(FAIL)
	if VERBOSE:
		print(Fore.YELLOW+f"	MISHMATCHES: {diff}"+Style.RESET_ALL)


# Description translation missing:
print('\n## => Description translation test:')
success = True
for lang in ['de','fr','jp','ko','zh','en']:
	missing_transl = list(descriptions[descriptions[lang].isna()].index)
	if len(missing_transl) != 0:
		success = False
		if VERBOSE:
			print(Fore.YELLOW+f"	- {lang} missing translations: {missing_transl}" + Style.RESET_ALL)

if success:
	print(PASS)
else:
	print(FAIL)


# gifs path matching
print('\n## => Gifs path matching test:')
success = True
fname_clear = glob.glob(gif_folder + 'clear/*.gif')
fname_clear = [os.path.normpath(i) for i in fname_clear]
fname_blacked = glob.glob(gif_folder + 'blacked/*.gif')
fname_blacked = [os.path.normpath(i) for i in fname_blacked]
errors_clear = set([])
errors_blacked = set([])
for idx in pokemon_data.index:
	if (not pd.isna(pokemon_data.loc[idx, 'clear_path'])) and\
		 os.path.normpath(pokemon_data.loc[idx, 'clear_path']) not in fname_clear:
		success = False
		errors_clear.add(idx)
	if (not pd.isna(pokemon_data.loc[idx, 'blacked_path'])) and\
		os.path.normpath(pokemon_data.loc[idx, 'blacked_path']) not in fname_blacked:
		success = False
		errors_blacked.add(idx)

if success:
	print(PASS)
else:
	if VERBOSE:
		print(Fore.YELLOW+f"	FILES NOT FOUND:")
		print(f"		- clear: {errors_clear}")
		print('number of errors: ', len(errors_clear))
		print(f"		- blacked: {errors_blacked}")
		print('number of errors: ', len(errors_blacked))
		print(Style.RESET_ALL)
	print(FAIL)


# missing gifs 
print('\n## => Missing gifs test:')
success = True
clear_missing = []
blacked_missing = []
for idx in pokemon_data.index:
	if pd.isna(pokemon_data.loc[idx, 'clear_path']):
		clear_missing.append(idx)
		success = False
	if pd.isna(pokemon_data.loc[idx, 'blacked_path']):
		success = False
		blacked_missing.append(idx)
if success:
	print(PASS)
else:
	print(FAIL)
	if VERBOSE:
		print(Fore.YELLOW+f"	MISSING GIFS:")
		print(f"		- clear: {clear_missing}")
		print('number of errors: ', len(clear_missing))
		print(f"		- blacked: {blacked_missing}")
		print('number of errors: ', len(blacked_missing))
		print(Style.RESET_ALL)