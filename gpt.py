from dotenv import load_dotenv

load_dotenv()

import os
import openai

openai.api_key = os.getenv("OPENAI_TOKEN", None)



class Prompt:
    prompt_template = """
    {instructions}

    The text: {text}

    Output:"""

    instructions = """This is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly."""
    temperature = 0.0

    expected_args = ['text']

    def __init__(self, prompt_args):
        if openai.api_key is None:
            raise "OpenAI API Key not found. Please set the OPENAI_TOKEN environment variable"
        
        missing_args = [arg for arg in self.expected_args if arg not in prompt_args]
        if missing_args:
            raise "Prompt is missing arguments: {}".format(", ".join(missing_args))
        
        self.hydrated_prompt = self.prompt_template.format(instructions=self.instructions, **prompt_args)

    def __call__(self):
        gpt3_session = openai.Completion.create(
            engine="text-davinci-003",
            prompt=self.hydrated_prompt,
            temperature=self.temperature,
            max_tokens=4000,
            n=1,
        )
        response = gpt3_session.choices[0].text
        return response

class CleanUp(Prompt):
    instructions = """This is a transcription of some voice notes taken by a
    human. It probably contains errors and homophones.

    Please fix evident transcription errors, remove filler words, and make the text more readable.
    """

class WriteEmail(Prompt):
    instructions = """This is a transcription of some voice notes taken by a
    human. It probably contains errors and homophones.

    Please use these notes to write an friendly but concise email.
    
    The text: {text}

    Output:
    """

class WriteNotes(Prompt):
    instructions = """This is a transcription of some voice notes taken by a
    human. It probably contains errors and homophones.

    Please use these notes to write a terse series of bulleted notes.
    
    The text: {text}

    Output:
    """

class Chain():
    prompts = []
    description = "Abstract base chain"

    @property
    def verbose_description(self):
        return self.description + '\n\n' + '\n===>\n'.join([str(prompt) for prompt in self.prompts])

    def __call__(self, prompt_args):
        if not 'text' in prompt_args:
            raise 'text is required as an argument'
        text = prompt_args['text']
        for prompt in self.prompts:
            prompt_args['text'] = text
            text = prompt(prompt_args)()
        return text
        

class CleanupChain(Chain):
    prompts = [CleanUp]

class EmailChain(Chain):
    prompts = [CleanUp, WriteEmail]

class NiceNotesChain(Chain):
    prompts = [CleanUp, WriteNotes]

chains = {
        'Transcribe': CleanupChain,
        'Email': EmailChain,
        'Notes': NiceNotesChain}


def respond(msg):
    """
    Generate a response to a user-provided message

    Args:
        msg (str): The message to respond to

    Returns:
        response (str): The response to the user-provided message
    """

    if openai.api_key is None:
        response = (
            "OpenAI API Key not found. Please set the OPENAI_TOKEN environment variable"
        )
        return response

    # Generate a prompt based on the user-provided message, feel free to change this.
    prompt = f"""
    You are an assistant telegram bot that helps people with their daily tasks and answers their questions.
    You are currently chatting with a user. 

    user: 
    {msg}
    
    response:
    """

    gpt3_session = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.8,
        max_tokens=2024,
        n=1,
    )

    # Generate a response to the user-provided message
    response = gpt3_session.choices[0].text
    return response
