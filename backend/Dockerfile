FROM python:3.10-slim

WORKDIR /app

# Тәуелділіктерді орнату
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Жоба кодын көшіру
COPY . .

# Жобаны іске қосу командасы (main.py орнына өз файлыңызды қойыңыз)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]