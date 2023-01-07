import datetime
import logging
import os
from typing import Callable

import emoji
from babel.dates import format_date
from dotenv import load_dotenv
from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, Application

load_dotenv()

PORT = int(os.getenv('PORT', 5000))
ENV = os.getenv('ENV')
HEROKU_PATH = os.getenv('HEROKU_PATH')
TOKEN = os.getenv('TOKEN')
LOCALE = os.getenv('LOCALE')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Constants

ACCEPTED_CHARACTERS = ['.', ',', ':', ';', '!', '?', '(', ')', '[', ']', '{', '}', '/', '\\', '-', '_', '+', '=', '*', '@', '#', '$', '%', '^', '&', '|', '<', '>', '~', '`', '"', "'", '·', '’']

POST, TITLE, EMOJI, DATE, DESCRIPTION, LINK, CONTACT, CONFIRMATION = ['post', 'title', 'emoji', 'date', 'description',
                                                                      'link', 'contact', 'confirmation']

fields_and_questions = {
    POST: 'Please read carefully the rules of posting with /rules before sending your post as any post that does not '
          'comply with these rules will not be posted!',
    TITLE: 'What is the title of the post?',
    EMOJI: 'What is the emoji of the post?',
    DATE: 'What is the date of the post?',
    DESCRIPTION: 'What is the description of the post?',
    LINK: 'What is the link of the post?',
    CONTACT: 'What is the contact of the post?',
    CONFIRMATION: '⬆️ Do you confirm this post? ⬆️',
}

LIMITS = {
    TITLE: 10,
    EMOJI: 1,
    DESCRIPTION: 100,
    LINK: 100,
    CONTACT: 50,
}

SPECIFIC_FORMATTING_INSTRUCTIONS = {
    TITLE: 'No emoji nor special characters',
    DATE: 'DD/MM or DD/MM-DD/MM',
}

flow = [POST, TITLE, EMOJI, DATE, DESCRIPTION, LINK, CONTACT, CONFIRMATION]

CONFIRM = '✅'
DENY = '❌'

suffix = 'Send /post to start again!'
CONFIRM_SENT = 'Your post request has been sent to the moderatos! ' + suffix
CANCEL_SENT = 'Your post request has been cancelled! ' + suffix


# Helper functions

async def build_post(update: Update, context: CallbackContext) -> str:
    """Builds the post to be sent to the channel"""
    user_data = context.user_data
    text = ""
    text += f"<b>{user_data[TITLE]}</b> {user_data[EMOJI]}\n"
    text += f"<i>{' - '.join([format_date(datetime.datetime.strptime(d, '%d/%m'), format='dd MMMM', locale=LOCALE) for d in user_data[DATE].split('-')])}</i>\n"
    text += f"\n"
    text += f"{user_data[DESCRIPTION]}\n"
    text += f"\n"
    text += f"<a href='{user_data[LINK]}'>Lien d'inscription</a>\n"
    text += f"\n"
    text += f"Contact : {user_data[CONTACT]}\n"

    return text


def and_(predicates: list[Callable[[str], bool]]) -> Callable[[str], bool]:
    """Returns a function that checks if a string satisfies all the given predicates."""
    return lambda s: all([p(s) for p in predicates])


# returns a function that checks if a string is only composed of non special charaters
def is_only_non_special_characters() -> Callable[[str], bool]:
    """Returns a function that checks if a string is only composed of non special charaters."""
    return lambda s: all([c.isalnum() or c.isspace() or c in ACCEPTED_CHARACTERS for c in s])


def is_shorter_than(length: int) -> Callable[[str], bool]:
    """Returns a function that checks if a string is shorter than a given length."""
    return lambda s: len(s) < length


def is_emoji() -> Callable[[str], bool]:
    """Returns a function that checks if a string is an emoji."""
    return lambda s: emoji.emoji_count(s) == 1 and len(s) == 1


def _check_one_date(text: str) -> bool:
    """Checks one date"""
    if len(text) == 5 and text[2] == '/':
        try:
            datetime.datetime.strptime(text, '%d/%m')
            return True
        except ValueError:
            return False
    return False


