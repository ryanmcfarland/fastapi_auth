SELECT 
    u.username,
    u.email,
    u.password_hash,
    u.created_at,
    u.verified,
    ARRAY_AGG(ur.user_role) as user_roles
FROM users u
INNER JOIN user_roles ur ON u.id = ur.user_id
WHERE u.username = %(username)s
GROUP BY u.id;