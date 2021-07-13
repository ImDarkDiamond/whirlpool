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
        
    async def make_message(self, action: str, ctx, user=None, reason: str=None) -> str:
        message = await modlog_utils.assemble_message(
            action,
            ctx=ctx,
            reason=reason,
            mod=ctx.author,
            user=user
        )

        return message

    @commands.command()
    @commands.guild_only()
    @checks.mod_role_or_perms(kick_members=True)
    @checks.has_mute_role()
    async def mute(self, ctx, users: commands.Greedy[MemberID], *, reason: ActionReason = "[no reason provided]"):

        final_string = ""
        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)
        channel = config and config.mod_logs
        role = config and config.mute_role

        for user in users:
            try:
                await user.add_roles(role,reason=reason)

                if user.id in config.mutedmembers:
                    final_string += f"Failed to mute <@{user.id}>, user already muted!\n"
                    continue
                else:
                    config.mutedmembers.add(user.id)
                    mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)
                    await self.bot.pool.execute("UPDATE guild_settings SET mutedmembers = $1 WHERE id = $2",config.mutedmembers,ctx.guild.id)

                message = await self.make_message("mute",ctx,user=user,reason=reason)
                await channel.send(message)
                
                user_message = f"ℹ️ You have been muted in **{ctx.guild.name}** for \"{reason}\""
                try:
                    await user.send(user_message)
                except:
                    pass

                final_string += f"Successfully muted <@{user.id}>!\n"
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

                if user.id not in config.mutedmembers:
                    final_string += f"Failed to unmute <@{user.id}>, user is not muted!\n"
                    continue
                else:
                    config.mutedmembers.remove(user.id)
                    mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)
                    await self.bot.pool.execute("UPDATE guild_settings SET mutedmembers = $1 WHERE id = $2",config.mutedmembers,ctx.guild.id)

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

def setup(bot):
    bot.add_cog(Mod(bot))