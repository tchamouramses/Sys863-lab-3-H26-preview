FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mv .env.example .env
EXPOSE 5000

CMD ["python", "run.py"]
