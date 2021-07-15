
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'strikeactiontype') THEN
        CREATE TYPE StrikeActionType AS ENUM ('mute','kick','ban','tempmute','tempban');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'modactiontype') THEN
        CREATE TYPE ModActionType AS ENUM('mute','kick','ban','tempmute','tempban', 'strike_add', 'pardon', 'note_add', 'note_remove','unmute', 'unban');
    END IF;

END$$;


CREATE TABLE IF NOT EXISTS guild_settings (
    "id"                BIGINT PRIMARY KEY,
    "modrole"           BIGINT,
    "muterole"          BIGINT,
    "modlogs"           BIGINT,
    "messagelogs"       BIGINT,
    "serverlogs"        BIGINT,
    "mutedmembers"      BIGINT[] DEFAULT '{}',
    
    "max_newlines"      BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS guild_strikes ( 
    "guild_id"          BIGINT NOT NULL,
    "user_id"           BIGINT NOT Null,
    "strikes"           BIGINT DEFAULT 0,

                        PRIMARY KEY(guild_id,user_id)
);

CREATE TABLE IF NOT EXISTS punishments (
    "action_id"         BIGSERIAL UNIQUE,
    "guild_id"          BIGINT NOT NULL,
    "action"            StrikeActionType NOT NULL,
    "strikes"           BIGINT NOT NULL,
    "time"              VARCHAR,

                        PRIMARY KEY(guild_id,strikes,action)
);

CREATE TABLE IF NOT EXISTS mod_actions (
    "case_id"           BIGSERIAL PRIMARY KEY,
    "guild_id"          BIGINT NOT NULL,
    "mod_id"            BIGINT NOT NULL,
    "target_id"         BIGINT NOT NULL,
    "action_type"       ModActionType NOT NULL,
    "created_at"        TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    "reason"            VARCHAR(2000)
);

CREATE TABLE IF NOT EXISTS reminders (
    "id"                SERIAL PRIMARY KEY,
    "expires"           TIMESTAMP WITH TIME ZONE,
    "created"           TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    "event"             VARCHAR,
    "extra"             JSON DEFAULT '{}'::JSONB
);

-- SAVE FOR LATER
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
-- CREATE TABLE IF NOT EXISTS muted_members (
--     "guild_id"          BIGINT NOT NULL,
--     "member_id"         BIGINT NOT NULL,

--                         PRIMARY KEY(guild_id,member_id)
-- )
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 