import json
from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F, Q, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone

from .models import Product, Category, ProductVariation, Dispatch, StockArrival


@login_required
def inventory_dashboard(request):
    """
    Dashboard Operativo: 
    Muestra KPIs financieros y, lo más importante, 
    la Tabla de Alertas de Insumos Críticos (Lixiviación).
    """
    # 1. KPIs Financieros Globales
    metrics = ProductVariation.objects.aggregate(
        total_cost=Sum(F('stock') * F('product__cost_price'), output_field=DecimalField()),
        total_sales=Sum(F('stock') * F('product__sale_price'), output_field=DecimalField())
    )
    
    total_cost = metrics['total_cost'] or 0
    total_sales_value = metrics['total_sales'] or 0
    projected_profit = total_sales_value - total_cost

    # 2. Datos para Gráficos (Stock por Categoría)
    categories = Category.objects.all()
    cat_labels = []
    cat_stocks = []
    for cat in categories:
        stock = ProductVariation.objects.filter(product__category=cat).aggregate(total=Sum('stock'))['total'] or 0
        if stock > 0:
            cat_labels.append(cat.name)
            cat_stocks.append(stock)

    # 3. LÓGICA DE ALERTAS E INSUMOS CRÍTICOS
    # Filtramos solo los productos marcados como críticos y activos
    all_critical_products = Product.objects.filter(is_active=True, is_critical=True)
    
    # Procesamos en Python porque 'stock_status' es una @property del modelo
    critical_list = []
    for p in all_critical_products:
        # Añadimos a la lista para mostrar en el dashboard
        critical_list.append(p)

    # Ordenamos por prioridad de riesgo: 
    # OUT_OF_STOCK (0) -> CRITICAL (1) -> LOW (2) -> OK (3)
    status_priority = {'OUT_OF_STOCK': 0, 'CRITICAL': 1, 'LOW': 2, 'OK': 3}
    critical_list.sort(key=lambda x: status_priority.get(x.stock_status, 3))

    context = {
        'total_cost': total_cost,
        'total_sales_value': total_sales_value,
        'projected_profit': projected_profit,
        'cat_labels': cat_labels,
        'cat_stocks': cat_stocks,
        'critical_products': critical_list, # <--- Nueva variable para el template
        'recent_arrivals': StockArrival.objects.all().select_related('variation__product', 'user').order_by('-arrival_date')[:5],
        'recent_dispatches': Dispatch.objects.all().select_related('variation__product', 'user').order_by('-dispatched_at')[:5],
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def inventory_list(request):
    """Lista Maestra con Búsqueda y Ordenamiento"""
    query = request.GET.get('q', '')
    order = request.GET.get('o', 'name')

    # Anotamos el stock total sumando las variaciones
    products = Product.objects.annotate(
        total_qty=Coalesce(Sum('variations__stock'), 0)
    ).select_related('category')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))

    # Mapa de ordenamiento
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
def create_product(request):
    """
    Creación de Producto Maestro + Variantes.
    ACTUALIZADO: Ahora soporta 'is_critical' y 'daily_usage_rate'.
    """
    if request.method == 'POST':
        variations_data = request.POST.get('variations_data')
        
        try:
            with transaction.atomic():
                # 1. Datos Generales
                category_id = request.POST.get('category')
                category = get_object_or_404(Category, id=category_id)

                barcode_val = request.POST.get('barcode', '').strip() or None
                
                # 2. Captura de nuevos campos logísticos
                # El checkbox en HTML no envía 'false', simplemente no envía nada si no está marcado.
                is_critical = request.POST.get('is_critical') == 'on' 
                daily_usage = request.POST.get('daily_usage_rate', 0)

                # 3. Crear Producto
                product = Product.objects.create(
                    name=request.POST.get('name'),
                    sku=request.POST.get('sku').upper(),
                    category=category,
                    cost_price=request.POST.get('cost_price', 0),
                    sale_price=request.POST.get('sale_price', 0),
                    min_stock_level=request.POST.get('min_stock_level', 5),
                    barcode=barcode_val,
                    # Campos Nuevos
                    is_critical=is_critical,
                    daily_usage_rate=daily_usage
                )

                # 4. Crear Variaciones
                if variations_data:
                    vars_list = json.loads(variations_data)
                    for item in vars_list:
                        ProductVariation.objects.create(
                            product=product,
                            size=item['size'].upper(),
                            color=item['color'].capitalize(),
                            sku_variant=item['sku_variant'].upper(),
                            stock=item['stock']
                        )
                
                messages.success(request, f"Material '{product.name}' registrado exitosamente.")
                return redirect('inventory_list')
        
        except Exception as e:
            if "duplicate key" in str(e):
                messages.error(request, "Error: El SKU ya existe en el sistema.")
            else:
                messages.error(request, f"Error al crear: {str(e)}")
    
    return render(request, 'inventory/product_form.html', {
        'categories': Category.objects.all()
    })


