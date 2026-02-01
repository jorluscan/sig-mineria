from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

# ==========================================
# 1. CATEGORÍAS
# ==========================================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre de Categoría"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Descripción"))

    class Meta:
        verbose_name = _("Categoría")
        verbose_name_plural = _("Categorías")

    def __str__(self):
        return self.name


# ==========================================
# 2. ALMACENES (UBICACIONES FÍSICAS)
# ==========================================
class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre del Almacén"))
    address = models.TextField(blank=True, null=True, verbose_name=_("Dirección"))
    is_active = models.BooleanField(default=True, verbose_name=_("Está activo"))

    class Meta:
        verbose_name = _("Almacén")
        verbose_name_plural = _("Almacenes")

    def __str__(self):
        return self.name


# ==========================================
# 3. PRODUCTO MAESTRO (LOGÍSTICA AVANZADA)
# ==========================================
class Product(models.Model):
    class TrackingType(models.TextChoices):
        NONE = 'NONE', _('Sin Seguimiento')
        LOT = 'LOT', _('Por Lote')
        SERIAL = 'SERIAL', _('Por Número de Serie')

    # Identificación
    sku = models.CharField(max_length=50, unique=True, verbose_name=_("SKU (Código Interno)"))
    name = models.CharField(max_length=255, verbose_name=_("Descripción del Material"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Ficha Técnica / Detalles"))
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name=_("Código de Barras"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Categoría"))
    unit_of_measure = models.CharField(max_length=20, default='unidad', verbose_name=_("Unidad de Medida"))

    # Financiero
    cost_price = models.DecimalField(max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Costo Promedio"))
    sale_price = models.DecimalField(max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Valor Referencia (Activo)"))

    # Control de Stock y Alertas
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Stock Mínimo (Alerta)"))
    tracking_type = models.CharField(max_length=10, choices=TrackingType.choices, default=TrackingType.NONE, verbose_name=_("Tipo de Seguimiento"))
    
    # --- LOGÍSTICA CRÍTICA (NUEVO) ---
    is_critical = models.BooleanField(default=False, verbose_name=_("Es Insumo Crítico"))
    daily_usage_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.0, 
        help_text=_("Consumo promedio diario para calcular días restantes."),
        verbose_name=_("Tasa de Consumo Diario")
    )
    # ---------------------------------

    is_active = models.BooleanField(default=True, verbose_name=_("Activo en Catálogo"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- PROPIEDADES CALCULADAS ---

    @property
    def total_stock(self):
        """Suma el stock físico de todas las variaciones/ubicaciones"""
        return self.variations.aggregate(total=Sum('stock'))['total'] or 0

    @property
    def estimated_days_remaining(self):
        """Calcula días operativos restantes basado en el consumo diario"""
        stock = self.total_stock
        rate = self.daily_usage_rate
        
        if stock <= 0:
            return 0
        if rate <= 0:
            return 999  # Sin consumo registrado, duración indefinida
            
        return round(stock / float(rate), 1)

    @property
    def stock_status(self):
        """Semáforo de estado para el Dashboard"""
        stock = self.total_stock
        min_level = self.min_stock_level
        
        # Prioridad 1: Sin Stock
        if stock <= 0:
            return 'OUT_OF_STOCK'
        
        # Prioridad 2: Crítico (Por debajo del mínimo)
        if stock <= min_level:
            return 'CRITICAL'
        
        # Prioridad 3: Bajo (Cerca del mínimo, margen del 20%)
        # Convertimos a float para asegurar comparación correcta
        if float(stock) <= (float(min_level) * 1.2):
            return 'LOW'
            
        return 'OK'

    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"


# ==========================================
# 4. VARIACIONES (TALLAS / ESPECIFICACIONES)
# ==========================================
class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    size = models.CharField(max_length=50, verbose_name=_("Medida / Especificación")) # Ej: 10mm, XL, 1 Litro
    color = models.CharField(max_length=50, verbose_name=_("Tipo / Variante"))        # Ej: Acero, Rojo, Sintético
    sku_variant = models.CharField(max_length=50, unique=True, verbose_name=_("SKU Variante"))
    stock = models.IntegerField(default=0, verbose_name=_("Stock Físico"))

    class Meta:
        verbose_name = _("Variación de Producto")
        verbose_name_plural = _("Variaciones")

    def __str__(self):
        return f"{self.product.name} [{self.size} - {self.color}]"


# ==========================================
# 5. LOTES (CONTROL DE CADUCIDAD)
# ==========================================
class ProductLot(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='lots')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    lot_number = models.CharField(max_length=50)
    expiration_date = models.DateField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('product', 'lot_number', 'warehouse')

    def __str__(self):
        return f"Lote {self.lot_number} - {self.product.name}"


# ==========================================
# 6. NÚMEROS DE SERIE (MAQUINARIA)
# ==========================================
class SerialNumber(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serial_numbers')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='IN_STOCK')

    def __str__(self):
        return f"SN: {self.serial_number}"


# ==========================================
# 7. DESPACHOS (SALIDAS OPERATIVAS)
# ==========================================
class Dispatch(models.Model):
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, related_name='dispatches')
    quantity = models.PositiveIntegerField(verbose_name=_("Cantidad Despachada"))
    destination = models.CharField(max_length=255, verbose_name=_("Destino / Área"))
    dispatched_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    @property
    def total_value(self):
        """Valor contable de la salida (basado en precio referencia)"""
        return self.quantity * self.variation.product.sale_price

    def save(self, *args, **kwargs):
        # Descuento automático de stock al guardar
        if not self.pk: # Solo al crear
            self.variation.stock -= self.quantity
            self.variation.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Salida: {self.quantity} de {self.variation.sku_variant}"


# ==========================================
# 8. REPOSICIONES (ENTRADAS DE ALMACÉN)
# ==========================================
class StockArrival(models.Model):
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, related_name='arrivals')
    quantity = models.PositiveIntegerField(verbose_name=_("Cantidad Recibida"))
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4, default=0.0, verbose_name=_("Costo Unitario"))
    supplier = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Proveedor"))
    arrival_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    @property
    def total_value(self):
        """Valor total de la entrada (inversión)"""
        return self.quantity * self.unit_cost

    def save(self, *args, **kwargs):
        # Aumento automático de stock al guardar
        if not self.pk: # Solo al crear
            self.variation.stock += self.quantity
            self.variation.save()
            
            # Actualizar costo promedio del producto maestro (Estrategia Último Precio)
            product = self.variation.product
            product.cost_price = self.unit_cost
            product.save()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Entrada: {self.quantity} de {self.variation.sku_variant}"