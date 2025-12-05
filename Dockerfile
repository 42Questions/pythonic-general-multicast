FROM python:3.14-slim

WORKDIR /app

COPY src/ ./src/
COPY tests/ ./tests/

RUN pip install --no-cache-dir pytest

CMD ["python", "-u", "src/client.py"]
