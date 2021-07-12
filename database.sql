CREATE TABLE IF NOT EXISTS guild_settings (
    "id"              BIGINT PRIMARY KEY,
    "modrole"         BIGINT,

    "modlogs"         BIGINT,
    "messagelogs"     BIGINT,
    "serverlogs"      BIGINT,
    
    "max_newlines"    BIGINT DEFAULT 0
);