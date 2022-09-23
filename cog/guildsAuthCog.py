import logging
import discord
from discord.ext import commands, tasks
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from dateutil import parser
from discord import Embed, Colour, slash_command
import os
from cog.whosThatPokemonCog import(
    guildNotActive, 
    BaseProfiler,
    botGuilds,
    patreonUsers,
    GetGuildInfo)
from patreonAPI import fetch_patreons
from str.string_db import string_translator

import asyncio

class guildsAuthCog(commands.Cog):
    def __init__(self, bot:discord.Bot, patreonKey, patreonCreatorId, engine):
        self.patreonKey = patreonKey
        self.patreonCreatorId = patreonCreatorId
        self.bot = bot
        self.db_engine = engine
        self.async_session = sessionmaker(self.db_engine, expire_on_commit=False, class_=AsyncSession)
        self.trial_days = int(os.getenv("DAYS_OF_TRIAL"))
        self.color = Colour.red()
        self.verification.start()
        self.free_period = True
        self.patreon_link = "https://www.patreon.com/whosthatpokemon"
        self.guildWhiteList = [752464482424586290, 822033257142288414]
        self.logger = logging.getLogger('discord')
        self.strings = string_translator('str/strings.csv', self.async_session)
        self.default_poke_gen = '123456'

    async def verifyPatreon(self, guildObj: botGuilds, patreonIds:list) -> str:
        """Return the discord id of the patreon if there is a match, None otherwise"""

        ## => ASSIGN TO THE GUILD THE CORRECT PATREON
        discordGuild = self.bot.get_guild(int(guildObj.guild_id))
        if str(guildObj.owner.id) in patreonIds:
            return str(guildObj.owner.id)
        else:
            return None


    async def updatePatreons(self):
        ## => FETCH PATREONS FROM API
        patreons_dict = await fetch_patreons(os.getenv("PATREON_TOKEN"))
        ## => KEEP IN THE DB ONLY THE ACTIVE PATRONS
        async with self.async_session() as session:
            patreonsDb = await session.execute(select(patreonUsers))
            patreonsDb = patreonsDb.scalars().all()
            ## => CHECK PATREONS IN THE DATABASE
            for patreon in patreonsDb:
                if not patreon.discord_id in patreons_dict.keys():
                    ## => USER IS NOT A PATREON ANYMORE
                    await session.delete(patreon)
                elif patreons_dict[patreon.discord_id]['declined_since'] == 'None':
                    ## => USER HAS BEEN DECLINED
                    await session.delete(patreon)
                    patreons_dict.pop(patreon.discord_id)
                else:
                    # Check if patreon is not declined
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
                                    patreon=True)
                session.add(newGuild)

            newGuild.currently_joined=True
            await session.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        p = BaseProfiler("on_guild_remove")
        ## => UPDATE GUILD INFO TO NOT JOINED
        async with self.async_session() as session:
            newGuild = await GetGuildInfo(session, guild.id)
            if newGuild:
                newGuild.currently_joined= False
                await session.commit()
                self.logger.info("BOT LEFT GUILD: ", guild.name)

    @tasks.loop(minutes=10)
    async def verification(self):
        
        tic = datetime.now()
        ## => UPDATE PATREONS INTO THE DB
        await self.updatePatreons()
        await self.bot.wait_until_ready()
        ## => VERIFY EVERY GUILD
        async with self.async_session() as session:
            # Query users eligible for guild activation
            patreons = await session.execute(select(patreonUsers
                                    ).where(patreonUsers.sub_status != 'None'))
            patreons = patreons.scalars().all()
            patreonIds = [p.discord_id for p in patreons if int(p.tier) >= 500]
            guilds = await session.execute(select(botGuilds).filter_by(currently_joined=True))
            guilds = guilds.scalars().all()
            
            async def activate_guild(guild):
                """
                Coroutine to check if a patreon is the owner of this guild and 
                update the database.bot_guilds and database.patreon_users
                """
                if self.free_period:
                    guild.patreon=True
                    guild.patreon_discord_id=None
                    return

                if int(guild.guild_id) in self.guildWhiteList:
                    ## => WHITELISTED GUILD DOES NOT NEED VERIFICATION
                    guild.patreon = True
                    guild.patreon_discord_id = None

                else:
                    ## => CHECK FOR PATREON SUBSCRIPTION
                    patreonId = await self.verifyPatreon(guild, patreonIds)
                    
                    if patreonId:
                        ## => ACTIVATE THE GUILD WITH PATREON
                        guild.patreon = True
                        guild.patreon_discord_id = str(patreonId)
                    else:
                        ## => DEACTIVATE THE GUILD
                        guild.patreon = False
                        guild.patreon_discord_id = None
                        guild.poke_generation = self.default_poke_gen
                        pass

            # Check all the guilds in a async way
            await asyncio.gather(*map(activate_guild, guilds))
            await session.commit()

        toc = datetime.now()
        delta = toc-tic
        self.logger.info(f"Verification executed in: {str(delta)}")

    @slash_command(name = "help", description="Show this message")
    async def help(self, ctx:discord.ApplicationContext):
        ## => GUILD INFO FROM DB
        # TODO cambiare in slash command
        async with self.async_session() as session:
            guildInfo = await GetGuildInfo(session, ctx.guild.id)
        join_date = parser.parse(guildInfo.joined_utc)
        days_left = self.trial_days - (datetime.utcnow()-join_date).days
        trial_flag = days_left >= 0 and guildInfo.patreon_discord_id ==None

        embed = Embed(title="Commands help", colour=self.color)        
        # If there are no arguments, just list the commands:
        for i,x in enumerate(self.bot.application_commands):
            cmd = x
            embed.add_field(
                name=cmd.name+' ',
                value=cmd.description,
                inline=False
            )

        t = await self.strings.get_batch(['activation', 'whitelist', 'free_bot', 'trial_days', 'activation_ok', 'activation_error', 'instructions'], 
                                ctx.channel_id)
        activation, whitelist, free_bot, trial_days, activation_ok, activation_error, instructions = t

        if ctx.guild.id in self.guildWhiteList:
            embed.set_footer(text=f"{activation}:  {whitelist}")
        elif self.free_period:
            embed.description = f"**{activation}:** {free_bot} [Patreon link]({self.patreon_link})"
        elif trial_flag:
            embed.description = f"**{activation}:**  {days_left} {trial_days} [Patreon link]({self.patreon_link})"+instructions+"\n"
        elif guildInfo.patreon == False:
            embed.descriprion = f"**{activation}:**  {activation_error} [Patreon link]({self.patreon_link})"+instructions
        elif guildInfo.patreon_discord_id != None:
            embed.set_footer(text=f"{activation}:  {activation_ok}")

        bot_msg = await ctx.send_response(embed=embed)
    
    @commands.Cog.listener()
    async def on_ready(self):
        p = BaseProfiler("on_ready")
        self.logger.info("Bot connected")
        
        
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
                                        patreon=True,
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
            string = self.strings.get('expired', ctx.channel.id)
            embed = self.embedText(f"{string} {self.patreon_link}")
            await ctx.send(embed = embed)
            self.logger.info("GUILD WITHOUT PERMISSION DENIED: ", ctx.guild.name)
        elif isinstance(error, commands.errors.MissingPermissions):
            return
        elif isinstance(error, commands.errors.CommandOnCooldown):
            return
        elif isinstance(error, commands.errors.CommandNotFound):
            return
        elif isinstance(error, commands.errors.UserInputError):
            embed = self.embedText(str(error))
            await ctx.send(embed=embed)
        elif isinstance(error, commands.errors.CommandError):
            self.logger.warning(error)
            
            ## => CHECK IF GUILD IS IN THE DB
            async with self.async_session() as session:
                guildInfo = await GetGuildInfo(session, ctx.guild.id)
                if not guildInfo:
                    newGuild = botGuilds(guild_id=str(ctx.guild.id),
                                    joined_utc=str(datetime.utcnow()),
                                    currently_joined = True,
                                    patreon=True)
                    session.add(newGuild)
                    await session.commit()
                    self.logger.warning("GUILD ADDED TO THE DB IN ERROR HANDLER: ", ctx.guild.name)
        else:
            self.logger.warning(error)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx:discord.ApplicationContext, error):
        
        if isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.send_response(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
        
        elif isinstance(error, discord.ApplicationCommandError):
            if isinstance(error, discord.errors.ApplicationCommandInvokeError):
                self.logger.info(error)
            else:
                await ctx.send_followup(embed=self.embedText(error), ephemeral=True)
        
        elif isinstance(error, discord.errors.NotFound):
            self.logger.info(error)
        
        else:
            self.logger.warning(error)

