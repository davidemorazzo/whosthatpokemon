import discord
from sqlalchemy import select
from database import botChannelIstance, botGuilds

class LangButtons(discord.ui.View):
    def __init__(self, poke_cog, guild_id, lang_id:str):
        super().__init__(timeout=None)
        self.poke_cog = poke_cog
        self.langs = poke_cog.languages
        self.add_item(Dropdown(self.poke_cog, self.langs, guild_id, lang_id))


class Dropdown(discord.ui.Select):
    def __init__(self, poke_cog, langs, guild_id, lang_id:str):
        self.poke_cog = poke_cog
        self.langs = langs
        self.lang_id = lang_id
        self.guild_id = guild_id
        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label=language, value=self.langs[language])\
            for language in self.langs
        ]

        string = self.poke_cog.strings.s_get('lang_btn', lang_id)
        super().__init__(
            placeholder=string,
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
            guildInfo = await session.execute(select(botChannelIstance).filter_by(channel_id=str(interaction.channel.id)))
            guildInfo = guildInfo.scalars().first()
            guildInfo.language = lang
            await session.commit()
        
        string = self.poke_cog.strings.s_get('lang_ok', lang)
        embed = self.poke_cog.embedText(string)
        await interaction.response.edit_message(
                                    embed = embed, 
                                    view=None, 
                                    delete_after=10
                                    )