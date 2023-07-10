import logging
import os

import requests
from internetarchive import search_items, get_item
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler, CallbackContext,
)

# Telegram Bot API token
TOKEN = "5994782318:AAGwm1aZVE9fCMsbSPqEN55kfnxb5JKmt1Q"

# Conversation states
SEARCH_BOOK = 0

# Directory to store downloaded books
BOOKS_DIRECTORY = "books"

if not os.path.exists(BOOKS_DIRECTORY):
    os.makedirs(BOOKS_DIRECTORY)


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Welcome to the Book Search Bot!\n\nPlease enter the title of the book you want to search."
    )
    return SEARCH_BOOK


def search_book(update: Update, context: CallbackContext):
    query = update.message.text

    try:
        results = search_items('title:' + query)
        if len(results) > 0:
            # Create a list of book titles with corresponding identifiers
            book_list = [(result["title"], result["identifier"]) for result in results]

            if len(book_list) > 0:
                # Store the book_list in the user's context for later use
                context.user_data["book_list"] = book_list

                keyboard = []
                for index, (title, _) in enumerate(book_list, start=1):
                    # Create a button for each book
                    button = InlineKeyboardButton(title, callback_data=str(index))

                    # Add the button to the row
                    keyboard.append([button])

                # Create a reply markup with the inline keyboard
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send the search results with the inline keyboard
                update.message.reply_text(
                    "Here are the search results for '" + query + "':",
                    reply_markup=reply_markup,
                )
            else:
                update.message.reply_text("No books found. Please try a different search term.")
        else:
            update.message.reply_text("No books found. Please try a different search term.")
    except Exception as e:
        logging.error("Error occurred during book search: " + str(e))
        update.message.reply_text("Failed to search for books. Please try again later.")

    return SEARCH_BOOK


def select_book(update: Update, context: CallbackContext):
    query = update.callback_query
    book_list = context.user_data.get("book_list")

    if not book_list:
        query.answer("No book list found. Please start a new search.")
        return ConversationHandler.END

    book_id = int(query.data) - 1
    if 0 <= book_id < len(book_list):
        book = book_list[book_id]
        book_title = book[0]
        book_identifier = book[1]

        try:
            item = get_item(book_identifier)
            files = item.files

            # Filter files based on the PDF extension
            pdf_files = [file for file in files if file["name"].lower().endswith(".pdf")]

            if len(pdf_files) > 0:
                # Get the first PDF file in the item
                file = pdf_files[0]
                file_url = "https://archive.org/download/" + book_identifier + "/" + file["name"]

                # Send the book as a document
                update.message.reply_document(file_url, caption=book_title)
            else:
                update.message.reply_text("No PDF files found for the selected book.")
        except Exception as e:
            logging.error("Error occurred during book retrieval: " + str(e))
            update.message.reply_text("Failed to retrieve the book. Please try again later.")

    return ConversationHandler.END


def main():
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    # Create the Telegram Bot updater
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Create a conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SEARCH_BOOK: [
                MessageHandler(filters.text & ~filters.command, search_book),
                CallbackQueryHandler(select_book),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add the conversation handler to the dispatcher
    dispatcher.add_handler(conv_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
