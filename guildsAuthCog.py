from discord.ext import commands, tasks
from database import patreonUsers, botGuilds
from sqlalchemy.orm import Session
from sqlalchemy import insert, update
from datetime import datetime, timedelta
from dateutil import parser
from discord import Embed, Colour
from patreonAPI import fetch_patreons

import os

class guildsAuthCog(commands.Cog):
    def __init__(self, bot, patreonKey, patreonCreatorId, engine):
        self.patreonKey = patreonKey
        self.patreonCreatorId = patreonCreatorId
        self.bot = bot
        self.db_engine = engine
        self.trial_days = int(os.getenv("DAYS_OF_TRIAL"))
        self.color = Colour.orange()
        self.verification.start()
        self.patreon_link = "https://www.patreon.com/whosthatpokemon"
        self.patreonInstructions = "\n**IMPORTANT: ** The patreon subscription have to be made by a server administrator, otherwise the bot will not activate. Remember to connect from patreon to your discord accout!"
        self.guildWhiteList = []

    async def verifyPatreon(self, guildObj: botGuilds, patreonIds:list) -> str:
        ## => ASSIGN TO THE GUILD THE CORRECT PATREON
        discordGuild = self.bot.get_guild(int(guildObj.guild_id))
        
        if guildObj.patreon_discord_id in patreonIds:
            return guildObj.patreon_discord_id ## => KEEP THE CURRENT PATREON
        else:
            for patreonId in patreonIds:
                try:
                    user = discordGuild.get_member(int(patreonId))
                except : user = None

                if user and user.guild_permissions.administrator:
                    return patreonId
            return None ## => NO PATREON FOUNDED

    def updatePatreons(self):
        ## => FETCH PATREONS FROM API
        patreons_dict = fetch_patreons(os.getenv("PATREON_TOKEN"))
        ## => KEEP IN THE DB ONLY THE ACTIVE PATRONS
        with Session(self.db_engine) as session:
            patreonsDb = session.query(patreonUsers).all()
            ## => CHECK PATREONS IN THE DATABASE
            for patreon in patreonsDb:
                if not patreon.discord_id in patreons_dict.keys():
                    ## => USER IS NOT A PATREON ANYMORE
                    session.delete(patreon)
                else:
                    patreons_dict.pop(patreon.discord_id)
            
            ## => ADD NEW PATREONS
            for newPatreonId in patreons_dict.keys():
                patreonObj = patreonUsers(discord_id = newPatreonId,
                                            tier = patreons_dict[newPatreonId][1],
                                            sub_status = patreons_dict[newPatreonId][0],
                                            guild_id = None)
                session.add(patreonObj)

            session.commit()
            print("Patreon db commit")



    def embedText(self, text):
        text = text.replace('"', '\"').replace("'", "\'")
        return Embed(description=f"**{text}**", color=self.color)

    @commands.Cog.listener() #TODO: provare se funziona quando bot è spento
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

    @tasks.loop(minutes=10)
    async def verification(self):
        
        print("Start verification")
        ## => UPDATE PATREONS INTO THE DB
        self.updatePatreons()
        await self.bot.wait_until_ready()
        ## => VERIFY EVERY GUILD
        with Session(self.db_engine) as session:
            patreons = session.query(patreonUsers).all()
            patreonIds = [p.discord_id for p in patreons]
            guilds = session.query(botGuilds).filter_by(currently_joined=True).all()
            for guild in guilds:
                patreonId = await self.verifyPatreon(guild, patreonIds)

                if int(guild.guild_id) in self.guildWhiteList:
                    ## => WHITELISTED GUILD DOES NOT NEED VERIFICATION
                    guild.activate = True
                    guild.patreon_discord_id = None

                elif not patreonId:
                    ## => CHECK FOR TRIAL PERIOD
                    now = datetime.utcnow()
                    joined = parser.parse(guild.joined_utc)
                    guild.patreon_discord_id = None
                    if now-joined > timedelta(days=self.trial_days):
                        guild.activate = False
                        guild.patreon_discord_id = None
                    else:
                        guild.activate = True
                        guild.patreon_discord_id = None
                else:
                    ## => ACTIVATE THE GUILD WITH PATREON
                    guild.activate = True
                    guild.patreon_discord_id = str(patreonId)
        
            session.commit()
            print("Guilds verification db commit")

    @commands.command(name = "help", help="Show this message")
    async def help(self, ctx):
        ## => GUILD INFO FROM DB
        with Session(self.db_engine, expire_on_commit=False) as session:
            guildInfo = session.query(botGuilds).filter_by(guild_id=str(ctx.guild.id)).first()
        join_date = parser.parse(guildInfo.joined_utc)
        days_left = self.trial_days - (datetime.utcnow()-join_date).days
        trial_flag = days_left >= 0 and guildInfo.patreon_discord_id ==None

        embed = Embed(title="Commands help", colour=self.color)
        command_names_list = [(x.name, x.signature, x.help) for x in self.bot.commands]
        
        # If there are no arguments, just list the commands:
        for i,x in enumerate(self.bot.commands):
            embed.add_field(
                name=x.name+' '+x.signature ,
                value=x.help,
                inline=False
            )

        if ctx.guild.id in self.guildWhiteList:
            embed.set_footer(text="ACTIVATION:  This guild is whitelisted, so activation is not needed.")
        elif trial_flag:
            embed.description = f"**ACTIVATION:**  {days_left} days left before trial period will end. To keep using the bot please subscribe to our patreon! [Patreon link]({self.patreon_link})"+self.patreonInstructions+"\n"
        elif guildInfo.activate == False:
            embed.descriprion = f"**ACTIVATION:**  the bot is not activated. To activate the bot please subscribe to our patreon! [Patreon link]({self.patreon_link})"+self.patreonInstructions
        elif guildInfo.patreon_discord_id != None:
            embed.set_footer(text="ACTIVATION:  the bot is activated with patreon subscription")

        bot_msg = await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            embed = self.embedText(f"Trial period has expired! To gain full access to the bot please activate the bot using this link {self.patreon_link}")
            await ctx.send(embed = embed)
            print("GUILD WITHOUT PERMISSION DENIED: ", ctx.guild.name)
        else:
            print(error)

