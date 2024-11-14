FROM  python:latest
ENV PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  VIRTUAL_ENV=/voice_bot/venv \
  PATH="/voice_bot/venv/bin:$PATH" \
  PYTHONPATH=/voice_bot

WORKDIR /voice_bot

COPY requirements.txt requirements.txt

COPY start.sh /voice_bot/start.sh

RUN python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/pip install --upgrade pip \
    && $VIRTUAL_ENV/bin/pip install -r requirements.txt

COPY . .

RUN chmod +x /voice_bot/start.sh

CMD ["./start.sh"]