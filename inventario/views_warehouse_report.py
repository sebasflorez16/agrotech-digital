from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Warehouse, Supply
from .serializers import SupplySerializer
from django.http import HttpResponse
from django.template.loader import render_to_string
#import weasyprint
from django.conf import settings
import os

def warehouse_report_view(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    supplies = Supply.objects.filter(warehouse=warehouse).select_related('category', 'subcategory')
    supplies_list = []
    for s in supplies:
        supplies_list.append({
            'name': s.name,
            'category': s.category.name if s.category else '',
            'subcategory': s.subcategory.name if s.subcategory else '',
            'quantity': s.quantity,
            'unit_display': s.get_unit_display() if hasattr(s, 'get_unit_display') else s.unit,
            'unit_value': s.unit_value,
            'total_value': (s.quantity or 0) * (s.unit_value or 0),
            'description': s.description or ''
        })
    return render(request, 'inventario/warehouse_report.html', {
        'warehouse': warehouse,
        'supplies': supplies_list,
        'fecha': timezone.now(),
    })

def warehouse_report_pdf(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    supplies = Supply.objects.filter(warehouse=warehouse).select_related('category', 'subcategory')
    supplies_list = []
    for s in supplies:
        supplies_list.append({
            'name': s.name,
            'category': s.category.name if s.category else '',
            'subcategory': s.subcategory.name if s.subcategory else '',
            'quantity': s.quantity,
            'unit_display': s.get_unit_display() if hasattr(s, 'get_unit_display') else s.unit,
            'unit_value': s.unit_value,
            'total_value': (s.quantity or 0) * (s.unit_value or 0),
            'description': s.description or ''
        })
    html = render_to_string('inventario/warehouse_report.html', {
        'warehouse': warehouse,
        'supplies': supplies_list,
        'fecha': timezone.now(),
        'pdf_mode': True
    })
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_almacen_{warehouse.id}.pdf"'
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'agrotech-logo.png')
   
    return response
