from database import pokemonData, init_database
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import numpy as np
import asyncio

async def main():
	pokemon_data = pd.read_csv('str/pokemon_data.csv')
	pokemon_data['pokedex_num'] = pokemon_data['pokedex_num'].fillna(0)
	pokemon_data['tier'] = pokemon_data['tier'].fillna(0)
	pokemon_data['generation'] = pokemon_data['generation'].fillna('')
	rows = []
	for idx in pokemon_data.index:
		## => Create binary obj from image
		clear_path = pokemon_data.loc[idx, 'clear_path']
		try:
			with open(clear_path, "rb") as image:
				f = image.read()
				b_clear = bytearray(f)
		except:
			b_clear = None

		blacked_path = pokemon_data.loc[idx, 'blacked_path']
		try:
			with open(blacked_path, "rb") as image:
				f = image.read()
				b_blacked = bytearray(f)
		except:
			b_blacked = None

		shiny_path = pokemon_data.loc[idx, 'shiny_path']
		try:
			with open(shiny_path, "rb") as image:
				f = image.read()
				b_shiny = bytearray(f)
		except:
			b_shiny = None

		## => Insert into database
		obj = pokemonData(
			id = pokemon_data.loc[idx, 'name'],
			pokedex_num = pokemon_data.loc[idx, 'pokedex_num'],
			patreon_tier = pokemon_data.loc[idx, 'tier'],
			generation = pokemon_data.loc[idx, 'generation'],
			de = pokemon_data.loc[idx, 'de'],
			fr = pokemon_data.loc[idx, 'fr'],
			jp = pokemon_data.loc[idx, 'jp'],
			ko = pokemon_data.loc[idx, 'ko'],
			zh = pokemon_data.loc[idx, 'zh'],
			en = pokemon_data.loc[idx, 'en'],
			es = pokemon_data.loc[idx, 'es'],
			it = pokemon_data.loc[idx, 'it'],
			hi = pokemon_data.loc[idx, 'hi'],
			clear_img = b_clear,
			blacked_img = b_blacked, 
			shiny_img = b_shiny
		)
		rows.append(obj)
	
	## => Database connection
	smkr = sessionmaker(init_database('postgresql+asyncpg://wdomuberrwkvzh:f3b37ae66dd1397e652ccb0bd0851d6fd6b30c0db76bc2182183cafe7dd67232@ec2-52-209-171-51.eu-west-1.compute.amazonaws.com:5432/d2ioeuuac8amki'),
				expire_on_commit=False,
				class_=AsyncSession
				)

	async with smkr() as session:
		for r in rows:
			session.add(r)
		await session.commit()


if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
