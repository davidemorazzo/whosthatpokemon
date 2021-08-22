from discord.colour import Color
from discord.ext import commands
from discord import Embed, File, Colour
from sqlalchemy.sql.expression import text
from sqlalchemy.sql import func
from database import botGuilds, userPoints, botChannelIstance
from sqlalchemy.orm import Session
from sqlalchemy import desc
from os import listdir
from dotenv import load_dotenv
from random import choice, shuffle
from collections import Counter
from datetime import datetime
import pandas as pd

class guildNotActive(commands.errors.CheckFailure):
    pass

class whosThatPokemon(commands.Cog):
    def __init__(self, bot, engine, data_path):
        load_dotenv()
        self.bot = bot
        self.db_engine = engine
        self.color = Colour.red()
        self.pokemonDataFrame = pd.read_csv(data_path, index_col='name')
    
    def embedText(self, text):
        text = text.replace('"', '\"').replace("'", "\'")
        return Embed(description=f"**{text}**", color=self.color)

    def correctGuess(self, guess:str, solution:str) -> bool:
        compare = lambda x, y: Counter(x)==Counter(y)
        ## => DECIDE IF THE GUESS IS CORRECT
        guess = guess.lower().strip()
        wordSolution = solution.split('-')
        guess = guess.replace('-o', ' o') # fix kommo-o ...
        wordGuess = guess.split(' ')
        
        ## => REPLACE IDENTIFIERS
        if "y" in wordGuess and "mega" in wordGuess:
            wordGuess.remove("mega")
            wordGuess.remove("y")
            wordGuess.append("megay")
        if "x" in wordGuess and "mega" in wordGuess:
            wordGuess.remove("mega")
            wordGuess.remove("x")
            wordGuess.append("megax")
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
        return compare(wordSolution, wordGuess)
            
    def createQuestion(self, guild, skip=False, channel=None):
        gif_name = choice(self.pokemonDataFrame.index)
        ## => SEND EMBED
        embed = Embed(color=self.color)
        embed.set_author(name = "Who's That Pokemon?", icon_url=self.bot.user.avatar_url)
        embed.description = "Type the name of the pokémon to guess it"
        thumb = File(self.pokemonDataFrame.loc[gif_name]['blacked_path'], filename="gif.gif")
        embed.set_thumbnail(url="attachment://gif.gif")
        # embed.set_footer(text="DEBUG ONLY: "+gif_name)
        
        ## => MEMORIZE THE SOLUTION
        with Session(self.db_engine) as session:
            thisGuild = session.query(botChannelIstance).filter_by(guild_id=str(guild.id), 
                                                                    channel_id=str(channel)).first()
            if not thisGuild:
                return None, None
            if skip and thisGuild.guessing == False:
                return None, None
            thisGuild.guessing = True
            thisGuild.current_pokemon=gif_name
            thisGuild.is_guessed=False
            session.commit()

        return thumb, embed

    async def cog_check(self, ctx):
        ## => CHECK ACTIVATION
        if ctx.guild:
            with Session(self.db_engine) as session:
                guildInfo = session.query(botGuilds).filter_by(guild_id=str(ctx.guild.id)).first()
                if not guildInfo:
                    newGuild = botGuilds(guild_id=str(ctx.guild.id),
                                    joined_utc=str(datetime.utcnow()),
                                    currently_joined = True,
                                    activate=True)
                    session.add(newGuild)
                    session.commit()
                    guildInfo = newGuild
                if guildInfo.activate:
                    return True
                else:
                    raise guildNotActive(guildInfo.guild_id)
    
    async def only_admin(ctx):
        if ctx.message.author.guild_permissions.administrator:
            return True
        raise commands.errors.NotOwner("Only administrator can run this command")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        
        if message.author == self.bot.user or message.guild == None:
            return

        ## => FETCH GUILD DATA FROM DATABASE
        with Session(self.db_engine) as session:
            guildInfo = session.query(botChannelIstance).filter_by(guild_id=str(message.guild.id), channel_id=str(message.channel.id)).first()
            if not guildInfo:
                return
            guildActivation = session.query(botGuilds).filter_by(guild_id=str(message.guild.id)).first()
            if not guildActivation.activate:
                return

        ## => CHECK FOR THE CORRECT SOLUTION
        raw_solution = guildInfo.current_pokemon
        if not raw_solution or guildInfo.is_guessed:
            return
        if self.correctGuess(message.content, raw_solution):
           
            ## => DB OPERATIONS
            with Session(self.db_engine, expire_on_commit=False) as session:
                ## => UPDATE GUILD STATUS
                guildInfo = session.query(botChannelIstance).filter_by(guild_id=str(message.guild.id),
                                                                        channel_id=str(message.channel.id)).first()
                guildInfo.is_guessed = True
                session.commit()
                ## => FETCH USER
                currentUser = session.query(userPoints).filter_by(guild_id=str(message.guild.id), user_id=str(message.author.id)).first()
                if not currentUser:
                    ## => USER NOT FOUNDED -> ADD IT TO DATABASE
                    newUser = userPoints(user_id = str(message.author.id), 
                                        guild_id=str(message.guild.id),
                                        points=0,
                                        points_from_reset = 0)
                    session.add(newUser)
                    currentUser = newUser
                ## => INCREASE POINTS
                currentUser.points = currentUser.points + 1 #global points
                currentUser.points_from_reset = currentUser.points_from_reset + 1
                currentUser.last_win_date = str(datetime.utcnow())
                serverWins = currentUser.points_from_reset
                ## => FETCH USER GLOBALLY
                userGlobally = session.query(userPoints).filter_by(user_id=str(message.author.id)).all()
                userGlobalPoints = 0
                for entry in userGlobally:
                    userGlobalPoints += entry.points
                session.commit()
            # 
            # ## => CREATE DESCRIPTION AND CLEAR GIF EMBED
            # clearEmbed = Embed(color=self.color)
            # clearEmbed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
            # description = self.pokemonDataFrame.loc[raw_solution]['description']
            # clearEmbed.description = description
            # clearThumb = File(self.pokemonDataFrame.loc[raw_solution]['clear_path'], filename="clear.png")
            # clearEmbed.set_thumbnail(url="attachment://clear.png")
            # await message.channel.send(file=clearThumb, embed=clearEmbed)
            # 
            # ## => SEND CORRECT-GUESS MESSAGE
            # embed = Embed(color=self.color)
            # embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
            # embed.description = f"Pikachu: {message.author.mention} You're correct! You now have {serverWins} local wins and {userGlobalPoints} global wins!\n"
            # embed.set_footer(text="You can check local and global ranks by typing:\n wtp!rank 1-50\n wtp!rank global 1-50")
            # pika = File("./pikachu.gif", "pikachu.gif")
            # embed.set_thumbnail(url="attachment://pikachu.gif")
            # await message.channel.send(file=pika, embed=embed)

            description = self.pokemonDataFrame.loc[raw_solution]['description']
            if description.strip() != "":
                ## => SEND CORRECT-GUESS MESSAGE WITH DESCRIPTION
                embed = Embed(color=self.color)
                embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
                embed.description = f"{message.author.mention} You're correct! You now have {serverWins} local wins and {userGlobalPoints} global wins!\n"
                embed.description += "\n" + description + "\n."
                embed.set_footer(text="You can check local and global ranks by typing:\n wtp!rank 1-50\n wtp!rank global 1-50")
                clearThumb = File(self.pokemonDataFrame.loc[raw_solution]['clear_path'], filename="clear.gif")
                embed.set_thumbnail(url="attachment://clear.gif")
                await message.channel.send(file=clearThumb, embed=embed)
            else:
                ## => SEND CORRECT-GUESS MESSAGE STANDARD
                embed = Embed(color=self.color)
                embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
                embed.description = f"Pikachu: {message.author.mention} You're correct! You now have {serverWins} local wins and {userGlobalPoints} global wins!\n"
                embed.set_footer(text="You can check local and global ranks by typing:\n wtp!rank 1-50\n wtp!rank global 1-50")
                pika = File("./pikachu.gif", "pikachu.gif")
                embed.set_thumbnail(url="attachment://pikachu.gif")
                await message.channel.send(file=pika, embed=embed)

            ## => SEND NEW QUESTION
            if guildInfo.guessing:
                file, embed = self.createQuestion(message.guild, channel=guildInfo.channel_id)
                await message.channel.send(file=file, embed=embed)
                
        # await self.bot.process_commands(message)
    
    @commands.command(name="start", help="Start guessing a pokémon")
    async def startGuess(self, ctx):
        ## => CHECK IF ALREADY STARTED
        with Session(self.db_engine, expire_on_commit=False) as session:
            guildInfo = session.query(botChannelIstance).filter_by(guild_id=str(ctx.guild.id),
                                                                    channel_id = str(ctx.channel.id)).first()
            if not guildInfo:
                ## => ADD CHANNEL ISTANCE  
                channelIstance = botChannelIstance(guild_id = str(ctx.guild.id),
                                                    channel_id = str(ctx.channel.id),
                                                    guessing = True)
                session.add(channelIstance)
                session.commit()

            elif guildInfo.guessing:
                embed = self.embedText("The game is already started! To skip this pokémon use wtp!skip")
                await ctx.send(embed=embed)
                return
        
        ## => GET NEW POKEMON
        file, embed = self.createQuestion(ctx.guild, channel=str(ctx.channel.id))
        await ctx.send(file=file, embed=embed)
            

    @commands.command(name="stop", help="Stop guessing a pokémon")
    async def stopGuess(self, ctx):
        ## => UPDATE THE DB
        with Session(self.db_engine) as session:
            thisGuild = session.query(botChannelIstance).filter_by(guild_id=str(ctx.guild.id),
                                                                    channel_id=str(ctx.channel.id)).first()
            if not thisGuild:
                embed = self.embedText("The game is not running on this channel, to start use wtp!start")
            else:
                thisGuild.guessing = False
                session.commit()
                embed = self.embedText("Guessing has been stopped! To resume the game use the start command")
        await ctx.send(embed=embed)


    @commands.command(name="hint", help="Hint for guessing the current pokémon")
    async def hint(self, ctx):
        with Session(self.db_engine) as session:
            thisGuild = session.query(botChannelIstance).filter_by(guild_id=str(ctx.guild.id),
                                                                    channel_id=str(ctx.channel.id)).first()
            if not thisGuild:
                await ctx.send(embed=self.embedText("You are not currently guessing pokémons, use the start command to begin!"))
            elif thisGuild.guessing:
                ## => SCRAMBLE THE SOLUTION
                solution = list(thisGuild.current_pokemon)
                shuffle(solution)
                scrambled = ''.join(solution).replace("-", " ")
                await ctx.send(embed = self.embedText(f"Here's a hint: {scrambled}"))


    @commands.command(name="rank", help="Get the list of the best users. Use rank global to see the rank across every server. Specify also a limit of shown users (1-50): rank global 10")
    async def rank(self, ctx, *, args=None):
        await ctx.trigger_typing()
        ## => PARSE ARGUMENTS
        if args:
            global_flag = "global" in args
            words = args.split(' ')
            try:
                if len(words) == 2 and global_flag:
                    number = int(words[1])
                elif len(words) == 1 and not global_flag:
                    number = int(words[0])
                else:
                    ## => DEFAULT CASEs
                    number = 10
            except :
                return
        else:
            global_flag = False
            number = 10

        if number > 50:
            return

        ## => GET DATA FROM DATABASE
        text = ''
        with Session(self.db_engine) as session:
            if global_flag:
                ## => GLOBAL RANKS FROM SQL
                q = session.query(userPoints.user_id, func.sum(userPoints.points).label("global_points"))
                q = q.group_by(userPoints.user_id
                    ).order_by(desc("global_points")
                    ).limit(number)
                userList = q.all()
                ## => FORMAT TEXT
                for num, line in enumerate(userList):
                    user_obj = self.bot.get_user(int(line[0]))
                    if not user_obj:
                        try:
                            user_obj = await self.bot.fetch_user(line[0])
                        except :
                            user_obj = None
                    if user_obj:
                        text = text + f"#{num+1} {user_obj.name} | Win count: {line[1]}\n"
            else:
                ## => LOCAL USERS ORDERED BY SQL
                users = session.query(userPoints).filter_by(guild_id=str(ctx.guild.id)).order_by(desc(userPoints.points_from_reset)
                        ).limit(number).all()
                ## => FORMAT TEXT
                for num, user in enumerate(users):
                    user_obj = ctx.guild.get_member(int(user.user_id))
                    if user_obj:
                        text = text + f"#{num+1} {user_obj.name} | Win count: {user.points_from_reset}\n"

        if text == '':
            text = '.'       
        ## => SEND EMBED     
        embed = Embed(color=self.color)
        embed.add_field(name=self.bot.user.name, value = text)
        thumbnail = File("./trophy.gif", "trophy.gif")
        embed.set_thumbnail(url="attachment://trophy.gif") 
        await ctx.send(embed = embed, file = thumbnail)

    @commands.cooldown(1, 20, commands.BucketType.channel)
    @commands.command(name="skip", help="Skip this pokémon. 20 seconds of cooldown")
    async def skip(self, ctx):
        ## => SEND PREVIOUS SOLUTION
        with Session(self.db_engine) as session:
            channelIstance = session.query(botChannelIstance).filter_by(guild_id=str(ctx.guild.id), channel_id=str(ctx.channel.id)).first()
            raw_solution = channelIstance.current_pokemon
        description = self.pokemonDataFrame.loc[raw_solution]['description']
        if description.strip() != "":
            clearEmbed = Embed(color=self.color)
            clearEmbed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
            clearEmbed.description = description
            clearThumb = File(self.pokemonDataFrame.loc[raw_solution]['clear_path'], filename="clear.gif")
            # clearThumb = File("D:\\Programmazione\\Fiverr\\andychand400 v2\\gif script\\ezgif.com-gif-maker.webp", filename="clear.webp")
            clearEmbed.set_thumbnail(url="attachment://clear.gif")
            await ctx.send(file=clearThumb, embed=clearEmbed)

        file, embed = self.createQuestion(ctx.guild, skip=True, channel=str(ctx.channel.id))
        if not file:
            ## => GUILD NOT GUESSING
            embed = self.embedText("Start playing with Wtp!start")
            await ctx.send(embed=embed)
            return
        await ctx.send(file=file, embed=embed)

    @commands.command(name="resetrank", help="Reset to zero the wins of the players of this server. Global points will be preserved. Only administrator")
    @commands.check(only_admin)
    async def resetrank(self, ctx):      
        ## => POINTS_FROM_RESET TO 0 IN THE DB
        with Session(self.db_engine) as session:
            guildPlayers = session.query(userPoints).filter_by(guild_id = str(ctx.guild.id)).all()
            for player in guildPlayers:
                player.points_from_reset = 0
            session.commit()
        embed = self.embedText("Local ranks reset succesful!")
        await ctx.send(embed=embed)

    @commands.command(name="prefix", help="Change the prefix of the bot. Admin only. Example: wtp!prefix ? ")
    @commands.check(only_admin)
    async def changePrefix(self, ctx, prefix:str): 
        ## => CHECK PREFIX
        if len(prefix.split(" ")) != 1 or '\"' in prefix or "\'" in prefix:
            embed = self.embedText(f"Prefix not valid")
            await ctx.send(embed=embed)
            return
        ## => CHANGE THE PREFIX IN THE DATABASE
        with Session(self.db_engine) as session:
            guildInfo = session.query(botGuilds).filter_by(guild_id=str(ctx.guild.id)).first()
            guildInfo.prefix = prefix
            session.commit()
        
        embed = self.embedText(f"Prefix changed to {prefix}")
        await ctx.send(embed=embed)



    