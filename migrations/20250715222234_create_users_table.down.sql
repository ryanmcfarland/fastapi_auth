-- DOWN Migration
DROP TABLE IF EXISTS user_refresh_tokens;

DROP TABLE IF EXISTS user_roles;

DROP TABLE IF EXISTS users;

DROP TRIGGER IF EXISTS trigger_create_default_user_role;