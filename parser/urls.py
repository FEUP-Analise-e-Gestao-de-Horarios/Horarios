from django.urls import path
from . import views

app_name = "parser"

urlpatterns = [
    path('parse/', views.parse),
    path('selecionar_aulas_em_paralelo/', views.selecionar_aulas_em_paralelo, name='selecionar_aulas_em_paralelo'),
    path('guardar_aulas_em_paralelo/', views.guardar_aulas_em_paralelo, name='guardar_aulas_em_paralelo'),
]