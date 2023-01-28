from dotenv import load_dotenv

load_dotenv()

import os
import requests
import time
import gpt

import flask
import telebot

app = flask.Flask(__name__)

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"], threaded=False)

chains = gpt.chains

# TODO maintain state of this
CURRENT_CHAIN = 'notes'

WEBHOOK_URL = "https://overheardbot.vercel.app"


def get_current_chain():
    return CURRENT_CHAIN


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
        /list_chains Lists all available prompts
        /set_chain <prompt_name> Sets the prompt to use for the bot
        /show_chain <prompt_name> Shows the prompt
        /gpt <message> - Get a GPT-3 generated reply based on your prompt in gpt.py
        
        """,
    )

@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    file_info = bot.get_file(message.voice.file_id)
    file_id = file_info.file_id
    # GET from this url https://johnmcdonnell--telegram-transcribe.modal.run  passing in file_id as an argument
    # This will return a JSON response with the transcript
    # We can then send that to the user
    bot.send_message(message.chat.id, 'Attempting to transcribe. This may take a few seconds.')

    response = requests.get(f'https://johnmcdonnell--telegram-transcribe.modal.run?file_id={file_id}', timeout=300)
    if response.status_code == 200 and response.json()['text']:
        bot.reply_to(message, response.json()['text'])
    else:
        bot.reply_to(message, 'Sorry, transcription failed')



@bot.message_handler(commands=["list_prompts"])
def list_prompts(message):
    """ List all available prompts """
    chainlist = '\n* '.join(chains.keys())
        
    bot.reply_to(message, chainlist)


@bot.message_handler(commands=["gpt"])
def gpt_response(message):
    """Generate a response to a user-provided message make sure to change the prompt in gpt.py
    and set the OPENAI_TOKEN environment variable"""
    response = gpt.respond(message.text)
    bot.reply_to(message, response)


@bot.message_handler(func=lambda message: True, content_types=["text"])
def echo_message(message):
    """Echo the user message"""
    response = chains[get_current_chain()]({'text': message.text})
    bot.reply_to(message, response)


if __name__ == "__main__":
    # Remove webhook, it fails sometimes the set if there is a previous webhook
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
