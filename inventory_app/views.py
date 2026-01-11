from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F
from .models import Product, Category, ProductVariation, Dispatch, StockArrival

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F
from .models import Product, Category, ProductVariation, Dispatch, StockArrival

@login_required
def inventory_dashboard(request):
    """Dashboard Global: Finanzas, Gráficos y Alertas"""
    products = Product.objects.all()
    
    # 1. CÁLCULOS FINANCIEROS (Basados en variaciones con stock)
    # Valor de Inversión (Costo x Cantidad)
    total_cost = ProductVariation.objects.aggregate(
        total=Sum(F('stock') * F('product__cost_price'))
    )['total'] or 0

    # Valor de Venta (Precio Venta x Cantidad)
    total_sales_value = ProductVariation.objects.aggregate(
        total=Sum(F('stock') * F('product__sale_price'))
    )['total'] or 0

    # Utilidad Proyectada
    projected_profit = total_sales_value - total_cost

    # 2. ALERTAS DE STOCK BAJO
    low_stock_count = 0
    for p in products:
        if p.total_stock <= p.min_stock_level:
            low_stock_count += 1

    # 3. DATOS PARA EL GRÁFICO DE DONA (Categorías)
    categories = Category.objects.all()
    cat_labels = []
    cat_stocks = []

    for cat in categories:
        stock_en_categoria = ProductVariation.objects.filter(
            product__category=cat
        ).aggregate(total=Sum('stock'))['total'] or 0
        
        if stock_en_categoria > 0:
            cat_labels.append(cat.name)
            cat_stocks.append(stock_en_categoria)

    # 4. ACTIVIDAD RECIENTE
    recent_arrivals = StockArrival.objects.all().order_by('-arrival_date')[:5]
    recent_dispatches = Dispatch.objects.all().order_by('-dispatched_at')[:5]

    context = {
        'total_products': products.count(),
        'total_cost': total_cost,
        'total_sales_value': total_sales_value,
        'projected_profit': projected_profit,
        'low_stock_count': low_stock_count,
        'cat_labels': cat_labels,
        'cat_stocks': cat_stocks,
        'recent_arrivals': recent_arrivals,
        'recent_dispatches': recent_dispatches,
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def inventory_list(request):
    """Lista Maestra con Filtros"""
    products = Product.objects.all().order_by('name')
    categories = Category.objects.all()
    return render(request, 'inventory/inventory_list.html', {
        'products': products, 
        'categories': categories
    })

@login_required
def product_detail(request, pk):
    """Ficha técnica con costos, códigos de barra e historial"""
    product = get_object_or_404(Product, pk=pk)
    
    # Procesar actualización rápida de stock desde la ficha
    if request.method == 'POST':
        var_id = request.POST.get('variation_id')
        new_stock = request.POST.get('new_stock')
        variation = get_object_or_404(ProductVariation, id=var_id)
        variation.stock = new_stock
        variation.save()
        messages.success(request, f"Stock de {variation.product.name} ({variation.color}) actualizado manualmente.")

    variations = product.variations.all()
    context = {
        'product': product,
        'variations': variations,
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
def create_dispatch(request):
    """Interfaz para salida de mercancía (Despachos)"""
    if request.method == 'POST':
        variation_id = request.POST.get('variation_id')
        qty = int(request.POST.get('quantity'))
        dest = request.POST.get('destination')
        
        variation = get_object_or_404(ProductVariation, id=variation_id)
        
        if variation.stock >= qty:
            variation.stock -= qty
            variation.save()
            
            Dispatch.objects.create(
                variation=variation,
                quantity=qty,
                destination=dest,
                user=request.user
            )
            messages.success(request, f"Despacho exitoso de {qty} unidad(es).")
            return redirect('inventory_dashboard')
        else:
            messages.error(request, "Error: Stock insuficiente.")

    products = Product.objects.all()
    return render(request, 'inventory/dispatch_form.html', {'products': products})

@login_required
def create_stock_arrival(request):
    """Interfaz para entrada de mercancía (Ingresos)"""
    if request.method == 'POST':
        variation_id = request.POST.get('variation_id')
        qty_str = request.POST.get('quantity')
        supplier = request.POST.get('supplier', 'General')
        
        if not variation_id or not qty_str:
            messages.error(request, "Por favor complete los campos obligatorios.")
            return redirect('create_stock_arrival')

        qty = int(qty_str)
        variation = get_object_or_404(ProductVariation, id=variation_id)
        
        # 1. Aumentar stock físico
        variation.stock += qty
        variation.save()
        
        # 2. Crear el registro de entrada (Aquí fallaba antes por falta de import)
        StockArrival.objects.create(
            variation=variation,
            quantity=qty,
            supplier=supplier,
            user=request.user
        )
        
        messages.success(request, f"Se han ingresado {qty} unidades de {variation.product.name} al sistema.")
        return redirect('inventory_dashboard')

    products = Product.objects.all()
    return render(request, 'inventory/stock_arrival_form.html', {'products': products})


@login_required
def create_product(request):
    """Registrar una nueva prenda en el catálogo de D'Kurvas"""
    if request.method == 'POST':
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        description = request.POST.get('description')
        cost_price = request.POST.get('cost_price')
        sale_price = request.POST.get('sale_price')
        category_id = request.POST.get('category')
        min_stock = request.POST.get('min_stock_level', 5)
        barcode = request.POST.get('barcode')

        category = get_object_or_404(Category, id=category_id)

        # Crear el producto
        new_product = Product.objects.create(
            name=name,
            sku=sku,
            description=description,
            cost_price=cost_price,
            sale_price=sale_price,
            category=category,
            min_stock_level=min_stock,
            barcode=barcode
        )
        
        messages.success(request, f"Producto '{name}' creado exitosamente. Ahora añade sus tallas.")
        return redirect('product_detail', pk=new_product.pk)

    categories = Category.objects.all()
    return render(request, 'inventory/product_form.html', {'categories': categories})




