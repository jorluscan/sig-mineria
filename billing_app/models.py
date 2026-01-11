# billing_app/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from decimal import Decimal

# Importamos los modelos de otras apps con los que nos relacionaremos
# (Aunque no se use directamente en este archivo, es buena práctica tenerlo presente)
from inventory_app.models import Product


class Client(models.Model):
    """Representa a un cliente de la empresa."""
    class ClientType(models.TextChoices):
        NATURAL = 'NATURAL', _('Persona Natural')
        JURIDICAL = 'JURIDICAL', _('Persona Jurídica')

    client_type = models.CharField(
        max_length=10,
        choices=ClientType.choices,
        default=ClientType.NATURAL,
        verbose_name=_("Tipo de Cliente")
    )
    full_name = models.CharField(
        max_length=255, verbose_name=_("Nombre Completo / Razón Social"))
    identification_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_("Cédula / RIF")
    )
    address = models.TextField(
        blank=True, null=True, verbose_name=_("Dirección"))
    phone = models.CharField(max_length=50, blank=True,
                             null=True, verbose_name=_("Teléfono"))
    email = models.EmailField(
        max_length=100, blank=True, null=True, verbose_name=_("Correo Electrónico"))
    contact_person = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Persona de Contacto"))

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Fecha de Creación"))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_("Última Actualización"))

    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")

    def __str__(self):
        return self.full_name


class Invoice(models.Model):
    """Representa una factura de venta."""
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Borrador')
        ISSUED = 'ISSUED', _('Emitida')
        PAID = 'PAID', _('Pagada')
        VOID = 'VOID', _('Anulada')

    invoice_number = models.CharField(
        max_length=50, unique=True, verbose_name=_("Número de Factura"))
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, verbose_name=_("Cliente"))
    invoice_date = models.DateField(verbose_name=_("Fecha de la Factura"))
    due_date = models.DateField(
        blank=True, null=True, verbose_name=_("Fecha de Vencimiento"))

    subtotal = models.DecimalField(
        max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Subtotal"))
    tax_amount = models.DecimalField(
        max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Monto de Impuesto"))
    discount_amount = models.DecimalField(
        max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Monto de Descuento"))
    total_amount = models.DecimalField(
        max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Monto Total"))

    status = models.CharField(
        max_length=10,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        verbose_name=_("Estado")
    )

    payment_method = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("Método de Pago"))
    notes = models.TextField(blank=True, null=True, verbose_name=_("Notas"))

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Creado por")
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Fecha de Creación"))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_("Última Actualización"))

    class Meta:
        verbose_name = _("Factura")
        verbose_name_plural = _("Facturas")

    def __str__(self):
        return f"Factura #{self.invoice_number} - {self.client.full_name}"


class InvoiceItem(models.Model):
    """Representa un ítem o línea de producto dentro de una factura."""
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='items', verbose_name=_("Factura"))
    product = models.ForeignKey(
        'inventory_app.Product', on_delete=models.SET_NULL, null=True, verbose_name=_("Producto"))

    # Campos denormalizados para mantener la integridad histórica de la factura
    product_name = models.CharField(
        max_length=255, verbose_name=_("Nombre del Producto en la Venta"))
    sku = models.CharField(max_length=50, verbose_name=_("SKU en la Venta"))
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Cantidad"))
    unit_price = models.DecimalField(
        max_digits=18, decimal_places=4, verbose_name=_("Precio Unitario en la Venta"))
    line_total = models.DecimalField(
        max_digits=18, decimal_places=4, verbose_name=_("Total de Línea"), default=0)

    class Meta:
        verbose_name = _("Ítem de Factura")
        verbose_name_plural = _("Ítems de Factura")

    def __str__(self):
        return f"{self.quantity} x {self.product_name} en Factura #{self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        # Lógica de auto-cálculo para el total de la línea
        if self.product:
            self.product_name = self.product.name
            self.sku = self.product.sku
            # Si no se ha especificado un precio, tomar el precio de venta del producto
            if not self.unit_price or self.unit_price == 0:
                self.unit_price = self.product.sale_price

        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
