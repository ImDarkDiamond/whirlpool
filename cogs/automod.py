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
import re
import copypastas
from logging_ import ModLogUtils

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #invite_regex

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        if type(message.author) != discord.User:
            if message.author.guild_permissions.administrator:
                return

        invite_search = re.search(mod_config.invite_regex, message.content)
        config = await mod_cache.get_guild_config(self.bot,message.guild.id)
        channel = config and config.mod_logs

        if config:
            if config.copypasta_strikes > 0:
                strikes = config.copypasta_strikes

                for pasta in copypastas.copypastas:
                    if pasta['pasta'].lower() in message.content.lower():
                        try:
                            await message.delete()
                        except:
                            pass                        

                        query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                                VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                                DO UPDATE SET strikes = guild_strikes.strikes + $3
                                RETURNING *
                                """
                    
                        update = await self.bot.pool.fetchrow(query, message.guild.id, message.author.id, strikes)
                        if channel:
                            modlog_messages = await ModLogUtils.assemble_message(
                                "strike_add",
                                strikes_added=strikes,
                                strikes={
                                    'old':update['strikes']-strikes,
                                    'new':update['strikes']
                                },
                                reason=f"\"{pasta['name']}\" copypasta",
                                mod=self.bot.user,
                                user=message.author,
                                guild=message.guild,
                                bot=self.bot
                            )

                            await channel.send(modlog_messages)

                        self.bot.dispatch("strike_add", 
                            guild=message.guild,
                            user=message.author, 
                            strikes=update['strikes'],
                            old_strikes=update['strikes']-strikes, 
                        )
                        break

            if config.max_newlines > 0:
                new_lines = message.content.count("\n")

                if new_lines >= config.max_newlines:
                    try:
                        await message.delete()
                    except:
                        pass
                
                    strikes = new_lines - config.max_newlines
                    

                    query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                            VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                            DO UPDATE SET strikes = guild_strikes.strikes + $3
                            RETURNING *
                            """
                
                    update = await self.bot.pool.fetchrow(query, message.guild.id, message.author.id, strikes)
                    if channel:
                        modlog_messages = await ModLogUtils.assemble_message(
                            "strike_add",
                            strikes_added=strikes,
                            strikes={
                                'old':update['strikes']-strikes,
                                'new':update['strikes']
                            },
                            reason=f"`{new_lines}` new lines in a single message.",
                            mod=self.bot.user,
                            user=message.author,
                            guild=message.guild,
                            bot=self.bot
                        )

                        await channel.send(modlog_messages)

                    self.bot.dispatch("strike_add", 
                        guild=message.guild,
                        user=message.author, 
                        strikes=update['strikes'],
                        old_strikes=update['strikes']-strikes, 
                    )


            if config.max_mentions > 0:
                mentions = len(message.raw_mentions)

                if mentions >= config.max_mentions:
                    try:
                        await message.delete()
                    except:
                        pass
                    
                    strikes = mentions - config.max_mentions
                    

                    query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                            VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                            DO UPDATE SET strikes = guild_strikes.strikes + $3
                            RETURNING *
                            """
                
                    update = await self.bot.pool.fetchrow(query, message.guild.id, message.author.id, strikes)
                    if channel:
                        modlog_messages = await ModLogUtils.assemble_message(
                            "strike_add",
                            strikes_added=strikes,
                            strikes={
                                'old':update['strikes']-strikes,
                                'new':update['strikes']
                            },
                            reason=f"Mentioned `{mentions}` users in a single message.",
                            mod=self.bot.user,
                            user=message.author,
                            guild=message.guild,
                            bot=self.bot
                        )

                        await channel.send(modlog_messages)

                    self.bot.dispatch("strike_add", 
                        guild=message.guild,
                        user=message.author, 
                        strikes=update['strikes'],
                        old_strikes=update['strikes']-strikes, 
                    )

            if config.max_role_mentions > 0:
                role_mentions = len(message.raw_role_mentions)

                if role_mentions >= config.max_role_mentions:
                    try:
                        await message.delete()
                    except:
                        pass

                    strikes = role_mentions - config.max_role_mentions
                    

                    query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                            VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                            DO UPDATE SET strikes = guild_strikes.strikes + $3
                            RETURNING *
                            """
                
                    update = await self.bot.pool.fetchrow(query, message.guild.id, message.author.id, strikes)
                    if channel:
                        modlog_messages = await ModLogUtils.assemble_message(
                            "strike_add",
                            strikes_added=strikes,
                            strikes={
                                'old':update['strikes']-strikes,
                                'new':update['strikes']
                            },
                            reason=f"Mentioned `{role_mentions}` roles in a single message.",
                            mod=self.bot.user,
                            user=message.author,
                            guild=message.guild,
                            bot=self.bot
                        )

                        await channel.send(modlog_messages)

                    self.bot.dispatch("strike_add", 
                        guild=message.guild,
                        user=message.author, 
                        strikes=update['strikes'],
                        old_strikes=update['strikes']-strikes, 
                    )

            if invite_search and config.invite_strikes > 0:
                try:
                    await message.delete()
                except:
                    pass

                strikes = config.invite_strikes
                

                query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                        VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                        DO UPDATE SET strikes = guild_strikes.strikes + $3
                        RETURNING *
                        """
            
                update = await self.bot.pool.fetchrow(query, message.guild.id, message.author.id, strikes)
                if channel:
                    modlog_messages = await ModLogUtils.assemble_message(
                        "strike_add",
                        strikes_added=strikes,
                        strikes={
                            'old':update['strikes']-strikes,
                            'new':update['strikes']
                        },
                        reason=f"Posted an invite link.",
                        mod=self.bot.user,
                        user=message.author,
                        guild=message.guild,
                        bot=self.bot
                    )

                    await channel.send(modlog_messages)

                self.bot.dispatch("strike_add", 
                    message.guild,
                    message.author, 
                    strikes=update['strikes'],
                    old_strikes=update['strikes']-strikes, 
                )

            if config.everyone_strikes > 0:
                if message.channel.permissions_for(message.author).mention_everyone:
                    return

                if re.search(mod_config.everyone_regex, message.content) or re.search(mod_config.here_regex, message.content):
                    try:
                        await message.delete()
                    except:
                        pass

                    strikes = config.everyone_strikes
                    

                    query = """INSERT INTO guild_strikes(guild_id,user_id,strikes)
                            VALUES($1,$2,$3) ON CONFLICT (guild_id, user_id)
                            DO UPDATE SET strikes = guild_strikes.strikes + $3
                            RETURNING *
                            """
                
                    update = await self.bot.pool.fetchrow(query, message.guild.id, message.author.id, strikes)
                    if channel:
                        modlog_messages = await ModLogUtils.assemble_message(
                            "strike_add",
                            strikes_added=strikes,
                            strikes={
                                'old':update['strikes']-strikes,
                                'new':update['strikes']
                            },
                            reason=f"Attempted @\u200beveryone",
                            mod=self.bot.user,
                            user=message.author,
                            guild=message.guild,
                            bot=self.bot
                        )

                        await channel.send(modlog_messages)

                    self.bot.dispatch("strike_add", 
                        message.guild,
                        message.author, 
                        strikes=update['strikes'],
                        old_strikes=update['strikes']-strikes, 
                    )

def setup(bot):
    bot.add_cog(AutoMod(bot))