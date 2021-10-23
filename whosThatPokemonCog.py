from discord.ext import commands
from discord import Embed, File, Colour
from discord.ext.commands import Cooldown
from discord.ext.commands.cooldowns import BucketType
import sqlalchemy
from sqlalchemy.sql.expression import text
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from sqlalchemy import desc
from dotenv import load_dotenv
from random import choice, shuffle
from collections import Counter
from datetime import datetime, timedelta
import pandas as pd
from database import botGuilds, userPoints, botChannelIstance
from discord_components import Button, ButtonStyle

class guildNotActive(commands.errors.CheckFailure):
    pass

class whosThatPokemon(commands.Cog):
    def __init__(self, bot, engine, data_path):
        load_dotenv()
        self.bot = bot
        self.db_engine = engine
        self.color = Colour.red()
        self.pokemonDataFrame = pd.read_csv(data_path, index_col='name')
        self.skip_button = "⏭️"
        self.rank_button = "👑"
        self.hint_button = "❓"
        self.global_rank_button = "🌍"
        self.on_cooldown = {}

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
    
    def checkCooldownCache(self, token, cooldownSeconds):
        """Check if command is on cooldown and delete old keys"""
        
        currentTime = datetime.utcnow()
        if token in self.on_cooldown.keys():
            if self.on_cooldown[token] + timedelta(seconds=cooldownSeconds) > currentTime:
                # command still on cooldown
                retry_after = (currentTime-self.on_cooldown[token]).seconds
                cooldownObj = Cooldown(1, cooldownSeconds, BucketType.channel) 
                raise commands.errors.CommandOnCooldown(cooldownObj, retry_after)

        for key in list(self.on_cooldown.keys()):
            if self.on_cooldown[key] + timedelta(seconds=cooldownSeconds) < currentTime:
                # cooldown expired
                del self.on_cooldown[key]

        return True
            
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
    
    def getHint(self, ctx):
        ## => CREATE HINT EMBED
        with Session(self.db_engine) as session:
            thisGuild = session.query(botChannelIstance).filter_by(guild_id=str(ctx.guild.id),
                                                                    channel_id=str(ctx.channel.id)).first()
            if not thisGuild or not thisGuild.guessing:
                embed=self.embedText("You are not currently guessing pokémons, use the start command to begin!")
                return embed
            else:
                ## => SCRAMBLE THE SOLUTION
                solution = list(thisGuild.current_pokemon)
                shuffle(solution)
                scrambled = ''.join(solution).replace("-", " ")
                embed = self.embedText(f"Here's a hint: {scrambled}")
                return embed
    
    async def getRank(self, global_flag, number, guild_id):
        ## => SQL QUERY
        with Session(self.db_engine) as session:
            if global_flag:
                q = session.query(userPoints.user_id, userPoints.username, func.sum(userPoints.points).label("global_points")
                    ).group_by(userPoints.user_id, userPoints.username
                    ).order_by(desc("global_points")
                    ).limit(2*number) # fetch double of the needed users to compensate deleted accounts
                users = q.all()
            else:
                users = session.query(userPoints).filter_by(guild_id=str(guild_id)).order_by(desc(userPoints.points_from_reset)
                        ).limit(2*number).all()
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
                    if global_flag:
                        text = text + f"#{num+1} {username} | Win count: {user[2]}\n"
                    else:
                        text = text + f"#{num+1} {username} | Win count: {user.points_from_reset}\n"
                    
                    num = num + 1
                
                ## => STOP AT REQUESTED ENTRIES REACHED
                if num >= number:
                    break
        
        if text == '':
            text = '.'
        return text
    
    def addButtons(self):
        components=[[Button(style=ButtonStyle.gray, custom_id="hint_btn", emoji=self.hint_button),
                        Button(style=ButtonStyle.gray, custom_id="skip_btn", emoji=self.skip_button),
                        Button(style=ButtonStyle.gray, custom_id="local_btn", emoji=self.rank_button),
                        Button(style=ButtonStyle.gray, custom_id="global_btn", emoji=self.global_rank_button)]]

        return components 

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
    
    def getServerPrefix(self, message):
        if message.guild:
            ## => SERVER MESSAGE
            with Session(self.db_engine, expire_on_commit=False) as session:
                guildInfo = session.query(botGuilds).filter_by(guild_id=str(message.guild.id)).first()
                if guildInfo.prefix:
                    return guildInfo.prefix
                else:
                    return "wtp!"
        else:
            ## => DIRECT MESSAGE
            return "wtp!"
    
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
                                        points_from_reset = 0,
                                        username = message.author.name)
                    session.add(newUser)
                    currentUser = newUser
                ## => INCREASE POINTS
                currentUser.points = currentUser.points + 1 #global points
                currentUser.points_from_reset = currentUser.points_from_reset + 1
                currentUser.last_win_date = str(datetime.utcnow())
                currentUser.username = message.author.name
                serverWins = currentUser.points_from_reset
                ## => UPDATE USERNAME IN ALL THE USER ENTRIES
                query = sqlalchemy.text(f"update user_points set username = '{message.author.name}' where user_id='{message.author.id}'")
                connection = self.db_engine.connect()
                res = connection.execute(query)
                ## => FETCH USER GLOBALLY
                userGlobally = session.query(userPoints).filter_by(user_id=str(message.author.id)).all()
                userGlobalPoints = 0
                for entry in userGlobally:
                    userGlobalPoints += entry.points
                session.commit()

            ## => GET SERVER PREFIX
            guildPrefix = self.getServerPrefix(message)# last element should be the custom prefix, if not present it is standard prefix

            description = self.pokemonDataFrame.loc[raw_solution]['description']
            if description.strip() != "":
                ## => SEND CORRECT-GUESS MESSAGE WITH DESCRIPTION
                embed = Embed(color=self.color)
                embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
                embed.description = f"{message.author.mention} You're correct! You now have {serverWins} local wins and {userGlobalPoints} global wins!\n"
                embed.description += "\n" + description + "\n."
                embed.set_footer(text=f"You can check local and global ranks by typing:\n {guildPrefix}rank 1-30\n {guildPrefix}rank global 1-30")
                clearThumb = File(self.pokemonDataFrame.loc[raw_solution]['clear_path'], filename="clear.gif")
                embed.set_thumbnail(url="attachment://clear.gif")
                await message.channel.send(file=clearThumb, embed=embed)
            else:
                ## => SEND CORRECT-GUESS MESSAGE STANDARD
                embed = Embed(color=self.color)
                embed.set_author(name="Who's That Pokémon?", icon_url=self.bot.user.avatar_url)
                embed.description = f"Pikachu: {message.author.mention} You're correct! You now have {serverWins} local wins and {userGlobalPoints} global wins!\n"
                embed.set_footer(text=f"You can check local and global ranks by typing:\n {guildPrefix}rank 1-30\n {guildPrefix}rank global 1-30")
                pika = File("./gifs/pikachu.gif", "pikachu.gif")
                embed.set_thumbnail(url="attachment://pikachu.gif")
                await message.channel.send(file=pika, embed=embed)

            ## => SEND NEW QUESTION
            if guildInfo.guessing:
                file, embed = self.createQuestion(message.guild, channel=guildInfo.channel_id)
                await message.channel.send(file=file, embed=embed, components=self.addButtons())
                
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
        await ctx.send(file=file, embed=embed, components=self.addButtons())
            

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
        embed = self.getHint(ctx)
        await ctx.send(embed=embed)


    @commands.command(name="rank", help="Get the list of the best users. Use rank global to see the rank across every server. Specify also a limit of shown users (1-30): rank global 10")
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
                embed = self.embedText(f"Wrong command arguments. Check {ctx.prefix}help command")
                await ctx.send(embed=embed)
                return
        else:
            global_flag = False
            number = 10

        if number > 30:
            embed = self.embedText(f"Wrong command arguments. Check {ctx.prefix}help command")
            await ctx.send(embed=embed)
            return
        
        ## => GET FORMATTED LEADERBOARD
        text = await self.getRank(global_flag, number, ctx.guild.id)
                   
        ## => SEND EMBED     
        embed = Embed(color=self.color)
        embed.add_field(name=self.bot.user.name, value = text)
        thumbnail = File("./gifs/trophy.gif", "trophy.gif")
        embed.set_thumbnail(url="attachment://trophy.gif") 
        await ctx.send(embed = embed, file = thumbnail)

    @commands.command(name="skip", help="Skip this pokémon. 20 seconds of cooldown")
    async def skip(self, ctx):

        ## => CUSTOM COOLDOWN
        cooldownAmount = 20
        token = ctx.message.channel.id
        self.checkCooldownCache(token, cooldownAmount)
        message = ctx.message
        currentTime = datetime.utcnow()
        self.on_cooldown[message.channel.id] = currentTime

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

        buttons = self.addButtons()
        await ctx.send(file=file, embed=embed, components=buttons)
        
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


    @commands.Cog.listener()
    async def on_button_click(self, interaction):
        message = interaction.message
        reactionCtx = await self.bot.get_context(message)

        if interaction.custom_id=="hint_btn":
            await reactionCtx.trigger_typing()
            hint_embed = self.getHint(reactionCtx)
            await interaction.respond(embed=hint_embed, ephemeral=False)

        elif interaction.custom_id=="skip_btn":
            reactionCtx.command = self.skip
            reactionCtx.invoked_with = 'skip'
            try:
                await self.skip.invoke(reactionCtx)
                await interaction.respond(type=6)
                skipDisabledButtons = self.addButtons()
                skipDisabledButtons[0][1].set_disabled(True) # disable skip button
                await message.edit(components=skipDisabledButtons)
            except :
                await interaction.respond(embed=self.embedText("Skip command on cooldown"))

        elif interaction.custom_id=="local_btn":
            await reactionCtx.trigger_typing()
            ## => GET LOCAL LEADERBOARD
            text = await self.getRank(False, 10, message.guild.id)
            ## => SEND EMBED     
            embed = Embed(color=self.color)
            embed.add_field(name=f"Server Rank {self.rank_button} - "+self.bot.user.name, value = text)
            thumbnail = File("./gifs/trophy.gif", "trophy.gif")
            embed.set_thumbnail(url="attachment://trophy.gif")
            await interaction.send(embed=embed, file=thumbnail)

        elif interaction.custom_id=="global_btn":
            await reactionCtx.trigger_typing()
            ## => GET LOCAL LEADERBOARD
            text = await self.getRank(True, 10, message.guild.id)
            ## => SEND EMBED     
            embed = Embed(color=self.color)
            embed.add_field(name=f"Global Rank {self.global_rank_button} - "+self.bot.user.name, value = text)
            thumbnail = File("./gifs/trophy.gif", "trophy.gif")
            embed.set_thumbnail(url="attachment://trophy.gif")
            await interaction.send(embed=embed, file=thumbnail)