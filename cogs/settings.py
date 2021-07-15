from discord.ext import commands, menus
from utilities import cache, checks, formats
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
    async def punishment(self, ctx, number: int, action: str, time=None) -> None:
        acceptable_actions = ['mute','kick','ban','tempban','tempmute']

        if number < 1:
            return await ctx.send("Amount of strikes needed must be above **1**")

        if action.lower() not in acceptable_actions:
            return await ctx.send(f"Action must be in `{', '.join(acceptable_actions)}`")

        query = """INSERT INTO punishments(guild_id,action,strikes,time)
                    VALUES($1,$2,$3,$4) RETURNING *
                """
        try:
            insert = await self.bot.pool.fetchrow(query, ctx.guild.id, action.lower(), number, time)
        except asyncpg.UniqueViolationError as err:
            confirm = await formats.prompt(ctx,f"A punishment for the action {action.lower()} already exists. Do you want to delete it?")
            if not confirm:
                return await ctx.send("Aborthing!")

            nested_query = "(SELECT action_id FROM punishments WHERE guild_id = $2 AND action = $1)"
            await self.bot.pool.execute(f"DELETE FROM punishments WHERE action_id = {nested_query} AND guild_id = $2",action.lower(),ctx.guild.id)
            return await ctx.send("Deleted that punishment!")

        embed = discord.Embed(
            description=f"When a user reaches **{number}** strikes, I will **{action.lower()}** them."
        )
        embed.color = discord.Color.green()
        embed.add_field(name="Strikes",value=f"`{number}`",inline=False)
        embed.add_field(name="Action", value=f"`{action.lower()}`",inline=False)
        if time:
            embed.add_field(name="Duration", value=f"`{time}`",inline=False)

        await ctx.send(f"Added a new punishment!",embed=embed)

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

        await ctx.send(f"{mod_config.custom_emojis['check']} Successfully set your modlogs to {'off' if channel is None else channel}")

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

        await ctx.send(f"{mod_config.custom_emojis['check']} Successfully set your serverlogs to {'off' if channel is None else channel}")

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

        await ctx.send(f"{mod_config.custom_emojis['check']} Successfully set your messagelogs to {'off' if channel is None else channel}")

    @commands.command()
    @commands.guild_only()
    @checks.has_guild_permissions(manage_guild=True)
    async def mutedrole(self, ctx) -> None:
        ...
        
def setup(bot):
    bot.add_cog(Settings(bot))