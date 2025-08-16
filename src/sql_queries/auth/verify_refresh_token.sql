WITH token_check AS (
    UPDATE user_refresh_tokens 
    SET last_refresh_at = NOW() AT TIME ZONE 'UTC'
    FROM users u
    WHERE user_refresh_tokens.user_id = u.id
        AND u.username = %(username)s
        AND user_refresh_tokens.refresh_token = %(refresh_token)s
    RETURNING user_refresh_tokens.user_id
)
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN true 
        ELSE false 
    END as valid
FROM token_check;