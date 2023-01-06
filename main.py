import datetime
import logging
import os
from typing import Callable

import emoji
from dotenv import load_dotenv
from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, Application

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Variables

POST_WARNING_MESSAGE = "Please read carefully the rules of posting with /rules before sending your post as any post " \
                       "that does not comply with these rules will not be posted!"

fields_and_questions = {
    'title': 'What is the title of the post?',
    'emoji': 'What is the emoji of the post?',
    'date': 'What is the date of the post?',
    'description': 'What is the description of the post?',
    'link': 'What is the link of the post?',
    'contact': 'What is the contact of the post?',
    'confirmation': 'Send \'Yes\' to confirm?',
}

LIMITS = {
    'title': 10,
    'emoji': 1,
    'description': 100,
    'link': 100,
    'contact': 50,
}

TITLE, EMOJI, DATE, DESCRIPTION, LINK, CONTACT, CONFIRMATION = fields_and_questions.keys()
flow = [TITLE, EMOJI, DATE, DESCRIPTION, LINK, CONTACT, CONFIRMATION]

CONFIRM = '✅'
DENY = '❌'

# Global variables

post = {}


# Helper functions

async def build_post(update: Update, context: CallbackContext) -> str:
    """Builds the post to be sent to the channel"""
    print(post)
    text = ""
    for field in flow:
        if field in post:
            text += f"{field}: {post[field]}\n"
    return text


def is_shorter_than(length: int) -> Callable[[str], bool]:
    """Returns a function that checks if a string is shorter than a given length."""
    return lambda s: len(s) < length


def is_emoji() -> Callable[[str], bool]:
    """Returns a function that checks if a string is an emoji."""
    return lambda s: emoji.emoji_count(s) == 1 and len(s) == 1


def check_one_date(text: str) -> bool:
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
    return lambda s: check_one_date(s) if len(s) == 5 else (
            len(s) == 11 and s[5] == '-' and check_one_date(s[:5]) and check_one_date(
        s[6:]) and datetime.datetime.strptime(s[:5], '%d/%m') < datetime.datetime.strptime(s[6:], '%d/%m'))


async def send_confirmation_menu(update: Update, context: CallbackContext) -> None:
    """."""
    reply_keyboard = [['Yes', 'No']]
    # build the post and send it if the keyboard
    text = await build_post(update, context)
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return


async def go_next(update: Update, context: CallbackContext, field: str, rule: Callable[[str], bool],
                  **kwargs) -> str:
    """Stores the confirmation and ends the conversation."""
    user = update.message.from_user
    text = update.message.text
    logger.info("%s of %s: %s", field, user.first_name, text)
    while not rule(text):
        await update.message.reply_text(fields_and_questions[field])
        return field
    post[field] = update.message.text

    # reply with question of next field
    next_field = flow[flow.index(field) + 1]

    if next_field == CONFIRMATION:
        await send_confirmation_menu(update, context)
        await update.message.reply_text(fields_and_questions[next_field], reply_markup=ReplyKeyboardRemove())
        return next_field

    await update.message.reply_text(fields_and_questions[next_field])

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
    await update.message.reply_text(POST_WARNING_MESSAGE)
    first_field = flow[0]
    await update.message.reply_text(fields_and_questions[first_field])
    return first_field


async def title(update: Update, context: CallbackContext) -> str:
    """Stores the title."""
    return await go_next(update, context, TITLE, is_shorter_than(LIMITS[TITLE]))


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

    if update.message.text == 'Yes':
        await update.message.reply_text(
            'thanks for the information! I will send the post to the channel now.',
            reply_markup=ReplyKeyboardRemove())

        # Send the post to the channel
        await context.bot.send_message(
            chat_id=os.getenv('MODERATION_CHAT_ID'),
            text=f'<b>{post["title"]}</b>\n\n{post["description"]}\n\n<a href="{post["link"]}">Read more</a>',
            parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            'thanks for the information! I will not send the post to the channel.',
            reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        'Bye! I hope we can talk again some day.',
        reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    print("Going live!")
    load_dotenv()

    # Create application
    application = Application.builder().token(os.getenv('TOKEN')).build()

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
    application.run_polling()

    return


if __name__ == '__main__':
    main()
