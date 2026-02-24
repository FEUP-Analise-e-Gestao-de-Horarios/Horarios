# Projeto-Integrador

For a description of the directory structure see [structure](Structure.md).

# Django Environment Setup:

## 1. Installing Dependencies:

Install git, python and pip:

```
sudo apt install git python pip
```

_Note: assuming Ubuntu as the OS. For other distributions or OSs the command may differ_

**On the server only, install nginx and supervisor:**

```
sudo apt install nginx supervisor
```

Install pipenv and django:

```
pip install pipenv django
```

## 2. Clone the repository:

```
git clone <url or ssh>
```

_Note: on the server it is recommended to use the github deployment key_

Change to the directory:

```
cd Projeto-Integrador
```

_Note: replace Projeto-Integrador with the directory name, if different_

## 3. Create the Environment:

Inside the Projeto-Integrador directory:

```
pipenv install django
```

This creates the virtual environment, installs the dependencies and prepares the project.
To enter the virtual environment:

```
pipenv shell
```

and to exit:
`ctrl+c`

## 4. Migrations and Static Files:

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

## 5. Run the server on localhost and check if it works:

To run the server in development mode:

```
python manage.py runserver
```

Check if it reports any errors or missing migrations.

To stop: `ctrl+c`

_Note: if you get a module import error, install it:_

```
pipenv install <module>
```

or

```
pip install <module>
```

To log in to the application, use the username `admin` with the password `passhorarios`.

The 'Name' project in the application serves only as a placeholder, it has no associated database, and can be deleted after the first login.

# Deployment:

## 6. Configure settings.py

_From here on, this is only relevant for deployment on the production server_

Edit the file `FeupScheduleEditor/settings.py`, set `DEBUG=False`

From the Projeto-Integrador directory:

```
nano FeupScheduleEditor/settings.py
```

Change line 36 to:
`DEBUG = False`

_Note: the line number may change if the file has also been modified. If so, search for the `DEBUG` entry_

## 7. Configure NGINX:

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

## 8. Daphne

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

## 9. Configure Supervisor

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

# 10. Start the Server

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
