from utilities import cache
import discord

class ModConfig:
    __slots__ = ('id','modrole','muterole','modlogs','messagelogs','serverlogs',
                'max_newlines','bot', 'mutedmembers')

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
        self.mutedmembers = set(record['mutedmembers'] or [])

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

@cache.cache()
async def get_guild_config(bot, guild_id):
    query = """SELECT * FROM guild_settings WHERE id=$1;"""
    async with bot.pool.acquire(timeout=300.0) as con:
        record = await con.fetchrow(query, guild_id)
        if record is not None:
            return await ModConfig.from_record(record, bot)
        return None