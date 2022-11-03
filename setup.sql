CREATE TABLE IF NOT EXISTS rewards_roles (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL, 

    requirement INT NOT NULL,

    PRIMARY KEY(guild_id, role_id)
);