-- easier than trying to grab the refresh_token, just logout the user from all instances (currently max of two)
DELETE FROM user_refresh_tokens 
WHERE user_id = %(user_id)s