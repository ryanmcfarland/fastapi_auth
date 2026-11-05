-- Get User by unique identifier
SELECT
    u.id,
    u.username,
    u.display_name,
    u.slug,
    u.email,
    u.password_hash,
    u.created_at,
    u.verified,
    ARRAY_AGG(r.role_name) as user_roles
FROM users u
INNER JOIN user_roles ur ON u.id = ur.user_id
INNER JOIN roles r ON ur.role_id = r.id
WHERE u.username = %(identifier)s OR u.email = %(identifier)s
GROUP BY u.id;