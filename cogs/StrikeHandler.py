from operator import mod
import typing
from discord.ext import commands, menus
from utilities import cache, checks, StrikeSwitcher
import discord
import textwrap
import datetime
import traceback
import modlog_utils
import mod_cache


class StrikeHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_strike_add(self, ctx, user: typing.Union[discord.Member,discord.User], strikes, **kwargs):
        StrikeHandler2 = StrikeSwitcher.Strikes(ctx, user)
        await StrikeHandler2.fill_cache()

        config = await mod_cache.get_guild_config(self.bot,ctx.guild.id)
        channel = config and config.mod_logs
        mute_role = config and config.mute_role

        async def send_modlog(action: str, reason: str) -> None:
            message = await modlog_utils.assemble_message(
                action,
                ctx=ctx,
                reason=reason,
                mod=ctx.bot.user,
                user=user
            )

            await channel.send(message)
        
        async with self.bot.pool.acquire() as conn:
            punishments = """SELECT * FROM punishments WHERE guild_id = $1"""
            punishments = await conn.fetch(punishments, ctx.guild.id)
            punishments = [x for x in punishments]

            if not punishments:
                return
            try:
                for puni in range(len(punishments)):
                    time = punishments[puni]['time']
                    if strikes >= punishments[puni]['strikes']:
                        if strikes >= punishments[puni-1]['strikes']:
                            if punishments[puni-1]['action'] == punishments[puni]['action'] and len(punishments) > 1:
                                break
                            
                            await StrikeHandler2.actions(punishments[puni-1]['action'].lower(), old_strikes=kwargs.get('old_strikes'), strikes=strikes, time=time)
                            break

                        if punishments[puni]['action'].lower() == 'mute':
                            await StrikeHandler2.actions('mute', old_strikes=kwargs.get('old_strikes'), strikes=strikes, time=time)
                            
                        if punishments[puni]['action'].lower() == 'kick':
                            await StrikeHandler2.actions('kick', old_strikes=kwargs.get('old_strikes'), strikes=strikes)
        
                        if punishments[puni]['action'].lower() == 'ban':
                            await StrikeHandler2.actions('ban', old_strikes=kwargs.get('old_strikes'), strikes=strikes, time=time)
                            
            except Exception as err:
                print(f"err33: {err}")
def setup(bot):
    bot.add_cog(StrikeHandler(bot))