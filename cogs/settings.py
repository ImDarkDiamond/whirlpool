from discord.ext import commands, menus
from utilities import cache, checks, formats, userfriendlly
import discord
import textwrap
import datetime
import traceback
import asyncpg
import typing
import mod_config
import mod_cache

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def settings_handler(self, ctx, key:str, value):

        value = None if value is None else value
        sql = f"""INSERT INTO guild_settings(id,{key}) VALUES($1,$2)
                ON CONFLICT (id) DO UPDATE SET {key} = $2"""

        return await ctx.bot.pool.execute(sql, ctx.guild.id, value)

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def punishment(self, ctx, number: int, action: str, *, time: str=None) -> None:
        acceptable_actions = ['mute','kick','ban','tempban','tempmute']

        if number < 1:
            return await ctx.send("Amount of strikes needed must be above **1**")

        if action.lower() not in acceptable_actions:
            return await ctx.send(f"Action must be in `{', '.join(acceptable_actions)}`")

        if time:
            try:
                userfriendlly.FutureTime(time)
            except commands.BadArgument:
                return await ctx.send("Invalid time provided.")

        query = """INSERT INTO punishments(guild_id,action,strikes,time)
                    VALUES($1,$2,$3,$4) RETURNING *
                """
        try:
            insert = await self.bot.pool.fetchrow(query, ctx.guild.id, action.lower(), number, time)
        except asyncpg.UniqueViolationError as err:
            confirm = await formats.prompt(ctx,f"A punishment for the action {action.lower()} already exists. Do you want to delete it?")
            if not confirm:
                return await ctx.send("Aborthing!")

            nested_query = "(SELECT action_id FROM punishments WHERE guild_id = $2 AND action = $1 AND strikes = $3)"
            await self.bot.pool.execute(f"DELETE FROM punishments WHERE action_id = {nested_query} AND guild_id = $2",action.lower(),ctx.guild.id,number)
            return await ctx.send("Deleted that punishment!")

        embed = discord.Embed(
            description=f"When a user reaches **{number}** strikes, I will **{action.lower()}** them."
        )
        embed.color = discord.Color.green()
        embed.add_field(name="Strikes",value=f"`{number}`",inline=False)
        embed.add_field(name="Action", value=f"`{action.lower()}`",inline=False)
        if time:
            embed.add_field(name="Duration", value=f"`{time}`",inline=False)

        await ctx.send(f"{mod_config.custom_emojis['check']} Successfully added a new punishment!")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def settings(self, ctx) -> None:

        config = await mod_cache.get_guild_config(ctx.bot,ctx.guild.id)

        if not config:
            return await ctx.send(f"{mod_config.custom_emojis['x']} This server is not cached.")

        async with self.bot.pool.acquire() as conn:
            config = await conn.fetchrow("SELECT * FROM guild_settings WHERE id = $1", ctx.guild.id)
            punishments = await conn.fetch("SELECT * FROM punishments WHERE guild_id = $1", ctx.guild.id)

            if not config:
                return await ctx.send(f"{mod_config.custom_emojis['x']} This server does not have any custom settings.")

            embed = discord.Embed(color=0x71a2b1)

            embed.add_field(name="📊 Server Settings",value=textwrap.dedent(f"""
            Prefix: {ctx.prefix}
            Mod Role: {f"<@&{config['modrole']}>" if config['modrole'] else "None"}
            Muted Role: {f"<@&{config['muterole']}>" if config['muterole'] else "None"}
            Mod Logs: {f"<#{config['modlogs']}>" if config['modlogs'] else "None"}
            Message logs: {f"<#{config['messagelogs']}>" if config['messagelogs'] else "None"}
            Voice logs: {f"<#{config['voicelogs']}>" if config['voicelogs'] else "None"}
            Avatar logs: {f"<#{config['avatarlogs']}>" if config['avatarlogs'] else "None"}
            Server logs: {f"<#{config['serverlogs']}>" if config['serverlogs'] else "None"}"""
            ))

            embed.add_field(name="🚩 Punishments", value="\n".join([f"`{x['strikes']} 🚩`: **{x['action']}** {mod_config.emoji_key[x['action'].lower()]}" for x in punishments]) if punishments else "No punishments set")
            
            embed.add_field(name="🛡️ Automod Settings", value=textwrap.dedent(f"""
            __Anti Advertisement__
            Invite links: `{config['invite_strikes']} 🚩`
        
            __Maximum Mentions__
            User mentions: `{config['max_mentions']}`
            Role mentions: `{config['max_role_mentions']}`

            __Misc Msg Settings__
            Max Lines per Msg: `{config['max_newlines']}`
            Copypastas: `{config['copypasta_strikes']} 🚩`
            \@everyone attempt: `{config['everyone_strikes']} 🚩`
            """))

            await ctx.send(f"**{self.bot.user.name}** settings on **{ctx.guild.name}**:", embed=embed)

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def modlogs(self, ctx, *, channel: typing.Union[discord.TextChannel,str]) -> None:

        if type(channel) != discord.TextChannel and type(channel) == str:
            if channel.lower() != 'off':
                return await ctx.send("You must provide either a channel, or 'OFF'")

        channel = None if type(channel) != discord.TextChannel and channel.lower() == 'off' else channel
        await self.settings_handler(ctx, "modlogs", channel.id if type(channel) == discord.TextChannel else channel)
        mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)

        if channel is None:
            return await ctx.send(f"{mod_config.custom_emojis['check']} Moderation actions will no longer be logged!")
        await ctx.send(f"{mod_config.custom_emojis['check']} Moderation actions will now be logged in {channel}")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def serverlogs(self, ctx, *, channel: typing.Union[discord.TextChannel,str]) -> None:

        if type(channel) != discord.TextChannel and type(channel) == str:
            if channel.lower() != 'off':
                return await ctx.send("You must provide either a channel, or 'OFF'")

        channel = None if type(channel) != discord.TextChannel and channel.lower() == 'off' else channel
        await self.settings_handler(ctx, "serverlogs", channel.id if type(channel) == discord.TextChannel else channel)
        mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)

        if channel is None:
            return await ctx.send(f"{mod_config.custom_emojis['check']} Server related actions will no longer be logged!")
        await ctx.send(f"{mod_config.custom_emojis['check']} Server related actions will now be logged in {channel}")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def avatarlogs(self, ctx, *, channel: typing.Union[discord.TextChannel,str]) -> None:

        if type(channel) != discord.TextChannel and type(channel) == str:
            if channel.lower() != 'off':
                return await ctx.send("You must provide either a channel, or 'OFF'")

        channel = None if type(channel) != discord.TextChannel and channel.lower() == 'off' else channel
        await self.settings_handler(ctx, "avatarlogs", channel.id if type(channel) == discord.TextChannel else channel)
        mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)

        if channel is None:
            return await ctx.send(f"{mod_config.custom_emojis['check']} Avatars will no longer be logged!")
        await ctx.send(f"{mod_config.custom_emojis['check']} Avatars will now be logged in {channel}")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def voicelogs(self, ctx, *, channel: typing.Union[discord.TextChannel,str]) -> None:

        if type(channel) != discord.TextChannel and type(channel) == str:
            if channel.lower() != 'off':
                return await ctx.send("You must provide either a channel, or 'OFF'")

        channel = None if type(channel) != discord.TextChannel and channel.lower() == 'off' else channel
        await self.settings_handler(ctx, "voicelogs", channel.id if type(channel) == discord.TextChannel else channel)
        mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)

        if channel is None:
            return await ctx.send(f"{mod_config.custom_emojis['check']} Voice Joins/Leaves/Moves will no longer be logged!")
        await ctx.send(f"{mod_config.custom_emojis['check']} Voice Joins/Leaves/Moves will now be logged in {channel}")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def messagelogs(self, ctx, *, channel: typing.Union[discord.TextChannel,str]) -> None:

        if type(channel) != discord.TextChannel and type(channel) == str:
            if channel.lower() != 'off':
                return await ctx.send("You must provide either a channel, or 'OFF'")

        channel = None if type(channel) != discord.TextChannel and channel.lower() == 'off' else channel
        await self.settings_handler(ctx, "messagelogs", channel.id if type(channel) == discord.TextChannel else channel)
        mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)

        if channel is None:
            return await ctx.send(f"{mod_config.custom_emojis['check']} Messages will no longer be logged!")
        await ctx.send(f"{mod_config.custom_emojis['check']} Messages will now be logged in {channel}")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(administrator=True)
    async def modrole(self, ctx, *, role: discord.Role=None) -> None:
        
        if role:
            if role > ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                return await ctx.send(f"This role is above your own. Please get someone higher to set it!")

        value = None if role is None else role.id
        sql = f"""INSERT INTO guild_settings(id,modrole) VALUES($1,$2)
                ON CONFLICT (id) DO UPDATE SET modrole = $2"""
        
        await ctx.bot.pool.execute(sql, ctx.guild.id, value)
        mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)

        await ctx.send(f"{mod_config.custom_emojis['check']} Successfully set your modrole to {'none' if role is None else role}")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(administrator=True)
    async def muterole(self, ctx, *, role: discord.Role=None) -> None:
                        
        if role:
            if ctx.guild.me.guild_permissions.manage_roles is False:
                return await ctx.send(f"I do not have the `MANAGE_ROLES` permission. Please give me the permission, and rerun this command.")

            if role > ctx.guild.me.top_role:
                return await ctx.send(f"This role is above my highest role, please move my highest role above it!")        

        value = None if role is None else role.id
        sql = f"""INSERT INTO guild_settings(id,muterole) VALUES($1,$2) ON CONFLICT (id) DO UPDATE SET muterole = $2"""
        await ctx.bot.pool.execute(sql, ctx.guild.id, value)
        mod_cache.get_guild_config.invalidate(ctx.bot, ctx.guild.id)

        if role is None:
            return await ctx.send(f"{mod_config.custom_emojis['check']} Successfully unset your muterole!")
        await ctx.send(f"{mod_config.custom_emojis['check']} Successfully set your mute role to {role}!")

def setup(bot):
    bot.add_cog(Settings(bot))