FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY main.py .
COPY requirements.txt .

RUN mkdir -p instance

RUN ls -la templates/

EXPOSE 5000

ENV FLASK_APP=main.py
ENV FLASK_ENV=development

CMD ["python", "main.py"]
