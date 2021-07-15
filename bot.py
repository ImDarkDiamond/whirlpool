from discord.ext import commands
import discord
from utilities._config import Config
import datetime, re
import json, asyncio
import logging
import traceback
import aiohttp
import sys
from collections import Counter, deque, defaultdict

import config
import asyncpg

log = logging.getLogger(__name__)

def _prefix_callable(bot, msg):
    user_id = bot.user.id
    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if msg.guild is None:
        base.append('>>')
    else:
        base.extend(bot.prefixes.get(msg.guild.id, ['>>']))
    return base

class TeddyBear(commands.AutoShardedBot):
    def __init__(self):
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True)
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            reactions=True,
        )

        super().__init__(
            command_prefix=_prefix_callable,
            description="A vortex like discord bot written in python",
            fetch_offline_members=False,
            allowed_mentions=allowed_mentions,
            intents=intents
        )

        self.client_id = config.client_id
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.resumes = defaultdict(list)
        self.identifies = defaultdict(list)
        self.pool = None
        self.db = self.pool
        self.prefixes = Config("prefixes.json")
        self.blacklist = Config('blacklist.json')
        self.mutual_servers = dict()
        self._prev_events = deque(maxlen=10)
        self.spam_control = commands.CooldownMapping.from_cooldown(10, 12.0, commands.BucketType.user)
        self._auto_spam_count = Counter()
        self.started_at = datetime.datetime.utcnow()
        self.message_counters = {"bots":0,"users":0,"commands":0,"self":0}
        self.owners = list()
        self.guild_punishments = dict()
        self.initial_extensions = [
            "cogs.owner",
            "cogs.stats",
            "cogs.strikes",
            "cogs.settings",
            "cogs.StrikeHandler",
            "cogs.mod",
            "cogs.reminders",
            "logging_.BasicLogging",
        ]     

    async def get_mutual_guilds(self, user_id: int, update_bypass: bool=False):

        try:
            if self.mutual_servers.get(user_id) and not update_bypass:
                return self.mutual_servers.get(user_id)

            for guild in self.guilds:
                if user_id in [member.id for member in guild.members]:
                    if self.mutual_servers.get(user_id):
                        self.mutual_servers[user_id].append(guild.id)
                        continue

                    self.mutual_servers[user_id] = [guild.id]
            
            return self.mutual_servers.get(user_id)
        except Exception as err:
            print(err)

    async def send_message(self, channel_id: int, *args, **kwargs):
        """Convenience for sending messages w/ self.bot.http.send_message"""

        await self.http.send_message(
            channel_id,
            *args,
            **kwargs
        )

    def _clear_gateway_data(self):
        one_week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        for shard_id, dates in self.identifies.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

        for shard_id, dates in self.resumes.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

    async def on_socket_response(self, msg):
        self._prev_events.append(msg)

    async def before_identify_hook(self, shard_id, *, initial):
        self._clear_gateway_data()
        self.identifies[shard_id].append(datetime.datetime.utcnow())
        await super().before_identify_hook(shard_id, initial=initial)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f'{original.__class__.__name__}: {original}', file=sys.stderr)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(error)

    def get_guild_prefixes(self, guild, *, local_inject=_prefix_callable):
        proxy_msg = discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        return self.prefixes.get(guild_id, ['>>'])

    async def set_guild_prefixes(self, guild, prefixes):
        if len(prefixes) == 0:
            await self.prefixes.put(guild.id, [])
        elif len(prefixes) > 10:
            raise RuntimeError('Cannot have more than 10 custom prefixes.')
        else:
            await self.prefixes.put(guild.id, sorted(set(prefixes), reverse=True))


    async def add_to_blacklist(self, object_id):
        await self.blacklist.put(object_id, True)

    async def remove_from_blacklist(self, object_id):
        try:
            await self.blacklist.remove(object_id)
        except KeyError:
            pass

    async def query_member_named(self, guild, argument, *, cache=False):
        """Queries a member by their name, name + discrim, or nickname.
        Parameters
        ------------
        guild: Guild
            The guild to query the member in.
        argument: str
            The name, nickname, or name + discrim combo to check.
        cache: bool
            Whether to cache the results of the query.
        Returns
        ---------
        Optional[Member]
            The member matching the query or None if not found.
        """
        if len(argument) > 5 and argument[-5] == '#':
            username, _, discriminator = argument.rpartition('#')
            members = await guild.query_members(username, limit=100, cache=cache)
            return discord.utils.get(members, name=username, discriminator=discriminator)
        else:
            members = await guild.query_members(argument, limit=100, cache=cache)
            return discord.utils.find(lambda m: m.name == argument or m.nick == argument, members)

    async def get_or_fetch_member(self, guild, member_id):
        """Looks up a member in cache or fetches if not found.
        Parameters
        -----------
        guild: Guild
            The guild to look in.
        member_id: int
            The member ID to search for.
        Returns
        ---------
        Optional[Member]
            The member or None if not found.
        """

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard = self.get_shard(guild.shard_id)
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    async def resolve_member_ids(self, guild, member_ids):
        """Bulk resolves member IDs to member instances, if possible.
        Members that can't be resolved are discarded from the list.
        This is done lazily using an asynchronous iterator.
        Note that the order of the resolved members is not the same as the input.
        Parameters
        -----------
        guild: Guild
            The guild to resolve from.
        member_ids: Iterable[int]
            An iterable of member IDs.
        Yields
        --------
        Member
            The resolved members.
        """

        needs_resolution = []
        for member_id in member_ids:
            member = guild.get_member(member_id)
            if member is not None:
                yield member
            else:
                needs_resolution.append(member_id)

        total_need_resolution = len(needs_resolution)
        if total_need_resolution == 1:
            shard = self.get_shard(guild.shard_id)
            if shard.is_ws_ratelimited():
                try:
                    member = await guild.fetch_member(needs_resolution[0])
                except discord.HTTPException:
                    pass
                else:
                    yield member
            else:
                members = await guild.query_members(limit=1, user_ids=needs_resolution, cache=True)
                if members:
                    yield members[0]
        elif total_need_resolution <= 100:
            # Only a single resolution call needed here
            resolved = await guild.query_members(limit=100, user_ids=needs_resolution, cache=True)
            for member in resolved:
                yield member
        else:
            # We need to chunk these in bits of 100...
            for index in range(0, total_need_resolution, 100):
                to_resolve = needs_resolution[index:index + 100]
                members = await guild.query_members(limit=100, user_ids=to_resolve, cache=True)
                for member in members:
                    yield member

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()

        self.pool = await asyncpg.create_pool(
            config.postgresql,
            max_size=150
        )

        for extension in self.initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as err:
                log.error(f"Error while loading extension \"{extension}\".",exc_info=err)   

        with open("database.sql") as f:
            await self.pool.execute(f.read())
    
        app_info = await self.application_info()
        app_team = app_info.team

        self.owners.append([x.id for x in app_team.members])
        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_shard_resumed(self, shard_id):
        print(f'Shard ID {shard_id} has resumed...')
        self.resumes[shard_id].append(datetime.datetime.utcnow())

    @discord.utils.cached_property
    def stats_webhook(self):
        wh_id, wh_token = self.config.stat_webhook
        hook = discord.Webhook.partial(id=wh_id, token=wh_token, adapter=discord.AsyncWebhookAdapter(self.session))
        return hook
    
    def log_spammer(self, ctx, message, retry_after, *, autoblock=False):
        guild_name = getattr(ctx.guild, 'name', 'No Guild (DMs)')
        guild_id = getattr(ctx.guild, 'id', None)
        fmt = 'User %s (ID %s) in guild %r (ID %s) spamming, retry_after: %.2fs'
        log.warning(fmt, message.author, message.author.id, guild_name, guild_id, retry_after)
        if not autoblock:
            return

        wh = self.stats_webhook
        embed = discord.Embed(title='Auto-blocked Member', colour=0xDDA453)
        embed.add_field(name='Member', value=f'{message.author} (ID: {message.author.id})', inline=False)
        embed.add_field(name='Guild Info', value=f'{guild_name} (ID: {guild_id})', inline=False)
        embed.add_field(name='Channel Info', value=f'{message.channel} (ID: {message.channel.id}', inline=False)
        embed.timestamp = datetime.datetime.utcnow()
        return wh.send(embed=embed)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=commands.Context)

        if ctx.command is None:
            return

        if ctx.author.id in self.blacklist:
            return

        if ctx.guild is not None and ctx.guild.id in self.blacklist:
            return

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
        retry_after = bucket.update_rate_limit(current)
        author_id = message.author.id
        if retry_after and author_id != self.owner_id:
            self._auto_spam_count[author_id] += 1
            if self._auto_spam_count[author_id] >= 5:
                await self.add_to_blacklist(author_id)
                del self._auto_spam_count[author_id]
                await self.log_spammer(ctx, message, retry_after, autoblock=True)
            else:
                self.log_spammer(ctx, message, retry_after)
            return
        else:
            self._auto_spam_count.pop(author_id, None)

        await self.invoke(ctx)


    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_guild_join(self, guild):
        if guild.id in self.blacklist:
            await guild.leave()

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        try:
            super().run(config.token, reconnect=True)
        finally:
            with open('prev_events.log', 'w', encoding='utf-8') as fp:
                for data in self._prev_events:
                    try:
                        x = json.dumps(data, ensure_ascii=True, indent=4)
                    except:
                        fp.write(f'{data}\n')
                    else:
                        fp.write(f'{x}\n')

    @property
    def config(self):
        return __import__('config')