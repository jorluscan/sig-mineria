# delivery_app/admin.py

from django.contrib import admin
from .models import DeliveryNote, DeliveryNoteItem

# Register your models here.


class DeliveryNoteItemInline(admin.TabularInline):
    """
    Permite editar los ítems de la nota de entrega directamente
    dentro de la vista de la nota de entrega.
    """
    model = DeliveryNoteItem
    extra = 1


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(admin.ModelAdmin):
    list_display = ('delivery_note_number', 'client',
                    'delivery_date', 'status')
    list_filter = ('status', 'delivery_date')
    search_fields = ('delivery_note_number', 'client__full_name')
    inlines = [DeliveryNoteItemInline]
