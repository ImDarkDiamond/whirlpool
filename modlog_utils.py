from discord import User, Guild
import discord
import mod_config
from time import strftime
from bot import TeddyBear


async def insert_mod_action(ctx, **kwargs) -> int:

    async with ctx.bot.pool.acquire() as conn:

        query = """INSERT INTO mod_actions(guild_id,mod_id,target_id,action_type,reason) 
                    VALUES($1,$2,$3,$4,$5) RETURNING *
                """

        insert = await conn.fetchrow(
            query,
            ctx.guild.id,
            ctx.author.id,
            kwargs.get("target_id"),
            kwargs.get("action_type"),
            kwargs.get("reason"),
        )

    return insert["case_id"]


async def assemble_message(
    key: str,
    ctx=None,
    notes_added: int = None,
    notes_removed: int = None,
    strikes_added: int = None,
    strikes_removed: int = None,
    strikes: dict = None,
    reason: str = None,
    user: User = None,
    mod: User = None,
    case_id: int = None
) -> str:

    if case_id == None:
        case_id = await insert_mod_action(
            ctx=ctx, action_type=key, reason=reason, target_id=user.id
        )

    time_string = f"`[{strftime('%H:%M:%S')}]`"
    reason_string = f"`[ Reason ]` {reason}"

    quick_user = mod_config.message_key.get("quick_user")
    id_shortcut = mod_config.message_key.get("id_shortcut")
    strike_shortcut = mod_config.message_key.get("strike_shortcut")

    main_string = mod_config.message_key[key.lower()].format(
        mod=quick_user.format(username=mod.name, discrim=mod.discriminator),
        user=quick_user.format(username=user.name, discrim=user.discriminator),
        user_id=id_shortcut.format(id=user.id),
        time="**10** minutes",
        notes_added=notes_added,
        notes_removed=notes_removed,
        strikes_removed=strikes_removed,
        strikes_added=strikes_added,
        strikes=strike_shortcut.format(**strikes) if strikes else None,
    )

    return f"""{time_string} `[{case_id}]` {mod_config.emoji_key[key.lower()]} {main_string}\n{reason_string}"""
