from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import insert

Base = declarative_base()

class patreonUsers(Base):
    __tablename__ = "patreon_users"

    discord_id = Column(Integer, primary_key=True, nullable=False)
    tier = Column(Integer, nullable=False)
    sub_status = Column(String, nullable=False)
    guild_id = Column(Integer)

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
    guessing  = Column(Boolean, nullable=False)
    current_pokemon = Column(String)
    is_guessed = Column(Boolean)

    def __repr__(self):
        return "<Guild(guild_id=%s, activated=%s, join=%s, patreon_user_id=%s)>" % (
            self.guild_id, self.activate, self.joined_utc, self.patreon_discord_id)

class userPoints(Base):
    __tablename__ = "user_points"
    user_id = Column(String, primary_key=True, nullable=False)
    guild_id = Column(String, primary_key=True, nullable=False)
    points = Column(Integer, nullable=False)


def init_database(url:String):

    engine = create_engine(url, echo=False)
    Base.metadata.create_all(bind=engine)
    return engine

if __name__ == '__main__':
    session = Session(create_engine('postgresql+psycopg2://postgres:root@localhost/postgres'))
    q = insert(botGuilds).values(guild_id = "822033257142288414", activate=True, joined_utc = str(datetime.utcnow()),
                                    patreon_discord_id = '1010',
                                    guessing=False,
                                    currently_joined = True)
    session.execute(q)
    session.commit()  