-- Insert a new user and return their username and email
INSERT INTO users (username, email, slug, display_name, password_hash)
VALUES (%(username)s, %(email)s, %(slug)s, %(display_name)s, %(password_hash)s)
RETURNING username, email;