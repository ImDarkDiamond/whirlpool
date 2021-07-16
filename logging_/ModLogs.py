from operator import mod
from discord.ext import commands, menus, tasks
from discord.ext.commands.core import command
# from utilities import time
import pytz
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
import mod_config
import time
from . import ModLogUtils

class ModLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        try:
            config = await mod_cache.get_guild_config(self.bot,guild.id)

            if not config:
                return

            if not config.mod_logs:
                return  

            limit = datetime.datetime.utcfromtimestamp(time.time() - 60)
            log = await self.wait_for_logs(
                guild,
                discord.AuditLogAction.ban,
                user,
                lambda e: e.target == user
                and e.created_at.replace(tzinfo=pytz.UTC) > limit.replace(tzinfo=pytz.UTC),
            )


            if log:
                if log.user.id == self.bot.user.id:
                    return

                message = await ModLogUtils.assemble_message(
                    "ban",
                    guild=guild,
                    user=user,
                    mod=log.user,
                    bot=self.bot,
                    reason=log.reason,
                )
                await config.mod_logs.send(message)            

        except Exception as err:
            print(err)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        try:
            config = await mod_cache.get_guild_config(self.bot,guild.id)

            if not config:
                return

            if not config.mod_logs:
                return  

            limit = datetime.datetime.utcfromtimestamp(time.time() - 60)
            log = await self.wait_for_logs(
                guild,
                discord.AuditLogAction.unban,
                user,
                lambda e: e.target == user
                and e.created_at.replace(tzinfo=pytz.UTC) > limit.replace(tzinfo=pytz.UTC),
            )

            if log:
                if log.user.id == self.bot.user.id:
                    return

                message = await ModLogUtils.assemble_message(
                    "unban",
                    guild=guild,
                    user=user,
                    mod=log.user,
                    bot=self.bot,
                    reason=log.reason,
                )
                await config.mod_logs.send(message)            

        except Exception as err:
            print(err)
    
    @commands.Cog.listener()
    async def on_member_remove(self, user):
        if user.id == self.bot.user.id:
            return

        async for entry in user.guild.audit_logs(
            action=discord.AuditLogAction.kick, limit=25
        ):
            if (
                user.joined_at is None
                or user.joined_at > entry.created_at
                or entry.created_at.replace(tzinfo=pytz.UTC) < datetime.datetime.utcfromtimestamp(time.time() - 30).replace(tzinfo=pytz.UTC)
            ):
                break
            if entry.user.id == self.bot.user.id:
                return

            if entry.target == user:
                config = await mod_cache.get_guild_config(self.bot,user.guild.id)

                if not config:
                    return

                if not config.mod_logs:
                    return  

                message = await ModLogUtils.assemble_message(
                    "kick",
                    guild=user.guild,
                    user=user,
                    mod=entry.user,
                    bot=self.bot,
                    reason=entry.reason,
                )
                await config.mod_logs.send(message)          

    async def wait_for_logs(self, guild, action, user, matcher, check_limit=10, retry=True):

        limit = datetime.datetime.utcfromtimestamp(time.time() - 60)
        log = await self.find_log(
            guild,
            discord.AuditLogAction.ban,
            lambda e: e.target == user
            and e.created_at.replace(tzinfo=pytz.UTC) > limit.replace(tzinfo=pytz.UTC),
        )
        if log is None:
            await asyncio.sleep(1)
            log = await self.find_log(
                guild,
                discord.AuditLogAction.ban,
                lambda e: e.target == user
                and e.created_at.replace(tzinfo=pytz.UTC)
                > limit.replace(tzinfo=pytz.UTC),
            )

        if log is not None:
            return log
                
    async def find_actual_log(self, guild, action, matcher, check_limit, retry):
        try:
            if guild.me is None:
                return None
            entry = None
            if guild.me.guild_permissions.view_audit_log:
                try:
                    async for e in guild.audit_logs(action=action, limit=check_limit):
                        if matcher(e):
                            if entry is None or e.id > entry.id:
                                entry = e
                except discord.Forbidden:
                    pass
            if entry is None and retry:
                await asyncio.sleep(2)
                return await self.find_log(guild, action, matcher, check_limit, False)
            if entry is not None and isinstance(entry.target, discord.Object):
                entry.target = await self.bot.get_or_fetch_member(entry.target.id)
            return entry
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return None

    async def find_log(self, guild, action, matcher, check_limit=10, retry=True):
        try:
            return await asyncio.wait_for(
                self.find_actual_log(guild, action, matcher, check_limit, retry), 10
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return None

def setup(bot):
    bot.add_cog(ModLogs(bot))