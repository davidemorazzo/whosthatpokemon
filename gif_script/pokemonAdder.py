"""
Script to add to the main datafram new pokemon.
All gifs present in the 'WORKSPACE' will be processed and copied into the CLEAR and BLACKED gifs
"""

from glob import glob
import pandas as pd
from gifBlackConversion import convert_gif
import os
import shutil


WORKSPACE = 'gif_script\\gifWorkspace'
NEWCLEAR = 'gif_script\\gifWorkspace\\clear'
NEWBLACKED = 'gif_script\\gifWorkspace\\blacked'
TMPPATH = 'gif_script\\gifWorkspace\\'

CLEAR = '.\\gifs\\clear\\'
BLACKED = '.\\gifs\\blacked\\'
MAIN_DF = 'pokemon_data.csv'

newGifs = glob(WORKSPACE+'\\*.gif')
df = pd.DataFrame(columns=['name','pokedex_num','clear_path','blacked_path','description','tier','generation'])

for gif in newGifs:
	gifName = gif.split('\\')[2]
	print("\nGIF NAME:    ", gifName)
	description = None
	while not description:
		description = input("Enter description: ")
	
	try:
		tier = input("Enter tier: ")
	except:
		tier = 0

	try:
		gen = input("Enter generation")
	except:
		gen = ""

	newPokemon = {	"name":gifName.replace('.gif', ''),
					"pokedex_num":None,
					'clear_path':CLEAR+gifName,
					'blacked_path':BLACKED+gifName,
					'description':description,
					'tier':tier,
					'generation':gen}

	# convert gif to blacked
	print("\nConverting ...")
	try:
		convert_gif(gifName, WORKSPACE)
		print("Converted")
	except :
		print("Corrupted file: discarted")
	
	
	# add row to dataframe
	df.loc[newPokemon['name']] = newPokemon

print(df)
while True:
	try:
		res = input("insert name of gif to remove, otherwise presdd Ctrl-Z")
	except:
		break
	try:
		df.drop(res.replace(".gif", ''))
		print("Removed!\n")
	except:
		print("Gif not found\n")

# save images into the main gif folder ad add to main dataframe new info
print("Moving files...")
mainDataframe = pd.read_csv(MAIN_DF, index_col='name')
for index, row in df.iterrows():
	try:
		mainDataframe.loc[index]
		print(f"{index} already exists")
	except:
		# add new gif
		mainDataframe.loc[index] = row
		shutil.copyfile(NEWBLACKED+'\\'+index+'.gif', row['blacked_path'])
		shutil.copyfile(WORKSPACE+'\\'+index+'.gif', row['clear_path'])

mainDataframe.to_csv(MAIN_DF)