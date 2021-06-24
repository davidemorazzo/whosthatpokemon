from discord.ext import commands, tasks
from database import patreonUsers, botGuilds
from sqlalchemy.orm import Session
from sqlalchemy import insert, update
from datetime import datetime, timedelta
from dateutil import parser
from discord import Embed, Colour

class guildsAuthCog(commands.Cog):
    def __init__(self, bot, patreonKey, patreonCreatorId, engine):
        self.patreonKey = patreonKey
        self.patreonCreatorId = patreonCreatorId
        self.bot = bot
        self.db_engine = engine
        self.trial_days = 30
        self.color = Colour.orange()
        # await self.verification().start()
        self.patreon_link = "https://patreon.com"

    def verifyPatreon(self, guild_id) -> bool:
        ## => ASSIGN TO THE GUILD THE CORRECT PATREON
        #TODO: da fare
        pass

    def updatePatreons(self):
        ## => UPDATE DATABASE FROM PATREON API
        # TODO: da fare
        pass

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

    @tasks.loop(minutes=5)
    async def verification(self):
        print("Start verification")
        ## => UPDATE PATREONS
        self.updatePatreons()
        
        ## => VERIFY EVERY GUILD
        with Session(self.db_engine) as session:
            guilds = session.query(botGuilds).all()
            for guild in guilds:
                if guild.currently_joined:
                    patreonStatus = self.verifyPatreon(guild.id)
                    if not patreonStatus:
                        ## => CHECK FOR TRIAL PERIOD
                        now = datetime.utcnow()
                        joined = parser.parse(guild.joined_utc)
                        if now-joined > timedelta(days=self.trial_days):
                            guild.activate = False
        
        session.commit()

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
        if trial_flag:
            embed.set_footer(text=f"ACTIVATION: {days_left} days left before trial period will end. To keep using the bot please subscribe to our patreon! {self.patreon_link}")
        if guildInfo.activate == False:
            embed.set_footer(text="ACTIVATION: the bot is not activated. To activate the bot please subscribe to our patreon! {self.patreon_link}")
        if guildInfo.patreon_discord_id != None:
            embed.set_footer(text="ACTIVATION: the bot is activated from patreon subscription")

        # If there are no arguments, just list the commands:
        for i,x in enumerate(self.bot.commands):
            embed.add_field(
                name=x.name+' '+x.signature ,
                value=x.help,
                inline=False
            )
        bot_msg = await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            embed = self.embedText(f"Trial period has expired! To gain full access to the bot please activate the bot using this link {self.patreon_link}")
            await ctx.send(embed = embed)
            print("GUILD WITHOUT PERMISSION DENIED: ", ctx.guild.name)
        else:
            print(error)

