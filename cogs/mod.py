from logging import exception
from operator import mod
from discord.ext import commands, menus, tasks
from discord.ext.commands.core import command
from utilities import cache, checks, time
from pytz import timezone
from collections import Counter, defaultdict
import asyncio
import discord
import textwrap
import datetime
import traceback
import modlog_utils
import mod_cache
import typing
import asyncpg
class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f'{argument}'

        if len(ret) > 512:
            reason_max = 512
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret

def can_execute_action(ctx, user, target):
    return user.id == ctx.bot.owner_id or \
           user == ctx.guild.owner or \
           user.top_role > target.top_role
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

class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity
class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._data_batch = defaultdict(list)
        self._batch_lock = asyncio.Lock(loop=bot.loop)
        self._disable_lock = asyncio.Lock(loop=bot.loop)
        self.batch_updates.add_exception_type(asyncpg.PostgresConnectionError)
        self.batch_updates.start()

    def cog_unload(self):
        self.batch_updates.stop()
        self.bulk_send_messages.stop()

    async def bulk_insert(self):
        query = """UPDATE guild_settings
                   SET mutedmembers = $1 WHERE 
                   id = $2
                """

        if not self._data_batch:
            return

        final_data = []
        for guild_id, data in self._data_batch.items():
            config = await mod_cache.get_guild_config(self.bot, guild_id)
            as_set = config.mutedmembers
            for member_id, insertion in data:
                func = as_set.add if insertion else as_set.discard
                func(member_id)

            final_data = list(as_set)
            mod_cache.get_guild_config.invalidate(self.bot, guild_id)

        await self.bot.pool.execute(query, final_data, guild_id)
        self._data_batch.clear()

    @tasks.loop(seconds=15.0)
    async def batch_updates(self):
        async with self._batch_lock:
            await self.bulk_insert()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        guild_id = after.guild.id
        config = await mod_cache.get_guild_config(self.bot, guild_id)
        
        if config is None:
            return

        if config.muterole is None:
            return

        before_has = before._roles.has(config.muterole)
        after_has = after._roles.has(config.muterole)

        if before_has == after_has:
            return

        async with self._batch_lock:
            self._data_batch[guild_id].append((after.id, after_has))

    async def make_message(self, action: str, ctx, user=None, reason: str=None, time:str = None) -> str:
        message = await modlog_utils.assemble_message(
            action,
            ctx=ctx,
            reason=reason,
            mod=ctx.author,
            user=user,
            time=time
        )

        return message

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(kick_members=True)
    @checks.has_mute_role()
    async def mute(self, ctx, users: commands.Greedy[MemberID], *, when: time.UserFriendlyTime(commands.clean_content,default='[no reason provided]')): #reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs
        role = config and config.mute_role
        reminder = self.bot.get_cog('Reminder')

        for user in users:
            try:
                await user.add_roles(role,reason=when.arg)

                # if user.id in config.mutedmembers:
                #     final_string += f"Failed to mute <@{user.id}>, user already muted!\n"
                #     continue
                # else:
                #     config.mutedmembers.add(user.id)
                #     mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)
                #     await self.bot.pool.execute("UPDATE guild_settings SET mutedmembers = $1 WHERE id = $2",config.mutedmembers,ctx.guild.id)

                if when.dt is None:
                    message = await self.make_message("mute",ctx,user=user,reason=when.arg)
                else:
                    if reminder is None:
                        await ctx.send("Sorry, temporary commands can't be used rightnow.")
                        break
                    
                    timer = await reminder.create_timer(when.dt, 'tempmute', ctx.guild.id,
                                                                                ctx.author.id,
                                                                                user.id,
                                                                                role.id,
                                                                                created=ctx.message.created_at)
                    message = await self.make_message("tempmute",ctx,user=user,reason=when.arg,time=time.human_timedelta(when.dt))

                await channel.send(message)
                
                user_message = f"ℹ️ You have been muted in **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                final_string += f"""Successfully muted <@{user.id}>{f", for {time.human_timedelta(when.dt)}" if when.dt else ""}!\n"""
            except Exception as err:
                print(err)
                final_string += f"Failed to mute <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(kick_members=True)
    @checks.has_mute_role()
    async def unmute(self, ctx, users: commands.Greedy[MemberID], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs
        role = config and config.mute_role

        for user in users:
            try:
                await user.remove_roles(role,reason=reason)

                # if user.id not in config.mutedmembers:
                #     final_string += f"Failed to unmute <@{user.id}>, user is not muted!\n"
                #     continue
                # else:
                #     config.mutedmembers.remove(user.id)
                #     mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)
                #     await self.bot.pool.execute("UPDATE guild_settings SET mutedmembers = $1 WHERE id = $2",config.mutedmembers,ctx.guild.id)

                message = await self.make_message("unmute",ctx,user=user,reason=reason)
                await channel.send(message)
                
                user_message = f"ℹ️ You have been unmuted in **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                final_string += f"Successfully unmuted <@{user.id}>!\n"
            except Exception as err:
                print(err)
                final_string += f"Failed to unmute <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(kick_members=True)
    async def kick(self, ctx, users: commands.Greedy[MemberID], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            try:
                user_message = f"ℹ️ You have been kicked from **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                await user.kick(reason=reason)

                message = await self.make_message("kick",ctx,user=user,reason=reason)
                await channel.send(message)
            
                final_string += f"Successfully kicked <@{user.id}>!\n"
            except Exception as err:
                print(err)
                final_string += f"Failed to kick <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(ban_members=True)
    async def ban(self, ctx, users: commands.Greedy[MemberID], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            try:
                user_message = f"ℹ️ You have been banned from **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                await user.ban(reason=reason)

                message = await self.make_message("ban",ctx,user=user,reason=reason)
                await channel.send(message)
            
                final_string += f"Successfully banned <@{user.id}>!\n"
            except Exception as err:
                print(err)
                final_string += f"Failed to ban <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(ban_members=True)
    async def softban(self, ctx, users: commands.Greedy[MemberID], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            try:
                user_message = f"ℹ️ You have been banned from **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                await user.ban(reason=reason,delete_message_days=7)
                await ctx.guild.unban(user, reason=f"Unban after soft ban by {ctx.author} (ID:{ctx.author.id})")

                message = await self.make_message("ban",ctx,user=user,reason=reason)
                await channel.send(message)
            
                final_string += f"Successfully soft-banned <@{user.id}>!\n"
            except Exception as err:
                print(err)
                final_string += f"Failed to ban <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(ban_members=True)
    async def unban(self, ctx, users: commands.Greedy[BannedMember], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            user = user.user


            try:
                user_message = f"ℹ️ You have been unbanned from **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                await ctx.guild.unban(user, reason=reason)

                message = await self.make_message("unban",ctx,user=user,reason=reason)
                await channel.send(message)
            
                final_string += f"Successfully unbanned <@{user.id}>!\n"
            except Exception as err:
                print(err)
                final_string += f"Failed to unban <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(ban_members=True)
    async def silentban(self, ctx, users: commands.Greedy[MemberID], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            try:
                user_message = f"ℹ️ You have been banned from **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                await user.ban(reason=reason, delete_message_days=0)

                message = await self.make_message("ban",ctx,user=user,reason=reason)
                await channel.send(message)
            
                final_string += f"Successfully banned <@{user.id}>!\n"
            except Exception as err:
                print(err)
                final_string += f"Failed to ban <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(manage_messages=True)
    async def reason(self, ctx, case_id:int, reason: ActionReason = "[no reason provided]"):

        case = await self.bot.pool.fetchrow("SELECT * FROM mod_actions WHERE case_id = $1 AND guild_id = $2",
                                             case_id, ctx.guild.id)

        if not case:
            return await ctx.send(f"There is no case with the id __#{case_id}__")

        if ctx.author.id != case['mod_id']:
            if ctx.author.id != ctx.guild.owner_id:
                return await ctx.send("Only the owner of the case or server may change it's resaon.")

        
        query = """UPDATE mod_actions SET reason = $1 WHERE case_id = $2 AND guild_id = $3"""
        await self.bot.pool.execute(query, reason, case_id, ctx.guild.id)

        await ctx.send(f"Successfully updated case __#{case_id}__")

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(move_members=True)
    async def voicekick(self, ctx, users: commands.Greedy[MemberID], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            try:
                # user_message = f"ℹ️ You have been banned from **{ctx.guild.name}** for \"{reason}\""
                # try:
                #     await user.send(user_message)
                # except:
                #     pass

                await user.move_to(None, reason=reason)

                # message = await self.make_message("ban",ctx,user=user,reason=reason)
                # await channel.send(message)
            
                final_string += f"Successfully voice kicked <@{user.id}>!\n"
            except Exception as err:
                print(err)
                final_string += f"Failed to voice kick <@{user.id}>!\n"
                continue

        await ctx.send(final_string,allowed_mentions=discord.AllowedMentions(users=False,everyone=False,roles=False))

    @commands.Cog.listener()
    async def on_tempmute_timer_complete(self, timer):
        guild_id, mod_id, member_id, role_id = timer.args
        config = await mod_cache.get_guild_config(self.bot,guild_id)
        await self.bot.wait_until_ready()

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        member = await self.bot.get_or_fetch_member(guild, member_id)
        if member is None or not role_id in [x.id for x in member.roles]:
            async with self._batch_lock:
                self._data_batch[guild_id].append((member_id, False))
            return

        if mod_id != member_id:
            moderator = await self.bot.get_or_fetch_member(guild, mod_id)
            if moderator is None:
                try:
                    moderator = await self.bot.fetch_user(mod_id)
                except:
                    # request failed somehow
                    moderator = f'Mod ID {mod_id}'
                else:
                    moderator = f'{moderator} (ID: {mod_id})'
            else:
                moderator = f'{moderator} (ID: {mod_id})'

            reason = f'Automatic unmute from timer made by {moderator}.'
        else:
            reason = f'Expiring self-mute made by {member}'

        try:
            await member.remove_roles(discord.Object(id=role_id), reason=reason)
        except discord.HTTPException:
            # if the request failed then just do it manually
            async with self._batch_lock:
                self._data_batch[guild_id].append((member_id, False))


def setup(bot):
    bot.add_cog(Mod(bot))