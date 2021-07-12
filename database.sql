
-- DO $$ 
-- BEGIN
--     IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'StrikeActionType') THEN
--         CREATE TYPE StrikeActionType AS ENUM ('mute','kick','ban','tempmute','tempban');
--     END IF;
-- END$$;


CREATE TABLE IF NOT EXISTS guild_settings (
    "id"              BIGINT PRIMARY KEY,
    "modrole"         BIGINT,
    "muterole"        BIGINT,
    "modlogs"         BIGINT,
    "messagelogs"     BIGINT,
    "serverlogs"      BIGINT,
    
    "max_newlines"    BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS guild_strikes ( 
    "guild_id"        BIGINT NOT NULL,
    "user_id"         BIGINT NOT Null,
    "strikes"         BIGINT DEFAULT 0,

    PRIMARY KEY(guild_id,user_id)
);

CREATE TABLE IF NOT EXISTS strike_actions (
    "guild_id"        BIGINT NOT NULL,
    "action"          StrikeActionType NOT NULL,
    "needed_strikes"  BIGINT NOT NULL,
    "time"            VARCHAR
)