# python-telegram-bot that will do a conversation with the user to get informations about a post the bot will make to a channel with specific formatting

import logging
import os

from dotenv import load_dotenv
from telegram.constants import ParseMode
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, Application


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# States

POST, TITLE, EMOJI, DATE, DESCRIPTION, LINK, CONTACT, CONFIRMATION = range(8)

# Global variables

post = {}


# Functions

async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Hi!')
    return


async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text('Help!')
    return


async def new_post(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about the post."""
    await update.message.reply_text(
        'Hi! I will ask you a few questions about the post you want to create. '
        'You can use /cancel to stop talking to me.\n\n'
        'What is the title of the post?')
    return TITLE


async def title(update: Update, context: CallbackContext) -> int:
    """Stores the title and asks for an emoji."""
    user = update.message.from_user
    logger.info("Title of %s: %s", user.first_name, update.message.text)
    post['title'] = update.message.text

    await update.message.reply_text('What is the emoji of the post?')

    return EMOJI


async def emoji(update: Update, context: CallbackContext) -> None:
    """Stores the emoji and asks for the date of the event."""
    user = update.message.from_user
    logger.info("Emoji of %s: %s", user.first_name, update.message.text)
    post['emoji'] = update.message.text

    await update.message.reply_text('What is the date of the post?')

    return DATE


async def date(update: Update, context: CallbackContext) -> int:
    """Stores the date and asks for a description."""
    user = update.message.from_user
    logger.info("Date of %s: %s", user.first_name, update.message.text)
    post['date'] = update.message.text

    await update.message.reply_text('What is the description of the post?')

    return DESCRIPTION


async def description(update: Update, context: CallbackContext) -> int:
    """Stores the description and asks for a link."""
    user = update.message.from_user
    logger.info("Description of %s: %s", user.first_name, update.message.text)
    post['description'] = update.message.text

    await update.message.reply_text('What is the link of the post?')

    return LINK


async def link(update: Update, context: CallbackContext) -> int:
    """Stores the link and asks for a contact."""
    user = update.message.from_user
    logger.info("Link of %s: %s", user.first_name, update.message.text)
    post['link'] = update.message.text

    await update.message.reply_text('What is the contact of the post?')

    return CONTACT


async def contact(update: Update, context: CallbackContext) -> int:
    """Stores the contact and asks for confirmation."""
    user = update.message.from_user
    logger.info("COntact of %s: %s", user.first_name, update.message.text)
    post['contact'] = update.message.text

    reply_keyboard = [['Yes', 'No']]

    await update.message.reply_text(
        'Please confirm the post:\n\n'
        f'Title: {post["title"]}\n'
        f'Emoji: {post["emoji"]}\n'
        f'Date: {post["date"]}\n'
        f'Description: {post["description"]}\n'
        f'Link: {post["link"]}\n\n'
        f'Contact: {post["contact"]}\n\n'
        'Is this correct?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return CONFIRMATION


async def confirmation(update: Update, context: CallbackContext) -> int:
    """Stores the confirmation and ends the conversation."""
    user = update.message.from_user
    logger.info("Confirmation of %s: %s", user.first_name, update.message.text)
    post['confirmation'] = update.message.text

    if post['confirmation'] == 'Yes':
        await update.message.reply_text(
            'thanks for the information! I will send the post to the channel now.',
            reply_markup=ReplyKeyboardRemove())

        # Send the post to the channel
        await context.bot.send_message(
            chat_id=os.getenv('CHANNEL_ID'),
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
            EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, emoji)],
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
