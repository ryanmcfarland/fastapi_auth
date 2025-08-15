SELECT 
    true as valid
FROM users u
INNER JOIN user_refresh_tokens ur ON u.id = ur.user_id
WHERE
    u.username = %(username)s
    and ur.refresh_token = %(refresh_token)s