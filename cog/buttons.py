import discord

class FourButtons(discord.ui.View):
    def __init__(self, poke_cog):
        super().__init__(timeout=None)
        self.poke_cog = poke_cog
        self.skip_button = "⏭️"
        self.rank_button = "👑"
        self.hint_button = "❓"
        self.global_rank_button = "🌍"
        self.logger = self.poke_cog.logger
        self.string_db = self.poke_cog.strings

    async def on_cooldown(self, btn_name:str, interaction:discord.Interaction)->bool:
        # Check cooldown for spicific messages or for the channel
        if self.poke_cog.cooldown.is_on_cooldown(interaction.channel_id,
                                                btn_name,
                                                30):
            self.logger.debug(f"{interaction.message.id}/{interaction.custom_id} on cooldown")
            string = await self.string_db.get('btn_cooldown', interaction.channel_id)
            await interaction.response.send_message(embed=self.poke_cog.embedText(string), ephemeral=True)
            return True
        return False


    # define buttons
    @discord.ui.button(style=discord.ButtonStyle.grey,
                        emoji='❓')
    async def hint_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'hint_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
        
        hint_embed = await self.poke_cog.getHint(interaction.guild_id, 
                                                interaction.channel_id)
        await interaction.response.send_message(embed=hint_embed, ephemeral=False)
        self.poke_cog.cooldown.add_cooldown(interaction.channel_id, id)

    @discord.ui.button(style=discord.ButtonStyle.grey,
                emoji='⏭️')
    async def skip_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'skip_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
        
        # Send prev. solution
        solution_embed, clear_thumb = await self.poke_cog.solution_embed(interaction.guild_id, interaction.channel_id)
        if solution_embed:
            await interaction.response.send_message(file=clear_thumb, embed=solution_embed)
        file, embed = await self.poke_cog.createQuestion(interaction.guild,
                            skip=True,
                            channel_id=str(interaction.channel_id))
        if not file:
            ## => GUILD NOT GUESSING
            string = await self.string_db.get('skip_error', interaction.channel_id)
            embed = self.embedText(string)
            await interaction.follow(embed=embed)
            return
        await interaction.followup.send(file=file, embed=embed, view=FourButtons(self.poke_cog))
        # Start cooldown
        self.poke_cog.cooldown.add_cooldown(interaction.channel_id, id)

    @discord.ui.button(style=discord.ButtonStyle.grey,
                emoji = '👑')
    async def local_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'local_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
            
        message = interaction.message
        text = await self.poke_cog.getRank(False, 20, message.guild.id, message.channel.id)
        ## => SEND EMBED     
        embed = discord.Embed(color=self.poke_cog.color)
        embed.set_author(name=self.poke_cog.bot.user.name)
        string = await self.string_db.get('server_rank', interaction.channel_id)
        embed.add_field(name=f"{string} {self.rank_button}", value = text)
        thumbnail = discord.File("./gifs/trophy.gif", "trophy.gif")
        embed.set_thumbnail(url="attachment://trophy.gif")
        await interaction.response.send_message(embed=embed, file=thumbnail, ephemeral=False)
        self.poke_cog.cooldown.add_cooldown(interaction.channel_id, id)


    @discord.ui.button(style=discord.ButtonStyle.grey,
                emoji = '🌍')
    async def global_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'global_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
        
        await interaction.response.defer()
        message = interaction.message
        text = await self.poke_cog.getRank(True, 20, message.guild.id, message.channel.id)
        ## => SEND EMBED     
        embed = discord.Embed(color=self.poke_cog.color)
        embed.set_author(name=self.poke_cog.bot.user.name)
        string = await self.string_db.get('global_rank', interaction.channel_id)
        embed.add_field(name=f"{string} {self.global_rank_button}", value = text)
        thumbnail = discord.File("./gifs/globe.gif", "trophy.gif")
        embed.set_thumbnail(url="attachment://trophy.gif")
        await interaction.followup.send(embed=embed, file=thumbnail, ephemeral=False)
        self.poke_cog.cooldown.add_cooldown(interaction.channel_id, id)

    
    @discord.ui.button(style=discord.ButtonStyle.grey,
                emoji = '✨')
    async def shiny_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        """
        Get shiny cathes rank
        """
        id = 'shiny_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return

        await interaction.response.defer()
        rank = await self.poke_cog.getShinyRank()
        # Create text
        text = '\n'.join([f"<@{u[0]}> | {u[1]}" for u in rank])
        ## => SEND EMBED
        embed = discord.Embed(color=self.poke_cog.color)
        embed.set_author(name=self.poke_cog.bot.user.name)
        string = await self.string_db.get('shiny_rank', interaction.channel_id)
        embed.add_field(name=f"{string} ✨", value = text)
        thumbnail = discord.File("./gifs/spinning_star.gif", "spinning_star.gif")
        embed.set_thumbnail(url="attachment://spinning_star.gif")
        await interaction.followup.send(embed=embed, file=thumbnail, ephemeral=False)
        self.poke_cog.cooldown.add_cooldown(interaction.channel_id, id)
        