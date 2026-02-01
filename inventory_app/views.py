import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F, Q, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.urls import reverse
from .models import Product, Category, ProductVariation, Dispatch, StockArrival

@login_required
def inventory_dashboard(request):
    """Dashboard Global: KPIs Financieros y Movimientos"""
    metrics = ProductVariation.objects.aggregate(
        total_cost=Sum(F('stock') * F('product__cost_price'), output_field=DecimalField()),
        total_sales=Sum(F('stock') * F('product__sale_price'), output_field=DecimalField())
    )
    
    total_cost = metrics['total_cost'] or 0
    total_sales_value = metrics['total_sales'] or 0
    projected_profit = total_sales_value - total_cost

    categories = Category.objects.all()
    cat_labels = []
    cat_stocks = []
    for cat in categories:
        stock = ProductVariation.objects.filter(product__category=cat).aggregate(total=Sum('stock'))['total'] or 0
        if stock > 0:
            cat_labels.append(cat.name)
            cat_stocks.append(stock)

    context = {
        'total_cost': total_cost,
        'total_sales_value': total_sales_value,
        'projected_profit': projected_profit,
        'cat_labels': cat_labels,
        'cat_stocks': cat_stocks,
        'recent_arrivals': StockArrival.objects.all().select_related('variation__product', 'user').order_by('-arrival_date')[:5],
        'recent_dispatches': Dispatch.objects.all().select_related('variation__product', 'user').order_by('-dispatched_at')[:5],
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def inventory_list(request):
    """Lista Maestra con Búsqueda AJAX y Ordenamiento Dinámico"""
    query = request.GET.get('q', '')
    order = request.GET.get('o', 'name')

    products = Product.objects.annotate(
        total_qty=Coalesce(Sum('variations__stock'), 0)
    ).select_related('category')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))

    sort_mapping = {
        'sku': 'sku', '-sku': '-sku',
        'name': 'name', '-name': '-name',
        'cost': 'cost_price', '-cost': '-cost_price',
        'price': 'sale_price', '-price': '-sale_price',
        'stock': 'total_qty', '-stock': '-total_qty'
    }

    products = products.order_by(sort_mapping.get(order, 'name'))

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'inventory/inventory_table_partial.html', {'products': products})

    return render(request, 'inventory/inventory_list.html', {'products': products, 'query': query})

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'inventory/product_detail.html', {
        'product': product,
        'variations': product.variations.all(),
    })

@login_required
def product_search_ajax(request):
    """Buscador corregido según tu models.py (size y color son CharFields)"""
    query = request.GET.get('q', '').strip()
    results = []
    
    try:
        if len(query) > 1:
            # Buscamos variaciones que coincidan con el nombre del producto o SKU
            variations = ProductVariation.objects.filter(
                Q(product__name__icontains=query) | Q(product__sku__icontains=query)
            ).select_related('product')[:10]
            
            for v in variations:
                # Aquí estaba el error: size y color ya son el texto en tu modelo
                talla = v.size if v.size else "U"
                color = v.color if v.color else ""
                
                results.append({
                    'id': str(v.id),
                    'name': f"{v.product.name} ({talla} - {color})",
                    'sku': v.product.sku,
                    'price': float(v.product.sale_price),
                    'cost': float(v.product.cost_price),
                    'stock': int(v.stock),
                })
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e), 'results': []}, status=500)

@login_required
def create_dispatch(request):
    """Registro de salida masiva de mercancía mediante JSON"""
    if request.method == 'POST':
        items_data = request.POST.get('items_data')
        destination = request.POST.get('destination')
        
        if not items_data:
            messages.error(request, "No se han seleccionado productos.")
            return redirect('create_dispatch')

        try:
            with transaction.atomic():
                items = json.loads(items_data)
                for item in items:
                    variation = get_object_or_404(ProductVariation, id=item['id'])
                    quantity = int(item['qty'])
                    
                    if variation.stock < quantity:
                        raise ValueError(f"Stock insuficiente para {variation.product.name}")

                    # Crear registro de despacho
                    Dispatch.objects.create(
                        variation=variation,
                        quantity=quantity,
                        destination=destination,
                        user=request.user
                    )
                    
                    # El modelo debería descontar el stock en su save() o mediante un signal. 
                    # Si no lo hace, descomenta la siguiente línea:
                    # variation.stock -= quantity
                    # variation.save()

                messages.success(request, f"Despacho a '{destination}' procesado con éxito.")
                return redirect('inventory_list')
        except Exception as e:
            messages.error(request, f"Error al procesar el despacho: {str(e)}")
            
    return render(request, 'inventory/dispatch_form.html')

@login_required
def create_stock_arrival(request):
    """Registro de reposición masiva de inventario"""
    if request.method == 'POST':
        items_data = request.POST.get('items_data')
        supplier = request.POST.get('supplier', 'General')
        
        if not items_data:
            messages.error(request, "No se han seleccionado productos.")
            return redirect('create_stock_arrival')

        try:
            with transaction.atomic():
                items = json.loads(items_data)
                for item in items:
                    variation = get_object_or_404(ProductVariation, id=item['id'])
                    quantity = int(item['qty'])
                    
                    # Registrar ingreso
                    StockArrival.objects.create(
                        variation=variation,
                        quantity=quantity,
                        unit_cost=variation.product.cost_price,
                        supplier=supplier,
                        user=request.user
                    )
                    
                    # variation.stock += quantity
                    # variation.save()

                messages.success(request, f"Reposición de '{supplier}' cargada con éxito.")
                return redirect('inventory_list')
        except Exception as e:
            messages.error(request, f"Error en la reposición: {str(e)}")

    return render(request, 'inventory/stock_arrival_form.html')

@login_required
def create_product(request):
    if request.method == 'POST':
        cat = get_object_or_404(Category, id=request.POST.get('category'))
        new_p = Product.objects.create(
            name=request.POST.get('name'), sku=request.POST.get('sku'),
            description=request.POST.get('description'), cost_price=request.POST.get('cost_price'),
            sale_price=request.POST.get('sale_price'), category=cat
        )
        return redirect('product_detail', pk=new_p.pk)
    return render(request, 'inventory/product_form.html', {'categories': Category.objects.all()})

@login_required
def update_product_price(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        nuevo_precio = request.POST.get('new_price')
        if nuevo_precio:
            product.sale_price = nuevo_precio
            product.save()
            messages.success(request, f"Precio de {product.name} actualizado a ${nuevo_precio}")
    return redirect('product_detail', pk=pk)