@login_required
def update_product_price(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        nuevo_precio = request.POST.get('new_price')
        if nuevo_precio:
            product.sale_price = nuevo_precio
            product.save()
            messages.success(request, "Precio de referencia actualizado.")
    return redirect('product_detail', pk=pk)


@login_required
def product_search_ajax(request):
    """Buscador para formularios de Entrada/Salida"""
    query = request.GET.get('q', '').strip()
    results = []
    
    try:
        if len(query) > 1:
            # Buscamos variaciones que coincidan
            variations = ProductVariation.objects.filter(
                Q(product__name__icontains=query) | 
                Q(product__sku__icontains=query) |
                Q(sku_variant__icontains=query)
            ).select_related('product')[:15]
            
            for v in variations:
                spec = v.size if v.size else "Std"
                type_ = v.color if v.color else "Gen"
                
                results.append({
                    'id': str(v.id),
                    'name': f"{v.product.name} ({spec} - {type_})",
                    'sku': v.sku_variant, # Usamos el SKU específico de la variante
                    'price': float(v.product.sale_price),
                    'cost': float(v.product.cost_price),
                    'stock': int(v.stock),
                })
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e), 'results': []}, status=500)


@login_required
def create_dispatch(request):
    """Registro de Salidas (Consumo)"""
    if request.method == 'POST':
        items_data = request.POST.get('items_data')
        destination = request.POST.get('destination')
        # En tu form nuevo hay un campo receiver_id si lo implementaste, 
        # sino puedes usar el usuario actual o ignorarlo.
        
        if not items_data:
            messages.error(request, "Seleccione items para despachar.")
            return redirect('create_dispatch')

        try:
            with transaction.atomic():
                items = json.loads(items_data)
                for item in items:
                    variation = get_object_or_404(ProductVariation, id=item['id'])
                    quantity = int(item['qty'])
                    
                    if variation.stock < quantity:
                        raise ValueError(f"Stock insuficiente para {variation.product.name}")

                    Dispatch.objects.create(
                        variation=variation,
                        quantity=quantity,
                        destination=destination,
                        user=request.user
                    )
                    # El modelo Dispatch descuenta stock en save()

                messages.success(request, f"Salida hacia '{destination}' registrada.")
                return redirect('inventory_list')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
    # Obtenemos usuarios para el select de "Responsable" (Opcional)
    from django.contrib.auth.models import User
    users = User.objects.all().order_by('username')
    return render(request, 'inventory/dispatch_form.html', {'users': users})


@login_required
def create_stock_arrival(request):
    """Registro de Entradas (Reposición)"""
    if request.method == 'POST':
        items_data = request.POST.get('items_data')
        supplier = request.POST.get('supplier', 'General')
        
        if not items_data:
            messages.error(request, "Seleccione items para ingresar.")
            return redirect('create_stock_arrival')

        try:
            with transaction.atomic():
                items = json.loads(items_data)
                for item in items:
                    variation = get_object_or_404(ProductVariation, id=item['id'])
                    quantity = int(item['qty'])
                    cost = float(item['cost'])
                    
                    StockArrival.objects.create(
                        variation=variation,
                        quantity=quantity,
                        unit_cost=cost,
                        supplier=supplier,
                        user=request.user
                    )
                    # El modelo StockArrival aumenta stock y actualiza costo promedio en save()

                messages.success(request, f"Entrada de '{supplier}' registrada.")
                return redirect('inventory_list')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'inventory/stock_arrival_form.html')


@login_required
def inventory_reports(request):
    """Reportes de Auditoría"""
    interval = request.GET.get('interval', 'daily')
    report_type = request.GET.get('type', 'dispatches')
    now = timezone.now()
    
    if interval == 'weekly':
        start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
    elif interval == 'monthly':
        start_date = now.replace(day=1, hour=0, minute=0, second=0)
    elif interval == 'custom':
        s = request.GET.get('start')
        e = request.GET.get('end')
        if s and e:
            start_date = timezone.make_aware(datetime.strptime(s, '%Y-%m-%d')).replace(hour=0, minute=0)
            now = timezone.make_aware(datetime.strptime(e, '%Y-%m-%d')).replace(hour=23, minute=59)
        else:
            start_date = now.replace(hour=0, minute=0)
    else: # daily
        start_date = now.replace(hour=0, minute=0, second=0)

    # Consultas
    if report_type == 'dispatches':
        records = Dispatch.objects.filter(dispatched_at__range=[start_date, now]).select_related('variation__product', 'user').order_by('-dispatched_at')
        kpi_color = "zinc"
    else:
        records = StockArrival.objects.filter(arrival_date__range=[start_date, now]).select_related('variation__product', 'user').order_by('-arrival_date')
        kpi_color = "gold"

    # Cálculos
    total_qty = records.aggregate(Sum('quantity'))['quantity__sum'] or 0
    # Calculamos valor en python ya que es una propiedad del modelo
    total_val = sum(r.total_value for r in records)

    return render(request, 'inventory/reports.html', {
        'interval': interval,
        'report_type': report_type,
        'dispatches': records if report_type == 'dispatches' else [],
        'arrivals': records if report_type == 'arrivals' else [],
        'kpi_units': total_qty,
        'kpi_money': total_val,
        'kpi_color': kpi_color,
        'start_val': request.GET.get('start', ''),
        'end_val': request.GET.get('end', ''),
    })