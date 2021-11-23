from discord.ext import commands
import os
from dotenv import load_dotenv
from whosThatPokemonCog import whosThatPokemon
from guildsAuthCog import guildsAuthCog
from database import init_database
import psycopg2

COMMAND_PREFIX = ["Wtp!", "wtp!"]
POKEMON_DATAFRAME = "pokemon_data5.csv"

def noDirectMessage(ctx):
    if ctx.guild != None:
        return True
    raise commands.errors.NoPrivateMessage

def getServerPrefix(bot, message):
    if message.guild:
        ## => SERVER MESSAGE
        base = COMMAND_PREFIX
        prefixes = base
        try:
            connection = psycopg2.connect(HEROKU_DB_STRING.replace("+psycopg2", ""), sslmode='require')
        except :
            connection = psycopg2.connect("postgresql://postgres:root@localhost/whosthatpokemon")
        cursor = connection.cursor()
        cursor.execute(f"select prefix from bot_guilds where guild_id = '{message.guild.id}'"
                        )
        serverPrefix = cursor.fetchone()
        cursor.close()
        connection.close()
        if serverPrefix:
            if serverPrefix[0]:
                prefixes = base + [serverPrefix[0]]
                
        return prefixes
        
    else:
        ## => DIRECT MESSAGE
        return COMMAND_PREFIX

if __name__ == '__main__':
    load_dotenv()

    ## => TRY DATABASE CONNECTION
    try:
        ## => INITIALIZE FOR LOCAL MACHINE
        LOCAL_DB_STRING = 'postgresql+psycopg2://postgres:root@localhost/whosthatpokemon'
        engine = init_database(LOCAL_DB_STRING)
        BOT_TOKEN = "ODU1MzkyOTMxMjAzMjUyMjM0.YMx0vw.GUK6TGjobT6Ez2KE4KrCi21RFdQ" ## => TOKEN DI DAVIDE
        print("Bot initialized for local machine")
    except:
        try:
            ## => INITIALIZE FOR HEROKU
            HEROKU_DB_STRING = os.environ.get("HEROKU_POSTGRESQL_CHARCOAL_URL").replace("postgres://", "postgresql+psycopg2://")
            print(HEROKU_DB_STRING)
            engine = init_database(HEROKU_DB_STRING)
            BOT_TOKEN = os.getenv("DISCORD_TOKEN")
            print("Bot inizialied for Heroku server")
        except Exception as e:
            print("Could not connect to the database: ", e)
            exit()

    # cache = MemberCacheFlags().none()
    # cache.joined = True
    # intents = Intents().default()
    # intents.members = True

    bot = commands.Bot(command_prefix=getServerPrefix)
    bot.remove_command("help")
    bot.add_cog(guildsAuthCog(bot, os.getenv("PATREON_TOKEN"), os.getenv("PATREON_CREATOR_ID"), engine))
    bot.add_cog(whosThatPokemon(bot, engine, POKEMON_DATAFRAME))
    bot.add_check(noDirectMessage)

    bot.run(BOT_TOKEN)
