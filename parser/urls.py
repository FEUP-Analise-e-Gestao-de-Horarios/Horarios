from django.urls import path
from . import views

app_name = "parser"

urlpatterns = [
    path('parse/', views.parse),
    path('selecionar_simultaneas/', views.candidatos_turmas_simultaneas, name='selecionar_simultaneas'),
    path('guardar_simultaneas/', views.guardar_simultaneas, name='guardar_simultaneas'),
]