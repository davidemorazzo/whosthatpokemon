import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from database import botChannelIstance

class string_translator():
	def __init__(self, string_db:str, sessionmaker:sessionmaker) -> str:
		self.df = pd.read_csv(string_db, index_col='name')
		self.a_session = sessionmaker

	def s_get(self, id:str, lang_id:str):
		"""
		Get a single string given the language id
		"""
		return str(self.df.loc[id, lang_id])
	
	async def get (self, id:str, channel_id:str):
		"""
		Get a single string given the id
		"""
		async with self.a_session() as session:
			stmt = select(botChannelIstance).where(botChannelIstance.channel_id == str(channel_id))
			result = await session.execute(stmt)
			guild_info = result.scalars().first()
			if guild_info:
				language = guild_info.language
		
		return str(self.df.loc[id, language])
	
	async def get_batch(self, ids:list, channel_id:str) -> tuple:
		"""
		Get a list of strings given a list of ids
		"""
		async with self.a_session() as session:
			stmt = select(botChannelIstance).where(botChannelIstance.channel_id == str(channel_id))
			result = await session.execute(stmt)
			guild_info = result.scalars().first()
			if guild_info:
				language = guild_info.language
		
		strings = [self.df.loc[i, language] for i in ids]
		return tuple(strings)
