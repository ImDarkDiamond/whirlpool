from logging import exception
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

class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f'{ctx.author} (ID: {ctx.author.id}): {argument}'

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(kick_members=True)
    async def strike(self, ctx, strikes: int, users: commands.Greedy[discord.Member], *, reason: ActionReason = None) -> None:
        
        if strikes < 1:
            return await ctx.send("Amount of strikes must be above **1**")

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            try:
                query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                        VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                        DO UPDATE SET strikes = guild_strikes.strikes + $3
                        RETURNING *
                        """
            
                update = await self.bot.pool.fetchrow(query, ctx.guild.id, user.id, strikes)

                if channel:
                    message = await modlog_utils.assemble_message(
                        "strike_add",
                        ctx=ctx,
                        strikes_added=strikes,
                        strikes={
                            'old':update['strikes']-strikes,
                            'new':update['strikes']
                        },
                        reason=reason,
                        mod=ctx.author,
                        user=user
                    )

                    await channel.send(message)

                self.bot.dispatch("strike_add", 
                    ctx,
                    user, 
                    strikes=update['strikes'],
                    old_strikes=update['strikes']-strikes, 
                )

            except Exception as err:
                print(err)
                final_string += f"Failed to give strikes to <@{user.id}>!\n"
                continue

            final_string += f"Gave `{strikes}` strikes to <@{user.id}> `[{update['strikes']-strikes} → {update['strikes']}]`!\n"

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(kick_members=True)
    async def pardon(self, ctx, strikes: int, users: commands.Greedy[discord.Member], *, reason: ActionReason = None) -> None:

        if strikes < 1:
            return await ctx.send("Amount of strikes must be above **1**")

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        async def send_modlog(new_strikes:int, old_strikes:int) -> None:
            message = await modlog_utils.assemble_message(
                "pardon",
                ctx=ctx,
                strikes_removed=strikes,
                strikes={
                    'old':old_strikes,
                    'new':new_strikes
                },
                reason=reason,
                mod=ctx.author,
                user=user
            )

            await channel.send(message)

        for user in users:
            try:
                async with self.bot.pool.acquire() as conn:
                    query = """SELECT * FROM guild_strikes
                                WHERE guild_id = $1 AND user_id = $2
                            """
                    initial_data = await conn.fetchrow(query,ctx.guild.id,user.id)

                    if not initial_data:
                        final_string += f"<@{user.id}> Doesn't have any strikes!\n"
                        continue
                    
                    if initial_data['strikes'] - strikes <= 0:
                        await conn.execute("DELETE FROM guild_strikes WHERE guild_id = $1 AND user_id = $2",ctx.guild.id,user.id)
                        final_string += f"Pardoned all strikes from <@{user.id}>!\n"

                        if channel:
                            await send_modlog(0,initial_data['strikes'])
                        continue
                    else:
                        query = """UPDATE guild_strikes SET strikes = $1 WHERE guild_id = $2 AND user_id = $3 RETURNING *"""
                        update = await conn.fetchrow(query, initial_data['strikes'] - strikes,ctx.guild.id, user.id)

                    if channel:
                        await send_modlog(update['strikes'],initial_data['strikes'])

            except Exception as err:
                print(err)
                final_string += f"Failed to pardon strike from <@{user.id}>!\n"
                continue

            final_string += f"Pardoned `{strikes}` strikes from <@{user.id}> `[{initial_data['strikes']} → {update['strikes']}]`!\n"

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

def setup(bot):
    bot.add_cog(Mod(bot))