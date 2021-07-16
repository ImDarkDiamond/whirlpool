from discord import User, Guild
import discord
import mod_config
import typing
from time import strftime
from bot import TeddyBear

async def insert(bot, **kwargs) -> int:
        
    async with bot.pool.acquire() as conn:

        query = """INSERT INTO mod_actions(guild_id,mod_id,target_id,action_type,reason) 
                    VALUES($1,$2,$3,$4,$5) RETURNING *
                """

        insert = await conn.fetchrow(
            query,
            kwargs.get("guild").id,
            kwargs.get("mod").id,
            kwargs.get("target_id"),
            kwargs.get("action_type"),
            kwargs.get("reason"),
        )

    return insert["case_id"]

async def assemble_message(
    key: str,
    guild: discord.Guild,
    user: typing.Union[discord.User,discord.Member],
    mod: typing.Union[discord.User,discord.Member],
    bot,
    **kwargs
) -> str:

    case_id = kwargs.get("case_id")
    reason = kwargs.get("reason") or "[no reason provided]"
    time = kwargs.get("time")
    notes_added = kwargs.get("notes_added")
    notes_removed = kwargs.get("notes_removed")
    strikes_added = kwargs.get("strikes_added")
    strikes_removed = kwargs.get("strikes_removed")
    strikes = kwargs.get("strikes")

    if case_id == None:
        case_id = await insert(action_type=key, reason=reason, target_id=user.id, bot=bot, guild=guild, mod=mod)

    time_string = f"`[{strftime('%H:%M:%S')}]`"
    reason_string = f"`[ Reason ]` {reason}"        

    quick_user = mod_config.message_key.get("quick_user")
    id_shortcut = mod_config.message_key.get("id_shortcut")
    strike_shortcut = mod_config.message_key.get("strike_shortcut")

    main_string = mod_config.message_key[key.lower()].format(
        mod=quick_user.format(username=mod.name, discrim=mod.discriminator),
        user=quick_user.format(username=user.name, discrim=user.discriminator),
        user_id=id_shortcut.format(id=user.id),
        time=time,        
        notes_added=notes_added,
        notes_removed=notes_removed,
        strikes_removed=strikes_removed,
        strikes_added=strikes_added,
        strikes=strike_shortcut.format(**strikes) if strikes else None,    
    )

    return f"""{time_string} `[{case_id}]` {mod_config.emoji_key[key.lower()]} {main_string}\n{reason_string}"""
