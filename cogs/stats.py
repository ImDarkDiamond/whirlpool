from discord.ext import commands, menus
import discord
import textwrap
import datetime
import traceback


class Error(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @discord.utils.cached_property
    def webhook(self):

        wh_id, wh_token = self.bot.config.stat_webhook
        hook = discord.Webhook.partial(id=wh_id, token=wh_token, session=self.bot.session)
        return hook

    async def log_error(self, *, ctx=None, extra=None):
        e = discord.Embed(title='Error', colour=0xdd5f53)
        e.description = f'```py\n{traceback.format_exc()}\n```'
        e.add_field(name='Extra', value=extra, inline=False)
        e.timestamp = datetime.datetime.utcnow()

        if ctx is not None:
            fmt = '{0} (ID: {0.id})'
            author = fmt.format(ctx.author)
            channel = fmt.format(ctx.channel)
            guild = 'None' if ctx.guild is None else fmt.format(ctx.guild)

            e.add_field(name='Author', value=author)
            e.add_field(name='Channel', value=channel)
            e.add_field(name='Guild', value=guild)

        await self.webhook.send(embed=e)

    async def send_guild_stats(self, e, guild):
        e.add_field(name='Name', value=guild.name)
        e.add_field(name='ID', value=guild.id)
        e.add_field(name='Shard ID', value=guild.shard_id or 'N/A')
        e.add_field(name='Owner', value=f'{guild.owner} (ID: {guild.owner_id})')

        bots = sum(m.bot for m in guild.members)
        total = guild.member_count
        e.add_field(name='Members', value=str(total))
        e.add_field(name='Bots', value=f'{bots} ({bots/total:.2%})')

        if guild.icon:
            e.set_thumbnail(url=guild.icon_url)

        if guild.me:
            e.timestamp = guild.me.joined_at

        await self.webhook.send(embed=e)
        
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        e = discord.Embed(colour=0x53dda4, title='New Guild') # green colour
        await self.send_guild_stats(e, guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        e = discord.Embed(colour=0xdd5f53, title='Left Guild') # red colour
        await self.send_guild_stats(e, guild)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, (commands.CommandInvokeError, commands.ConversionError)):
            return

        error = error.original
        if isinstance(error, (discord.Forbidden, discord.NotFound, menus.MenuError)):
            return

        e = discord.Embed(title='Command Error', colour=0xcc3366)
        e.add_field(name='Name', value=ctx.command.qualified_name)
        e.add_field(name='Author', value=f'{ctx.author} (ID: {ctx.author.id})')

        fmt = f'Channel: {ctx.channel} (ID: {ctx.channel.id})'
        if ctx.guild:
            fmt = f'{fmt}\nGuild: {ctx.guild} (ID: {ctx.guild.id})'

        e.add_field(name='Location', value=fmt, inline=False)
        e.add_field(name='Content', value=textwrap.shorten(ctx.message.content, width=512))

        exc = ''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False))
        e.description = f'```py\n{exc}\n```'
        e.timestamp = datetime.datetime.utcnow()
        await self.webhook.send(embed=e)

def setup(bot):
    bot.add_cog(Error(bot))