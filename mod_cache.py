from utilities import cache
import discord

class ModConfig:
    __slots__ = ('id','modrole','muterole','modlogs','messagelogs','serverlogs',
                'max_newlines','bot', 'mutedmembers','voicelogs','avatarlogs',
                'max_mentions','max_role_mentions','invite_strikes','everyone_strikes',
                'copypasta_strikes')

    @classmethod
    async def from_record(cls, record, bot):
        self = cls()

        self.bot = bot
        self.id = record['id']
        self.modrole = record['modrole']
        self.muterole = record['muterole']
        self.modlogs = record['modlogs']
        self.messagelogs = record['messagelogs']
        self.serverlogs = record['serverlogs']
        self.avatarlogs = record['avatarlogs']
        self.max_newlines = record['max_newlines']
        self.voicelogs = record['voicelogs']
        self.mutedmembers = set(record['mutedmembers'] or [])
        self.max_mentions = record['max_mentions']
        self.max_role_mentions = record['max_role_mentions']
        self.invite_strikes = record['invite_strikes']
        self.everyone_strikes = record['everyone_strikes']
        self.copypasta_strikes = record['copypasta_strikes']

        return self

    @property
    def mute_role(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.muterole and guild.get_role(self.muterole)

    @property
    def mod_logs(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.modlogs and guild.get_channel(self.modlogs)

    @property
    def server_logs(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.serverlogs and guild.get_channel(self.serverlogs)

    @property
    def message_logs(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.messagelogs and guild.get_channel(self.messagelogs)

    @property
    def voice_logs(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.messagelogs and guild.get_channel(self.voicelogs)

    @property
    def avatar_logs(self):
        guild = self.bot.get_guild(self.id)
        return guild and self.messagelogs and guild.get_channel(self.avatarlogs)


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
            dumb = await ModConfig.from_record(record, bot)
            print(dumb)
            return dumb
        return None