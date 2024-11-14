from amplitude import Amplitude, BaseEvent
from config import settings
from concurrent.futures import ThreadPoolExecutor

client = Amplitude(settings.amplitude_api_key)
pool = ThreadPoolExecutor(max_workers=1)

class Events:  # содержит все возможные ивенты
    @staticmethod
    def start_event(user_id: str):
        event = BaseEvent(event_type="Start bot", user_id=user_id)
        pool.submit(client.track(event))