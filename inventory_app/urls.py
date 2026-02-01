# inventory_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Principal
    path('dashboard/', views.inventory_dashboard, name='inventory_dashboard'),
    
    # Listado y Detalle de Productos
    path('inventario/', views.inventory_list, name='inventory_list'),
    path('producto/<int:pk>/', views.product_detail, name='product_detail'),
    
    # Creación de Registros (Formularios)
    path('catalogo/nuevo/', views.create_product, name='create_product'),
    path('despacho/nuevo/', views.create_dispatch, name='create_dispatch'),
    path('ingreso/nuevo/', views.create_stock_arrival, name='create_stock_arrival'),
    
    # Endpoints de Búsqueda (AJAX)
    path('product-search-ajax/', views.product_search_ajax, name='product_search_ajax'),
    # Actulizacion de Precio
    path('producto/<int:pk>/cambiar-precio/', views.update_product_price, name='update_product_price'),
]