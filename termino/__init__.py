from redbot.core.bot import Red
from redbot.core.utils import get_end_user_data_statement

from .termino import Termino

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


async def setup(bot: Red):
    global OLD_SHUTDOWN_COMMAND
    global OLD_RESTART_COMMAND
    OLD_SHUTDOWN_COMMAND = bot.remove_command("shutdown")
    OLD_RESTART_COMMAND = bot.remove_command("restart")
    await bot.add_cog(Termino(bot))
