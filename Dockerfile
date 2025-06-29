FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install -U pip
RUN pip install discord.py

CMD ["python", "bot.py"]
