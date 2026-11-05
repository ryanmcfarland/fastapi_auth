INSERT INTO
    user_roles (user_id, role_id)
VALUES
    (%(user_id)s, (SELECT id FROM roles WHERE role_name = 'admin'))