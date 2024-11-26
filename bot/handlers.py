import os

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart

from bot.event_tracker import Events
from bot.utils import Utils, save_about

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    Events.start_event(str(message.from_user.id))
    user_id = message.from_user.id
    answer = await Utils.get_response_from_openai(message.text, state, int(user_id))
    await message.answer("Привет! Я — AI-aссистент. А как вас зовут и какую должность вы занимаете в компании?")
    await message.answer(answer[1])


@router.message(F.content_type == "voice")
async def process_voice_message(message: Message, bot: Bot, state: FSMContext):
    processing_message = await message.answer("Обрабатываем информацию...")
    voice_path = await Utils.save_voice_as_mp3(bot, message)

    transcripted_voice_text = await Utils.audio_to_text(voice_path)
    user_id = message.from_user.id
    answer = await Utils.get_response_from_openai(transcripted_voice_text, state, int(user_id))
    os.remove(voice_path)

    await save_about(tg_id=answer[0], new_dialog=f"пользователь: {transcripted_voice_text} \n Бот:{answer[1]} \n",
                     new_tread_id=answer[2])

    await message.answer(answer[1])
    await processing_message.delete()

@router.message(F.content_type == "text")
async def process_voice_message(message: Message, bot: Bot, state: FSMContext):
    processing_message = await message.answer("Обрабатываем информацию...")
    user_id = message.from_user.id
    answer = await Utils.get_response_from_openai(message.text, state, int(user_id))

    await save_about(tg_id=answer[0], new_dialog=f"пользователь: {message.text} \n Бот:{answer[1]} \n",
                     new_tread_id=answer[2])

    await message.answer(answer[1])
    await processing_message.delete()


