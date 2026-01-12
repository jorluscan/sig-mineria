from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Q
from django.http import JsonResponse
from django.urls import reverse
from .models import Product, Category, ProductVariation, Dispatch, StockArrival

@login_required
def inventory_dashboard(request):
    """Dashboard Global: Finanzas, Gráficos y Alertas"""
    products = Product.objects.all()
    
    # KPIs Financieros
    total_cost = ProductVariation.objects.aggregate(
        total=Sum(F('stock') * F('product__cost_price'))
    )['total'] or 0

    total_sales_value = ProductVariation.objects.aggregate(
        total=Sum(F('stock') * F('product__sale_price'))
    )['total'] or 0

    projected_profit = total_sales_value - total_cost

    # Alerta Stock Bajo
    low_stock_count = sum(1 for p in products if p.total_stock <= p.min_stock_level)

    # Datos Gráfico de Dona
    categories = Category.objects.all()
    cat_labels = []
    cat_stocks = []
    for cat in categories:
        stock = ProductVariation.objects.filter(product__category=cat).aggregate(total=Sum('stock'))['total'] or 0
        if stock > 0:
            cat_labels.append(cat.name)
            cat_stocks.append(stock)

    context = {
        'total_products': products.count(),
        'total_cost': total_cost,
        'total_sales_value': total_sales_value,
        'projected_profit': projected_profit,
        'low_stock_count': low_stock_count,
        'cat_labels': cat_labels,
        'cat_stocks': cat_stocks,
        'recent_arrivals': StockArrival.objects.all().order_by('-arrival_date')[:5],
        'recent_dispatches': Dispatch.objects.all().order_by('-dispatched_at')[:5],
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def inventory_list(request):
    """Lista Maestra de Inventario"""
    products = Product.objects.all().order_by('name')
    categories = Category.objects.all()
    return render(request, 'inventory/inventory_list.html', {
        'products': products, 
        'categories': categories
    })

@login_required
def product_detail(request, pk):
    """Ficha técnica detallada del producto"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        var_id = request.POST.get('variation_id')
        new_stock = request.POST.get('new_stock')
        variation = get_object_or_404(ProductVariation, id=var_id)
        variation.stock = new_stock
        variation.save()
        messages.success(request, f"Stock de {variation.product.name} actualizado.")

    return render(request, 'inventory/product_detail.html', {
        'product': product,
        'variations': product.variations.all(),
    })

def product_search_ajax(request):
    query = request.GET.get('q', '')
    results = []
    
    if len(query) > 1:
        # Buscamos en nombre o SKU (insensible a mayúsculas/minúsculas)
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        )[:6] # Limitamos a 6 para mantener la elegancia
        
        for p in products:
            results.append({
                'name': p.name,
                'sku': p.sku,
                'url': f'/producto/{p.id}/', # Asegúrate de que esta URL sea la correcta en tu sistema
            })
            
    return JsonResponse({'results': results})

# --- Vistas de creación (Despacho, Ingreso, Producto) ---
@login_required
def create_dispatch(request):
    if request.method == 'POST':
        variation_id = request.POST.get('variation_id')
        qty = int(request.POST.get('quantity'))
        variation = get_object_or_404(ProductVariation, id=variation_id)
        if variation.stock >= qty:
            variation.stock -= qty
            variation.save()
            Dispatch.objects.create(variation=variation, quantity=qty, destination=request.POST.get('destination'), user=request.user)
            messages.success(request, "Despacho exitoso.")
            return redirect('inventory_dashboard')
        messages.error(request, "Stock insuficiente.")
    return render(request, 'inventory/dispatch_form.html', {'products': Product.objects.all()})

@login_required
def create_stock_arrival(request):
    if request.method == 'POST':
        var_id = request.POST.get('variation_id')
        qty = int(request.POST.get('quantity'))
        variation = get_object_or_404(ProductVariation, id=var_id)
        variation.stock += qty
        variation.save()
        StockArrival.objects.create(variation=variation, quantity=qty, supplier=request.POST.get('supplier', 'General'), user=request.user)
        messages.success(request, "Ingreso registrado.")
        return redirect('inventory_dashboard')
    return render(request, 'inventory/stock_arrival_form.html', {'products': Product.objects.all()})

@login_required
def create_product(request):
    if request.method == 'POST':
        category = get_object_or_404(Category, id=request.POST.get('category'))
        new_product = Product.objects.create(
            name=request.POST.get('name'), sku=request.POST.get('sku'),
            description=request.POST.get('description'), cost_price=request.POST.get('cost_price'),
            sale_price=request.POST.get('sale_price'), category=category
        )
        return redirect('product_detail', pk=new_product.pk)
    return render(request, 'inventory/product_form.html', {'categories': Category.objects.all()})