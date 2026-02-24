# Project Structure

## Application Directories

The repository contains the following application directories:

- `FeupScheduleEditor`
- `parser`
- `login`
- `core`
- `users`

Within these, the following files stand out:

- `urls.py` — maps URLs to each function
- `views.py` — defines those functions, rendering pages or JSON
- `models.py` — defines relational models

### FeupScheduleEditor

This directory contains the majority of the project. In addition to the files above, the following also stand out:

- `settings.py` — project configuration
- `asgi.py` — ASGI application configuration

## Notable Directories

- `database/` — contains the `.sql` database file and:
    - `ProjectX/` directories, where `X` is the project id, each containing the initial and general databases and the conflicts file
- `getHorariosFromDB/` — contains auxiliary `.py` files used by the project
- `templates/` — contains partial `.html` files used to render pages
- `static/` — contains the static `.js` and `.css` files used in the project, loaded in `DEBUG=True` mode
- `staticfiles/` — where the server loads static files in `DEBUG=False` mode; populated from `static/` by running:
    ```
    python manage.py collectstatic
    ```
