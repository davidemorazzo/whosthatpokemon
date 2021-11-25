from discord.ext import commands
import os
from dotenv import load_dotenv
from sqlalchemy import exc
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from cog.whosThatPokemonCog import whosThatPokemon, botGuilds
from cog.guildsAuthCog import guildsAuthCog
from database import init_database
import psycopg2
from profiling.profiler import BaseProfiler
import logging

COMMAND_PREFIX = ["Wtp!", "wtp!"]
POKEMON_DATAFRAME = "pokemon_data.csv"

def noDirectMessage(ctx):
    if ctx.guild != None:
        return True
    raise commands.errors.NoPrivateMessage

async def getServerPrefix(bot, message):
    p = BaseProfiler("getServerPrefix")
    
    if message.guild:
        ## => SERVER MESSAGE
        prefixes = COMMAND_PREFIX
        try:
            serverPrefix = bot.customGuildPrefixes[message.guild.id]
        except :
            serverPrefix = None
        
        if serverPrefix:
            prefixes = prefixes + [serverPrefix]
                
        return prefixes
        
    else:
        ## => DIRECT MESSAGE
        return COMMAND_PREFIX

if __name__ == '__main__':
    load_dotenv()

    ## => TRY DATABASE CONNECTION
    try:
        ## => INITIALIZE FOR LOCAL MACHINE
        LOCAL_DB_STRING = 'postgresql+asyncpg://postgres:root@localhost/whosthatpokemon'
        engine = init_database(LOCAL_DB_STRING)
        BOT_TOKEN = "ODU1MzkyOTMxMjAzMjUyMjM0.YMx0vw.GUK6TGjobT6Ez2KE4KrCi21RFdQ" ## => TOKEN DI DAVIDE
        print("Bot initialized for local machine")
    except:
        try:
            ## => INITIALIZE FOR HEROKU
            HEROKU_DB_STRING = os.environ.get("HEROKU_POSTGRESQL_CHARCOAL_URL").replace("postgres://", "postgresql+psycopg2://")
            #HEROKU_DB_STRING = 'postgresql+asyncpg://wdomuberrwkvzh:f3b37ae66dd1397e652ccb0bd0851d6fd6b30c0db76bc2182183cafe7dd67232@ec2-52-209-171-51.eu-west-1.compute.amazonaws.com:5432/d2ioeuuac8amki'
            engine = init_database(HEROKU_DB_STRING)
            BOT_TOKEN = os.getenv("DISCORD_TOKEN")
            print("Bot inizialied for Heroku server")
        except Exception as e:
            print("Could not connect to the database: ", e)
            exit()

    ## => SETUP LOGGING
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)  

    bot = commands.Bot(command_prefix=getServerPrefix)
    bot.remove_command("help")
    bot.add_cog(guildsAuthCog(bot, os.getenv("PATREON_TOKEN"), os.getenv("PATREON_CREATOR_ID"), engine))
    bot.add_cog(whosThatPokemon(bot, engine, POKEMON_DATAFRAME))
    bot.add_check(noDirectMessage)
    bot.customGuildPrefixes = {}

    print("Bot spooling up...")
    bot.run(BOT_TOKEN)
