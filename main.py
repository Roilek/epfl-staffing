# python-telegram-bot that will do a conversation with the user to get informations about a post the bot will make to a channel with specific formatting

import logging
import os

from dotenv import load_dotenv
from telegram.constants import ParseMode
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, Application, \
    PicklePersistence

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# States

POST, TITLE, DESCRIPTION, IMAGE, LINK, CONFIRMATION = range(6)

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
    """Stores the title and asks for a description."""
    user = update.message.from_user
    text = update.message.text
    context.user_data["title"] = text
    logger.info("Title of %s: %s", user.first_name, text)

    await update.message.reply_text('What is the description of the post?')

    return DESCRIPTION


async def description(update: Update, context: CallbackContext) -> int:
    """Stores the description and asks for an image."""
    user = update.message.from_user
    text = update.message.text
    context.user_data["description"] = text
    logger.info("Description of %s: %s", user.first_name, text)

    await update.message.reply_text('What is the image of the post?')

    return IMAGE


async def image(update: Update, context: CallbackContext) -> int:
    """Stores the image and asks for a link."""
    user = update.message.from_user
    text = update.message.text
    context.user_data["image"] = text
    logger.info("Image of %s: %s", user.first_name, text)

    await update.message.reply_text('What is the link of the post?')

    return LINK


async def link(update: Update, context: CallbackContext) -> int:
    """Stores the link and asks for confirmation."""
    user = update.message.from_user
    text = update.message.text
    context.user_data["link"] = text
    logger.info("Link of %s: %s", user.first_name, text)

    user_data = context.user_data

    reply_keyboard = [['Yes', 'No']]

    await update.message.reply_text(
        'Please confirm the post:\n\n'
        f'Title: {user_data["title"]}\n'
        f'Description: {user_data["description"]}\n'
        f'Image: {user_data["image"]}\n'
        f'Link: {user_data["link"]}\n\n'
        'Is this correct?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return CONFIRMATION


async def confirmation(update: Update, context: CallbackContext) -> int:
    """Stores the confirmation and ends the conversation."""
    user = update.message.from_user
    text = update.message.text
    context.user_data["confirmation"] = text
    logger.info("Confirmation of %s: %s", user.first_name, text)

    user_data = context.user_data

    if user_data['confirmation'] == 'Yes':
        await update.message.reply_text(
            'thanks for the information! I will send the post to the channel now.',
            reply_markup=ReplyKeyboardRemove())

        # Send the post to the channel
        await context.bot.send_message(chat_id=os.getenv('CHANNEL_ID'), text=f'<b>{user_data["title"]}</b>\n\n{user_data["description"]}\n\n<a href="{user_data["link"]}">Read more</a>', parse_mode=ParseMode.HTML)
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

    persistence = PicklePersistence(filepath="conversationbot")

    # Create application
    application = Application.builder().token(os.getenv('TOKEN')).persistence(persistence).build()

    # Add conversation handler with the states POST, TITLE, DESCRIPTION, IMAGE, LINK, CONFIRMATION
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('post', new_post)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, image)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, link)],
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
