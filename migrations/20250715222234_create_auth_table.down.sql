-- DOWN Migration
DROP TRIGGER IF EXISTS trigger_create_default_user_role ON users CASCADE;

DROP TRIGGER IF EXISTS trigger_limit_user_refresh_tokens ON user_refresh_tokens CASCADE;

DROP TABLE IF EXISTS user_refresh_tokens;

DROP TABLE IF EXISTS user_roles;

DROP TABLE IF EXISTS users;

DROP TABLE IF EXISTS roles;