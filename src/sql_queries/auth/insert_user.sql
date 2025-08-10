-- Insert a new user and return their username and email
INSERT INTO users (username, email, password_hash)
VALUES (%(username)s, %(email)s, %(password_hash)s)
RETURNING username, email;