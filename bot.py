import os
import requests
import logging
from internetarchive import get_item, download
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatAction
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

# Telegram Bot API token
TOKEN = "5994782318:AAFgAWeVpXJqM7VHphFBeaw2L9iyXImilUQ"

# Conversation states
SEARCH_BOOK, SELECT_BOOK, CONTINUE_SEARCH = range(3)

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
        response = requests.get("https://archive.org/advancedsearch.php?q=" + query + "&output=json")
        response.raise_for_status()
        data = response.json()

        if "response" in data and "docs" in data["response"]:
            results = data["response"]["docs"]
            if len(results) > 0:
                # Create a list of book titles with corresponding identifiers
                book_list = [(book["title"], book["identifier"]) for book in results]

                # Store the book_list in the user's context for later use
                context.user_data["book_list"] = book_list

                # Create a formatted string with the book options
                options = "\n".join([str(index + 1) + ". " + title for index, (title, _) in enumerate(book_list)])

                update.message.reply_text(
                    "Here are the search results:\n" + options + "\nPlease enter the number of the book you want to download."
                )
                return SELECT_BOOK

        update.message.reply_text("No books found. Please try a different search term.")
    except requests.exceptions.RequestException as e:
        logging.error("Error occurred during book search: " + str(e))
        update.message.reply_text("Failed to search for books. Please try again later.")

    return ConversationHandler.END


def select_book(update: Update, context: CallbackContext) -> ConversationHandler:
    query = update.message.text
    book_list = context.user_data.get("book_list")

    if not book_list:
        update.message.reply_text("No book list found. Please start a new search.")
        return ConversationHandler.END

    try:
        book_id = int(query) - 1
        if 0 <= book_id < len(book_list):
            book = book_list[book_id]
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

                    # Send chat action to indicate file upload
                    update.message.chat.send_action(action=ChatAction.UPLOAD_DOCUMENT)

                    # Send the PDF file to the user
                    context.bot.send_document(chat_id=update.effective_chat.id, document=file_url)

                    # Ask the user if they want to continue searching
                    reply_markup = ReplyKeyboardMarkup(
                        [["Yes", "No"]],
                        one_time_keyboard=True,
                        resize_keyboard=True
                    )
                    update.message.reply_text("Book selected and sent successfully.\n\nDo you want to search again?",
                                              reply_markup=reply_markup)
                    return CONTINUE_SEARCH
                else:
                    update.message.reply_text("No PDF files found for the selected book.\n\nDo you want to search again?")
                    return CONTINUE_SEARCH
            except Exception as e:
                logging.error("Error occurred during book retrieval: " + str(e))
                update.message.reply_text("Failed to retrieve the book. Please try again later.")
        else:
            update.message.reply_text("Invalid book number. Please try again.")
    except ValueError:
        update.message.reply_text("Invalid input. Please enter a valid book number.")

    return ConversationHandler.END


def continue_search(update: Update, context: CallbackContext):
    user_choice = update.message.text.lower()
    if user_choice == "yes":
        update.message.reply_text("Please enter the title of the book you want to search.")
        return SEARCH_BOOK
    else:
        update.message.reply_text("Search ended. Thank you!")
        return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Search cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    # Create the Telegram Bot updater and dispatcher
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Create a conversation handler with three states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SEARCH_BOOK: [MessageHandler(Filters.text & ~Filters.command, search_book)],
            SELECT_BOOK: [
                MessageHandler(Filters.regex(r"^\d+$"), select_book),
            ],
            CONTINUE_SEARCH: [
                MessageHandler(Filters.regex(r"^(Yes|No)$"), continue_search),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add the conversation handler to the dispatcher
    dispatcher.add_handler(conv_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
