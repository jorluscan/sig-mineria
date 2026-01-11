# delivery_app/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

# Importamos los modelos de otras apps con los que nos relacionaremos
from billing_app.models import Client, Invoice
from inventory_app.models import Product


class DeliveryNote(models.Model):
    """Representa una nota de entrega o despacho."""
    class DeliveryStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pendiente')
        PREPARING = 'PREPARING', _('En Preparación')
        DISPATCHED = 'DISPATCHED', _('Despachada')
        DELIVERED = 'DELIVERED', _('Entregada')
        CANCELLED = 'CANCELLED', _('Cancelada')

    delivery_note_number = models.CharField(
        max_length=50, unique=True, verbose_name=_("Número de Nota de Entrega"))

    # Vínculos con otros módulos
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, verbose_name=_("Cliente"))
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Factura Asociada (Opcional)")
    )

    delivery_date = models.DateField(verbose_name=_("Fecha de Despacho"))
    delivery_address = models.TextField(verbose_name=_("Dirección de Entrega"))

    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        verbose_name=_("Estado del Despacho")
    )

    # Personas involucradas
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_delivery_notes',
        verbose_name=_("Creado por")
    )
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivered_notes',
        verbose_name=_("Transportista/Despachado por")
    )
    received_by = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Recibido por (Nombre y C.I.)"))

    notes = models.TextField(blank=True, null=True,
                             verbose_name=_("Notas Adicionales"))
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Fecha de Creación"))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_("Última Actualización"))

    class Meta:
        verbose_name = _("Nota de Entrega")
        verbose_name_plural = _("Notas de Entrega")

    def __str__(self):
        return f"Nota de Entrega #{self.delivery_note_number} para {self.client.full_name}"


class DeliveryNoteItem(models.Model):
    """Representa un ítem o línea de producto dentro de una nota de entrega."""
    delivery_note = models.ForeignKey(
        DeliveryNote, on_delete=models.CASCADE, related_name='items', verbose_name=_("Nota de Entrega"))
    product = models.ForeignKey(
        'inventory_app.Product', on_delete=models.PROTECT, verbose_name=_("Producto"))

    # Campos denormalizados para mantener la integridad histórica
    product_name = models.CharField(
        max_length=255, verbose_name=_("Nombre del Producto"))
    sku = models.CharField(max_length=50, verbose_name=_("SKU"))

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Cantidad a Despachar"))

    class Meta:
        verbose_name = _("Ítem de Nota de Entrega")
        verbose_name_plural = _("Ítems de Nota de Entrega")

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
