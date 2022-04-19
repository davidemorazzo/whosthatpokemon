import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from database import botGuilds

class string_translator():
	def __init__(self, string_db:str, sessionmaker:sessionmaker) -> str:
		self.df = pd.read_csv(string_db, index_col='name')
		self.a_session = sessionmaker
	
	async def get (self, id:str, guild_id:str):
		"""
		Get a single string given the id
		"""
		async with self.a_session() as session:
			stmt = select(botGuilds).where(botGuilds.guild_id == str(guild_id))
			result = await session.execute(stmt)
			guild_info = result.scalars().first()
			if guild_info:
				language = guild_info.language
		
		return self.df.loc[id, language]
	
	async def get_batch(self, ids:list, guild_id:str) -> tuple:
		"""
		Get a list of strings given a list of ids
		"""
		async with self.a_session() as session:
			stmt = select(botGuilds).where(botGuilds.guild_id == str(guild_id))
			result = await session.execute(stmt)
			guild_info = result.scalars().first()
			if guild_info:
				language = guild_info.language
		
		strings = [self.df.loc[i, language] for i in ids]
		return tuple(strings)
