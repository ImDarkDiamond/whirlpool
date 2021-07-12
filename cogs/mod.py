from discord.ext import commands, menus
from utilities import cache
import discord
import textwrap
import datetime
import traceback
import modlog_utils


class ModConfig:
    __slots__ = ('id','modrole','muterole','modlogs','messagelogs','serverlogs',
                'max_newlines','bot')

    @classmethod
    async def from_record(cls, record, bot):
        self = cls()

        self.bot = bot
        self.id = record['id']
        self.modrole = record['modrole']
        self.muterole = record['muterole']
        self.modlogs = record['modlogs']
        self.messagelogs = record['messagelogs'],
        self.serverlogs = record['serverlogs'],
        self.max_newlines = record['max_newlines']

        return self

    @property
    def mute_role(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.muterole and guild.get_role(self.muterole)

    @property
    def mod_logs(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.modlogs and guild.get_channel(self.modlogs)

    # def is_muted(self, member):
    #     return member.id in self.muted_members

    async def apply_mute(self, member, reason):
        if self.muterole:
            await member.add_roles(discord.Object(id=self.muterole), reason=reason)


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cache.cache()
    async def get_guild_config(self, guild_id):
        query = """SELECT * FROM guild_settings WHERE id=$1;"""
        async with self.bot.pool.acquire(timeout=300.0) as con:
            record = await con.fetchrow(query, guild_id)
            if record is not None:
                return await ModConfig.from_record(record, self.bot)
            return None

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def strike(self, ctx, strikes: int, users: commands.Greedy[discord.Member], *, reason: str = None) -> None:
        
        if strikes < 1:
            return await ctx.send("Amount of strikes must be above **1**")

        final_string = ""
        config = await self.get_guild_config(ctx.guild.id)
        channel = config and config.mod_logs

        for user in users:
            query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                       VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                       DO UPDATE SET strikes = guild_strikes.strikes + $3
                       RETURNING * 
                    """
        
            update = await self.bot.pool.fetchrow(query, ctx.guild.id, user.id, strikes)

            if channel:
                try:
                    message = modlog_utils.assemble_message(
                        "strike_add",
                        1,
                        strikes_removed=None,
                        strikes_added=strikes,
                        strikes={'old':update['strikes']-strikes,'new':update['strikes']},
                        reason=reason,

                        mod=ctx.author,
                        user=user
                    )

                    await channel.send(message)
                except:
                    pass

            final_string += f"Gave `{strikes}` strikes to **{user.name}**#{user.discriminator} for a total of `{update['strikes']}` strikes ({update['strikes']-strikes} → {update['strikes']})\n"

        await ctx.send(final_string)

def setup(bot):
    bot.add_cog(Mod(bot))