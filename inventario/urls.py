from django.urls import path
from . import views_warehouse_report

urlpatterns = [
    path('warehouse-report/<int:warehouse_id>/', views_warehouse_report.warehouse_report_view, name='warehouse_report'),
    path('warehouse-report/<int:warehouse_id>/pdf/', views_warehouse_report.warehouse_report_pdf, name='warehouse_report_pdf'),
]
