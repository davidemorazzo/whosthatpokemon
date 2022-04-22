import discord
from sqlalchemy import select
from database import botGuilds

class GenButtons(discord.ui.View):
    def __init__(self, poke_cog, active_gens, guild_id, lang_id:str):
        super().__init__(timeout=60)
        self.poke_cog = poke_cog
        self.string_db = poke_cog.strings
        self.active_gens = active_gens
        self.add_item(Dropdown(self.poke_cog, active_gens, guild_id, lang_id))


class Dropdown(discord.ui.Select):
    def __init__(self, poke_cog, active_gens, guild_id, lang_id:str):
        self.poke_cog = poke_cog
        self.active_gens = active_gens
        self.guild_id = guild_id
        # Set the options that will be presented inside the dropdown
        generations = list(self.poke_cog.pokemonGenerations.keys())
        options = [
            discord.SelectOption(label=gen, value=self.poke_cog.pokemonGenerations[gen])\
            for gen in generations
        ]

        for o in options:
            if self.poke_cog.pokemonGenerations[o.label] in active_gens:
                o.default = True

        # Get strings
        string = self.poke_cog.strings.s_get('generation_select', lang_id)
        super().__init__(
            placeholder=string,
            min_values=1,
            max_values=len(generations),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        """
        record the selected generations in the database
        """
        selection_string = ''.join(self.values)
        async with self.poke_cog.async_session() as session:
            guildInfo = await session.execute(select(botGuilds).filter_by(guild_id=str(self.guild_id)))
            guildInfo = guildInfo.scalars().first()
            guildInfo.poke_generation = selection_string
            await session.commit()
        
        string = await self.poke_cog.strings.get('generation_ok', self.guild_id)
        embed = self.poke_cog.embedText(string)
        await interaction.response.edit_message(
                                    embed = embed, 
                                    view=None, 
                                    delete_after=10
                                    )