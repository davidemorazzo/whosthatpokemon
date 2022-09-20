from datetime import datetime, timedelta
from numpy import ScalarType
import pandas as pd
from io import BytesIO

from database import patreonUsers, pokemonData
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker


class cooldown:
    def __init__(self):
        self.on_cooldown = {}
    
    def _create_token_(self, id, cmd_name):
        return f"{id}/{cmd_name}"
    
    def add_cooldown(self, id, cmd_name):
        """ Add a <guild_id/<cmd_name> token to the dict """
        self.on_cooldown[self._create_token_(id, cmd_name)] = datetime.utcnow()

    def is_on_cooldown(self, id, cmd_name, cooldownSeconds) -> bool:
        """check if a token is still on cooldown"""
        
        currentTime = datetime.utcnow()
        token=self._create_token_(id, cmd_name)
        
        # Check all cooldown dict
        for key in list(self.on_cooldown.keys()):
            if self.on_cooldown[key] + timedelta(seconds=cooldownSeconds) < currentTime:
                # cooldown expired
                del self.on_cooldown[key]
        
        if token in self.on_cooldown.keys():
            if self.on_cooldown[token] + timedelta(seconds=cooldownSeconds) > currentTime:
                # command still on cooldown
                retry_after = (currentTime-self.on_cooldown[token]).seconds
                return True
            else:
                return False
        else:
            return False


def create_shiny_paginator(pokemon_owned:list, lang_id:str, pokedex_df:pd.DataFrame) -> list:
    """
    Return a list of the pages that can be used to create the Paginator
    """
    rows = []
    for i,poke in enumerate(pokemon_owned):
        name = pokedex_df.loc[poke, lang_id]     
        new_row = f"{i+1}. ** {name.title()} **"
        rows.append(new_row)

    # Pagination
    row_per_page = 5
    pgs = []
    for i in range(len(rows) // row_per_page + 1):
        temp = []
        for j in range(row_per_page):
            if row_per_page*i+j >= len(rows):
                break
            temp.append(rows[row_per_page*i+j])
        pgs.append(temp)

    return pgs

async def get_clear_gif(pokemon_id:str, smkr:sessionmaker) -> BytesIO:
    async with smkr() as session:
        stmt = select(pokemonData.clear_img).where(pokemonData.id == pokemon_id)
        result = await session.execute(stmt)
        file_bin = result.scalars().first()
        return BytesIO(file_bin)

async def get_blacked_gif(pokemon_id:str, smkr:sessionmaker) -> BytesIO:
    async with smkr() as session:
        stmt = select(pokemonData.blacked_img).where(pokemonData.id == pokemon_id)
        result = await session.execute(stmt)
        file_bin = result.scalars().first()
        return BytesIO(file_bin)

async def get_shiny_gif(pokemon_id:str, smkr:sessionmaker) -> BytesIO:
    async with smkr() as session:
        stmt = select(pokemonData.shiny_img).where(pokemonData.id == pokemon_id)
        result = await session.execute(stmt)
        file_bin = result.scalars().first()
        return BytesIO(file_bin)


async def is_user_patreon(user_id:int, smkr:sessionmaker) -> bool:
    """
    Check in the database if the user is pateron
    """
    async with smkr() as session:
        stmt = select(patreonUsers
            ).where(patreonUsers.id == str(user_id)
            ).where(patreonUsers.sub_status == None)
        result = await session.execute(stmt)
        patreon = result.scalars().first()
        return bool(patreon)
        
