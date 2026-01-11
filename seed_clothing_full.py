import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()

from inventory_app.models import Product, Category, ProductVariation

def seed_full_inventory():
    print("--- Generando Catálogo Completo (50 Artículos) ---")

    # 1. Definición de Categorías
    categories_data = [
        ("Caballeros", "Ropa formal y casual para hombres"),
        ("Damas", "Moda femenina y accesorios"),
        ("Niños", "Ropa infantil para todas las edades"),
        ("Calzado", "Zapatos, zapatillas y botas"),
        ("Accesorios", "Bolsos, cinturones y joyería")
    ]
    
    categories = {}
    for name, desc in categories_data:
        cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
        categories[name] = cat

    # 2. Atributos para Variaciones
    colores = ["Negro", "Blanco", "Azul Marino", "Gris", "Rojo", "Verde Oliva"]
    tallas_ropa = ["S", "M", "L", "XL"]
    tallas_calzado = ["38", "39", "40", "41", "42"]
    
    # 3. Lista de 50 Productos (10 por categoría)
    items = {
        "Caballeros": ["Camisa Oxford", "Pantalón Chino", "Camiseta Básica", "Chaqueta Cuero", "Jeans Regular", "Suéter Lana", "Bermuda Cargo", "Traje Formal", "Chaleco", "Sudadera"],
        "Damas": ["Vestido Largo", "Blusa Seda", "Falda Midi", "Leggings", "Top Encaje", "Chaqueta Jean", "Pantalón Palazzo", "Mono Casual", "Cárdigan", "Shorts"],
        "Niños": ["Conjunto Algodón", "Pijama Dibujos", "Overol", "Camiseta Estampada", "Pantalón Elástico", "Vestido Niña", "Abrigo Infantil", "Shorts Playa", "Suéter Rayas", "Body Bebé"],
        "Calzado": ["Tenis Deportivos", "Zapatos Vestir", "Botines", "Sandalias", "Mocasines", "Zapatillas Running", "Botas Lluvia", "Pantuflas", "Zuecos", "Chanclas"],
        "Accesorios": ["Cinturón Cuero", "Gorra", "Bufanda", "Reloj Pulsera", "Bolsa Mano", "Gafas Sol", "Cartera", "Corbata Seda", "Guantes", "Mochila"]
    }

    total_products = 0
    
    for cat_name, product_list in items.items():
        for i, p_name in enumerate(product_list):
            sku_base = f"{cat_name[:3].upper()}-{i+1:03d}"
            
            # Crear o obtener el Producto
            cost = random.uniform(10, 50)
            sale = cost * random.uniform(1.8, 2.5)
            
            product, created = Product.objects.get_or_create(
                sku=sku_base,
                defaults={
                    'name': p_name,
                    'category': categories[cat_name],
                    'cost_price': round(cost, 2),
                    'sale_price': round(sale, 2),
                    'min_stock_level': 5,
                    'unit_of_measure': 'unidad'
                }
            )

            if created:
                total_products += 1
                # Determinar tallas disponibles según la categoría
                if cat_name == "Calzado":
                    current_tallas = tallas_calzado
                elif cat_name == "Accesorios":
                    current_tallas = ["Única"]
                else:
                    current_tallas = tallas_ropa
                
                # CORRECCIÓN: Seleccionar el mínimo entre lo disponible y 2
                k_sizes = min(len(current_tallas), 2)
                selected_sizes = random.sample(current_tallas, k_sizes)
                selected_colors = random.sample(colores, 2)

                for size in selected_sizes:
                    for color in selected_colors:
                        ProductVariation.objects.get_or_create(
                            product=product,
                            size=size,
                            color=color,
                            defaults={
                                'sku_variant': f"{sku_base}-{size}-{color[:3].upper()}",
                                'stock': random.randint(15, 60)
                            }
                        )

    print(f"Éxito: Se han cargado {total_products} productos nuevos con sus respectivas tallas y colores.")

if __name__ == '__main__':
    seed_full_inventory()