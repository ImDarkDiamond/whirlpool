from operator import mod
from discord.ext import commands, menus
from discord.ext.commands.core import command
from utilities import cache, checks
import discord
import textwrap
import datetime
import traceback
import modlog_utils
import mod_cache


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.mod_role_or_perms(kick_members=True)
    async def strike(self, ctx, strikes: int, users: commands.Greedy[discord.Member], *, reason: str = None) -> None:
        
        if strikes < 1:
            return await ctx.send("Amount of strikes must be above **1**")

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                       VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                       DO UPDATE SET strikes = guild_strikes.strikes + $3
                       RETURNING *
                    """
        
            update = await self.bot.pool.fetchrow(query, ctx.guild.id, user.id, strikes)

            if channel:
                try:
                    message = await modlog_utils.assemble_message(
                        "strike_add",
                        ctx=ctx,
                        strikes_removed=None,
                        strikes_added=strikes,
                        strikes={'old':update['strikes']-strikes,'new':update['strikes']},
                        reason=reason,

                        mod=ctx.author,
                        user=user
                    )

                    await channel.send(message)
                except:
                    pass

            final_string += f"Gave `{strikes}` strikes to **{user.name}**#{user.discriminator} for a total of `{update['strikes']}` strikes ({update['strikes']-strikes} → {update['strikes']})\n"

        await ctx.send(final_string)

def setup(bot):
    bot.add_cog(Mod(bot))