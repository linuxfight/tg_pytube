from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from utils.callback_handler import on_callback_query
from utils.message_handler import on_link, on_start_message
from utils.login import login


app = login()


app.add_handler(MessageHandler(on_start_message, filters.command('start')))
app.add_handler((MessageHandler(on_link)))
app.add_handler(CallbackQueryHandler(on_callback_query))


if __name__ == '__main__':
    try:
        print("Bot is running")
        app.run()
    except KeyboardInterrupt:
        app.stop()
        pass
