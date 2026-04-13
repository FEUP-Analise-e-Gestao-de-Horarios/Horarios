"""Root URL configuration.

React SPA pages are served by ``spa_view``; API endpoints live under ``/api/``.
See docs/refactors/frontend.md for how React Router and Django URLs stay in sync.
"""

from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from src.projects.views.export import ProjectExportView

# SPA (Single Page Application) for React
spa_view = ensure_csrf_cookie(
    TemplateView.as_view(template_name="index.html"),
)


urlpatterns = [
    # React URLs
    path("", spa_view, name="dashboard"),
    path("login", spa_view, name="login"),
    path("forgot-password", spa_view, name="forgot-password"),
    path("change-password", spa_view, name="change-password"),
    path("projects/<int:project_id>/", spa_view, name="schedule"),
    path("projects/<int:project_id>/dashboard", spa_view, name="dashboard"),
    # API endpoints
    path("api/projects/", include("src.projects.urls")),
    path("api/auth/", include("src.login.urls")),
    path("admin/", admin.site.urls, name="admin"),  # TODO Check URL
    path("export/<int:project_id>", ProjectExportView.as_view()),
]

# TODO Check URLs bellow
# path("parser/", include("src.parser.urls")),
# path("groups", views.groups),
# path("deleteProject", views.deleteProject),
# path("editturnos/<int:projId>", views.editTurnos),
# path("emptytable/", views.createEmptyTable, name="emptytable"),
# path("getucs/", views.get_uc_list, name="get_uc_list"),
# path("table/", views.fillPageForCursoAno, name="table"),
# path("distribuicao/", views.distribuicao_view, name="distribuicao"),
# path("schedule/", views.schedule_view, name="schedule"),
# path("blocosturma/", views.blocosVermelhosTurma, name="blocosturma"),
# path("getdocentehorario/", views.get_docente_horario, name="getdocentehorario"),
# path("getsalahorario/", views.get_sala_horario, name="getsalahorario"),
# path("getdocenteminihorario", views.getDocenteMiniHorario, name="getdocenteminihorario"),
# path("getsalaminihorario", views.getSalaMiniHorario, name="getsalaminihorario"),
# path("editturnos/<int:projId>/createDocente/", views.createDocente),
# path("editturnos/<int:projId>/editDocentes/", views.editDocentes),
# path("editturnos/<int:projId>/editDocentes/makeChange/", views.editDocentesMakeChange),
# path("editturnos/<int:projId>/makechanges", views.makeChanges),
# path("manageProjects/<int:projId>", views.manageProjects),
# path("conflicts/<int:projId>/", views.getConflicts, name="conflicts_page"),
# path("ucview/<int:projId>/<str:uc_codigo>", views.uc_view, name="uc_view"),
# path("editturnos/<int:projId>/uc_changes/", views.uc_changes, name="uc_changes"),
# path("editturnos/<int:projId>/swap_teachers/", views.swap_teachers, name="swap_teachers"),
# path( "getaulaparalelosimultanea", views.getAulaSimultaneasParalelas, name="getaulaparalelosimultanea"),
# path("editturnos/<int:projId>/swap_aulas/", views.swap_aulas, name="swap_aulas"),
