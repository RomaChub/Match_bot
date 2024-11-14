import base64

import openai
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dotenv import load_dotenv
from openai import AsyncOpenAI
from config import settings
from database.database import AboutOrm, new_session

load_dotenv()
client = AsyncOpenAI()

async def save_about(who: str, what_can:str, who_need:str, user_id: str, text:str):
    about_orm = AboutOrm(who=who, what_can=what_can, who_need=who_need, user_id=user_id, all_text=text)
    async with new_session() as session:
        session.add(about_orm)
        await session.flush()
        await session.commit()

class Utils:
    def __init__(self):
        openai.api_key = settings.openai_api_key

    @classmethod
    async def save_voice_as_mp3(cls, bot: Bot, message: Message):
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_name = f"files/audio{file_id}.mp3"
        await bot.download_file(file_path, file_name)
        return file_name


    @classmethod
    async def audio_to_text(cls, file_path: str) -> str:
        with open(file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return str(transcript)


    @classmethod
    async def get_response_from_openai(cls, text: str, state: FSMContext):
        if settings.assistant_who_is_id != "no_id":
            assistant_who_is = await client.beta.assistants.retrieve(settings.assistant_who_is_id)
            assistant_who_need = await client.beta.assistants.retrieve(settings.assistant_who_need_id)
            assistant_what_can = await client.beta.assistants.retrieve(settings.assistant_what_can_id)
        else:
            assistant_who_is = await client.beta.assistants.create(
                name="Assistant",
                description="You must help determine who this person is ?",
                model="gpt-4o-mini",
            )
            assistant_who_need = await client.beta.assistants.create(
                name="Assistant",
                description="You will determine who a person is looking for ?",
                model="gpt-4o-mini",
            )
            assistant_what_can = await client.beta.assistants.create(
                name="Assistant",
                description="you will determine what a person can do ?",
                model="gpt-4o-mini",
            )
            settings.assistant_who_is_id = assistant_who_is.id
            settings.assistant_who_need_id = assistant_who_need.id
            settings.assistant_what_can_id = assistant_what_can.id

        assistant_who_is_id = settings.assistant_who_is_id
        assistant_who_need_id = settings.assistant_who_need_id
        assistant_what_can_is_id = settings.assistant_what_can_id

        data = await state.get_data()
        thread_who_is_id = data.get("thread_who_is_id")
        thread_who_need_id = data.get("thread_who_need_id")
        thread_what_can_id = data.get("thread_what_can_id")

        if not thread_who_is_id or not thread_who_need_id or not thread_what_can_id:
            thread_who_is_id = await client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": f""" 
                                    Text: {text} 
                        
                                    From the text you should understand who this person is, 
                                    first name last name position and 
                                    in the answer indicate only key important words.
                                    """
                    }
                ]
            )
            thread_who_is_id = thread_who_is_id.id

            thread_what_can_id = await client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": f""" 
                                    Text: {text} 
                                    
                                    From the text you should understand what this person does 
                                    and what he is good at and 
                                    in the answer indicate only key important words.
                                    """
                    }
                ]
            )
            thread_what_can_id = thread_what_can_id.id

            thread_who_need_id = await client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": f""" 
                                    Text: {text}
                                    
                                    From the text you should understand what kind of specialist a person needs and 
                                    in the answer indicate only key important words.
                                    """
                    }
                ]
            )
            thread_who_need_id = thread_who_need_id.id
            await state.update_data(thread_who_is_id=thread_who_is_id,thread_who_need_id=thread_who_need_id,thread_what_can_id=thread_what_can_id)
        else:
            thread_who_is = await client.beta.threads.messages.create(
                thread_id=thread_who_is_id,
                role="user",
                content=f""" 
                            Text: {text} 
                        
                            From the text you should understand who this person is, 
                            first name last name position and 
                            in the answer indicate only key important words.
                            """
            )
            thread_what_can = await client.beta.threads.messages.create(
                thread_id=thread_what_can_id,
                role="user",
                content=f""" 
                            Text: {text} 
                                
                            From the text you should understand what this person does 
                            and what he is good at and 
                            in the answer indicate only key important words.
                            """
            )
            thread_who_need = await client.beta.threads.messages.create(
                thread_id=thread_who_need_id,
                role="user",
                content=f""" 
                            Text: {text}
                            
                            From the text you should understand what kind of specialist a person needs and 
                            in the answer indicate only key important words.
                            """
            )


        run_who_is = await client.beta.threads.runs.create_and_poll(
            thread_id=thread_who_is_id,
            assistant_id=assistant_who_is_id)

        run_what_can = await client.beta.threads.runs.create_and_poll(
            thread_id=thread_what_can_id,
            assistant_id=assistant_what_can_is_id)

        run_who_need = await client.beta.threads.runs.create_and_poll(
            thread_id=thread_who_need_id,
            assistant_id=assistant_who_need_id)

        if run_who_is.status in ['requires_action', 'running', 'queued', 'failed', 'canceled', 'timed_out']:
            return str("Please, repeat.")
        if run_what_can.status in ['requires_action', 'running', 'queued', 'failed', 'canceled', 'timed_out']:
            return str("Please, repeat.")
        if run_who_need.status in ['requires_action', 'running', 'queued', 'failed', 'canceled', 'timed_out']:
            return str("Please, repeat.")

        if run_who_need.status == str("completed"):
            messages_who = await client.beta.threads.messages.list(thread_id=thread_who_is_id, run_id=run_who_is.id)
            messages_what_can = await client.beta.threads.messages.list(thread_id=thread_what_can_id, run_id=run_what_can.id)
            messages_who_need = await client.beta.threads.messages.list(thread_id=thread_who_need_id, run_id=run_who_need.id)

            message_content = messages_who.data[0].content[0].text
            annotations = message_content.annotations
            for annotation in annotations:
                message_content.value = message_content.value.replace(annotation.text, '')
            who = message_content.value

            message_content = messages_what_can.data[0].content[0].text
            annotations = message_content.annotations
            for annotation in annotations:
                message_content.value = message_content.value.replace(annotation.text, '')
            what_can = message_content.value

            message_content = messages_who_need.data[0].content[0].text
            annotations = message_content.annotations
            for annotation in annotations:
                message_content.value = message_content.value.replace(annotation.text, '')
            who_need = message_content.value

            res = [who, what_can, who_need]

            return res


