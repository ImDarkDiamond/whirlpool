from re import L
import discord
import mod_cache
import modlog_utils
import pytz
from discord.ext import commands
from utilities import userfriendlly, time as TimeTime
import datetime
from logging_ import ModLogUtils
class Strikes(object):
    def __init__(self, bot, guild, mod, user):
        self.user = user
        self.guild = guild
        self.mod = mod
        self.bot = bot
        self.cache: mod_cache.ModConfig = None
    
    def actions(self, action, *args, **kwargs):
        method = getattr(self, action, lambda: "Invalid action")
        return method(*args, **kwargs)

    async def fill_cache(self):
        self.cache = await mod_cache.get_guild_config(self.bot, self.guild.id)

    async def send_modlog(self, action: str, reason: str, **kwargs) -> None:
        channel = self.cache and self.cache.mod_logs
        case_id = await ModLogUtils.insert(
            self.bot,
            guild=self.guild,
            target_id=self.user.id,
            reason=reason,
            action_type=action,
            mod=self.mod
        )

        if channel:

            message = await ModLogUtils.assemble_message(
                action,
                reason=reason,
                mod=self.mod,
                user=self.user,
                guild=self.guild,
                bot=self.bot,
                time=kwargs.get("time"),
                case_id=case_id
            )

            await channel.send(message)

    async def mute(self, *args, **kwargs):
        try:
            mute_role = self.cache and self.cache.mute_role

            if mute_role:
                strikes = kwargs.get('strikes')
                time = kwargs.get('time')
                reason = f"[{kwargs.get('old_strikes')} → {strikes} strikes] Automatic mute for reaching `{strikes}` strikes."

                if time:
                    reminder = self.bot.get_cog('Reminder')
                    duration = userfriendlly.FutureTime(time).dt.replace(tzinfo=pytz.UTC)

                    timer = await reminder.create_timer(duration, 'tempmute', self.guild.id,
                                                                            self.mod.id,
                                                                            self.user.id,
                                                                            mute_role.id,
                                                                            created=datetime.datetime.now().replace(tzinfo=pytz.UTC))

                await self.user.add_roles(
                    mute_role,
                    reason=reason
                )
            
                await self.send_modlog(
                    "mute" if not time else "tempmute", 
                    reason=reason,
                    time=TimeTime.human_timedelta(duration) if time else None
                )

        except Exception as err:
            print(err)

    async def kick(self, *args, **kwargs):

        strikes = kwargs.get('strikes')
        reason = f"[{kwargs.get('old_strikes')} → {strikes} strikes] Automatic kick for reaching `{strikes}` strikes."

        await self.guild.kick(
            self.user,
            reason=reason
        )
    

        await self.send_modlog("kick", reason=reason)

    async def ban(self, *args, **kwargs):

        strikes = kwargs.get('strikes')
        time = kwargs.get('time')
        reason = f"[{kwargs.get('old_strikes')} → {strikes} strikes] Automatic ban for reaching `{strikes}` strikes."

        if time:
            reminder = self.bot.get_cog('Reminder')
            duration = userfriendlly.FutureTime(time).dt.replace(tzinfo=pytz.UTC)

            timer = await reminder.create_timer(duration, 'tempban', self.guild.id,
                                                                    self.mod.id,
                                                                    self.user.id,
                                                                    None,
                                                                    created=datetime.datetime.now().replace(tzinfo=pytz.UTC))

        await self.guild.ban(
            self.user,
            reason=reason,
        )
    

        await self.send_modlog("ban" if not time else "tempban", reason=reason, time=TimeTime.human_timedelta(duration))