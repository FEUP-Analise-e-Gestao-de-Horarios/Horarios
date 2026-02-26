# FEUP Análise e Gestão de Horários

A Django web application for analyzing and managing FEUP course schedules. It allows users to view, parse, and manage timetable data, with support for conflict detection and user authentication.

# Django Environment Setup

## 1. Installing Dependencies

_Note: assuming Ubuntu as the OS. For other distributions or OSs the command may differ_

**On the server only, install nginx and supervisor:**

```
sudo apt install nginx supervisor
```

Install git:

```
sudo apt install git
```

Install Python version mentioned on the Pipfile (we suggest using [pyenv](https://github.com/pyenv/pyenv)):

```
pyenv install 3.14.3
```

Install pipenv:

```
pip install pipenv
```

## 2. Create the Environment

Inside the dependencies:

```
pipenv install --dev
```

To enter the virtual environment:

```
pipenv shell
```

and to exit:

```
exit
```

## 3. Migrations and Static Files

Make sure you are inside the virtual environment with:

```
pipenv shell
```

To create the necessary migrations:

```
python manage.py makemigrations
```

To apply the migrations:

```
python manage.py migrate
```

To import static files, specifically .js and .css files:

```
python manage.py collectstatic
```

_Note: this imports all static files into the static/ directory_

## 4. Run the server on localhost and check if it works

To run the server in development mode:

```
python manage.py runserver
```

Check if it reports any errors or missing migrations.

To stop: `ctrl+c`

To log in to the application, use the username `admin` with the password `passhorarios`.

The 'Name' project in the application serves only as a placeholder, it has no associated database, and can be deleted after the first login.

# Deployment

## 5. Configure settings.py

_From here on, this is only relevant for deployment on the production server_

Edit the file `FeupScheduleEditor/settings.py`, set `DEBUG=False`

From the Projeto-Integrador directory:

```
nano FeupScheduleEditor/settings.py
```

Change line 36 to:
`DEBUG = False`

_Note: the line number may change if the file has also been modified. If so, search for the `DEBUG` entry_

## 6. Configure NGINX

To create the project's configuration block:

```
sudo nano /etc/nginx/sites-available/FeupScheduleEditor
```

Paste the following configuration:

```
server {
    listen 80;
    server_name 10.227.107.115;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Create the symbolic link with sites-enabled:

```
sudo ln -s /etc/nginx/sites-available/FeupScheduleEditor /etc/nginx/sites-enabled/
```

Test the configuration:

```
sudo nginx -t
```

If everything goes well, restart the site:

```
sudo service nginx restart
```

_Note: If you need to change the timeout duration:_

```
sudo nano /etc/nginx/nginx.conf
```

paste, in the http section:

```
    proxy_connect_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_read_timeout 3600s;
```

Replace 3600 with the desired time in seconds and restart:

```
sudo service nginx restart
```

## 7. Daphne

Before this, in the pipenv virtual environment, check if the project is ready for deployment:

```
python manage.py check --deploy
```

and carefully review the _warnings_ — some of these do not need to be fixed, depending on the implementation

In the project directory, in the pipenv virtual environment, run Daphne to start the server:

```
daphne FeupScheduleEditor.asgi:application
```

At this point, the site should be accessible in the browser via the IP address, on the Feup network or with a VPN.

To stop: `ctrl+c`

_Note: at this point the site only runs while daphne is running in the foreground and the SSH connection is active. Once the SSH connection is disconnected, the site will become inaccessible_

## 8. Configure Supervisor

To ensure that Daphne runs in the background, regardless of the SSH connection, you need to configure Supervisor:

```
sudo nano /etc/supervisor/conf.d/daphne.conf
```

_Note: if the directory does not exist, create it with:_

```
sudo mkdir /etc/supervisor/conf.d
```

_And run the previous command again._

Paste the following configuration:

```
[program:daphne]
command=/home/horarios/.local/share/virtualenvs/Projeto-Integrador-q-HvG0Rs/bin/daphne FeupScheduleEditor.asgi:application
directory=/home/horarios/Projeto-Integrador
user=horarios
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/daphne.log
```

_Note: If the daphne log file does not exist, create it:_

```
sudo touch /var/log/daphne.log
```

Replace the **command** and **directory** entries with:

`command=/path/to/your/virtual/env/bin/daphne FeupScheduleEditor.asgi:application`

And

`directory=/path/to/your/django/app`

Respectively.

Reload the changes:

```
sudo supervisorctl reread
sudo supervisorctl update
```

# 9. Start the Server

Activate Daphne through Supervisor:

```
sudo supervisorctl start daphne
```

At this point the site should be accessible.

To stop it:

```
sudo supervisorctl stop daphne
```

To view the supervisor logs:

```
sudo cat /var/log/supervisor/supervisord.log
```

And the daphne logs:

```
sudo cat /var/log/daphne.log
```

or, for the last 100 lines:

```
sudo tail -100 /var/log/daphne.log
```

For a description of the directory structure see [structure](Structure.md).
