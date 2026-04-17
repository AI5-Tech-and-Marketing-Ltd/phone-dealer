from django.db.models import Sum, Count, Q, F
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear, TruncDate
from django.utils import timezone
from datetime import timedelta
from inventory.models import Product, Allocation

def get_store_analytics(store, start_date=None, end_date=None, group_by='daily'):
    # Base query for products in this store
    products = Product.objects.filter(store=store)
    
    # Date filtering
    date_filter = Q()
    if start_date:
        date_filter &= Q(sold_at__gte=start_date)
    if end_date:
        date_filter &= Q(sold_at__lte=end_date)
    
    # 1. Total inventory value (Sum of cost_price for non-sold items)
    inventory_value = products.exclude(status='Sold').aggregate(total=Sum('cost_price'))['total'] or 0.00
    
    # 2. Phones in stock (status='Available')
    in_stock = products.filter(status='Available').count()
    
    # 3. Sales this week (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    week_sales = products.filter(status='Sold', sold_at__gte=seven_days_ago).aggregate(
        total_revenue=Sum('selling_price'),
        count=Count('id')
    )
    
    # 4. Active listings (Public + Available)
    active_listings = products.filter(status='Available', availability='Public').count()
    
    # 5. Recent activity (Last 10 allocations or sales)
    # This is a bit complex to combine, so we'll just take the last 10 status changes or allocations
    recent_products = products.order_by('-updated_at')[:5]
    recent_allocations = Allocation.objects.filter(store=store).order_by('-timestamp')[:5]
    
    activity = []
    for p in recent_products:
        activity.append({
            "type": "Product Update",
            "description": f"{p.brand} {p.model_name} status: {p.status}",
            "timestamp": p.updated_at
        })
    for a in recent_allocations:
        activity.append({
            "type": "Allocation",
            "description": f"{a.product.model_name} allocated to {a.allocated_to.full_name if a.allocated_to else 'N/A'}",
            "timestamp": a.timestamp
        })
    activity = sorted(activity, key=lambda x: x['timestamp'], reverse=True)
    
    # 6. Top Selling Models
    top_selling = products.filter(status='Sold').values('brand', 'model_name').annotate(
        sales_count=Count('id'),
        revenue=Sum('selling_price')
    ).order_by('-sales_count')[:5]
    
    # 7. Grouped Summations for Charts
    # group_by choices: daily, weekly, monthly, annually
    trunc_func = TruncDate('sold_at')
    # For more complex grouping, we'd use Extract, but TruncDate is good for daily/weekly trends
    
    sales_trend = products.filter(status='Sold').filter(date_filter).annotate(
        period=trunc_func
    ).values('period').annotate(
        revenue=Sum('selling_price'),
        volume=Count('id')
    ).order_by('period')

    # Convert periods to strings or appropriate scale for charts
    
    # 8. Top performing phones (Profitability)
    top_performing = products.filter(status='Sold').annotate(
        profit=F('selling_price') - F('cost_price')
    ).values('brand', 'model_name').annotate(
        avg_profit=Sum('profit') / Count('id'),
        total_profit=Sum('profit'),
        volume=Count('id')
    ).order_by('-total_profit')[:5]
    
    return {
        "inventory_value": inventory_value,
        "in_stock": in_stock,
        "week_sales": {
            "revenue": week_sales['total_revenue'] or 0.00,
            "count": week_sales['count']
        },
        "active_listings": active_listings,
        "recent_activity": activity,
        "top_selling_models": top_selling,
        "top_performing_phones": top_performing,
        "sales_trend": list(sales_trend),
        "market_trajectory": "Neutral" # Placeholder for algorithm-based trajectory
    }
