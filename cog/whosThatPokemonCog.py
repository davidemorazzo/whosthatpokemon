import discord
from discord.ext import commands, tasks
from discord import Embed, File, Colour
from discord.commands import slash_command, Option
from discord.ext.commands import Cooldown, CooldownMapping, BucketType

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import text
from sqlalchemy.future import select
from sqlalchemy.sql import func
from sqlalchemy import desc

from dotenv import load_dotenv
from random import choice
from collections import Counter
from datetime import datetime, timedelta
import pandas as pd
import asyncio
from dateutil import parser

from database import (
    botGuilds, 
    userPoints, 
    botChannelIstance, 
    patreonUsers,
    GetChannelIstance,
    GetGuildInfo)
from profiling.profiler import BaseProfiler
import logging
from .utils import(
    cooldown
)

from str.string_db import string_translator
from .buttons import FourButtons
from .generationBtn import GenButtons
from .languageBtn import LangButtons

class guildNotActive(commands.errors.CheckFailure):
    pass

class whosThatPokemon(commands.Cog):
    def __init__(self, bot:discord.Bot, engine, data_path, description_path):
        load_dotenv()
        self.bot = bot
        self.db_engine = engine
        self.async_session = sqlalchemy.orm.sessionmaker(self.db_engine, expire_on_commit=False, class_=AsyncSession)
        self.color = Colour.red()
        self.pokedexDataFrame = pd.read_csv(data_path, index_col='name')
        self.descriptionDataFrame = pd.read_csv(description_path, index_col='name')
        complete_data = self.pokedexDataFrame['clear_path'].notna() & \
                        self.pokedexDataFrame['blacked_path'].notna() & \
                        self.descriptionDataFrame['en'].notna()
        self.pokedexDataFrame = self.pokedexDataFrame[complete_data] # take out incomplete data
        self.cooldown = cooldown()
        self.pokemonGenerations = {
            'kanto':'1', 
            'johto':'2', 
            'hoenn':'3', 
            'unova':'4', 
            'kalos':'5', 
            'alola':'6',
            'mega':'m', 
            'gmax':'g', 
            'galar':'j'}
        self.logger = logging.getLogger('discord')
        self.languages = {'English':'en', 
                        'Français':'fr',
                        'Español':'es',
                        'Italiano':'it',
                        '한국인':'ko',
                        'Deutsch':'de',
                        'हिन्दी':'hi', 
                        '日本':'jp', 
                        '简体中文':'zh'}
        self.strings = string_translator('./str/strings.csv', self.async_session)
        # self.pokemon_spawn.start()

    def embedText(self, text):
        text = text.replace('"', '\"').replace("'", "\'")
        return Embed(description=f"**{text}**", color=self.color)

    def correctGuess(self, guess:str, solution:str, language_id:str) -> bool:
        """
        Return if the 'guess' is correct. Valid guesses are:
            - Guild language with identifiers
            - English with identifiers
            - English with no identifiers
            - English or language first word
        """

        compare = lambda x, y: Counter(x)==Counter(y)
        # Get solution in 'en' and the guild language
        try:
            en_solution = self.pokedexDataFrame.loc[solution,'en']
            translated_solution = self.pokedexDataFrame.loc[solution, language_id]
        except:
            return False
        ## => DECIDE IF THE GUESS IS CORRECT
        identifiers = ['gigantamax', 'galar', 'alola', 'mega', 'x', 'y', 'forme', 'style']
        no_ident = en_solution.split(' ')
        no_ident = [word for word in no_ident if word not in identifiers]
        en_solution = en_solution.lower().strip().split(' ')
        translated_solution = translated_solution.lower().strip().split(' ')
        first_word = [en_solution[0]]
        translated_first_word = [translated_solution[0]]
        wordGuess = guess.lower().split(' ')
        # No identifiers solution is also valid
        if "gmax" in wordGuess:
            wordGuess.remove("gmax")
            wordGuess.append("gigantamax")   
        if "galarian" in wordGuess:
            wordGuess.remove("galarian")
            wordGuess.append("galar")    
        if "alolan" in wordGuess:
            wordGuess.remove("alolan")
            wordGuess.append("alola")
        ## => FINAL COMPARISON
        result = compare(en_solution, wordGuess) or \
                compare(translated_solution, wordGuess) or \
                compare(no_ident, wordGuess) or \
                compare(first_word, wordGuess) or \
                compare(translated_first_word, wordGuess)

        return result

    async def get_guild_lang(self, channel_id:int) -> str:
        """
        Return the guild language ID
        """
        async with self.async_session() as session:
            stmt = select(botChannelIstance.language).where(botChannelIstance.channel_id == str(channel_id))
            result = await session.execute(stmt)
            language = result.scalars().first()
            return language
    
    async def getGuildGifList(self, guildObj) -> list:
        """Get list of available gifs for the specified guild. They are chosen by the selected
            generations in the database"""

        async with self.async_session() as session:
            row = await session.execute(select(botGuilds).filter_by(guild_id=str(guildObj.id)))
            guildInfo = row.scalars().first()
            # sections of the pokedex
            poke_generation = guildInfo.poke_generation
            # Get guild tier
            row = await session.execute(select(patreonUsers).filter_by(guild_id=str(guildObj.id)))
            patreon_info = row.scalars().first()
            if patreon_info:
                guild_tier = patreon_info.tier
            else:
                guild_tier = 0

        ## => CREATE LIST OF GIFS
        tier_filter = self.pokedexDataFrame['tier'].notna() >= guild_tier
        no_gen_filter =  self.pokedexDataFrame['generation'].isna()

        # Add to the list the correct generations
        gifList = list(self.pokedexDataFrame[no_gen_filter].index)
        for generation in self.pokemonGenerations.keys():
            if self.pokemonGenerations[generation] in poke_generation:
                gifList += list(self.pokedexDataFrame[self.pokedexDataFrame['generation']==generation].index)

        return gifList
            
    async def createQuestion(self, guild:discord.Guild, skip=False, channel_id:int=None) -> tuple:
        # async with self.async_session() as session:
            # p = BaseProfiler("createQuestion")
            # get guild patreon tier
            # query = await session.execute(select(botGuilds.guild_id, patreonUsers.tier
            #             ).join(patreonUsers, patreonUsers.discord_id == botGuilds.patreon_discord_id
            #             ).filter(botGuilds.guild_id == str(guild.id)))
	        
            # r = query.first()
            # if r:
            #     guildTier = r[1]
            # else:
            #     guildTier = 0

        availableGifs = await self.getGuildGifList(guild)
        if availableGifs:
            gif_name = choice(availableGifs)
            ## => SEND EMBED
            embed = Embed(color=self.color)
            embed.set_author(name = "Who's That Pokemon?", icon_url=self.bot.user.avatar.url)
            embed.description = await self.strings.get('question', channel_id)
            thumb = File(self.pokedexDataFrame.loc[gif_name]['blacked_path'], filename="gif.gif")
            embed.set_thumbnail(url="attachment://gif.gif")
            
            ## => MEMORIZE THE SOLUTION
            async with self.async_session() as session:
                thisGuild = await GetChannelIstance(session, guild.id, channel_id)
                if not thisGuild:
                    return None, None
                if skip and thisGuild.guessing == False:
                    return None, None
                thisGuild.guessing = True
                thisGuild.current_pokemon=gif_name
                thisGuild.is_guessed=False
                await session.commit()

            return thumb, embed
        
        return None, None
    
    async def getHint(self, guild_id, channel_id):
        ## => CREATE HINT EMBED
        strings = await self.strings.get_batch(['not_guessing', 'hint'], channel_id)
        async with self.async_session() as session:
            channel = await GetChannelIstance(session,guild_id, channel_id)
            lang_id = channel.language

        if not channel or not channel.guessing:
            embed=self.embedText(strings[0])
            return embed
        else:
            ## => SCRAMBLE THE SOLUTION
            raw_solution = channel.current_pokemon
            solution = self.pokedexDataFrame.loc[raw_solution, lang_id]
            solution = list(solution)
            if len(solution) <= 3:
                scrambled = "_ _ _"
            else:
                for i in range(0,len(solution)):
                    if i%2 == 1:
                        if solution[i] != ' ':
                            solution[i] = '\_'
            scrambled = ''.join(solution).replace("-", " ")
            embed = self.embedText(f"{strings[1]} {scrambled}")
            return embed
    
    async def getRank(self, global_flag, number, guild_id, channel_id):
        p = BaseProfiler("getRank")
        ## => SQL QUERY
        async with self.async_session() as session:
            if global_flag:
                q = await session.execute(select(userPoints.user_id, userPoints.username, func.sum(userPoints.points).label("global_points")
                    ).group_by(userPoints.user_id, userPoints.username
                    ).order_by(desc("global_points")
                    ).limit(2*number)) # fetch double of the needed users to compensate deleted accounts
                users = q.all()
            else:
                res = await session.execute(select(userPoints).filter_by(guild_id=str(guild_id)).order_by(desc(userPoints.points_from_reset)).limit(2*number))
                users = res.scalars().fetchall()
        
        ## => FORMAT TEXT
        num = 0 
        text = ''
        for user in users:
            ## => GET IF USERNAME IS IN DB, OTHERWISE FETCH FROM API
            if user.username != None:
                username = user.username
            else:
                try:
                    user_obj = await self.bot.fetch_user(int(user.user_id))
                    username = user_obj.name
                except :
                    username = None
            if username: # if username not founded => not added to the leaderboard
                string = await self.strings.get('win_count', channel_id)
                if global_flag:
                    text = text + f"#{num+1} {username} | {string}: {user[2]}\n"
                else:
                    text = text + f"#{num+1} {username} | {string}: {user.points_from_reset}\n"
                
                num = num + 1
            ## => STOP AT REQUESTED ENTRIES REACHED
            if num >= number:
                break
        if text == '':
            text = '.'
        return text
    

    async def cog_check(self, ctx):
        return True
    
    async def only_admin(self, ctx:discord.ApplicationContext):
        if ctx.author.guild_permissions.administrator:
            return True
        else:
            await ctx.delete()
            string = await self.strings.get('only_admin', ctx.channel_id)
            raise commands.errors.NotOwner(string)
	
    @commands.Cog.listener()
    async def on_message(self, message):
        p = BaseProfiler("on_message_global")
        if message.author == self.bot.user or message.guild == None:
            return

        ## => FETCH GUILD DATA FROM DATABASE
        async with self.async_session() as session:
            channelIstance = await GetChannelIstance(session, message.guild.id, message.channel.id)
            if not channelIstance:
                return
            guildInfo = await GetGuildInfo(session, message.guild.id)
            # if not guildActivation.patreon:
            #     return

        ## => CHECK FOR THE CORRECT SOLUTION
        raw_solution = channelIstance.current_pokemon
        if not raw_solution or channelIstance.is_guessed:
            return
        if self.correctGuess(message.content, raw_solution, channelIstance.language):
           
            ## => DB OPERATIONS
            async with self.async_session() as session:
                ## => UPDATE GUILD STATUS
                channelIstance = await GetChannelIstance(session, message.guild.id, message.channel.id)
                channelIstance.is_guessed = True
                channelIstance.last_win_date = str(datetime.utcnow())
                await session.commit()
                ## => FETCH USER
                currentUser = await session.execute(select(userPoints).filter_by(guild_id=str(message.guild.id), user_id=str(message.author.id)))
                currentUser = currentUser.scalars().first()
                if not currentUser:
                    ## => USER NOT FOUNDED -> ADD IT TO DATABASE
                    newUser = userPoints(user_id = str(message.author.id), 
                                        guild_id=str(message.guild.id),
                                        points=0,
                                        points_from_reset = 0,
                                        username = message.author.name)
                    session.add(newUser)
                    currentUser = newUser
                ## => INCREASE POINTS
                pointsToAdd = 1
                # if guildInfo.patreon:
                    # pointsToAdd = 2
                currentUser.points = currentUser.points + pointsToAdd #global points
                currentUser.points_from_reset = currentUser.points_from_reset + pointsToAdd
                currentUser.last_win_date = str(datetime.utcnow())
                currentUser.username = message.author.name
                serverWins = currentUser.points_from_reset
                ## => UPDATE USERNAME IN ALL THE USER ENTRIES
                username = message.author.name.replace("'", "\'")
                await session.execute(sqlalchemy.update(userPoints).
                                        where(userPoints.user_id==str(message.author.id)).
                                        values(username=username))
                ## => FETCH USER GLOBALLY
                userGlobally = await session.execute(select(userPoints).filter_by(user_id=str(message.author.id)))
                userGlobally = userGlobally.scalars().all()
                userGlobalPoints = 0
                for entry in userGlobally:
                    userGlobalPoints += entry.points
                await session.commit()

            # Get description and strings in the correct language
            language_id = await self.get_guild_lang(message.channel.id)
            description = self.descriptionDataFrame.loc[raw_solution][language_id]
            t = await self.strings.get_batch(['correct', 'points', 'server', 'global', 'ranks', 'it_is'], message.channel.id)
            correct_s, points_s, server_s, global_s, ranks_s, it_is = t
            translated_solution = self.pokedexDataFrame.loc[raw_solution][language_id]
            # Create and send response embed
            embed = Embed(color=self.color)
            embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar.url)
            embed.description = f"{message.author.mention} {it_is}** {translated_solution.title()} **\n"
            embed.add_field(name=points_s, value=f"``` {server_s}: {serverWins}\n {global_s}: {userGlobalPoints} ```", inline=False)
            embed.set_footer(text=ranks_s)
            if description.strip() != "":
                ## => SEND CORRECT-GUESS MESSAGE WITH DESCRIPTION
                embed.description += "\n" + description + "\n."
                clearThumb = File(self.pokedexDataFrame.loc[raw_solution]['clear_path'], filename="clear.gif")
                embed.set_thumbnail(url="attachment://clear.gif")
                await message.channel.send(file=clearThumb, embed=embed)
            else:
                ## => SEND CORRECT-GUESS MESSAGE STANDARD
                pika = File("./gifs/pikachu.gif", "pikachu.gif")
                embed.set_thumbnail(url="attachment://pikachu.gif")
                await message.channel.send(file=pika, embed=embed)

            ## => SEND NEW QUESTION
            if channelIstance.guessing:
                file, embed = await self.createQuestion(message.guild, channel_id=channelIstance.channel_id)
                await message.channel.send(file=file, embed=embed, view=FourButtons(self))
                
        # await self.bot.process_commands(message)
    
    @slash_command(name="start", 
                    description="Start guessing a pokémon",
                    cooldown=CooldownMapping(Cooldown(1, 30), BucketType.channel))
    async def startGuess(self, ctx):
        ## => CHECK IF ALREADY STARTED
        async with self.async_session() as session:
            guildInfo = await GetChannelIstance(session, ctx.guild.id, ctx.channel.id)
            if not guildInfo:
                ## => ADD CHANNEL ISTANCE  
                channelIstance = botChannelIstance(guild_id = str(ctx.guild.id),
                                                    channel_id = str(ctx.channel.id),
                                                    guessing = True)
                session.add(channelIstance)
                await session.commit()

            elif guildInfo.guessing:
                string = await self.strings.get('start_error', ctx.channel_id)
                embed = self.embedText(string)
                await ctx.send_response(embed=embed)
                return
        
        ## => GET NEW POKEMON
        file, embed = await self.createQuestion(ctx.guild, channel_id=str(ctx.channel.id))
        lang_id = await self.get_guild_lang(ctx.channel.id)
        await ctx.send_response(file=file, embed=embed, view=FourButtons(self))
            

    @slash_command(name="stop", description="Stop guessing a pokémon")
    async def stopGuess(self, ctx):
        ## => UPDATE THE DB
        async with self.async_session() as session:
            thisGuild = await GetChannelIstance(session, ctx.guild.id , ctx.channel.id)
            t = await self.strings.get_batch(['stop_error', 'stop_ok'], ctx.channel_id)
            stop_error, stop_ok = t
            
            if not thisGuild:
                embed = self.embedText(stop_error)
            else:
                thisGuild.guessing = False
                await session.commit()
                embed = self.embedText(stop_ok)
        await ctx.send_response(embed=embed)


    @slash_command(name="hint", description="Hint for guessing the current pokémon")
    async def hint(self, ctx):
        embed = await self.getHint(ctx.guild.id, ctx.channel.id)
        await ctx.send_response(embed=embed)


    @slash_command(name="rank", description="Get the list of the best users. Use rank global to see the rank across every server.")
    async def rank(self, 
                    ctx, 
                    ranking : Option(str, choices=["local", "global"], default="local"),
                    length : Option(int, min_value=1, max_value=20, default=10)
                ):
        
        ## => GET FORMATTED LEADERBOARD
        if ranking == "global":
            global_flag = True
        else:
            global_flag = False
        number = length

        text = await self.getRank(global_flag, number, ctx.guild.id, ctx.channel_id)
                   
        ## => SEND EMBED     
        embed = Embed(color=self.color)
        embed.add_field(name=self.bot.user.name, value = text)
        if global_flag:
            thumbnail = File("./gifs/globe.gif", "trophy.gif")
        else:
            thumbnail = File("./gifs/trophy.gif", "trophy.gif")

        embed.set_thumbnail(url="attachment://trophy.gif") 
        await ctx.respond(embed = embed, file = thumbnail)

    async def solution_embed(self, guild_id, channel_id) -> tuple:
        """
        return the correct solution embed
        """
        async with self.async_session() as session:
            channelIstance = await GetChannelIstance(session, guild_id, channel_id)
            raw_solution = channelIstance.current_pokemon
        
        language_id = await self.get_guild_lang(channel_id)
        description = self.descriptionDataFrame.loc[raw_solution][language_id]
        if pd.notna(description) and description.strip() != "":
            clearEmbed = Embed(color=self.color)
            clearEmbed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar.url)
            clearEmbed.description = description
            clearThumb = File(self.pokedexDataFrame.loc[raw_solution]['clear_path'], filename="clear.gif")
            clearEmbed.set_thumbnail(url="attachment://clear.gif")
            return clearEmbed, clearThumb
        else:
            return None, None

    @slash_command(name="skip", description="Skip this pokémon. 20 seconds of cooldown")
    async def skip(self, ctx:discord.ApplicationContext):
        ## => CUSTOM COOLDOWN
        cooldownAmount = 20
        id = ctx.channel_id
        if self.cooldown.is_on_cooldown(id, 'skip_btn', cooldownAmount):
            string = await self.strings.get('skip_cooldown', ctx.channel_id)
            await ctx.response.send_message(embed=self.embedText(string), ephemeral=True)
            self.logger.debug(f"{id}/skip_btn  ->  on cooldown")
            return

        self.cooldown.add_cooldown(id, 'skip_btn')

        ## => SEND PREVIOUS SOLUTION
        await ctx.defer()
        solution_embed, clear_thumb = await self.solution_embed(ctx.guild_id, ctx.channel_id)
        if solution_embed:
            await ctx.respond(file=clear_thumb, embed=solution_embed)

        file, embed = await self.createQuestion(ctx.guild, skip=True, channel_id=str(ctx.channel.id))
        if not file:
            ## => GUILD NOT GUESSING
            string = await self.strings.get('skip_error', ctx.channel_id)
            embed = self.embedText(string)
            await ctx.respond(embed=embed)
            return
        lang_id = await self.get_guild_lang(ctx.channel_id)
        await ctx.respond(file=file, embed=embed, view=FourButtons(self))
        
    @slash_command(name="resetrank", 
                    description="Reset to zero the points of this server players. Global points will be kept. Only administrator")
    async def resetrank(self, ctx):   

        await self.only_admin(ctx)
        ## => POINTS_FROM_RESET TO 0 IN THE DB
        async with self.async_session() as session:
            guildPlayers = await session.execute(select(userPoints
                                ).filter_by(guild_id = str(ctx.guild.id)))
            guildPlayers = guildPlayers.scalars().all()
            for player in guildPlayers:
                player.points_from_reset = 0
            await session.commit()
        string = await self.strings.get('reset_ok', ctx.channel_id)
        embed = self.embedText(string)
        await ctx.send_response(embed=embed)

    async def generationButtons(self, guild):
        """Generates the button layout for the specified guild. Buttons needed for 
            generation selection."""
                    
        async with self.async_session() as s:
            guildInfo = await s.execute(select(botGuilds).filter_by(guild_id=str(guild.id)))
            guildInfo = guildInfo.scalars().first()
            poke_generation = guildInfo.poke_generation
            lang_id = guildInfo.language
        
        view = GenButtons(self, poke_generation, guild.id, lang_id)
        return view

    @slash_command(name="selectgenerations",
                 description="Select the pokemon generations that are used in the game. Admin only")
    async def selectGen(self, ctx):

        await self.only_admin(ctx)
        try:
            await self.is_patreon(ctx.guild_id, ctx.channel_id)
        except:
            string = await self.strings.get('patreon_error', ctx.channel_id)
            embed = self.embedText(string)
            await ctx.send_response(embed=embed)
            return
        
        view = await self.generationButtons(ctx.guild)
        await ctx.send_response(view=view)

    async def is_patreon(self, guild_id, channel_id):
        """
        Check if the guild is patreon. Used for check
        """
        async with self.async_session() as session:
            guild = await session.execute(select(botGuilds).filter_by(guild_id=str(guild_id)))
            guild = guild.scalars().first()
            if guild.patreon == False:
                string = await self.strings.get('patreon_error', channel_id)
                raise Exception(string)

    @slash_command(name="selectlanguage",
                 description="Select the language used in the game. Admin only")
    async def selectLanguage(self, ctx:discord.ApplicationContext):
        await self.only_admin(ctx)
        try:
            await self.is_patreon(ctx.guild_id, ctx.channel_id)
        except:
            string = await self.strings.get('patreon_error', ctx.channel_id)
            embed = self.embedText(string)
            await ctx.send_response(embed=embed)
            return
        
        lang_id = await self.get_guild_lang(ctx.channel_id)
        view = LangButtons(self, ctx.guild.id, lang_id)
        await ctx.send_response(view=view)
    


    @tasks.loop(minutes=10)
    async def pokemon_spawn(self):
        async with self.async_session() as session:
            stmt = select(botChannelIstance
                    ).join(botGuilds, botChannelIstance.guild_id == botGuilds.guild_id
                    ).filter(botChannelIstance.guessing == True
                    ).filter(botGuilds.currently_joined == True)
            result = await session.execute(stmt)
            channels = result.scalars().all()

        async def spawn(channel_istance:botChannelIstance, time:datetime):
            try:
                guild_obj = await self.bot.fetch_guild(channel_istance.guild_id)
                channel_obj = await self.bot.fetch_channel(channel_istance.channel_id)
            except:
                return
            if channel_obj:
                # Check if there are no wins in the last 10 mins
                if not channel_istance.last_win_date or\
                    parser.parse(channel_istance.last_win_date) < time - timedelta(minutes=9):
                    file, embed = await self.createQuestion(guild_obj, channel_id=channel_obj.id)
                    if file:
                        await channel_obj.send(file=file, embed=embed)


        # Run the spawns in async way
        now = datetime.utcnow()
        for channel in channels:
            asyncio.create_task(spawn(channel, now))
        self.logger.debug('Spawning pokemon tasks running')
    
    @commands.command(aliases=['start', 'skip', 'hint', 'stop', 'rank', 'help'])
    async def old_command(self, ctx):
        """
        This command is deprecated. Use the slash commands instead.
        """
        string = "This command is deprecated. Use the slash commands instead. To enable them click on this link to add the permission to the bot.\
            https://discord.com/oauth2/authorize?client_id=866987691631575060&permissions=117760&scope=bot%20applications.commands"
        embed = self.embedText(string)
        await ctx.send(embed=embed)