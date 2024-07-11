# Projeto-Integrador

Para uma descrição da estrutura do diretório ver [estrutura](Structure.md).

# Preparação do Ambiente Django:


## 1. Instalação de Dependencias:

Instalar git, python e pip:

```
sudo apt install git python pip
```

*Nota: assumindo uso de Ubunto como OS. Para outras distribuições ou OSs o comando pode ser diferente*

**Apenas no servidor, instalar nginx e supervisor:**

```
sudo apt install nginx supervisor
```

Instalar pipenv e django:

```
pip install pipenv django
```


## 2. Clonar o repositório:
```
git clone <url ou ssh>
```

*Nota: no servidor é recomendado usar a chave de deployment do github*

Mudar para o diretório:

```
cd Projeto-Integrador
```

*Nota: trocar Projeto-Integrador pelo nome do diretório, se diferente*

## 3. Criar o Ambiente:

Dentro do diretório Projeto-Integrador:

```
pipenv install django
```

Isto cria o ambiente virtual, instala as dependencias e prepara o projeto.
Para aceder ao ambiente virtual:

```
pipenv shell
```

e para sair:
`ctrl+c`

## 4. Migrações e Ficheiros Estáticos:

Certificar que está dentro do ambiente virtual com:

```
pipenv shell
```

Para criar as necessárias migrações:

```
python manage.py makemigrations
```

Para efetuar as migrações:

```
python manage.py migrate
```

Para importar ficheiros estáticos, mais concretamente ficheiros .js e .css:

```
python manage.py collectstatic
```

*Nota: isto importa todos os ficheiros estáticos no diretório static/*

## 5. Correr o servidor em localhost e ver se funciona:
Para correr o servidor, em modo de desenvolvimento:

```
python manage.py runserver
```

Verificar se reporta algum erro ou migração em falta.

Para parar: `ctrl+c`

*Nota: se der erro de importação de um módulo, instale:*

```
pipenv install <módulo>
```

ou

```
pip install <módulo>
```

Para realizar o login na aplicação, basta usar o username `admin`, com a palavra-passe `passhorarios`.

O projeto 'Nome' na aplicação funciona apenas como placeholder, não tem uma base de dados associada, e pode ser apagado após o primeiro login.

# Deployment:

## 6. Configurar settings.py
*Apartir daqui, é apenas relevante para o deployment no servidor de produção*

Alterar o ficheiro `FeupScheduleEditor/settings.py`, colocar `DEBUG=False`

Apartir do diretório Projeto-Integrador:

```
nano FeupScheduleEditor/settings.py
```

Alterar a linha 36 para:
`DEBUG = False`

*Nota: o número da linha pode alterar, se o ficheiro também tiver sido alterado. Se for o caso, procurar pela entrada `DEBUG`*

## 7. Configurar NGINX:

Para criar o bloco de configuração do projeto:

```
sudo nano /etc/nginx/sites-available/FeupScheduleEditor
```

Colar a seguinte configuração:
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


Criar o link simbólico com os sites-enabled:

```
sudo ln -s /etc/nginx/sites-available/FeupScheduleEditor /etc/nginx/sites-enabled/
```

Testar a configuração:

```
sudo nginx -t
```

Se tudo correr bem, reiniciar o site:

```
sudo service nginx restart
```

*Nota: Se for necessário alterar o tempo necessário para timeout:*

```
sudo nano /etc/nginx/nginx.conf
```

colar, na secção http:

```
    proxy_connect_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_read_timeout 3600s;
```
Trocar 3600 pelo tempo desejado, em segundos e reiniciar:

```
sudo service nginx restart
```

## 8. Daphne

Antes disto, no ambiente virtual pipenv, verificar se o projeto está pronto para o deployment:

```
python manage.py check --deploy
```

e analisar bem os *warnings*, alguns destes não precisam de ser corrigidos, dependendo da implementação 

No diretório do projeto, no ambiente virtual pipenv, correr Daphne, para ligar o servidor:

```
daphne FeupScheduleEditor.asgi:application
```

Neste ponto, o site deve estar acessível no browser, através do IP, na rede da Feup ou com o vpn.

Para desligar: `ctrl+c`

*Nota: neste momento o site só corre enquando o daphne estiver a correr em primeiro plano e a ligação ssh estiver ativa. Assim que desconectar a ligação ssh, o site ficará inacessível*

## 9. Configurar Supervisor

Para garantir que o Daphne corre em segundo plano, independentemente da ligação ssh, é necessário configurar o Supervisor:

```
sudo nano /etc/supervisor/conf.d/daphne.conf
```

*Nota: se o diretório não existir, é preciso criá-lo com:*

```
sudo mkdir /etc/supervisor/conf.d
```

*E voltar a correr o comando anterior.*

Colar a seguinte configuração:

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

*Nota: Se o ficheiro de logs de daphne não exitir, crie:*

```
sudo touch /var/log/daphne.log
```

Alterar as entradas **command** e **directory** por:

`command=/path/to/your/virtual/env/bin/daphne FeupScheduleEditor.asgi:application`

E

`directory=/path/to/your/django/app`

Respetivamente.

Recarregar as mudanças:
```
sudo supervisorctl reread
sudo supervisorctl update
```

# 10. Ligar o Servidor

Ativar o Daphne através do Supervisor:

```
sudo supervisorctl start daphne
```

Neste momento o site deve estar acessível.

Para o parar:

```
sudo supervisorctl stop daphne
```

Se for necessário consultar os logs de supervisor fazer:
```
sudo cat /var/log/supervisor/supervisord.log
```

E os logs de daphne fazer:
```
sudo cat /var/log/daphne.log
```

ou, para as últimas 100 linhas:
```
sudo tail -100 /var/log/daphne.log
```
