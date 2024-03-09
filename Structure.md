O repositório contem os seguintes diretórios de aplicações:
 - FeupScheduleEditor
 - parser
 - login
 - core
 - users

Nestes destacam-se os ficheiros:
- urls.py, onde se mapeam os urls a cada função
- views.py, onde estão as dadas funções, que renderizam páginas ou JSON
- models.py, onde são definidos modelos relacionais

No caso da FeupScheduleEditor, onde é contido a maior parte do projeto, destacam-se, também, os ficheiros:
 - settings.py, que contém as configurações do projeto
 - asgi.py, que contém as configurações da aplicação ASGI
 - wsgi.py, que contém as configurações da aplicação WSGI

Destaca-se, também os seguintes diretórios:
- database, que contém o ficheiro .sql das bases de dados e:
  - diretórios ProjectX, onde X é o id do projeto, que contêm as bases de dados inicial e geral e o ficheiro de conflitos
- getHorariosFromDB, que contém ficheiros .py auxiliares, usados pelo projeto
- templates, que contém os ficheiros .html parciais, usados para renderizar as páginas
- static, onde estão contidos os ficheiros estáticos .js e .css usados no projeto, são carregados em modo DEBUG=True
- staticfiles, diretório onde o servidor carrega os ficheiros estáticos em modo DEBUG=False, são importados de /static ao usar
  ```python manage.py collectstatic```
