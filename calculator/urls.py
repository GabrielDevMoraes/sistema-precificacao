# calculator/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Páginas existentes
    path('', views.dashboard_view, name='dashboard'),
    path('calculadora/', views.calculator_view, name='calculator'),
    
    # --- ADICIONE ESTA LINHA ---
    path('api/search_ncm/', views.search_ncm_api_view, name='search_ncm_api'),
    
    # NOVAS URLs PARA GESTÃO DE PRODUTOS
    path('produtos/', views.produto_list_view, name='produto_list'),
    path('produtos/novo/', views.produto_create_view, name='produto_create'),
    path('produtos/<int:pk>/editar/', views.produto_update_view, name='produto_update'),
    path('produtos/<int:pk>/deletar/', views.produto_delete_view, name='produto_delete'),
    
    # API de cálculo (existente)
    path('api/calculate/', views.calculate_api_view, name='calculate_api'),
]