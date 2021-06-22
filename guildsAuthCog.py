from discord.ext import commands
from database import patreonUsers, botGuilds
from sqlalchemy.orm import Session
from sqlalchemy import insert, update
from datetime import datetime

class guildsAuthCog(commands.Cog):
    def __init__(self, bot, patreonKey, patreonCreatorId, engine):
        self.patreonKey = patreonKey
        self.patreonCreatorId = patreonCreatorId
        self.bot = bot
        self.db_engine = engine

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        ## => ADD GUILD TO DB
        with Session(self.db_engine) as session:
            ## => TRY TO FETCH THE GUILD FROM THE DB
            newGuild = session.query(botGuilds).filter_by(guild_id=str(guild.id)).first()
            if newGuild == None:
                ## => GUILD NOT FOUNDED -> ADD TO THE DATABASE
                newGuild = botGuilds(guild_id=(guild.id),
                                    joined_utc=str(datetime.utcnow()),
                                    guessing=False,
                                    currently_joined = True,
                                    activate=True)
                session.add(newGuild)

            newGuild.currently_joined=True
            session.commit()
        print("GUILD ADDED TO THE DB: ", guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        ## => UPDATE GUILD INFO TO NOT JOINED
        with Session(self.db_engine) as session:
            newGuild = session.query(botGuilds).filter_by(guild_id=str(guild.id)).first()
            newGuild.currently_joined= False
            session.commit()
            
        print("BOT LEFT GUILD: ", guild.name)