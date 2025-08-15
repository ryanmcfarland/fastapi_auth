/*
CTE that inserts token into `refresh_tokens` and then also updates user's last_login_at
*/
WITH token_insert AS (
    INSERT INTO user_refresh_tokens (user_id, refresh_token)
    SELECT u.id, %(refresh_token)s
    FROM users u
    WHERE u.username = %(username)s
    RETURNING user_id
)
UPDATE users 
SET last_login_at = NOW() AT TIME ZONE 'UTC'
FROM token_insert
WHERE users.id = token_insert.user_id