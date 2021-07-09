from discord.colour import Color
from discord.ext import commands
from discord import Embed, File, Colour
from sqlalchemy.sql.expression import text
from database import botGuilds, userPoints, botChannelIstance
from sqlalchemy.orm import Session
from sqlalchemy import desc
from os import listdir
from dotenv import load_dotenv
from random import choice, shuffle
from collections import Counter
from datetime import datetime

class whosThatPokemon(commands.Cog):
    def __init__(self, bot, gif_dir, engine):
        load_dotenv()
        self.bot = bot
        self.gif_dir = gif_dir
        self.db_engine = engine
        self.color = Colour.red()
        self.gif_list = listdir(self.gif_dir)
        self.active_guessing = {}
        self.patreon_link = "https://patreon.com"
    
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
        gif_name = choice(self.gif_list)
        ## => SEND EMBED
        embed = Embed(color=self.color)
        embed.set_author(name = "Who's That Pokemon?", icon_url=self.bot.user.avatar_url)
        embed.description = "Type the name of the pokémon to guess it"
        thumb = File(self.gif_dir+gif_name, filename="gif.gif")
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
            thisGuild.current_pokemon=gif_name.replace(".gif", "")
            thisGuild.is_guessed=False
            session.commit()

        return thumb, embed

    async def cog_check(self, ctx):
        ## => CHECK ACTIVATION
        if ctx.guild:
            with Session(self.db_engine) as session:
                guildInfo = session.query(botGuilds).filter_by(guild_id=str(ctx.guild.id)).first()
                return guildInfo.activate
    
    @commands.Cog.listener()
    async def on_message(self, message):
        
        if message.author == self.bot.user:
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

            ## => SEND CORRECT-GUESS MESSAGE
            embed = Embed(color=self.color)
            embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
            embed.description = f"Pikachu: {message.author.mention} You're correct! You now have {serverWins} local wins and {userGlobalPoints} global wins!\n"
            embed.set_footer(text="You can check local and global ranks by typing:\n wtp!rank 1-50\n wtp!rank global 1-50")
            file = File("./pikachu.gif", "pikachu.gif")
            embed.set_thumbnail(url="attachment://pikachu.gif")
            await message.channel.send(file=file, embed=embed)

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
                scrambled = ''.join(solution)
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
                ## => GLOBAL USERS
                all_users = session.query(userPoints).all()
                userDict = {}
                for user in all_users:
                    if user.user_id in userDict.keys():
                       userDict[user.user_id] = userDict[user.user_id] + user.points
                    else:
                        userDict[user.user_id] = user.points 
                userList = [(key, userDict[key]) for key in userDict.keys()]
                get_points = lambda u: u[1]
                userList.sort(key=get_points, reverse=True) 
                ## => FORMAT TEXT
                for num, line in enumerate(userList):
                    user_obj = await self.bot.fetch_user(line[0])
                    text = text + f"#{num+1} {user_obj.name} | Win count: {line[1]}\n"
                    if num+1 >= number:
                        break
            else:
                ## => LOCAL USERS ORDERED BY SQL
                users = session.query(userPoints).filter_by(guild_id=str(ctx.guild.id)).order_by(desc(userPoints.points_from_reset)).all()
                ## => FORMAT TEXT
                for num, user in enumerate(users):
                    user_obj = ctx.guild.get_member(int(user.user_id))
                    if user_obj:
                        text = text + f"#{num+1} {user_obj.name} | Win count: {user.points_from_reset}\n"
                    if num > number:
                        break
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
        file, embed = self.createQuestion(ctx.guild, skip=True, channel=str(ctx.channel.id))
        if not file:
            ## => GUILD NOT GUESSING
            embed = self.embedText("Start playing with Wtp!start")
            await ctx.send(embed=embed)
            return
        await ctx.send(file=file, embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot connected")

    @commands.command(name="resetrank", help="Reset to zero the wins of the players of this server. Global points will be preserved. Only administrator")
    async def resetrank(self, ctx):
        if not ctx.message.author.guild_permissions.administrator:
            ## => NOT ADMINISTRATOR
            embed = self.embedText("You need to be administrator to run this command")
            await ctx.send(embed=embed)
            return    
        
        ## => POINTS_FROM_RESET TO 0 IN THE DB
        with Session(self.db_engine) as session:
            guildPlayers = session.query(userPoints).filter_by(guild_id = str(ctx.guild.id)).all()
            for player in guildPlayers:
                player.points_from_reset = 0
            session.commit()
        embed = self.embedText("Local ranks reset succesful!")
        await ctx.send(embed=embed)