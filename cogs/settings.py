from discord.ext import commands, menus
from utilities import cache, checks, formats
import discord
import textwrap
import datetime
import traceback
import asyncpg


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

def setup(bot):
    bot.add_cog(Settings(bot))