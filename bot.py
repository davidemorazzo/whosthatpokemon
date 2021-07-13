from discord.ext import commands
from discord import MemberCacheFlags, Intents
import os
from dotenv import load_dotenv
from whosThatPokemonCog import whosThatPokemon
from guildsAuthCog import guildsAuthCog
from database import init_database
import psycopg2

COMMAND_PREFIX = ["Wtp!", "wtp!"]
GIF_DIRECTORY = "./gifs/blacked/"

def noDirectMessage(ctx):
    if ctx.guild != None:
        return True
    return False

def getServerPrefix(bot, message):
    if message.guild:
        ## => SERVER MESSAGE
        base = COMMAND_PREFIX
        connection = psycopg2.connect(HEROKU_DB_STRING)
        cursor = connection.cursor()
        cursor.execute(f"select prefix from bot_guilds where guild_id = '{message.guild.id}'"
                        )
        serverPrefix = cursor.fetchone()
        cursor.close()
        connection.close()
        if serverPrefix[0]:
            base.append(serverPrefix[0])
        return base
        
    else:
        ## => DIRECT MESSAGE
        return COMMAND_PREFIX

if __name__ == '__main__':
    load_dotenv()

    ## => TRY DATABASE CONNECTION
    try:
        ## => INITIALIZE FOR LOCAL MACHINE
        LOCAL_DB_STRING = 'postgresql+psycopg2://postgres:root@localhost/postgres'
        engine = init_database(LOCAL_DB_STRING)
        BOT_TOKEN = "ODU1MzkyOTMxMjAzMjUyMjM0.YMx0vw.GUK6TGjobT6Ez2KE4KrCi21RFdQ" ## => TOKEN DI DAVIDE
        print("Bot initialized for local machine")
    except:
        try:
            ## => INITIALIZE FOR HEROKU
            HEROKU_DB_STRING = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql+psycopg2://")
            print(HEROKU_DB_STRING)
            engine = init_database(HEROKU_DB_STRING)
            BOT_TOKEN = os.getenv("DISCORD_TOKEN")
            print("Bot inizialied for Heroku server")
        except Exception as e:
            print("Could not connect to the database: ", e)
            exit()

    cache = MemberCacheFlags().none()
    cache.joined = True
    intents = Intents().default()
    intents.members = True

    bot = commands.Bot(command_prefix=getServerPrefix, member_cache_flags=cache, intents=intents)
    bot.remove_command("help")
    bot.add_cog(guildsAuthCog(bot, os.getenv("PATREON_TOKEN"), os.getenv("PATREON_CREATOR_ID"), engine))
    bot.add_cog(whosThatPokemon(bot, GIF_DIRECTORY, engine))
    bot.add_check(noDirectMessage)

    bot.run(BOT_TOKEN)
    # bot.run("ODU1MzkyOTMxMjAzMjUyMjM0.YMx0vw.GUK6TGjobT6Ez2KE4KrCi21RFdQ") ## => TOKEN DI DAVIDE

