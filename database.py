from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
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
    activate = Column(Boolean, nullable=False)
    joined_utc = Column(String, nullable=False)
    currently_joined = Column(Boolean, nullable=False)
    patreon_discord_id = Column(String, unique=True, nullable=True)
    prefix = Column(String)

    def __repr__(self):
        return "<Guild(guild_id=%s, activated=%s, join=%s, patreon_user_id=%s)>" % (
            self.guild_id, self.activate, self.joined_utc, self.patreon_discord_id)

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
    UniqueConstraint(guild_id, channel_id)



def init_database(url:String):

    engine = create_engine(url.replace("asyncpg", "psycopg2"), echo=False)
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    async_engine = create_async_engine(url, echo=False)
    
    return async_engine