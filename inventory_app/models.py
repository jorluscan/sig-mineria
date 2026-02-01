from django.db import models
from django.utils.translation import gettext_lazy as _

# 1. Modelo de Categorías
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre de Categoría"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))

    class Meta:
        verbose_name = _("Categoría")
        verbose_name_plural = _("Categorías")

    def __str__(self):
        return self.name

# 2. Modelo de Almacenes
class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre del Almacén"))
    address = models.TextField(blank=True, null=True, verbose_name=_("Dirección"))
    is_active = models.BooleanField(default=True, verbose_name=_("Está activo"))

    class Meta:
        verbose_name = _("Almacén")
        verbose_name_plural = _("Almacenes")

    def __str__(self):
        return self.name

# 3. Modelo de Producto Base
class Product(models.Model):
    class TrackingType(models.TextChoices):
        NONE = 'NONE', _('Sin Seguimiento')
        LOT = 'LOT', _('Por Lote')
        SERIAL = 'SERIAL', _('Por Número de Serie')

    sku = models.CharField(max_length=50, unique=True, verbose_name=_("SKU (Código Interno)"))
    name = models.CharField(max_length=255, verbose_name=_("Nombre del Producto"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name=_("Código de Barras"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Categoría"))
    unit_of_measure = models.CharField(max_length=20, default='unidad', verbose_name=_("Unidad de Medida"))
    cost_price = models.DecimalField(max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Precio de Costo"))
    sale_price = models.DecimalField(max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Precio de Venta"))
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Nivel Mínimo de Stock"))
    tracking_type = models.CharField(max_length=10, choices=TrackingType.choices, default=TrackingType.NONE, verbose_name=_("Tipo de Seguimiento"))
    is_active = models.BooleanField(default=True, verbose_name=_("Está activo"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de Creación"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Última Actualización"))

    @property
    def net_profit(self):
        if self.sale_price and self.cost_price:
            return self.sale_price - self.cost_price
        return 0
    
    @property
    def total_stock(self):
        from django.db.models import Sum
        return self.variations.aggregate(total=Sum('stock'))['total'] or 0

    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")

    def __str__(self):
        return f"{self.name} ({self.sku})"

# 4. Variaciones de Ropa
class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50)
    sku_variant = models.CharField(max_length=50, unique=True)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.size} / {self.color}"

# 5. Lotes
class ProductLot(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='lots')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    lot_number = models.CharField(max_length=50)
    expiration_date = models.DateField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('product', 'lot_number', 'warehouse')

# 6. Números de Serie
class SerialNumber(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serial_numbers')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='IN_STOCK')

# 7. Registro de Despachos (Salidas)
class Dispatch(models.Model):
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, related_name='dispatches')
    quantity = models.PositiveIntegerField()
    destination = models.CharField(max_length=255)
    dispatched_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    @property
    def total_value(self):
        """Calcula el valor total de la salida (Precio de Venta)"""
        return self.quantity * self.variation.product.sale_price

    def __str__(self):
        return f"{self.quantity} x {self.variation}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.variation.stock -= self.quantity
            self.variation.save()
        super().save(*args, **kwargs)

# 8. Registro de Entradas (Reposiciones)
class StockArrival(models.Model):
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, related_name='arrivals')
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4, default=0.0)
    supplier = models.CharField(max_length=255, blank=True, null=True) 
    arrival_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    @property
    def cost_difference(self):
        return self.unit_cost - self.variation.product.cost_price

    @property
    def total_value(self):
        """Calcula el valor total de la entrada (Costo de Compra)"""
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"Entrada: {self.quantity} x {self.variation}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.variation.stock += self.quantity
            self.variation.save()
            product = self.variation.product
            product.cost_price = self.unit_cost
            product.save()
        super().save(*args, **kwargs)