from dotenv import load_dotenv

load_dotenv()

import os
import requests
import time
import gpt
from model import Chat, Message

import flask
import telebot
import model

app = flask.Flask(__name__)

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"], threaded=False)

chains = gpt.chains

# TODO maintain state of this
CURRENT_CHAIN = 'notes'

WEBHOOK_URL = "https://overheardbot.vercel.app/webhook"
#WEBHOOK_URL = "https://7b3c-142-254-83-181.ngrok.io/webhook"


def get_current_chain(chat):
    return chat.active_chain


@app.route("/")
def hello():
    """ Just a simple check if the app is running """
    return {"status": "ok"}


# Process webhook calls
@app.route("/webhook", methods=["POST"])
def webhook():
    if flask.request.headers.get("content-type") == "application/json":
        json_string = flask.request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ""
    else:
        flask.abort(403)

@bot.message_handler(commands=["help", "start"])
def send_welcome(message):
    bot.reply_to(
        message,
        """
        Welcome to the demo bot. 

        Send a voice message to receive a transcription!

        Or run through one of our prompts.

        /help Prints this help message
        /list_chains Lists all available chains
        /set_chain <prompt_name> Sets the chain to use for the bot
        /show_chain <prompt_name> Info about the chain
        """,
    )

@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    chat = Chat.get_or_create(telegram_chat_id=message.chat.id)
    chat.save()
    message_row = Message.get_or_create(telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id)
    message_row.save()
    file_info = bot.get_file(message.voice.file_id)
    file_id = file_info.file_id
    # GET from this url https://johnmcdonnell--telegram-transcribe.modal.run  passing in file_id as an argument
    # This will return a JSON response with the transcript
    # We can then send that to the user
    if message_row.transcript:
        transcript = message_row.transcript
        print('Accessed existing transcript')
    else:
        print('Attempting transcription')
        bot.send_message(message.chat.id, 'Attempting to transcribe. This may take a few seconds.')
        response = requests.get(f'https://johnmcdonnell--telegram-transcribe.modal.run?file_id={file_id}', timeout=300)
        if response.status_code == 200 and response.json()['text']:
            transcript = response.json()['text']
        else:
            bot.reply_to(message, 'Sorry, transcription failed')
    
    try:
        print('Getting completion on OpenAI')
        response = chains[get_current_chain(chat)]()({'text': transcript})
        bot.reply_to(message, response)
    except:
        return



@bot.message_handler(commands=["list_chains"])
def list_chains(message):
    """ List all available chains """
    chainlist = '\n'.join(['* ' + chain for chain in chains.keys()])
    bot.reply_to(message, chainlist)


@bot.message_handler(commands=["set_chain"])
def set_chain(message):
    """ Set chain """
    chat = Chat.get_or_create(telegram_chat_id=message.chat.id)
    if message.text.split(' ')[1] in chains.keys():
        chat.active_chain = message.text.split(' ')[1]
        chat.save()
        bot.reply_to(message, f'Chain set to {chat.active_chain}')
    else:
        bot.reply_to(message, 'Invalid chain, please choose one of\n' + '\n'.join(['* ' + chain for chain in chains.keys()]))


@bot.message_handler(commands=["gpt"])
def gpt_response(message):
    """Generate a response to a user-provided message make sure to change the prompt in gpt.py
    and set the OPENAI_TOKEN environment variable"""
    chat = Chat.get_or_create(telegram_chat_id=message.chat.id)
    response = chains[get_current_chain(message.chat)]()({'text': message.text})
    bot.reply_to(message, response)


@bot.message_handler(func=lambda message: True, content_types=["text"])
def echo_message(message):
    """Echo the user message"""
    bot.reply_to(message, "Echo: " + message.text)


if __name__ == "__main__":
    # Remove webhook, it fails sometimes the set if there is a previous webhook
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
