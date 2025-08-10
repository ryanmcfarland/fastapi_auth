INSERT INTO user_refresh_tokens (user_id, refresh_token)
SELECT u.id, %(refresh_token)s
FROM users u
WHERE u.username = %(username)s