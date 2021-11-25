from discord.ext import commands, tasks
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from dateutil import parser
from discord import Embed, Colour
import os
from discord_components import DiscordComponents
from cog.whosThatPokemonCog import(
    guildNotActive, 
    BaseProfiler,
    botGuilds,
    patreonUsers,
    GetGuildInfo)
from patreonAPI import fetch_patreons

class guildsAuthCog(commands.Cog):
    def __init__(self, bot, patreonKey, patreonCreatorId, engine):
        self.patreonKey = patreonKey
        self.patreonCreatorId = patreonCreatorId
        self.bot = bot
        self.db_engine = engine
        self.async_session = sessionmaker(self.db_engine, expire_on_commit=False, class_=AsyncSession)
        self.trial_days = int(os.getenv("DAYS_OF_TRIAL"))
        self.color = Colour.red()
        # self.verification.start()
        self.free_period = True
        self.patreon_link = "https://www.patreon.com/whosthatpokemon"
        self.patreonInstructions = "\n**IMPORTANT: ** The patreon subscription have to be made by the owner of the server, otherwise the bot will not activate. Remember to connect from patreon to your discord account!"
        self.guildWhiteList = [752464482424586290, 822033257142288414]
        self.DiscordComponentsInit = False
        # test commmit master

    async def verifyPatreon(self, guildObj: botGuilds, patreonIds:list) -> str:
        """Return the discord id of the patreon if there is a match, None otherwise"""

        ## => ASSIGN TO THE GUILD THE CORRECT PATREON
        discordGuild = self.bot.get_guild(int(guildObj.guild_id))
        
        if guildObj.patreon_discord_id in patreonIds:
            return guildObj.patreon_discord_id ## => KEEP THE CURRENT PATREON
        else:
            for patreonId in patreonIds:
                # FIXME: controllare
                user = discordGuild.owner
                if user.guild_permissions.administrator:
                    return patreonId
            return None ## => NO PATREON FOUNDED

    async def updatePatreons(self):
        ## => FETCH PATREONS FROM API
        patreons_dict = fetch_patreons(os.getenv("PATREON_TOKEN"))
        ## => KEEP IN THE DB ONLY THE ACTIVE PATRONS
        async with self.async_session() as session:
            patreonsDb = await session.execute(select(patreonUsers))
            patreonsDb = patreonsDb.scalars().all()
            ## => CHECK PATREONS IN THE DATABASE
            for patreon in patreonsDb:
                if not patreon.discord_id in patreons_dict.keys():
                    ## => USER IS NOT A PATREON ANYMORE
                    await session.delete(patreon)
                else:
                    patreons_dict.pop(patreon.discord_id)
            
            ## => ADD NEW PATREONS
            for newPatreonId in patreons_dict.keys():
                patreonObj = patreonUsers(discord_id = newPatreonId,
                                            tier = patreons_dict[newPatreonId]['tier'],
                                            sub_status = patreons_dict[newPatreonId]['declined_since'],
                                            guild_id = None)
                session.add(patreonObj)

            await session.commit()



    def embedText(self, text):
        text = text.replace('"', '\"').replace("'", "\'")
        return Embed(description=f"**{text}**", color=self.color)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        p = BaseProfiler("on_guild_join")
        ## => ADD GUILD TO DB
        async with self.async_session() as session:
            ## => TRY TO FETCH THE GUILD FROM THE DB
            newGuild = await GetGuildInfo(session, guild.id)
            if newGuild == None:
                ## => GUILD NOT FOUNDED -> ADD TO THE DATABASE
                newGuild = botGuilds(guild_id=str(guild.id),
                                    joined_utc=str(datetime.utcnow()),
                                    currently_joined = True,
                                    activate=True)
                session.add(newGuild)

            newGuild.currently_joined=True
            await session.commit()
        print("GUILD ADDED TO THE DB: ", guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        p = BaseProfiler("on_guild_remove")
        ## => UPDATE GUILD INFO TO NOT JOINED
        async with self.async_session() as session:
            newGuild = await GetGuildInfo(session, guild.id)
            if newGuild:
                newGuild.currently_joined= False
                await session.commit()
                print("BOT LEFT GUILD: ", guild.name)

    @tasks.loop(minutes=10)
    async def verification(self):
        
        tic = datetime.now()
        ## => UPDATE PATREONS INTO THE DB
        await self.updatePatreons()
        await self.bot.wait_until_ready()
        ## => VERIFY EVERY GUILD
        async with self.async_session() as session:
            patreons = await session.execute(select(patreonUsers))
            patreons = patreons.scalars().all()
            patreonIds = [p.discord_id for p in patreons if not p.sub_status]
            guilds = await session.execute(select(botGuilds).filter_by(currently_joined=True))
            guilds = guilds.scalars().all()
            for guild in guilds:

                if int(guild.guild_id) in self.guildWhiteList:
                    ## => WHITELISTED GUILD DOES NOT NEED VERIFICATION
                    guild.activate = True
                    guild.patreon_discord_id = None

                elif self.free_period:
                    ## => DISABLE PATREON IN THE FREE PERIOD
                    guild.activate=True

                else:
                    ## => CHECK FOR PATREON SUBSCRIPTION
                    patreonId = await self.verifyPatreon(guild, patreonIds)
                    
                    if patreonId:
                        ## => ACTIVATE THE GUILD WITH PATREON
                        guild.activate = True
                        guild.patreon_discord_id = str(patreonId)

                    else:
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
        
            await session.commit()

        toc = datetime.now()
        delta = toc-tic
        print("Verification executed in: ", delta)

    @commands.command(name = "help", help="Show this message")
    async def help(self, ctx):
        ## => GUILD INFO FROM DB
        async with self.async_session() as session:
            guildInfo = await GetGuildInfo(session, ctx.guild.id)
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
        elif self.free_period:
            embed.description = f"**ACTIVATION:**  The bot is free for now! Please support us on Patreon! [Patreon link]({self.patreon_link})"
        elif trial_flag:
            embed.description = f"**ACTIVATION:**  {days_left} days left before trial period will end. To keep using the bot please subscribe to our patreon! [Patreon link]({self.patreon_link})"+self.patreonInstructions+"\n"
        elif guildInfo.activate == False:
            embed.descriprion = f"**ACTIVATION:**  the bot is not activated. To activate the bot please subscribe to our patreon! [Patreon link]({self.patreon_link})"+self.patreonInstructions
        elif guildInfo.patreon_discord_id != None:
            embed.set_footer(text="ACTIVATION:  the bot is activated with patreon subscription")

        bot_msg = await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_ready(self):
        p = BaseProfiler("on_ready")
        print("Bot connected")
        if not self.DiscordComponentsInit:
            DiscordComponents(self.bot)
            self.DiscordComponentsInit = True
        
        ## => UPDATE THE JOINED GUILDS IN THE DATABASE
        botJoinedGuilds = self.bot.guilds
        botJoinedGuildsIds = [g.id for g in botJoinedGuilds]
        dbGuilds = []
        async with self.async_session() as session:
            dbGuilds = await session.execute(select(botGuilds))
            dbGuilds = dbGuilds.scalars().all()
            
            for guildInfo in dbGuilds:
                if int(guildInfo.guild_id) in botJoinedGuildsIds:
                    guildInfo.currently_joined = True
                    botJoinedGuildsIds.remove(int(guildInfo.guild_id))
                else:
                    guildInfo.currently_joined = False
            
            ## => ADD THE GUILD THAT JOINED BUT NOT IN THE DB
            for guildId in botJoinedGuildsIds:
                newGuild = botGuilds(guild_id = str(guildId),
                                        activate=True,
                                        currently_joined=True,
                                        joined_utc=str(datetime.utcnow()),
                                        patreon_discord_id = None,
                                        prefix = None)
                session.add(newGuild)
            await session.commit()



    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        p = BaseProfiler("on_command_error")
        ## => EXCEPTION HANDLERS
        if isinstance(error, commands.errors.NotOwner):
            embed = self.embedText(str(error))
            await ctx.send(embed=embed)
        elif isinstance(error, commands.errors.NoPrivateMessage):
            return
        elif isinstance(error, guildNotActive):
            embed = self.embedText(f"Trial period has expired! To gain full access to the bot please activate the bot using this link {self.patreon_link}")
            await ctx.send(embed = embed)
            print("GUILD WITHOUT PERMISSION DENIED: ", ctx.guild.name)
        elif isinstance(error, commands.errors.CommandOnCooldown):
            return
        elif isinstance(error, commands.errors.CommandNotFound):
            return
        elif isinstance(error, commands.errors.UserInputError):
            embed = self.embedText(str(error))
            await ctx.send(embed=embed)
        elif isinstance(error, commands.errors.CommandError):
            print(error)
            
            ## => CHECK IF GUILD IS IN THE DB
            async with self.async_session() as session:
                guildInfo = await GetGuildInfo(session, ctx.guild.id)
                if not guildInfo:
                    newGuild = botGuilds(guild_id=str(ctx.guild.id),
                                    joined_utc=str(datetime.utcnow()),
                                    currently_joined = True,
                                    activate=True)
                    session.add(newGuild)
                    await session.commit()
                    print("GUILD ADDED TO THE DB IN ERROR HANDLER: ", ctx.guild.name)
        else:
            print(error)


