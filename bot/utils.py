import base64

import openai
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dotenv import load_dotenv
from openai import AsyncOpenAI
from config import settings
from database.database import AboutOrm, new_session
from sqlalchemy.future import select


load_dotenv()
client = AsyncOpenAI()

async def save_about(tg_id, new_dialog: str, new_tread_id: str):
    async with new_session() as session:
        # Находим существующую запись
        result = await session.execute(
            select(AboutOrm).filter(AboutOrm.tg_id == str(tg_id))
        )
        about_orm = result.scalar_one_or_none()  # Получаем объект ORM или None

        if about_orm:
            # Обновляем поля
            about_orm.dialog = f"\n{about_orm.dialog} \n{new_dialog}"  # Добавляем новый диалог
            about_orm.tread_id = new_tread_id
        else:
            # Если запись не найдена, создаем новую
            about_orm = AboutOrm(tg_id=tg_id, dialog=new_dialog, tread_id=new_tread_id)
            session.add(about_orm)

        # Сохраняем изменения в базе данных
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
    async def get_response_from_openai(cls, text: str, state: FSMContext, tg_id):
        async with new_session() as session:
            about_orm = await session.execute(
                select(AboutOrm).filter(AboutOrm.tg_id == str(tg_id))
            )
            about_orm = about_orm.scalar_one_or_none()  # Получаем один результат или None

            # Если запись найдена, то получаем tream_id, иначе None
            thread_who_is_id = about_orm.tread_id if about_orm else None

        print(thread_who_is_id)
        # Проверяем, существует ли ассистент
        if settings.assistant_who_is_id != "no_id":
            assistant_who_is = await client.beta.assistants.retrieve(settings.assistant_who_is_id)
        else:
            assistant_who_is = await client.beta.assistants.create(
                name="Assistant",
                description="Проводить первичное интервью с потенциальными клиентами, выявлять возможности для автоматизации бизнес-процессов с помощью ИИ и конвертировать ответы в лиды для дальнейшего взаимодействия.",
                model="gpt-4o-mini",
            )
            settings.assistant_who_is_id = assistant_who_is.id

        assistant_who_is_id = settings.assistant_who_is_id

        # Если тред ещё не существует, создаём его
        if not thread_who_is_id:
            print("Создаётся новый тред.")
            thread_response = await client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": f""" 
                                    Ты — AI-Ассистент, помогающий клиенту понять, как ИИ может оптимизировать их бизнес-процессы. Веди диалог кратко, по существу и не более трёх вопросов. По результатам опроса предложи решение и оффер. Избегай длинных ответов и излишних деталей.
                                    
### **Сценарий опроса**

### 1. **Начало разговора:**

Приветствуй пользователя и задавай первый вопрос для квалификации.

**Пример:**

«Йоу! Я — AI-aссистент. А как вас зовут и какую должность вы занимаете в компании?»

### 2. **Квалификация респондента:**

- Если **директор/руководитель**: перейди к вопросам для руководителей.
- Если **сотрудник/не менеджер**: спроси о задачах. **Пример:** «Какие задачи вы выполняете в своей работе?»

### 3. **Основные вопросы (выбираются на основе контекста):**

Задавай не более трёх вопросов:

- Какие задачи вы бы делегировали ИИ?
- Какие задачи в вашей работе часто повторяются?
- Часто ли вам приходится перерабатывать?
- Что вам особенно нравится делать в работе?

### 4. **Результаты для сотрудников (если не руководитель):**

На основе ответов предложи автоматизацию:

«На основе ваших ответов видно, что ИИ может помочь вам автоматизировать [вставить задачи]. Мы можем научить вас работать с этими инструментами. Это займёт минимум времени!»

**Предложи:**

«Запишитесь на бесплатный урок и порекомендуйте AI-бота своему руководителю или коллегам.»

### 5. **Вопросы для руководителей:**
Сколько человек работает в вашей компании и чем она занимается?

- Какие процессы вы хотели бы оптимизировать с помощью ИИ?
- Что для вас сейчас в приоритете?
    - Автоматизация процессов с помощью ИИ (от 1 до 10)
    - Обучение сотрудников ИИ для их задач (от 1 до 10)
    - Обучение руководства для стратегического использования ИИ (от 1 до 10)
    
### 6. **Результаты для руководителей:**

Приведи пример успешного кейса:

«Компания [название] внедрила ИИ для [процесс], что увеличило эффективность на X%. Мы можем предложить аналогичное решение для вас.»

**Заверши:**

«Давайте обсудим детали на встрече. Я расскажу, как ИИ может помочь именно вашему бизнесу. Напишите мне @shimanskij . Или мы напишем вам сами.»

### **Общие правила:**

1. Говори ясно, кратко и по делу.
2. Уточняй детали только по необходимости.
3. Заверши диалог предложением бесплатного урока и дальнейшего общения.
4. Не углубляйся в излишние подробности — сосредотачивайся на сути.

Сообщение пользователя:{text}
"""
                    }
                ]
            )
            thread_who_is_id = thread_response.id

            # Сохраняем новый тред в базу данных
            async with new_session() as session:
                if not about_orm:
                    new_orm = AboutOrm(tg_id=tg_id,dialog="", tread_id=thread_who_is_id)
                    session.add(new_orm)
                    await session.commit()
        else:
            # Добавляем сообщение в существующий тред
            print(f"Добавляем сообщение в существующий тред: {thread_who_is_id}")
            await client.beta.threads.messages.create(
                thread_id=thread_who_is_id,
                role="user",
                content=f"Клиент написал: {text}"
            )

        # Запускаем процесс обработки
        run_who_is = await client.beta.threads.runs.create_and_poll(
            thread_id=thread_who_is_id,
            assistant_id=assistant_who_is_id
        )

        # Проверяем статус обработки
        if run_who_is.status in ["requires_action", "running", "queued", "failed", "canceled", "timed_out"]:
            print(f"Ошибка обработки треда: {run_who_is.status}")
            return "Please, repeat."

        # Обработка завершена
        if run_who_is.status == "completed":
            messages_who = await client.beta.threads.messages.list(thread_id=thread_who_is_id, run_id=run_who_is.id)

            # Извлекаем последнее сообщение
            message_content = messages_who.data[0].content[0].text
            annotations = message_content.annotations
            for annotation in annotations:
                message_content.value = message_content.value.replace(annotation.text, '')
            who = message_content.value
            tread_id = thread_who_is_id
            res = [tg_id, who, tread_id]

            return res