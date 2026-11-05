--- DELETE ALL ENTRIES IN THE user_refresh_tokens TABLE THAT ARE OLDER THAN x DAYS ---
DELETE FROM user_refresh_tokens
WHERE created_at < NOW() - INTERVAL '365 days';
