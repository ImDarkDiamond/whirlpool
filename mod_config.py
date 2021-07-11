emoji_key = {
    "tempmute": "🤐",
    "ban": "🔨",
    "unban": "😇",
    "kick": "👢",
    "strike_add": "🚩",
    "pardon": "🏳️",
    "mute": "🔇",
    "unmute": "🔊",
    "notes_added": "🗒️",
    "notes_removed": "❌",
}
# Emojis used in modlogs.

message_key = {
    "quick_user": "**{username}**#{discrim}",
    "id_shortcut": "(ID:`{id}`)",
    "strike_shortcut": "`[{old} → {new}]`",
    # This is so we can just add like `{quick_user}` in the following messages
    "tempmute": "{mod} tempmuted {user} {user_id} for {time}",
    "ban": "{mod} banned {user} {user_id}",
    "unban": "{mod} unbanned {user} {user_id}",
    "kick": "{mod} kicked {user} {user_id}",
    "strike_add": "{mod} gave `{strikes_added}` strikes {strikes} to {user} {user_id}",
    "pardon": "{mod} pardoned `{strikes_removed}` strikes {strikes} from {user} {user_id}",
    "mute": "{mod} muted {user} {user_id}",
    "unmute": "{mod} unmuted {user} {user_id}",
    "notes_added": "{mod} gave `{notes_added}` notes to {user} {user_id}",
    "notes_removed": "{mod} removed `{notes_removed}` notes from {user} {user_id}",
}

# Messages used in modlogs. Not currently translated, but will most likely in the future.
# Parts like `[hh:mm:ss:]`, `[ reason ]`, `[<case id>]` aren't added here, it would just be useless
# They are instead added when generating the modlogs message.