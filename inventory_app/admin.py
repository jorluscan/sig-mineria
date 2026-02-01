# inventory_app/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Warehouse, Product, ProductLot, SerialNumber, Category, ProductVariation, Dispatch, StockArrival

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'is_active')
    search_fields = ('name',)

@admin.register(ProductVariation)
class ProductVariationAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'color', 'sku_variant', 'stock')
    list_filter = ('size', 'color', 'product__category')
    search_fields = ('sku_variant', 'product__name')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'sale_price', 'cost_price', 'total_stock', 'is_active')
    list_filter = ('tracking_type', 'is_active', 'category')
    search_fields = ('name', 'sku', 'barcode')
    readonly_fields = ('total_stock',) # El stock total se calcula solo

@admin.register(StockArrival)
class StockArrivalAdmin(admin.ModelAdmin):
    list_display = ('arrival_date', 'variation', 'quantity', 'unit_cost', 'color_difference', 'user')
    list_filter = ('arrival_date', 'variation__product__category')
    search_fields = ('variation__product__name', 'supplier')
    date_hierarchy = 'arrival_date'

    def color_difference(self, obj):
        """Muestra la diferencia de costo con colores: Verde (bajó/igual), Rojo (subió)"""
        diff = obj.cost_difference
        if diff > 0:
            color = "#ef4444" # Rojo Tailwind
            icon = "▲"
            text = f"+{diff:.2f}"
        elif diff < 0:
            color = "#10b981" # Verde Tailwind
            icon = "▼"
            text = f"{diff:.2f}"
        else:
            color = "#71717a" # Zinc
            icon = "●"
            text = "Sin cambio"
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, text
        )
    
    color_difference.short_description = "Variación de Costo"

@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = ('dispatched_at', 'variation', 'quantity', 'destination', 'user')
    list_filter = ('dispatched_at', 'variation__product__category')
    search_fields = ('variation__product__name', 'destination')

@admin.register(ProductLot)
class ProductLotAdmin(admin.ModelAdmin):
    list_display = ('product', 'lot_number', 'quantity', 'expiration_date', 'warehouse')
    search_fields = ('product__name', 'lot_number')

@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display = ('product', 'serial_number', 'status', 'warehouse')
    list_filter = ('status',)
    search_fields = ('product__name', 'serial_number')