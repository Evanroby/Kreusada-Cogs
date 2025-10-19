import datetime
from typing import Any, Dict, NoReturn, Optional, Union

import aiohttp
import bs4
import discord
import pycountry

try:
    import tabulate
except ModuleNotFoundError:
    tabulate = None

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import BadArgument, Cog, Context, Converter
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.views import SimpleMenu

from .menus import LabelledMenu, alpha_2_to_unicode


def square(t: str) -> str:
    return f"[{t}]"


def emojify(t: str) -> str:
    return f":{t}:"


def format_attr(t: str) -> str:
    return t.replace("_", " ").title()


EXCEPTIONS = {"russia": "ru"}
IMAGE_BASE = "https://flagpedia.net/data/flags/w580/{}.png"
INFO_BASE = "https://flagpedia.net/"
SPECIAL_IMAGES = {
    "england": {
        "url": "gb-eng",
        "emoji": "england",
    },
    "wales": {
        "url": "gb-wls",
        "emoji": "wales",
    },
    "scotland": {
        "url": "gb-sct",
        "emoji": "scotland",
    },
    "kosovo": {
        "url": "xk",
        "emoji": "flag_xk",
    },
    "palestine": {
        "url": "ps",
        "emoji": "flag_ps",
    },
}


class CountryConverter(Converter[Dict[str, Union[str, int, Dict[str, str]]]]):
    """Convert for country input"""

    async def convert(  # type: ignore[override]
        self, ctx: Context, argument: str
    ) -> Dict[str, Union[str, int, Dict[str, str]]]:
        argument = argument.lower()
        get = pycountry.countries.get

        if argument in SPECIAL_IMAGES:
            emoji = SPECIAL_IMAGES[argument]["emoji"]

            if tabulate:
                description = box(f"Emoji Information  [:{emoji}:]", lang="ini")
            else:
                description = box(f"Emoji Information: :{emoji}:", lang="yaml")

            country_name = argument.title()
            image = IMAGE_BASE.format(SPECIAL_IMAGES[argument]["url"])

            return {
                "description": description,
                "emoji": emojify(emoji),
                "name": square(country_name),
                "title": f":{emoji}: {country_name}",
                "image": image,
            }

        obj = get(name=argument) or get(alpha_2=argument)
        if not obj:
            for k, v in EXCEPTIONS.items():
                if k in argument:
                    obj = get(alpha_2=v)
                    break
            if not obj:
                raise BadArgument("Could not match %r to a country." % argument)

        ret: Dict[str, Union[str, int, Dict[str, str]]] = {
            "Name": obj.name.title(),
            "title": f":flag_{obj.alpha_2.lower()}: {obj.name}",
            "Emoji": f":flag_{obj.alpha_2.lower()}:",
            "image": IMAGE_BASE.format(obj.alpha_2.lower()),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(INFO_BASE + obj.alpha_2) as req:
                text = await req.text("utf-8")
        soup = bs4.BeautifulSoup(text, "html.parser")
        flag_content = soup.find("p", class_="flag-content")
        if flag_content and flag_content.text:
            ret["description"] = flag_content.text

        neighbours: Dict[str, str] = {}
        neighbour_list = soup.find("ul", class_="flag-grid")
        if neighbour_list:
            for li in neighbour_list.find_all("li"):
                if li.span and li.span.text and li.img and li.img.get("src"):
                    src = li.img["src"]
                    if isinstance(src, str):
                        neighbours[li.span.text] = alpha_2_to_unicode(src[16:-4])
        ret["neighbours"] = neighbours

        table = soup.find("table", class_="table-dl")
        if table and table.tbody:
            for tr in table.tbody.find_all("tr"):
                if tr.th and tr.th.text and tr.td and tr.td.text:
                    ret[tr.th.text] = tr.td.text

        return ret


class Flags(Cog):
    """Get flags from country names."""

    __version__ = "1.1.6"
    __author__ = "Kreusada"

    def __init__(self, bot: Red):
        self.bot = bot

    def format_help_for_context(self, ctx: Context) -> str:
        context = super().format_help_for_context(ctx)
        return f"{context}\n\nAuthor: {self.__author__}\nVersion: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs: Any) -> NoReturn:
        """Nothing to delete."""
        raise NotImplementedError

    @commands.has_permissions(embed_links=True)
    @commands.command()
    async def flag(
        self,
        ctx: Context,
        *,
        argument: Dict[str, Union[str, int, Dict[str, str]]] = commands.parameter(
            converter=CountryConverter
        ),
    ):
        """Get the flag for a country.

        Either the country name or alpha 2 code can be provided.

        **Examples:**

            - ``[p]flag russia``
            - ``[p]flag brazil``
            - ``[p]flag dk``
            - ``[p]flag se``
        """
        description = argument.pop("description", None)
        image = str(argument.pop("image"))
        title = str(argument.pop("title"))
        neighbours = argument.pop("neighbours", {})

        embed = discord.Embed(
            title=title,
            description=str(description) if description else None,
            color=await ctx.embed_colour(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        if not neighbours or not isinstance(neighbours, dict):
            value = "N/A"
        else:
            value = "\n".join(f"{v} {k}" for k, v in neighbours.items())
        embed.add_field(name="Neighbours", value=value, inline=False)
        embed.set_image(url=image)

        menu = LabelledMenu()
        menu.add_option("Flag Information", embed=embed, emoji="\N{WAVING WHITE FLAG}")

        embed = discord.Embed(
            title=title,
            colour=await ctx.embed_colour(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        overflow = {}
        for k, v in argument.items():
            v_str = str(v)
            if len(v_str) > 20:
                overflow[k] = v_str
            else:
                embed.add_field(name=str(k), value=v_str)

        for k, v in overflow.items():
            embed.add_field(name=str(k), value=v, inline=False)

        embed.set_thumbnail(url=image)
        menu.add_option("Country Information", embed=embed, emoji="\N{EARTH GLOBE EUROPE-AFRICA}")
        if isinstance(neighbours, dict):
            menu.set_neighbouring_countries(neighbours)
        await menu.start(ctx)

    @commands.command()
    async def flagemojis(
        self,
        ctx: commands.Context,
        *countries: str,
    ) -> None:
        """Get flag emojis for a list of countries.

        **Examples:**

            - ``[p]flagemojis qatar brazil mexico``
            - ``[p]flagemojis "solomon islands" germany``
        """
        if not countries:
            return await ctx.send_help()

        # Convert country arguments
        converter = CountryConverter()
        converted_countries = []
        for country in countries:
            try:
                result = await converter.convert(ctx, country)
                converted_countries.append(result)
            except BadArgument as e:
                await ctx.send(f"Error with {country}: {e}")
                return

        message = "\n".join(
            f"{c['Emoji']} - `{c['Emoji']}` ({c['Name']})" for c in converted_countries
        )
        for page in pagify(message):
            await ctx.send(page)

    @commands.has_permissions(embed_links=True)
    @commands.command()
    async def flags(self, ctx: commands.Context, page_number: Optional[int] = None):
        """Get a list of all the flags and their alpha 2 codes."""
        embeds = []
        message = "\n".join(
            f":flag_{c.alpha_2.lower()}: `[{c.alpha_2}]` {c.name}"  # type: ignore[union-attr]
            for c in pycountry.countries
        )
        pages = tuple(pagify(message, page_length=500))
        color = await ctx.embed_colour()
        for page in pages:
            embed = discord.Embed(
                title=f"All flags (page {pages.index(page) + 1}/{len(pages)})",
                description=page,
                color=color,
            )
            embeds.append(embed)
        if page_number is not None:
            try:
                embed = embeds[page_number - 1]
            except IndexError:
                await ctx.send(
                    f"Invalid page number provided, must be between 1 and {len(embeds)}."
                )
                return
            else:
                await ctx.send(embed=embed)
        else:
            await SimpleMenu(embeds, use_select_menu=True).start(ctx)
