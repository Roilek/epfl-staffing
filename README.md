# epfl-staffing
Bot to manage EPFL Staffing channel which aim at promoting staffing opportunities on the campus

This bot enable users to build posts that will be sent on a group for moderation and then on the dedicated channel.

Usage:
Clone the repo, host it wherever.
.env file structure:

TOKEN=   # Telegram bot token
CHANNEL_ID=   # The channel where the posts will be sent
MODERATION_CHAT_ID=   # The chat where the posts will be sent for moderation
ENV=   # The environment (DEV or PROD)
HEROKU_PATH=   # The path to the heroku app (only for DEV)
LOCALE=   # The locale (fr_FR for example)