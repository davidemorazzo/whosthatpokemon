import discord
from sqlalchemy import select
from database import botGuilds

class LangButtons(discord.ui.View):
    def __init__(self, poke_cog, guild_id):
        super().__init__(timeout=60)
        self.poke_cog = poke_cog
        self.langs = poke_cog.languages
        self.add_item(Dropdown(self.poke_cog, self.langs, guild_id))


class Dropdown(discord.ui.Select):
    def __init__(self, poke_cog, langs, guild_id):
        self.poke_cog = poke_cog
        self.langs = langs
        self.guild_id = guild_id
        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label=language, value=self.langs[language])\
            for language in self.langs
        ]

        # The placeholder is what will be shown when no option is chosen
        super().__init__(
            placeholder="Choose the language...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        """
        record the selected language in the database
        """
        lang = self.values[0]
        async with self.poke_cog.async_session() as session:
            guildInfo = await session.execute(select(botGuilds).filter_by(guild_id=str(self.guild_id)))
            guildInfo = guildInfo.scalars().first()
            guildInfo.language = lang
            await session.commit()
        
        string = await self.poke_cog.strings.get('lang_ok', interaction.guild_id)
        embed = self.poke_cog.embedText(string)
        await interaction.response.edit_message(
                                    embed = embed, 
                                    view=None, 
                                    delete_after=10
                                    )