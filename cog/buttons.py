import discord

class FourButtons(discord.ui.View):
    def __init__(self, poke_cog):
        super().__init__()
        self.poke_cog = poke_cog
        self.skip_button = "⏭️"
        self.rank_button = "👑"
        self.hint_button = "❓"
        self.global_rank_button = "🌍"
        self.logger = self.poke_cog.logger
        # TODO: da finire

    async def on_cooldown(self, btn_name:str, interaction:discord.Interaction)->bool:
        if self.poke_cog.cooldown.is_on_cooldown(interaction.message.id, 
                                                btn_name, 60):
            self.logger.debug(f"{interaction.message.id}/{interaction.custom_id} on cooldown")
            await interaction.response.send_message(embed=self.poke_cog.embedText("Button on cooldown"), ephemeral=True)
            return True
        return False


    # define buttons
    @discord.ui.button(label="hint", 
                        style=discord.ButtonStyle.grey,
                        emoji='❓')
    async def hint_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'hint_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
        
        hint_embed = await self.poke_cog.getHint(interaction.guild_id, 
                                                interaction.channel_id)
        await interaction.response.send_message(embed=hint_embed, ephemeral=False)
        self.poke_cog.cooldown.add_cooldown(interaction.message.id, id)

    @discord.ui.button(label="skip", 
                style=discord.ButtonStyle.grey,
                emoji='⏭️')
    async def skip_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'skip_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
        
        msg = interaction.message
        ctx = await self.poke_cog.bot.get_context(msg)
        ctx.command = self.poke_cog.skip
        ctx.invoked_with = 'skip'
        try:
            await self.poke_cog.skip.invoke(ctx)
            btn.disabled = True
            await interaction.response.edit_message(view=self)
        except :
            await interaction.response.send_message(embed=self.embedText("Skip command on cooldown"))
        self.poke_cog.cooldown.add_cooldown(interaction.message.id, id)

    @discord.ui.button(label="Local Rank", 
                style=discord.ButtonStyle.grey,
                emoji = '👑')
    async def local_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'local_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
            
        message = interaction.message
        text = await self.poke_cog.getRank(False, 20, message.guild.id)
        ## => SEND EMBED     
        embed = discord.Embed(color=self.poke_cog.color)
        embed.set_author(name=self.poke_cog.bot.user.name)
        embed.add_field(name=f"Server Rank {self.rank_button}", value = text)
        thumbnail = discord.File("./gifs/trophy.gif", "trophy.gif")
        embed.set_thumbnail(url="attachment://trophy.gif")
        await interaction.response.send_message(embed=embed, file=thumbnail, ephemeral=False)
        self.poke_cog.cooldown.add_cooldown(interaction.message.id, id)


    @discord.ui.button(label="Global Rank", 
                style=discord.ButtonStyle.grey,
                emoji = '🌍')
    async def global_btn(self, btn:discord.ui.Button, interaction:discord.Interaction):
        id = 'global_btn'
        cldwn = await self.on_cooldown(id, interaction)
        if cldwn:
            return
        
        await interaction.response.defer()
        message = interaction.message
        text = await self.poke_cog.getRank(True, 20, message.guild.id)
        ## => SEND EMBED     
        embed = discord.Embed(color=self.poke_cog.color)
        embed.set_author(name=self.poke_cog.bot.user.name)
        embed.add_field(name=f"Global Rank {self.global_rank_button}", value = text)
        thumbnail = discord.File("./gifs/globe.gif", "trophy.gif")
        embed.set_thumbnail(url="attachment://trophy.gif")
        await interaction.followup.send(embed=embed, file=thumbnail, ephemeral=False)
        self.poke_cog.cooldown.add_cooldown(interaction.message.id, id)
