# billing_app/admin.py

from django.contrib import admin
from .models import Client, Invoice, InvoiceItem
from decimal import Decimal


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'client_type',
                    'identification_number', 'phone', 'email')
    search_fields = ('full_name', 'identification_number')
    list_filter = ('client_type',)


class InvoiceItemInline(admin.TabularInline):
    """
    Permite editar los ítems de la factura directamente dentro de la vista de la factura.
    """
    model = InvoiceItem
    extra = 1  # Campos vacíos para añadir ítems por defecto.
    # Hacemos campos de solo lectura que se calculan solos
    readonly_fields = ('line_total', 'product_name', 'sku')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client',
                    'invoice_date', 'total_amount', 'status')
    list_filter = ('status', 'invoice_date')
    search_fields = ('invoice_number', 'client__full_name')
    # Hacemos los campos de totales de solo lectura en el formulario del admin
    readonly_fields = ('subtotal', 'tax_amount', 'total_amount',
                       'created_at', 'updated_at', 'created_by')

    # Aquí está la magia: añadimos los ítems de la factura a su página de detalle.
    inlines = [InvoiceItemInline]

    def save_model(self, request, obj, form, change):
        """Asigna el usuario actual al crear un objeto."""
        if not obj.pk:  # Si el objeto es nuevo
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """
        Este método se ejecuta después de guardar el objeto principal y sus inlines.
        Es el lugar perfecto para calcular los totales.
        """
        # Primero, ejecuta el guardado normal
        super().save_related(request, form, formsets, change)

        # 'form.instance' es el objeto de la factura que acabamos de guardar
        invoice = form.instance

        # Sumamos los totales de línea de todos los ítems asociados a esta factura
        subtotal = sum(item.line_total for item in invoice.items.all())

        # Asumimos una tasa de IVA del 16% por ahora. Esto lo haremos configurable más adelante.
        tax_rate = Decimal('0.16')
        tax_amount = subtotal * tax_rate

        # Calculamos el total final
        # NOTA: Aquí no estamos considerando el descuento aún, lo añadiremos después.
        total_amount = subtotal + tax_amount

        # Actualizamos los campos de la factura con los valores calculados
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total_amount = total_amount

        # Guardamos la factura de nuevo para persistir estos cambios
        invoice.save()
