FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r ./requirements.txt

EXPOSE 8000

COPY . .

CMD ["uvicorn", "app:app", "--reload", "--host=0.0.0.0", "--port=8000"]