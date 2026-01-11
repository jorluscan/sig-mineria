# purchasing_app/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

# Importamos los modelos de otras apps
from inventory_app.models import Product


class Supplier(models.Model):
    """Representa a un proveedor de productos."""
    name = models.CharField(max_length=255, unique=True,
                            verbose_name=_("Nombre del Proveedor"))
    contact_person = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Persona de Contacto"))
    email = models.EmailField(
        max_length=100, blank=True, null=True, verbose_name=_("Correo Electrónico"))
    phone = models.CharField(max_length=50, blank=True,
                             null=True, verbose_name=_("Teléfono"))
    address = models.TextField(
        blank=True, null=True, verbose_name=_("Dirección"))

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Fecha de Creación"))
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_("Última Actualización"))

    class Meta:
        verbose_name = _("Proveedor")
        verbose_name_plural = _("Proveedores")

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """Representa una orden de compra a un proveedor."""
    class POStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Borrador')
        SENT = 'SENT', _('Enviada')
        PARTIALLY_RECEIVED = 'PARTIALLY_RECEIVED', _('Recibida Parcialmente')
        FULLY_RECEIVED = 'FULLY_RECEIVED', _('Recibida Completamente')
        CANCELLED = 'CANCELLED', _('Cancelada')

    po_number = models.CharField(
        max_length=50, unique=True, verbose_name=_("Número de Orden de Compra"))
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, verbose_name=_("Proveedor"))
    order_date = models.DateField(verbose_name=_("Fecha de la Orden"))
    expected_delivery_date = models.DateField(
        blank=True, null=True, verbose_name=_("Fecha de Entrega Esperada"))

    status = models.CharField(
        max_length=20,
        choices=POStatus.choices,
        default=POStatus.DRAFT,
        verbose_name=_("Estado de la Orden")
    )

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
        verbose_name = _("Orden de Compra")
        verbose_name_plural = _("Órdenes de Compra")

    def __str__(self):
        return f"Orden #{self.po_number} a {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    """Representa un ítem de producto dentro de una orden de compra."""
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name=_("Orden de Compra"))
    product = models.ForeignKey(
        'inventory_app.Product', on_delete=models.PROTECT, verbose_name=_("Producto"))
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Cantidad Pedida"))
    cost_price = models.DecimalField(
        max_digits=18, decimal_places=4, verbose_name=_("Precio de Costo Acordado"))

    class Meta:
        verbose_name = _("Ítem de Orden de Compra")
        verbose_name_plural = _("Ítems de Orden de Compra")

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
