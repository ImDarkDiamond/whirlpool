from discord.ext import commands, menus
import discord
import textwrap
import datetime
import traceback



class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def punishment(self, ctx, number: int, action: str, time=None) -> None:
        acceptable_actions = ['mute','kick','ban','tempban','tempmute']

        if number < 1:
            return await ctx.send("Amount of strikes needed must be above **1**")

        if action.lower() not in acceptable_actions:
            return await ctx.send(f"Action must be in `{', '.join(acceptable_actions)}`")

        query = """INSERT INTO strike_actions(guild_id,action,needed_strikes,time)
                    VALUES($1,$2,$3,$4) RETURNING *
                """

        insert = await self.bot.pool.fetchrow(query, ctx.guild.id, action.lower(), number, time)
        embed = discord.Embed()
        embed.color = discord.Color.green()
        embed.add_field(name="Needed strikes",value=f"`{number}`")
        embed.add_field(name="Action", value=f"`{action.lower()}`")
        if time:
            embed.add_field(name="Time for punishment", value=f"`{time}`")

        await ctx.send(f"Added a new punishment when a user reaches `{number}` strikes.",embed=embed)


def setup(bot):
    bot.add_cog(Settings(bot))