def is_date() -> Callable[[str], bool]:
    """Returns a function that checks if a string is a date."""
    return lambda s: _check_one_date(s) if len(s) == 5 else (
            len(s) == 11 and s[5] == '-' and _check_one_date(s[:5]) and _check_one_date(
        s[6:]) and datetime.datetime.strptime(s[:5], '%d/%m') < datetime.datetime.strptime(s[6:], '%d/%m'))


def _get_question(field: str) -> str:
    """Returns the question to ask for a given field."""
    question = fields_and_questions[field]
    if field in LIMITS.keys():
        question += f' (max {LIMITS[field]} characters)'
    if field in SPECIFIC_FORMATTING_INSTRUCTIONS.keys():
        question += f' ({SPECIFIC_FORMATTING_INSTRUCTIONS[field]})'
    return question


async def go_next(update: Update, context: CallbackContext, field: str, rule: Callable[[str], bool]) -> str:
    """Stores the confirmation and ends the conversation."""
    user = update.message.from_user
    text = update.message.text
    logger.info("%s of %s: %s", field, user.first_name, text)
    while not rule(text):
        await update.message.reply_text(_get_question(field))
        return field
    context.user_data[field] = update.message.text

    # reply with question of next field
    next_field = flow[flow.index(field) + 1]

    if next_field == CONFIRMATION:
        reply_keyboard = [[CONFIRM, DENY]]
        text = await build_post(update, context)
        await update.message.reply_text(text,
                                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
                                        parse_mode=ParseMode.HTML)

    await update.message.reply_text(_get_question(next_field))

    return next_field


# Functions

async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    text = "Hello!\n"
    text += "You can use /post to request a new post on the EPFL Staffing channel (https://t.me/+fkbWQxKHD58xNGI8)"
    await update.message.reply_text(text)
    return


async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text('Help! [Work in progress...]')
    return


async def new_post(update: Update, context: CallbackContext) -> str:
    """Starts the conversation and asks the user about the post."""
    await update.message.reply_text(fields_and_questions[POST])
    return await go_next(update, context, POST, lambda s: True)


async def title(update: Update, context: CallbackContext) -> str:
    """Stores the title."""
    rule = and_([is_only_non_special_characters(), is_shorter_than(LIMITS[TITLE])])
    return await go_next(update, context, TITLE, rule)


async def myemoji(update: Update, context: CallbackContext) -> str:
    """Stores the emoji."""
    return await go_next(update, context, EMOJI, is_emoji())


async def date(update: Update, context: CallbackContext) -> str:
    """Stores the date."""
    return await go_next(update, context, DATE, is_date())


async def description(update: Update, context: CallbackContext) -> str:
    """Stores the description."""
    return await go_next(update, context, DESCRIPTION, is_shorter_than(LIMITS[DESCRIPTION]))


async def link(update: Update, context: CallbackContext) -> str:
    """Stores the link."""
    return await go_next(update, context, LINK, is_shorter_than(LIMITS[LINK]))


async def contact(update: Update, context: CallbackContext) -> str:
    """Stores the contact and asks for confirmation."""
    return await go_next(update, context, CONTACT, is_shorter_than(LIMITS[CONTACT]))


async def confirmation(update: Update, context: CallbackContext) -> int:
    """Stores the confirmation and ends the conversation."""
    user = update.message.from_user
    logger.info("Confirmation of %s: %s", user.first_name, update.message.text)

    if update.message.text == CONFIRM:
        await update.message.reply_text(CONFIRM_SENT, reply_markup=ReplyKeyboardRemove())

        # Send the post to the channel
        await context.bot.send_message(
            chat_id=os.getenv('MODERATION_CHAT_ID'),
            text=await build_post(update, context),
            parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    else:
        await update.message.reply_text(CANCEL_SENT, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(CANCEL_SENT, reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    print("Going live!")

    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler with the states POST, TITLE, DESCRIPTION, IMAGE, LINK, CONFIRMATION
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('post', new_post)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, myemoji)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, link)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmation)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Start the Bot
    print("Bot starting...")
    if os.environ.get('ENV') == 'DEV':
        application.run_polling()
    elif os.environ.get('ENV') == 'PROD':
        application.run_webhook(listen="0.0.0.0",
                                port=int(PORT),
                                webhook_url=HEROKU_PATH,
                                secret_token="passphrase")
    return


if __name__ == '__main__':
    main()
