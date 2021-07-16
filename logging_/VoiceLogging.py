from operator import mod
from discord.ext import commands, menus, tasks
from discord.ext.commands.core import command
from utilities import time
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

class VoiceLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        
        try:
            if before.channel != after.channel:

                config = await mod_cache.get_guild_config(self.bot,member.guild.id)
                quick_user = mod_config.message_key.get("quick_user")
                id_shortcut = mod_config.message_key.get("id_shortcut")
                key = "voice_join"

                if not config:
                    return

                if not config.voice_logs:
                    return     

                if before.channel is None:
                    key = "voice_join"

                elif after.channel is None:
                    key = "voice_leave"

                else:
                    key = "voice_move"

                def figure_out_channel():

                    if key == "voice_join": 
                        return after.channel
                    if key == "voice_leave":
                        return before.channel

                message = modlog_utils.assemble_reg_message(
                    key=key,
                    user=quick_user.format(username=member.name,discrim=member.discriminator),
                    user_id=id_shortcut.format(id=member.id),
                    channel=figure_out_channel(),
                    origin=before.channel,
                    new=after.channel
                )          

                await config.voice_logs.send(message)   

        except Exception as err:
            print(err)

def setup(bot):
    bot.add_cog(VoiceLogging(bot))