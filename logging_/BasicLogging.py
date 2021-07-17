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
import zlib
from PIL import Image
from io import BytesIO

class BasicLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def assemble_image(self, before, after, id) -> discord.File:
        try:
            # try:
            #     beforeA = await before.avatar.read()
            # except Exception as err:
            #     beforeA = await before.default_avatar.read()

            # try:
            #     afterA = await after.avatar.read()
            # except Exception as err:
            #     afterA = await after.default_avatar.read()

            before_img = Image.open(BytesIO(before)).resize((512,512))
            after_img = Image.open(BytesIO(after)).resize((512,512))

            canvas = Image.new('RGB', (before_img.width + after_img.width,512))
            canvas.paste(before_img,(0,0))
            canvas.paste(after_img,(after_img.width,0))

            fp = BytesIO()
            canvas.save(fp, "png")

            # return discord.File(BytesIO(canvas.tobytes("jpeg", "RGB")),f"{before.id}-avatar-change.jpeg")
            file =  discord.File(BytesIO(fp.getvalue()),f"{id}-avatar-change.png")
            return file
        except Exception as err:
            traceback.print_exc(limit=2)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        try:
            quick_user = mod_config.message_key.get("quick_user")
            id_shortcut = mod_config.message_key.get("id_shortcut")


            # Check for if they updated their name or discrim. :3
    
            guilds = await self.bot.get_mutual_guilds(before.id, update_bypass=True)
            # Enable bypass so we always get new servers. We may have been added to 
            # a server where the user is also! 

            # Maybe getting the avatars before the loop is smart...
            # Just shortcut for avatars if it has changed.
            if before.avatar != after.avatar:
                before_img = await before.avatar.read() or await before.default_avatar.read()
                after_img = await after.avatar.read() or await before.default_avatar.read()

            for server in guilds:
                config = await mod_cache.get_guild_config(self.bot,server)
                log_channel = config and config.server_logs
                if log_channel:

                    if before.name != after.name:
                        message = modlog_utils.assemble_reg_message(
                            key="name_change",
                            user=quick_user.format(username=before.name,discrim=before.discriminator),
                            new=after.name,
                            origin=before.name,
                            user_id=id_shortcut.format(id=before.id)
                        )
                        await config.server_logs.send(message)

                    if before.discriminator != after.discriminator:
                        message = modlog_utils.assemble_reg_message(
                            key="discrim_change",
                            user=quick_user.format(username=before.name,discrim=before.discriminator),
                            new=after.discriminator,
                            origin=before.discriminator,
                            user_id=id_shortcut.format(id=before.id)
                        )
                        await config.server_logs.send(message)

                    if before.avatar != after.avatar:
                        message = modlog_utils.assemble_reg_message(
                            key="avatar_change",
                            user=quick_user.format(username=before.name,discrim=before.discriminator),
                            user_id=id_shortcut.format(id=before.id)
                        )

                        image = await self.assemble_image(before_img,after_img,id=before.id)
                        await config.avatar_logs.send(message,file=image)
        except Exception as err:
            print(f"err: {err}")
                    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            config = await mod_cache.get_guild_config(self.bot,member.guild.id)
            quick_user = mod_config.message_key.get("quick_user")
            id_shortcut = mod_config.message_key.get("id_shortcut")
    
            if not config:
                return

            if not config.server_logs:
                return
            
            message = modlog_utils.assemble_reg_message(
                key="member_join",
                user=quick_user.format(username=member.name,discrim=member.discriminator),
                user_id=id_shortcut.format(id=member.id),
                account_age=time.human_timedelta(member.created_at),
                days_ago=(datetime.datetime.utcnow().replace(tzinfo=None) - member.created_at.replace(tzinfo=None)).days
            )
            await config.server_logs.send(message)            
        except Exception as err:
            print(err)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            config = await mod_cache.get_guild_config(self.bot,member.guild.id)
            quick_user = mod_config.message_key.get("quick_user")
            id_shortcut = mod_config.message_key.get("id_shortcut")
    
            if not config:
                return

            if not config.server_logs:
                return
            
            message = modlog_utils.assemble_reg_message(
                key="member_leave",
                user=quick_user.format(username=member.name,discrim=member.discriminator),
                user_id=id_shortcut.format(id=member.id),
                joined_at=time.human_timedelta(member.joined_at),
                days_ago=(datetime.datetime.utcnow().replace(tzinfo=None) - member.joined_at.replace(tzinfo=None)).days,
                roles=', '.join([f"`{role}`" for role in member.roles])
            )
            await config.server_logs.send(message)            
        except Exception as err:
            print(err)

    @commands.Cog.listener()
    async def on_message_delete(self, message):

        # Bots are stinky
        if message.author.bot: return

        try:
            config = await mod_cache.get_guild_config(self.bot,message.guild.id)
            quick_user = mod_config.message_key.get("quick_user")
            id_shortcut = mod_config.message_key.get("id_shortcut")
    
            if not config:
                return

            if not config.message_logs:
                return        

            embed = discord.Embed(color=0x71a2b1)

            if len(message.content) > 3999:
                url = await self.bot.generate_gist(message.content)
                embed.description = f"[`📄 View`]({url['url']}) | [`📩 Download`]({url['url']}/download)"

            if len(message.content) < 3999:
                embed.description = message.content

            message = modlog_utils.assemble_reg_message(
                key="message_delete",
                user=quick_user.format(username=message.author.name,discrim=message.author.discriminator),
                user_id=id_shortcut.format(id=message.author.id),
                channel=message.channel.mention
            )      

            await config.message_logs.send(message, embed=embed)    
        except Exception as err:
            print(err)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):

        # Bots are stinky
        if before.author.bot: return

        # Incase a message was pinned, etc. we dont want those.
        if after.content == before.content: return

        try:
            config = await mod_cache.get_guild_config(self.bot,before.guild.id)
            quick_user = mod_config.message_key.get("quick_user")
            id_shortcut = mod_config.message_key.get("id_shortcut")
    
            if not config:
                return

            if not config.message_logs:
                return        

            embed = discord.Embed(color=0x71a2b1)

            if len(before.content) >= 1024 and len(after.content) >= 1024:
                url = await self.bot.generate_gist(before.content,after.content)
                embed.description = "Seems both the before, and after cotnent are too big for embeds!\n" \
                                    f"[`📄 View`]({url['url']}) | [`📩 Download`]({url['url']}/download)"

            else:
                if len(before.content) >= 1024:
                    url = await self.bot.generate_gist(before.content)
                    embed.add_field(name="Before", value=f"[`📄 View`]({url['url']}) | [`📩 Download`]({url['url']}/download)", inline=False)
                else:
                    embed.add_field(name="Before", value=before.content)

                if len(after.content) >= 1024:
                    url = await self.bot.generate_gist(after.content)
                    embed.add_field(name="After", value=f"[`📄 View`]({url['url']}) | [`📩 Download`]({url['url']}/download)", inline=False)    
                else:
                    embed.add_field(name="After", value=after.content, inline=False)

            message = modlog_utils.assemble_reg_message(
                key="message_edit",
                user=quick_user.format(username=before.author.name,discrim=before.author.discriminator),
                user_id=id_shortcut.format(id=before.author.id),
                channel=before.channel.mention
            )          

            await config.message_logs.send(message, embed=embed)
        except Exception as err:
            print(err)

def setup(bot):
    bot.add_cog(BasicLogging(bot))