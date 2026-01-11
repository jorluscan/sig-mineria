from django.urls import path
from . import views

urlpatterns = [
    # Dashboard (Resumen)
    path('dashboard/', views.inventory_dashboard, name='inventory_dashboard'),
    
    # Inventario Maestro (La ruta que falta)
    path('inventario/', views.inventory_list, name='inventory_list'),
    
    # Gestión de Productos
    path('catalogo/nuevo/', views.create_product, name='create_product'),
    path('producto/<int:pk>/', views.product_detail, name='product_detail'),
    
    # Logística
    path('despacho/nuevo/', views.create_dispatch, name='create_dispatch'),
    path('inventario/ingreso/', views.create_stock_arrival, name='create_stock_arrival'),
]