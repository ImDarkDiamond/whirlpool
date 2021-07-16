from re import L
import discord
import mod_cache
import modlog_utils
import pytz
from discord.ext import commands
from utilities import userfriendlly, time as TimeTime
class Strikes(object):
    def __init__(self, ctx, user):
        self.user = user
        self.ctx = ctx
        self.bot = ctx.bot
        self.cache: mod_cache.ModConfig = None
    
    def actions(self, action, *args, **kwargs):
        method = getattr(self, action, lambda: "Invalid action")
        return method(*args, **kwargs)

    async def fill_cache(self):
        self.cache = await mod_cache.get_guild_config(self.bot, self.ctx.guild.id)

    async def send_modlog(self, action: str, reason: str, **kwargs) -> None:
        channel = self.cache and self.cache.mod_logs
        case_id = await modlog_utils.insert_mod_action(
            self.ctx,
            target_id=self.user.id,
            reason=reason,
            action_type=action
        )

        if channel:

            message = await modlog_utils.assemble_message(
                action,
                ctx=self.ctx,
                reason=reason,
                mod=self.bot.user,
                user=self.user,
                case_id=case_id,
                time=kwargs.get("time")
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

                    timer = await reminder.create_timer(duration, 'tempmute', self.ctx.guild.id,
                                                                            self.ctx.author.id,
                                                                            self.user.id,
                                                                            mute_role.id,
                                                                            created=self.ctx.message.created_at)

                await self.user.add_roles(
                    mute_role,
                    reason=reason
                )
            
                await self.send_modlog(
                    "mute" if not time else "tempmute", 
                    reason=reason,
                    time=TimeTime.human_timedelta(duration)
                )

        except Exception as err:
            print(err)

    async def kick(self, *args, **kwargs):

        strikes = kwargs.get('strikes')
        reason = f"[{kwargs.get('old_strikes')} → {strikes} strikes] Automatic kick for reaching `{strikes}` strikes."

        await self.ctx.guild.kick(
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

            timer = await reminder.create_timer(duration, 'tempban', self.ctx.guild.id,
                                                                    self.ctx.author.id,
                                                                    self.user.id,
                                                                    None,
                                                                    created=self.ctx.message.created_at)

        await self.ctx.guild.ban(
            "ban" if not time else "tempban", 
            reason=reason,
            time=TimeTime.human_timedelta(duration)
        )
    

        await self.send_modlog("ban", reason=reason)