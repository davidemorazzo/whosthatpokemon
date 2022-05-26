from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import Column, Integer, String, Boolean, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from datetime import datetime
from sqlalchemy import insert
from sqlalchemy.sql.schema import UniqueConstraint

Base = declarative_base()

class patreonUsers(Base):
    __tablename__ = "patreon_users"

    discord_id = Column(String, primary_key=True, nullable=False)
    tier = Column(String, nullable=False)
    sub_status = Column(String, nullable=False)
    guild_id = Column(String)

    def __repr__(self):
        return "<User(discord_id=%d, tier=%d, guild_id=%d, status=%d)>" % (
            self.discord_id, self.tier, self.guild_id, self.sub_status)

class botGuilds(Base):
    __tablename__ = "bot_guilds"
    guild_id = Column(String, primary_key=True, nullable=False)
    patreon = Column(Boolean, nullable=False)
    joined_utc = Column(String, nullable=False)
    currently_joined = Column(Boolean, nullable=False)
    patreon_discord_id = Column(String, unique=True, nullable=True)
    prefix = Column(String)
    poke_generation = Column(String, default='123456mgj')
    language = Column(String, default='en')

    def __repr__(self):
        return "<Guild(guild_id=%s, activated=%s, join=%s, patreon_user_id=%s)>" % (
            self.guild_id, self.patreon, self.joined_utc, self.patreon_discord_id)

class userPoints(Base):
    __tablename__ = "user_points"
    user_id = Column(String, primary_key=True, nullable=False)
    username = Column(String)
    guild_id = Column(String, primary_key=True, nullable=False)
    points = Column(Integer, nullable=False) # global points
    points_from_reset = Column(Integer, nullable=False)
    last_win_date = Column(String)
    

class botChannelIstance(Base):
    __tablename__ = "bot_channel_istance"
    istance_id = Column(Integer, primary_key=True, nullable=True)
    guild_id = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    guessing  = Column(Boolean, nullable=False)
    current_pokemon = Column(String)
    is_guessed = Column(Boolean)
    last_win_date = Column(String)
    language = Column(String, default='en')
    UniqueConstraint(guild_id, channel_id)

class shinyWin(Base):
    __tablename__ = "shiny_win"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(String, nullable=False)
    channel_id = Column(String, primary_key=True, nullable=False)
    user_id = Column(String, nullable=False)
    pokemon_id = Column(String, nullable=False)
    time = Column(String, nullable=False)

class pokemonData(Base):
    __tablename__ = "pokemon_data"
    id = Column(String, primary_key=True, nullable=False)
    pokedex_num = Column(Integer, nullable=True)
    clear_img = Column(LargeBinary)
    blacked_img = Column(LargeBinary)
    shiny_img = Column(LargeBinary)
    patreon_tier = Column(Integer)
    generation = Column(String)
    de = Column(String)
    fr = Column(String)
    jp = Column(String)
    ko = Column(String)
    zh = Column(String)
    en = Column(String)
    es = Column(String)
    it = Column(String)
    hi = Column(String)

    def __repr__(self):
        return "<Pokemon(id=%d, pokedex_num=%d, patreon_tier=%d, generation=%s)>" % (
            self.id, self.pokedex_num, self.patreon_tier, self.generation)
    


def init_database(url:String):

    engine = create_engine(url.replace("asyncpg", "psycopg2"), echo=False)
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    async_engine = create_async_engine(url, echo=False)
    
    return async_engine


async def GetChannelIstance(session, guild_id, ch_id) -> botChannelIstance:
    result = await session.execute(select(botChannelIstance).filter_by(guild_id=str(guild_id),
                                                                    channel_id=str(ch_id)))
    thisGuild = result.scalars().first()  
    return thisGuild   

async def GetGuildInfo(session, guild_id):
    guildInfo = await session.execute(select(botGuilds).filter_by(guild_id=str(guild_id)))
    guildInfo = guildInfo.scalars().first()
    return guildInfo

