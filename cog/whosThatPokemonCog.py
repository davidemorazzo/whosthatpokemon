import discord
from discord.ext import commands, tasks, pages
from discord import Embed, File, Colour, default_permissions
from discord.commands import slash_command, Option
from discord.ext.commands import Cooldown, CooldownMapping, BucketType

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import text
from sqlalchemy.future import select
from sqlalchemy.sql import func
from sqlalchemy import desc, text

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
    shinyWin,
    settings,
    GetChannelIstance,
    GetGuildInfo)
from profiling.profiler import BaseProfiler
import logging
from .utils import(
    cooldown,
    create_shiny_paginator,
    get_clear_gif,
    get_blacked_gif,
    get_shiny_gif,
    is_user_patreon
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
            'galar':'j',
            'other':'o'}
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
        self.channel_cache = {}
        self.shiny_rate = None
        self.patreon_point_mult = 2
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
        if channel_id in self.channel_cache:
            # try get from cache
            return self.channel_cache[channel_id]
        else:
            # get from database
            async with self.async_session() as session:
                stmt = select(botChannelIstance).where(botChannelIstance.channel_id == str(channel_id))
                result = await session.execute(stmt)
                channel_info = result.scalars().first()
            return channel_info.language
                
    
    async def getGuildGifList(self, guildObj:discord.Guild) -> list:
        """Get list of available gifs for the specified guild. They are chosen by the selected
            generations in the database"""

        async with self.async_session() as session:
            row = await session.execute(select(botGuilds).filter_by(guild_id=str(guildObj.id)))
            guildInfo = row.scalars().first()
            guildInfo : botGuilds
            # sections of the pokedex
            poke_generation = guildInfo.poke_generation

        ## => CREATE LIST OF GIFS
        # no_gen_filter =  self.pokedexDataFrame['generation'].isna()

        # Add to the list the correct generations
        # gifList = list(self.pokedexDataFrame[no_gen_filter].index)
        gifList = []
        for generation in self.pokemonGenerations.keys():
            if self.pokemonGenerations[generation] in poke_generation:
                gifList += list(self.pokedexDataFrame[self.pokedexDataFrame['generation']==generation].index)

        return gifList
            
    async def createQuestion(self, guild:discord.Guild, skip=False, channel_id:int=None) -> tuple[File, Embed]:
        availableGifs = await self.getGuildGifList(guild)
        if availableGifs:
            gif_name = choice(availableGifs)
            ## => SEND EMBED
            embed = Embed(color=self.color)
            embed.set_author(name = "Who's That Pokemon?", icon_url=self.bot.user.avatar.url)
            embed.description = await self.strings.get('question', channel_id)
            gif_file = await get_blacked_gif(gif_name, self.async_session)
            thumb = File(gif_file, filename="gif.gif")
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
    
    async def getShinyRank(self) -> list:
        async with self.async_session() as session:
            stmt = select(shinyWin.user_id, func.count(shinyWin.user_id)
                    ).group_by(shinyWin.user_id
                    ).order_by(desc(func.count(shinyWin.user_id))
                    ).limit(20)
            result = await session.execute(stmt)
            users = result.all()
        return users
	
    async def create_shiny_embed(self, raw_solution:str, user:discord.Member, stats:list, lang_id, shiny_count:int):
        # get translated strings
        points_str = self.strings.s_get('points', lang_id)
        ranks_str = self.strings.s_get('ranks', lang_id)
        it_is_str = self.strings.s_get('it_is', lang_id)
        shiny_win_1 = self.strings.s_get('shiny_win_1', lang_id)
        shiny_win_2 = self.strings.s_get('shiny_win_2', lang_id)

        # get translated description and name
        translated_description = self.descriptionDataFrame.loc[raw_solution][lang_id]
        translated_name = self.pokedexDataFrame.loc[raw_solution][lang_id]
        # create embed
        embed = Embed(color=self.color)
        embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar.url)
        embed.set_footer(text=ranks_str)
        embed.description = f"{user.mention} {it_is_str}** Shiny {translated_name.title()}**\n"
        embed.description += "\n" + f"{shiny_win_1} {shiny_count} {shiny_win_2}\n"
        embed.description += "\n" + translated_description + "\n."
        embed.set_thumbnail(url="attachment://shiny.gif")
        # Add stats
        embed.add_field(name=points_str, value=f"```{''.join(stats)}```", inline=False)
        
        # Attach shiny gif. If shiny gif don't exists then put the normal clear gif
        shiny_gif = await get_shiny_gif(raw_solution, self.async_session)
        if not shiny_gif:
            shiny_gif = await get_clear_gif(raw_solution, self.async_session)
        thumb  = File(shiny_gif, filename="shiny.gif")

        return embed, thumb

        
    async def create_win_embed(self, user:discord.Member, lang_id:str, raw_solution:str, stats:list):
        """
        Create embed for win. Not shiny win
        """
        # get strings
        ranks_str = self.strings.s_get('ranks', lang_id)
        it_is_str = self.strings.s_get('it_is', lang_id)
        points_str = self.strings.s_get('points', lang_id)
        # get translated description and name
        translated_description = self.descriptionDataFrame.loc[raw_solution][lang_id]
        translated_name = self.pokedexDataFrame.loc[raw_solution][lang_id]

        embed = Embed(color=self.color)
        embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar.url)
        embed.set_footer(text=ranks_str)
        embed.description = f"{user.mention} {it_is_str}** {translated_name.title()} **\n"
        embed.description += "\n" + translated_description + "\n."
        gif_file = await get_clear_gif(raw_solution, self.async_session)
        thumb = File(gif_file, filename="clear.gif")
        embed.set_thumbnail(url="attachment://clear.gif")
        #add stats
        embed.add_field(name=points_str, value=f"```{''.join(stats)}```", inline=False)

        return embed, thumb
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """
        On message routine. Here check if guess is correct
        """
        
        if message.author == self.bot.user or message.guild == None:
            return
        if message.channel.id not in self.channel_cache:
            return 

        ## => FETCH GUILD DATA FROM DATABASE
        async with self.async_session() as session:
            channelIstance = await GetChannelIstance(session, message.guild.id, message.channel.id)
            guildInfo = await GetGuildInfo(session, message.guild.id)

        ## => CHECK FOR THE CORRECT SOLUTION
        raw_solution = channelIstance.current_pokemon
        if not raw_solution or channelIstance.is_guessed:
            return
        if self.correctGuess(message.content, raw_solution, channelIstance.language):

            # Check if user is patreon
            patreon_user = await is_user_patreon(message.author.id, self.async_session)
           
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
                if patreon_user:
                    pointsToAdd = self.patreon_point_mult
                else:
                    pointsToAdd = 1
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

                ## => FETCH USER POSITION IN RANK
                stmt = text(f"""
                with point_table as (
                    select 	sum(user_points.points) as points, 
                            user_points.user_id as id
                    from user_points
                    group by user_points.user_id
                    order by points desc
                ), temp as (
                    select id, row_number() over (order by points desc) as rownum
                    from point_table
                )
                select rownum
                from temp
                where id = '{message.author.id}'""")
                result = await session.execute(stmt)
                user_rank_position = result.scalars().first()


                # Shiny win every X points
                # For patreon users the shiny rate is half
                if patreon_user:
                    shiny_win = (userGlobalPoints % (self.shiny_rate/2) == 0)
                else:
                    shiny_win = (userGlobalPoints % self.shiny_rate == 0)
                ## => STORE SHINY WIN
                if shiny_win:
                    shiny_win_entry = shinyWin(
                        guild_id=str(message.guild.id),
                        channel_id=str(message.channel.id),
                        user_id=str(message.author.id),
                        pokemon_id=channelIstance.current_pokemon,
                        time=str(datetime.utcnow())
                    )
                    session.add(shiny_win_entry)                
                await session.commit()

            ## => CREATE CORRECT GUESS EMBED ALSO SHINY
            # Get description and strings in the correct language
            language_id = await self.get_guild_lang(message.channel.id)
            t = await self.strings.get_batch(['points', 'server', 'global', 'rank_position', 'shiny'], message.channel.id)
            points_s, server_s, global_s, rank_position, shiny_s = t
            # Stats section creation
            async with self.async_session() as session:
                stmt = select(func.count(shinyWin.user_id)
                        ).group_by(shinyWin.user_id
                        ).where(shinyWin.user_id == str(message.author.id))
                result = await session.execute(stmt)
                shiny_count = result.scalars().first()

            stats = []
            stats.append(f"{server_s}: {serverWins}\n")
            stats.append(f"{global_s}: {userGlobalPoints}\n")
            stats.append(f"{shiny_s}: {shiny_count}\n")
            stats.append(f"{rank_position}: {user_rank_position}\n")
            # Create embed and send
            if shiny_win:
                embed, thumb = await self.create_shiny_embed(raw_solution, message.author, stats, language_id, shiny_count)
            else:
                embed, thumb = await self.create_win_embed(message.author, language_id, raw_solution, stats)                
            await message.channel.send(file=thumb, embed=embed)

            ## => SEND NEW QUESTION
            if channelIstance.guessing:
                file, embed = await self.createQuestion(message.guild, channel_id=channelIstance.channel_id)
                if embed:
                    await message.channel.send(file=file, embed=embed, view=FourButtons(self))
                else:
                    await message.channel.send(embed=self.embedText("No Generation selected. Use /selectgenerations"))
                
    
    @slash_command(name="start", 
                    description="Start guessing a pokémon",
                    cooldown=CooldownMapping(Cooldown(1, 30), BucketType.channel))
    @default_permissions(administrator=True)
    async def startGuess(self, ctx:discord.ApplicationContext):
        
        ## => CHECK IF ALREADY STARTED
        async with self.async_session() as session:
            channel_info = await GetChannelIstance(session, ctx.guild.id, ctx.channel.id)
            if not channel_info:
                ## => ADD CHANNEL ISTANCE  
                channel_info = botChannelIstance(guild_id = str(ctx.guild.id),
                                                    channel_id = str(ctx.channel.id),
                                                    guessing = True)
                session.add(channel_info)
                await session.commit()

            elif channel_info.guessing:
                string = await self.strings.get('start_error', ctx.channel_id)
                embed = self.embedText(string)
                await ctx.send_response(embed=embed)
                return
        
        ## => GET NEW POKEMON
        self.channel_cache[ctx.channel_id] = channel_info.language #cache the language
        file, embed = await self.createQuestion(ctx.guild, channel_id=str(ctx.channel.id))
        if embed:
            await ctx.send_response(file=file, embed=embed, view=FourButtons(self))
        else:
            await ctx.send_response(embed=self.embedText("No Generation selected. Use /selectgenerations"))
            

    @slash_command(name="stop", description="Stop guessing a pokémon")
    @default_permissions(administrator=True)
    async def stopGuess(self, ctx:discord.ApplicationContext):

        ## => UPDATE THE DB
        async with self.async_session() as session:
            thisGuild = await GetChannelIstance(session, ctx.guild.id , ctx.channel.id)
            t = await self.strings.get_batch(['stop_error', 'stop_ok'], ctx.channel_id)
            stop_error, stop_ok = t
            del self.channel_cache[ctx.channel_id] #delete channel from cache
            
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
            gif_file = await get_clear_gif(raw_solution, self.async_session)
            clearThumb = File(gif_file, filename="clear.gif")
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
    @default_permissions(administrator=True)
    async def resetrank(self, ctx):   

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
    @default_permissions(administrator=True)
    async def selectGen(self, ctx):

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
    @default_permissions(administrator=True)
    async def selectLanguage(self, ctx:discord.ApplicationContext):
        
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

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(1)
        async with self.async_session() as session:
            # Load shiny rate from the db
            stmt = select(settings)
            result = await session.execute(stmt)
            bot_settings = result.scalars().all()
            
            for setting in bot_settings:
                setting : settings
                if setting.id == 'shiny_rate':
                    self.shiny_rate = int(setting.value)
                elif setting.id == 'patreon_point_mult':
                    self.patreon_point_mult = int(setting.value)
                else:
                    self.logger.error(f"Setting {setting.id} not recognised")
            self.logger.info("settings loaded")

            

            # Load channel in local cache
            stmt = select(botChannelIstance.channel_id, botChannelIstance.language
                    ).where(botChannelIstance.guessing == True)
            result = await session.execute(stmt)
            channels = result.all()
        for channel in channels:
            self.channel_cache[int(channel.channel_id)] = channel.language
        self.logger.info('Cached channels')
     



    async def get_shiny_rank(self, channel_id) -> tuple:
        # Get ranks and format text
        ranks = await self.getShinyRank()
        # Get usernames
        username_ranks = []
        async with self.async_session() as session:
            for id,points in ranks:
                stmt = select(userPoints.username
                    ).where(userPoints.user_id == id
                    ).where(userPoints.username != None)
                result = await session.execute(stmt)
                username = result.scalars().first()
                if username:
                    username_ranks.append((username, points))

        shiny_count_str = await self.strings.get('shiny_count', str(channel_id))
        text = '\n'.join([f"#{cnt+1} {r[0]} | {shiny_count_str}: {r[1]}" for cnt, r in enumerate(username_ranks)])

        thumb = discord.File('./gifs/spinnig_star.gif', 'spinnig_star.gif')
        embed = Embed(
                    colour=self.color, 
                    title="Shiny Rank",
                    description=text
                ).set_author(
                    name=self.bot.user.display_name, 
                    icon_url=self.bot.user.avatar.url
                ).set_thumbnail(url="attachment://spinnig_star.gif")
        return embed, thumb


    @slash_command(name="shinyrank",
                    description="Global shiny leaderboard")
    async def shiny_rank(self, ctx:discord.ApplicationContext):
        embed, file = await self.get_shiny_rank(ctx.channel_id)
        await ctx.respond(embed=embed, file=file)

    @slash_command(name="shinyprofile",
                    description="List all of the Pokémon that you catched")
    async def shiny_profile(self, ctx:discord.ApplicationContext):     
        # get pokemon list from DB
        async with self.async_session() as session:
            stmt = select(shinyWin.pokemon_id
                    ).distinct(shinyWin.pokemon_id
                    ).where(shinyWin.user_id == str(ctx.author.id))
            result = await session.execute(stmt)
            pokemon_ids = result.scalars().all()
        
        # Create pages embed
        lang_id = await self.get_guild_lang(ctx.channel_id)
        paginated_pokemons = create_shiny_paginator(pokemon_ids, lang_id, self.pokedexDataFrame)
        embed_list = []
        for p in paginated_pokemons:
            embed = Embed(
                    colour=self.color, 
                    title="Shiny Profile",
                    description='\n'.join(p)
                ).set_author(
                    name=ctx.author.display_name
                )
            
            embed_list.append(embed)
        
        paginator = pages.Paginator(
                        pages=embed_list,
                        use_default_buttons=True)
        await paginator.respond(ctx.interaction, ephemeral=False)



    @commands.command(name="settings")
    async def change_setting(
        self,
        ctx:commands.Context,
        variable_name:str,
        value:str
        ):
        """Edit settings stored in the DB"""
        # Check if command author is ac2010
        if ctx.author.id != 632748792998789140:
            return

        sett_obj = settings(
            id = variable_name,
            value = value)
        try:
            # validate input params
            if variable_name == 'shiny_rate':
                self.shiny_rate = int(value)
            elif variable_name == 'patreon_point_mult':
                self.patreon_point_mult = int(value)
            else:
                raise Exception(f"Variable {variable_name} not found")
            # Update the database    
            async with self.async_session() as session:
                await session.merge(sett_obj)
                await session.commit()
            
            embed = self.embedText(f'{variable_name} set to: {value}')
        
        except Exception as e:
            embed = self.embedText(f"{e}\n**Command usage examples**:\n" + \
                                    "- settings shiny_rate 150\n" + \
                                    "- settings patreon_point_mult 3")
        
        await ctx.send(embed=embed)

