-- Update an existing user
UPDATE users SET password_hash = %(password_hash)s
WHERE username = %(username)s
RETURNING username, email;