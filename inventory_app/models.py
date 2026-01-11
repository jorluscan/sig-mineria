from django.db import models
from django.utils.translation import gettext_lazy as _

# 1. Modelo de Categorías (Nuevo para Tienda de Ropa)
class Category(models.Model):
    """Modelo para clasificar productos (Damas, Caballeros, etc.)"""
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre de Categoría"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))

    class Meta:
        verbose_name = _("Categoría")
        verbose_name_plural = _("Categorías")

    def __str__(self):
        return self.name

# 2. Modelo de Almacenes
class Warehouse(models.Model):
    """Representa un almacén o sucursal."""
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre del Almacén"))
    address = models.TextField(blank=True, null=True, verbose_name=_("Dirección"))
    is_active = models.BooleanField(default=True, verbose_name=_("Está activo"))

    class Meta:
        verbose_name = _("Almacén")
        verbose_name_plural = _("Almacenes")

    def __str__(self):
        return self.name

# 3. Modelo de Producto Base (Modificado con Categoría profesional)
class Product(models.Model):
    """Representa un producto base en el inventario."""
    class TrackingType(models.TextChoices):
        NONE = 'NONE', _('Sin Seguimiento')
        LOT = 'LOT', _('Por Lote')
        SERIAL = 'SERIAL', _('Por Número de Serie')

    sku = models.CharField(max_length=50, unique=True, verbose_name=_("SKU (Código Interno)"))
    name = models.CharField(max_length=255, verbose_name=_("Nombre del Producto"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name=_("Código de Barras"))

    # Relación profesional a la tabla Category
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
        """Calcula la ganancia neta restando el costo al precio de salida"""
        if self.sale_price and self.cost_price:
            return self.sale_price - self.cost_price
        return 0
    
    @property
    def total_stock(self):
        from django.db.models import Sum
        # Suma el stock de todas las variaciones de este producto
        return self.variations.aggregate(total=Sum('stock'))['total'] or 0

    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")

    def __str__(self):
        return f"{self.name} ({self.sku})"

# 4. Variaciones de Ropa (Talla y Color)
class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations', verbose_name=_("Producto"))
    size = models.CharField(max_length=10, verbose_name=_("Talla"))
    color = models.CharField(max_length=50, verbose_name=_("Color"))
    sku_variant = models.CharField(max_length=50, unique=True, verbose_name=_("SKU de Variante"))
    stock = models.IntegerField(default=0, verbose_name=_("Existencias"))

    def __str__(self):
        return f"{self.product.name} - {self.size} / {self.color}"

# 5. Lotes de Productos
class ProductLot(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='lots', verbose_name=_("Producto"))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name=_("Almacén"))
    lot_number = models.CharField(max_length=50, verbose_name=_("Número de Lote"))
    expiration_date = models.DateField(blank=True, null=True, verbose_name=_("Fecha de Vencimiento"))
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Cantidad en este Lote"))

    class Meta:
        verbose_name = _("Lote de Producto")
        verbose_name_plural = _("Lotes de Productos")
        unique_together = ('product', 'lot_number', 'warehouse')

    def __str__(self):
        return f"Lote {self.lot_number} de {self.product.name}"

# 6. Números de Serie
class SerialNumber(models.Model):
    class SerialStatus(models.TextChoices):
        IN_STOCK = 'IN_STOCK', _('En Almacén')
        SOLD = 'SOLD', _('Vendido')
        DEFECTIVE = 'DEFECTIVE', _('Defectuoso')

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serial_numbers', verbose_name=_("Producto"))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name=_("Almacén"))
    serial_number = models.CharField(max_length=100, unique=True, verbose_name=_("Número de Serie"))
    status = models.CharField(max_length=20, choices=SerialStatus.choices, default=SerialStatus.IN_STOCK, verbose_name=_("Estado"))

    class Meta:
        verbose_name = _("Número de Serie")
        verbose_name_plural = _("Números de Serie")

    def __str__(self):
        return f"Serial {self.serial_number} de {self.product.name}"

# 7. Registro de Despachos
class Dispatch(models.Model):
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, related_name='dispatches')
    quantity = models.PositiveIntegerField()
    destination = models.CharField(max_length=255)
    dispatched_at = models.DateTimeField(auto_now_add=True)
    # CORRECCIÓN: debe decir on_delete, no on_relative
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.quantity} x {self.variation} -> {self.destination}"

# 8. Registro de Entradas de Stock   
class StockArrival(models.Model):
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, related_name='arrivals')
    quantity = models.PositiveIntegerField()
    supplier = models.CharField(max_length=255, blank=True, null=True) # Proveedor o Taller
    arrival_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Entrada: {self.quantity} x {self.variation}"