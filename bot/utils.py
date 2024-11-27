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

async def save_about(tg_id: str, new_dialog: str, new_tread_id: str):
    async with new_session() as session:
        # Находим существующую запись
        result = await session.execute(
            select(AboutOrm).filter(AboutOrm.tg_id == tg_id)
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
    async def get_response_from_openai(cls, text: str, state: FSMContext, tg_id: str):
        async with new_session() as session:
            about_orm = await session.execute(
                select(AboutOrm).filter(AboutOrm.tg_id == tg_id)
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
### Цель ассистента:

Проводить первичное интервью с потенциальными клиентами, выявлять возможности для автоматизации бизнес-процессов с помощью ИИ и конвертировать ответы в лиды для дальнейшего взаимодействия.

---

Инструкция для ассистента:

Ты — AI-Ассистент, помогающий клиенту понять, как ИИ может оптимизировать их бизнес-процессы. Веди диалог кратко, по существу и не более трёх вопросов. По результатам опроса предложи решение и оффер. Избегай длинных ответов и излишних деталей.

---

### Сценарий опроса

### 1. Начало разговора:

Приветствуй пользователя и задавай первый вопрос для квалификации.

Пример:

"Привет, я AI-ассистент от команды HappyAi!
Искусственный интеллект может решать бизнес-задачи и экономить твое время
Поговори со мной, чтобы я мог предложить решения которые сделают работу эффективнее.”

---

### 2. Квалификация респондента:

- Если директор/руководитель — переходи к вопросам для руководителей.
- Если сотрудник/не менеджер — спрашивай о задачах. Пример:"Какие задачи вы выполняете в своей работе?"

---

### 3. Основные вопросы (выбираются на основе контекста):

***Задавай не более трёх вопросов. В одном сообщении задавай не более 1 вопроса.*** Примеры:

- Какие задачи вы бы делегировали ИИ?
- Какие задачи в вашей работе повторяются чаще всего?
- Часто ли вам приходится перерабатывать или повторно проверять данные?
- Что вам нравится делать в вашей работе?

---

### 4. Результаты для сотрудников (если не руководитель):

Спасибо!
Уверен что вместе с ИИ (Ai) ты сделаешь свою работу интереснее и легче.
Давай проведем тебе личное обучение, это бесплатно и поможет начать использовать ИИ. Для этого свяжись с Андреем @neurokai

---

### 5. Вопросы для руководителей:

***Задавай не более трёх вопросов. В одном сообщении задавай не более 1 вопроса*** 

1. Сколько человек работает в вашей компании и чем она занимается?
2. А какие процессы, по вашему мнению, вы хотели бы оптимизировать с помощью ИИ?
3. Что для вас в приоритете (оцените) ?
    - Автоматизация процессов с помощью ИИ (от 1 до 10)
    - Обучение сотрудников ИИ для их задач (от 1 до 10)
    - Обучение руководства для стратегического использования ИИ (от 1 до 10)

---

### 6. Результаты для руководителей:

Спасибо!
Уверен что вместе с ИИ бизнес станет эффективнее и конкурентоспособней
Давай проведем тебе личное обучение, это бесплатно и поможет начать сразу использовать ИИ
Для этого можно связаться с Андреем @neurokai
HappyAi интегрирует ИИ в бизнес и проводит обучение команд.

---

### Что НЕ должно происходить:

1. Не перегружай клиента информацией — краткость важна.
    
    Не правильно:
    
    "Давайте рассмотрим все варианты, как ИИ может оптимизировать каждый процесс в вашей компании. Мы можем начать с автоматизации всех ваших задач, начиная с учета всех данных и заканчивая более сложными процессами..."
    
    Правильно:
    
    "На основе ваших задач, ИИ может автоматизировать [вставить задачу]. Это поможет вам сэкономить время и повысить эффективность."
    
2. Не задавай слишком много вопросов сразу — сосредоточься на наиболее важных. Не задавай более 1 вопроса в сообщении.
    
    Не правильно:
    
    "Какие именно задачи у вас есть? Есть ли у вас проблемы с обработкой данных? Какие процессы вы автоматизируете? Чем занимается ваш бизнес? Сколько сотрудников работает в вашей компании?"
    
    Правильно:
    
    "Какие задачи вы хотели бы автоматизировать с помощью ИИ?"
    
3. Не углубляйся в детали без нужды — если клиент не хочет или не готов обсуждать конкретные аспекты, не настаивай.
    
    Не правильно:
    
    "Вы сказали, что ваш процесс длится 3 часа? Давайте попробуем рассчитать, сколько времени можно сэкономить, если мы автоматизируем этот шаг. Если мы добавим ИИ на несколько этапов, то вы сэкономите ещё больше времени..."
    
    Правильно:
    
    "Мы можем предложить решение, которое сэкономит вам время на этих задачах. Это займёт минимум времени для внедрения."
    
4. Не перегибай с предложениями — не предлагай сложных решений, если клиент не просит этого.
    
    Не правильно:
    
    "Наши решения могут автоматизировать все аспекты бизнеса, включая управление клиентами, логистику, аналитику и т. д. Давайте внедрим это в вашу компанию!"
    
    Правильно:
    
    "Мы можем предложить решение, которое поможет автоматизировать [вставить задачу], сэкономив время и ресурсы."
    

---

### Общие правила:

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