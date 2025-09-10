from redbot.core import Red
from redbot.core.utils import get_end_user_data_statement

from .namegenerator import NameGenerator

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


async def setup(bot: Red):
    await bot.add_cog(NameGenerator())
