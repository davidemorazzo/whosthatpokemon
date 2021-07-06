from discord.ext import commands
from discord import MemberCacheFlags, Intents
import os
from dotenv import load_dotenv
from whosThatPokemonCog import whosThatPokemon
from guildsAuthCog import guildsAuthCog
from database import init_database

COMMAND_PREFIX = ["Wtp!", "wtp!"]
GIF_DIRECTORY = "./gifs/blacked/"
# LOCAL_DB_STRING = 'postgresql+psycopg2://postgres:root@localhost/postgres'
HEROKU_DB_STRING = "postgresql+psycopg2://cgfixadaruqszn:cf447a5485e66ebfdedfb2932cf97f5653eb924de1e0073ef2c0795ddcbd69a6@ec2-54-155-92-75.eu-west-1.compute.amazonaws.com:5432/d30tc5veho3edc"

def noDirectMessage(ctx):
    if ctx.guild != None:
        return True
    return False

if __name__ == '__main__':
    load_dotenv()

    ## => TRY DATABASE CONNECTION
    try:
        ## => CONNECT TO LOCAL DB
        engine = init_database(HEROKU_DB_STRING)
    except:
        try:
            ## => CONNECT TO HEROKU POSTGRESQL
            HEROKU_DB_STRING = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql+psycopg2://")
            print(HEROKU_DB_STRING)
            engine = init_database(HEROKU_DB_STRING)
        except Exception as e:
            print("Could not connect to the database: ", e)
            exit()

    cache = MemberCacheFlags().none()
    cache.joined = True
    intents = Intents().default()
    intents.members = True

    bot = commands.Bot(command_prefix=COMMAND_PREFIX, member_cache_flags=cache, intents=intents)
    bot.remove_command("help")
    bot.add_cog(guildsAuthCog(bot, os.getenv("PATREON_TOKEN"), os.getenv("PATREON_CREATOR_ID"), engine))
    bot.add_cog(whosThatPokemon(bot, GIF_DIRECTORY, engine))
    bot.add_check(noDirectMessage)

    bot.run(os.getenv("DISCORD_TOKEN"))

