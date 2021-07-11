from discord import User, Guild
import mod_config
from time import strftime

def assemble_message(key: str, case_id:int, reason:str=None):
    
    time_string = f"`[{strftime('%H:%M:%S')}]`"
    reason_string = f"`[ Reason ]` {reason}"

    quick_user = mod_config.message_key.get("quick_user")
    id_shortcut = mod_config.message_key.get("id_shortcut")
    strike_shortcut = mod_config.message_key.get("strike_shortcut")

    main_string = mod_config.message_key[key.lower()].format(
        mod=quick_user.format(username="ibx34",discrim="6030"),
        user=quick_user.format(username="mellowmarshe",discrim="0001"),
        user_id=id_shortcut.format(id=300088143422685185),
        time="**10** minutes",
        notes_added=str(2),
        notes_removed=str(4),
        strikes_removed=str(14),
        strikes_added=str(343),
        strikes=strike_shortcut.format(old=str(200),new=str(400))
    )

    return f"""{time_string} `[{case_id}]` {mod_config.emoji_key[key.lower()]} {main_string}\n{reason_string}"""