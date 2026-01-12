from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.inventory_dashboard, name='inventory_dashboard'),
    path('inventario/', views.inventory_list, name='inventory_list'),
    path('producto/<int:pk>/', views.product_detail, name='product_detail'),
    path('catalogo/nuevo/', views.create_product, name='create_product'),
    path('despacho/nuevo/', views.create_dispatch, name='create_dispatch'),
    path('ingreso/nuevo/', views.create_stock_arrival, name='create_stock_arrival'),
    path('product-search-ajax/', views.product_search_ajax, name='product_search_ajax'),
]