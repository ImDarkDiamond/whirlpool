from re import L
import discord
import mod_cache
import modlog_utils
from discord.ext import commands

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

    async def send_modlog(self,action: str, reason: str) -> None:
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
                case_id=case_id
            )

            await channel.send(message)

    async def mute(self, *args, **kwargs):

        mute_role = self.cache and self.cache.mute_role

        if mute_role:
            strikes = kwargs.get('strikes')
            reason = f"[{kwargs.get('old_strikes')} → {strikes} strikes] Automatic mute for reaching `{strikes}` strikes."

            await self.user.add_roles(
                mute_role,
                reason=reason
            )
        
            await self.send_modlog("mute", reason=reason)

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
        reason = f"[{kwargs.get('old_strikes')} → {strikes} strikes] Automatic ban for reaching `{strikes}` strikes."

        await self.ctx.guild.ban(
            self.user,
            reason=reason,
            delete_message_days=7
        )
    

        await self.send_modlog("ban", reason=reason)