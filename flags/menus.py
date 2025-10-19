import unicodedata
from typing import Optional

import discord
from redbot.core.commands import Context


def alpha_2_to_unicode(alpha_2: str) -> str:
    """Convert an alpha-2 country code to Unicode flag emoji."""
    return "".join(
        unicodedata.lookup("REGIONAL INDICATOR SYMBOL LETTER " + a.upper()) for a in alpha_2
    )


class LabelledMenuSelect(discord.ui.Select):
    def __init__(self, neighbours: dict[str, str]):
        options = [discord.SelectOption(label=k, emoji=v) for k, v in neighbours.items()]
        super().__init__(placeholder="Neighbouring countries", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await interaction.response.send_message(
            f"Get information about {self.values[0]} with the command `{self.view.context.clean_prefix}flag {self.values[0]}`!",
            ephemeral=True,
        )


class LabelledMenuButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        self.grey_all_buttons()
        self.style = discord.ButtonStyle.green
        await interaction.response.edit_message(
            view=self.view, **self.view.options[self.label]["kwargs"]
        )

    def grey_all_buttons(self):
        assert self.view is not None
        for button in self.view.children:
            if isinstance(button, LabelledMenuButton):
                button.style = discord.ButtonStyle.grey


class LabelledMenu(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.context: Optional[Context] = None
        self.options: dict[str, dict] = {}
        self.select: Optional[discord.ui.Select] = None
        self.__insertion_order: list[str] = []
        self.message: Optional[discord.Message] = None

    def add_option(
        self,
        label: str,
        /,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        emoji: Optional[str] = None,
    ):
        self.options[label] = {
            "emoji": emoji,
            "kwargs": {"embed": embed, "content": content},
        }
        self.__insertion_order.append(label)
        self.add_item(LabelledMenuButton(label=label, emoji=emoji, row=2))

    def set_neighbouring_countries(self, neighbours: dict[str, str]):
        if not neighbours:
            return
        self.add_item(LabelledMenuSelect(neighbours))

    async def start(self, ctx: Context):
        self.context = ctx
        first_child = self.children[0]
        if isinstance(first_child, LabelledMenuButton):
            first_child.style = discord.ButtonStyle.green
        self.message = await ctx.send(
            **self.options[self.__insertion_order[0]]["kwargs"], view=self
        )

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction):
        if self.context is None:
            return False
        if interaction.user.id != self.context.author.id:
            await interaction.response.send_message(
                "You are not allowed to interact with this.", ephemeral=True
            )
            return False
        return True
