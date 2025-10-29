FROM python:3.12

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/
COPY .env.docker /code/.env

RUN chmod +x /code/start.sh
CMD ["sh", "-c", "python manage.py migrate && sh /code/start.sh"]