# purchasing_app/admin.py

from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem

# Register your models here.


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email')
    search_fields = ('name', 'contact_person')


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'status')
    list_filter = ('status', 'order_date')
    search_fields = ('po_number', 'supplier__name')
    inlines = [PurchaseOrderItemInline]
