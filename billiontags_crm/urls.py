"""billiontags_crm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve
from insertion_order.views import download_error_report

from billiontags_crm import settings
from categories.admin import admin_site      # Custom admin
from categories.views import send_email_view
from insertion_order.views import generate_io, generate_io_date, custom_admin_view, download_report, \
    line_item_status_request, LineItemsPerformanceViews
from invoices import views
from reports.views import UnderPacingLineItem, OverPacingLineItem, ReportNotLineItem, InvoiceSummaryReportView, \
    SpendSummaryView, CompanyForecastingSummaryView, CampaignForecastingSummaryView, InvoiceYetNotGeneratedView, \
    InvoiceUnderDeliveredView, InvoiceOverDeliveredView, InvoiceSummaryReconciliationView 

urlpatterns = [
                  path('insertion_order/bulk-upload/', custom_admin_view, name="report_bulk_upload"), # Upload bulk data

                  path('reports/invoice-not-yet-generated/', InvoiceYetNotGeneratedView.as_view(),
                       name="invoice_not_yet_generated"),
                  path('reports/invoice-under-delivered/', InvoiceUnderDeliveredView.as_view(),
                       name="invoice_under_delivered"),
                  path('reports/invoice-over-delivered/', InvoiceOverDeliveredView.as_view(),
                       name="invoice_over_delivered"),
                  
                  # Reports Urls
                  path('reports/under-pacing/', UnderPacingLineItem.as_view(), name="under_pacing_report"),
                  path('reports/over-pacing/', OverPacingLineItem.as_view(), name="over_pacing_report"),
                  path('reports/not-uploaded/', ReportNotLineItem.as_view(), name="not_uploaded_report"),
                  path('reports/invoice-summary/', InvoiceSummaryReportView.as_view(), name="not_uploaded_report"),
                  #path('reports/invoice-summary-reconciliation/',views.InvoiceSummaryReconciliationView.as_view(),name='invoice-summary-reconciliation'),
                  path('reports/invoice-summary-reconciliation/', InvoiceSummaryReconciliationView.as_view(), name='invoice-summary-reconciliation'),
                  

                  # Insertion order urls 
                  path('insertion_order/bulk-upload/download-report/', download_report, name="report_bulk_download"),   # Download after upload
                  path('insertion_order/download-error-report/', download_error_report, name='download_error_report'),  # add this on 29/06/26
                  path('insertion_order/line-item/<int:pk>/', line_item_status_request,name="update_line_item_status"),  # Update single line item
                  path('insertion_orders/line-items/', LineItemsPerformanceViews.as_view(),name="Line_Items_Performance"), # View all line items

                  path('', admin_site.urls, name="my_admin"),  # Custom admin at root URL
                  path('admin/', admin.site.urls),    # Default Django admin

                  path('generate-io/<int:pk>/', generate_io),  # Generate IO PDF
                  path('generate-date/<int:pk>/', generate_io_date),

                  # Invoice URLs:
                  path('generate-invoice/<int:pk>/', views.generate_invoice),  # Original invoice generator
                  path('generate-invoice-new/<int:pk>/', views.GenerateInvoiceView.as_view()),    # V2 invoice (class-based)
                  path('generate-invoice-new-2/<int:pk>/', views.GenerateInvoice2View.as_view()),   # V3 invoice
                  path('generate-letter/', views.AppointmentLetterPdfView.as_view()),     # Appointment letter pdf
                  
                  path('requests/', include('clientrequests.urls')),  # Client request module has its own urls.py
                  path('api/', send_email_view),  # Only ONE api/ endpoint — sends email 
                  
                  # Analytics urls 
                  path("analytics/spend/", SpendSummaryView.as_view(), name="spend-summary"),
                  path("analytics/campaign-forecasting/", CampaignForecastingSummaryView.as_view(),
                       name="campaign-forecasting-summary"),
                  path("analytics/company-forecasting/", CompanyForecastingSummaryView.as_view(),
                       name="company-forecasting-summary"),

                  path('summernote/', include('django_summernote.urls')),
              ] + [url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
                   url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATICFILES_DIRS})]
