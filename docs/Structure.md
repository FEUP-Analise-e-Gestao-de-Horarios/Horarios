The repository contains the following application directories:

- FeupScheduleEditor
- parser
- login
- core
- users

Within these, the following files stand out:

- urls.py, where URLs are mapped to each function
- views.py, where those functions are defined, rendering pages or JSON
- models.py, where relational models are defined

In the case of FeupScheduleEditor, which contains the majority of the project, the following files also stand out:

- settings.py, which contains the project configuration
- asgi.py, which contains the ASGI application configuration

The following directories also stand out:

- database, which contains the .sql database file and:
    - ProjectX directories, where X is the project id, containing the initial and general databases and the conflicts file
- getHorariosFromDB, which contains auxiliary .py files used by the project
- templates, which contains partial .html files used to render pages
- static, which contains the static .js and .css files used in the project, loaded in DEBUG=True mode
- staticfiles, the directory where the server loads static files in DEBUG=False mode, imported from /static by running
  `python manage.py collectstatic`
