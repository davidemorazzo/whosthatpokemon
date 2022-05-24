from datetime import datetime, timedelta
import pandas as pd


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
    pokemon_idxs = pokedex_df.loc[pokedex_df.pokedex_num.notna()] # get all the pokemons with pokedex number
    max_index = pokemon_idxs.pokedex_num.max()
    for i,poke in enumerate(pokemon_owned):
        name = pokedex_df.loc[poke, lang_id]     
        new_row = f"{i+1}. ** {name.title()} **"
        rows.append(new_row)

    # Pagination
    row_per_page = 30
    pgs = []
    for i in range(len(rows) // row_per_page + 1):
        temp = []
        for j in range(row_per_page):
            if row_per_page*i+j >= len(rows) - 1:
                break
            temp.append(rows[row_per_page*i+j])
        pgs.append(temp)

    return pgs





