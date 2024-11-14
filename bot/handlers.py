import os

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart

from bot.event_tracker import Events
from bot.utils import Utils, save_about

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    Events.start_event(str(message.from_user.id))
    await message.answer("Hello! Let's get acquainted.")
    await message.answer("Record a voice message and tell us who you are, how you are useful, and who you need.")

@router.message(F.content_type == "voice")
async def process_voice_message(message: Message, bot: Bot, state: FSMContext):
    processing_message = await message.answer("Wait, I'm processing your message")
    voice_path = await Utils.save_voice_as_mp3(bot, message)

    transcripted_voice_text = await Utils.audio_to_text(voice_path)

    answer = await Utils.get_response_from_openai(transcripted_voice_text, state)
    os.remove(voice_path)
    user_id = str(message.from_user.id)
    await save_about(who=answer[0], what_can=answer[1], who_need=answer[2], user_id=user_id, text=transcripted_voice_text)

    await processing_message.delete()
    await message.answer("I will send you an answer when I find a suitable person")


