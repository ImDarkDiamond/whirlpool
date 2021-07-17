from logging import exception
from operator import mod
from discord.ext import commands, menus
from discord.ext.commands.core import command
from utilities import cache, checks, time
from logging_ import ModLogUtils
import discord
import textwrap
import datetime
import traceback
import modlog_utils
import mod_cache
import mod_config

def can_execute_action(ctx, user, target):
    return user.id == ctx.bot.owner_id or \
           user == ctx.guild.owner or \
           user.top_role > target.top_role

class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f'{argument}'

        if len(ret) > 512:
            reason_max = 512
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret

class MemberID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f"{argument} is not a valid member or member ID.") from None
            else:
                m = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
                if m is None:
                    # hackban case
                    return type('_Hackban', (), {'id': member_id, '__str__': lambda s: f'Member ID {s.id}'})()

        if not can_execute_action(ctx, ctx.author, m):
            raise commands.BadArgument('You cannot do this action on this user due to role hierarchy.')
        return m

class Strikes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(kick_members=True)
    async def strike(self, ctx, strikes: int, users: commands.Greedy[discord.Member], *, reason: ActionReason = "[no reason provided]") -> None:
        
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

                try:
                    await user.send(f"{mod_config.custom_emojis['infow']} You were given `{strikes}` strikes `[{update['strikes']-strikes} → {update['strikes']}]` in **{ctx.guild.name}**\nreason: \"{reason}\" ")
                except:
                    pass

                if channel:
                    message = await ModLogUtils.assemble_message(
                        "strike_add",
                        strikes_added=strikes,
                        strikes={
                            'old':update['strikes']-strikes,
                            'new':update['strikes']
                        },
                        reason=reason,
                        mod=ctx.author,
                        user=user,
                        guild=ctx.guild,
                        bot=self.bot
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

            final_string += f"{mod_config.custom_emojis['plus']} Gave `{strikes}` strikes to <@{user.id}> `[{update['strikes']-strikes} → {update['strikes']}]`!\n"

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(kick_members=True)
    async def pardon(self, ctx, strikes: int, users: commands.Greedy[discord.Member], *, reason: ActionReason = "[no reason provided]") -> None:

        if strikes < 1:
            return await ctx.send("Amount of strikes must be above **1**")

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        async def send_modlog(new_strikes:int, old_strikes:int) -> None:
            message = await ModLogUtils.assemble_message(
                "pardon",
                strikes_removed=strikes,
                strikes={
                    'old':old_strikes,
                    'new':new_strikes
                },
                reason=reason,
                mod=ctx.author,
                user=user,
                guild=ctx.guild,
                bot=self.bot
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
                        final_string += f"{mod_config.custom_emojis['change']} <@{user.id}> Doesn't have any strikes!\n"
                        continue
                    
                    if initial_data['strikes'] - strikes <= 0:
                        await conn.execute("DELETE FROM guild_strikes WHERE guild_id = $1 AND user_id = $2",ctx.guild.id,user.id)
                        final_string += f"{mod_config.custom_emojis['minus']} Pardoned all strikes from <@{user.id}>!\n"

                        try:
                            await user.send(f"{mod_config.custom_emojis['infow']} You were pardoned of all your strikes `[{initial_data['strikes']} → 0]` in **{ctx.guild.name}**\nreason: \"{reason}\" ")
                        except:
                            pass
                
                        if channel:
                            await send_modlog(0,initial_data['strikes'])
                        continue
                    else:
                        query = """UPDATE guild_strikes SET strikes = $1 WHERE guild_id = $2 AND user_id = $3 RETURNING *"""
                        update = await conn.fetchrow(query, initial_data['strikes'] - strikes,ctx.guild.id, user.id)

                    try:
                        await user.send(f"{mod_config.custom_emojis['infow']} You pardoned of `{strikes}` strikes `[{initial_data['strikes']} → {update['strikes']}]` in **{ctx.guild.name}**\nreason: \"{reason}\" ")
                    except:
                        pass

                    if channel:
                        await send_modlog(update['strikes'],initial_data['strikes'])

            except Exception as err:
                print(err)
                final_string += f"Failed to pardon strike from <@{user.id}>!\n"
                continue

            final_string += f"{mod_config.custom_emojis['minus']} Pardoned `{strikes}` strikes from <@{user.id}> `[{initial_data['strikes']} → {update['strikes']}]`!\n"

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(kick_members=True)
    async def check(self, ctx, user: discord.User) -> None:

        
        try:
            ban_list = await ctx.guild.bans()
            config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
            strikes = await self.bot.pool.fetchval("SELECT strikes FROM guild_strikes WHERE guild_id = $1 AND user_id = $2",
                                                    ctx.guild.id, user.id)
            x_status_query = """SELECT expires FROM reminders WHERE 
                                extra #>> '{args,2}' = $1 AND extra #>> '{args,0}' = $2 
                                AND event = $3"""

            mute_status = await self.bot.pool.fetchval(x_status_query,str(user.id),str(ctx.guild.id),"tempmute")
            ban_status = await self.bot.pool.fetchval(x_status_query,str(user.id),str(ctx.guild.id),"tempban") 

            is_muted = user.id in config.mutedmembers
            is_banned =  discord.utils.find(lambda u: str(u.user) == user, ban_list)

            string = f"{mod_config.custom_emojis['check']} Moderation information for **{user.name}**#{user.discriminator} (ID:`{user.id}`)\n"
            string += f"🚩 Strikes: **{strikes or 0}**\n"
            string += f"🔇 Muted: {'**Yes**' if is_muted else '**No**'}\n"
            string += f"🤐 Mute Time Remaining: {f'{time.human_timedelta(mute_status)}' if mute_status else 'N/A'}\n"
            string += f"🔨 Banned: {'**Yes**' if is_banned else '**No**'}\n"
            string += f"⏲️ Ban Time Remaining: {f'{time.human_timedelta(ban_status)}' if ban_status else 'N/A'}\n"
            
            await ctx.send(string)
        except Exception as err:
            return await ctx.send(f"An error occured!```{err}```")

def setup(bot):
    bot.add_cog(Strikes(bot))