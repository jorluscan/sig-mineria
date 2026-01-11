# inventory_app/admin.py

from django.contrib import admin
from .models import Warehouse, Product, ProductLot, SerialNumber

# Register your models here.


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'is_active')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'sale_price', 'cost_price',
                    'tracking_type', 'is_active')
    list_filter = ('tracking_type', 'is_active', 'category')
    search_fields = ('name', 'sku', 'barcode')


@admin.register(ProductLot)
class ProductLotAdmin(admin.ModelAdmin):
    list_display = ('product', 'lot_number', 'quantity',
                    'expiration_date', 'warehouse')
    search_fields = ('product__name', 'lot_number')


@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display = ('product', 'serial_number', 'status', 'warehouse')
    list_filter = ('status',)
    search_fields = ('product__name', 'serial_number')
