# back meduzzen intership

    1.Іnstall requirements
    pip install -r requirements.txt

    2.Start the project using the command:
    python manage.py runserver

# launches within Docker

    1.For launch django app
    docker-compose up django_app

    2.For tests using the command:
    docker-compose up test

# database migrations

    1.For create migrations
    python manage.py make migrations

    2.For applying migrations

# database migrations within Docker

    1.For create migrations
    python manage.py make migrations

    2.For applying migrations
    docker-compose exec django_app python manage.py migrate
