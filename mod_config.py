emoji_key = {
    "tempmute": "🤐",
    "ban": "🔨",
    "unban": "🔧",
    "kick": "👢",
    "strike_add": "🚩",
    "pardon": "🏳️",
    "mute": "🔇",
    "unmute": "🔊",
    "note_add": "🗒️",
    "note_remove": "🗑️",
    "tempban": "⏲️",
    "message_delete": "❌",
    "message_edit": "⚠",
    "member_join": "📥",
    "member_leave": "📤",
    "voice_join": "<:voiceJoin2:864696361130524693>",
    "voice_leave": "<:voiceLeave2:864696361207463977>",
    "voice_move": "<:voiceChange2:864696361130524696>",
    "name_change": "📛",
    "discrim_change": "📛",
    "avatar_change": "🖼️"
}
# Emojis used in modlogs.

message_key = {
    "quick_user": "**{username}**#{discrim}",
    "id_shortcut": "(ID:`{id}`)",
    "strike_shortcut": "`[{old} → {new}]`",
    # This is so we can just add like `{quick_user}` in the following messages
    "tempmute": "{mod} tempmuted {user} {user_id} for {time}",
    "tempban": "{mod} banned {user} {user_id} for {time}",
    "ban": "{mod} banned {user} {user_id}",
    "unban": "{mod} unbanned {user} {user_id}",
    "kick": "{mod} kicked {user} {user_id}",
    "strike_add": "{mod} gave `{strikes_added}` strikes {strikes} to {user} {user_id}",
    "pardon": "{mod} pardoned `{strikes_removed}` strikes {strikes} from {user} {user_id}",
    "mute": "{mod} muted {user} {user_id}",
    "unmute": "{mod} unmuted {user} {user_id}",
    "note_add": "{mod} added `{notes_added}` notes to {user} {user_id}",
    "note_remove": "{mod} removed `{notes_removed}` notes from {user} {user_id}",
    "message_delete": "a message by {user} {user_id} was deleted in {channel}",
    "message_edit": "a message by {user} {user_id} was edited in {channel}",
    "member_join": "{user} {user_id} joined the server.\nCreation: {account_age} ({days_ago} days ago)",
    "member_leave": "{user} {user_id} left the server or was kicked.\nRoles: {roles}\nJoined: {joined_at} ({days_ago} days ago)",
    "voice_join": "{user} {user_id} has joined voice channel _{channel}_",
    "voice_leave": "{user} {user_id} has left voice channel _{channel}_",
    "voice_move": "{user} {user_id} has moved voice channels from _{origin}_ to _{new}_",
    "name_change": "{user} {user_id} has updated their name from _{origin}_ to _{new}_",
    "discrim_change": "{user} {user_id} has changed their discriminator from _{origin}_ to _{new}_",
    "avatar_change": "{user} {user_id} has changed their avatar"
}

# Messages used in modlogs. Not currently translated, but will most likely in the future.
# Parts like `[hh:mm:ss:]`, `[ reason ]`, `[<case id>]` aren't added here, it would just be useless
# They are instead added when generating the modlogs message.

custom_emojis = {
    "change": "<:yellowchange:864580282978795581>",
    "x": "<:x:864580283512520735>",
    "infow": "<:white_info:864580282930036737>",
    "question": "<:question:864580283352612874>",
    "plus": "<:plus:864580283343831061>",
    "minus": "<:minus:864580283306475560>",
    "check": "<:greenCheckBox:865423233956315167>", #"<:Check:864580283239235615>",
    "infob": "<:black_info:864580283218264064>"
}