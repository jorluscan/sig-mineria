import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()

from inventory_app.models import Product, Category, ProductVariation

def seed_data():
    print("--- Cargando Tienda de Ropa (Versión Final) ---")
    
    # 1. Crear Categorías
    cat_damas, _ = Category.objects.get_or_create(name="Damas")
    cat_caballeros, _ = Category.objects.get_or_create(name="Caballeros")

    # 2. Crear un Producto Principal
    # Eliminamos 'stock_quantity' porque el stock ahora vive en las variaciones
    producto, created = Product.objects.get_or_create(
        sku="JEAN-001",
        defaults={
            'name': "Jeans Slim Fit",
            'category': cat_caballeros,
            'sale_price': 35.00,
            'cost_price': 15.00,
            'min_stock_level': 5.00  # Usamos el nombre correcto del campo
        }
    )

    if created:
        print(f"Producto base '{producto.name}' creado.")

    # 3. Crear Variaciones de Tallas y Colores
    tallas = ['30', '32', '34', '36']
    colores = ['Azul Indigo', 'Negro Lavado']

    for t in tallas:
        for c in colores:
            # Usamos el campo 'stock' que sí existe en ProductVariation
            var, var_created = ProductVariation.objects.get_or_create(
                product=producto,
                size=t,
                color=c,
                defaults={
                    'sku_variant': f"JN-{t}-{c[:3].upper()}",
                    'stock': 25
                }
            )
            if var_created:
                print(f"  - Variante creada: Talla {t} / Color {c}")
    
    print("\n¡Éxito! Base de datos de ropa sincronizada correctamente.")

if __name__ == '__main__':
    seed_data()