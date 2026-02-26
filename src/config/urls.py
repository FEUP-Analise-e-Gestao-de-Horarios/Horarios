"""FeupScheduleEditor URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from src.FeupScheduleEditor import views

urlpatterns = [
    path("admin/", admin.site.urls),  # redirects to urls.py in admin module
    path(
        "parser/", include("src.parser.urls")
    ),  # redirects to urls.py in parser module
    path("", views.starter),
    path("groups", views.groups),
    path("deleteProject", views.deleteProject),
    path("login/", include("src.login.urls")),  # redirects to urls.py from login module
    path("editturnos/<int:projId>", views.editTurnos),  # projId extracted from uri
    path("emptytable/", views.createEmptyTable, name="emptytable"),
    path("getucs/", views.get_uc_list, name="get_uc_list"),
    path("table/", views.fillPageForCursoAno, name="table"),
    path("distribuicao/", views.distribuicao_view, name="distribuicao"),
    path("schedule/", views.schedule_view, name="schedule"),
    path("blocosturma/", views.blocosVermelhosTurma, name="blocosturma"),
    path("getdocentehorario/", views.get_docente_horario, name="getdocentehorario"),
    path("getsalahorario/", views.get_sala_horario, name="getsalahorario"),
    path(
        "getdocenteminihorario",
        views.getDocenteMiniHorario,
        name="getdocenteminihorario",
    ),
    path("getsalaminihorario", views.getSalaMiniHorario, name="getsalaminihorario"),
    path("editturnos/<int:projId>/createDocente/", views.createDocente),
    path("editturnos/<int:projId>/editDocentes/", views.editDocentes),
    path(
        "editturnos/<int:projId>/editDocentes/makeChange/", views.editDocentesMakeChange
    ),
    path("editturnos/<int:projId>/makechanges", views.makeChanges),
    path("manageProjects/<int:projId>", views.manageProjects),
    path("conflicts/<int:projId>/", views.getConflicts, name="conflicts_page"),
    path("export/<int:projId>", views.export),
    path("ucview/<int:projId>/<str:uc_codigo>", views.uc_view, name="uc_view"),
    path("editturnos/<int:projId>/uc_changes/", views.uc_changes, name="uc_changes"),
    path(
        "editturnos/<int:projId>/swap_teachers/",
        views.swap_teachers,
        name="swap_teachers",
    ),
    path(
        "getaulaparalelosimultanea",
        views.getAulaSimultaneasParalelas,
        name="getaulaparalelosimultanea",
    ),
    path("editturnos/<int:projId>/swap_aulas/", views.swap_aulas, name="swap_aulas"),
]
