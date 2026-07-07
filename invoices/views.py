
import calendar
from datetime import datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from easy_pdf.views import PDFTemplateView
from easy_pdf.rendering import render_to_pdf   # Added by me

from invoices.utils import get_aed_conversion
from invoices import utils

# Added by me
def get_invoice_pdf_bytes(invoice):
    """
    Renders the same invoice_template.html used by GenerateInvoiceView,
    but returns raw PDF bytes directly — no HTTP request/response involved.
    Used for email attachments.
    """
    utils.invoice_amount_calculation(invoice)

    show_po = False
    for campaign in invoice.campaigns.all():
        if campaign.purchase_order_no:
            show_po = True
            break
    context = {
        "pagesize": "A4",
        "invoice": invoice,
        "show_po": show_po,
    }

    return render_to_pdf("invoice_template.html", context)

 #(Add Currency)

# Version 1 — Old HTML view (just renders template)
def generate_invoice(request, pk):
    data = dict()

    invoice = utils.int_to_invoice(pk)
    today = invoice.invoice_on

    data['invoice'] = invoice
    last_day = calendar.monthrange(today.year, today.month)[1]
    data['last_date'] = datetime(year=today.year, month=today.month, day=last_day)
    data['first_date'] = datetime(year=today.year, month=today.month, day=1)

    return render(request, "invoice_template.html", data)


# PDF Download (staff only) — uses easy_pdf library to render the same
# template as a PDF. This is the view linked to the "Download Invoice"
# button in the admin list display and change form.
#
# Supports ?aed=1 query param to render the AED-converted invoice template
# with an extra "Total amount due in AED" line, using invoices.utils.get_aed_conversion().
class GenerateInvoiceView(PDFTemplateView):
    template_name = "invoice_template.html"

    def get(self, request, *args, **kwargs):
        # Pick template based on aed query param — normal invoice untouched
        if self.request.GET.get("aed") == "1":
            self.template_name = "invoice_template_aed.html"
        else:
            self.template_name = "invoice_template.html"

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        invoice = utils.int_to_invoice(self.kwargs['pk'])
        utils.invoice_amount_calculation(invoice)

        show_po = False
        for campaign in invoice.campaigns.all():
            if campaign.purchase_order_no:
                show_po = True
                break

        aed_conversion = None
        if self.request.GET.get("aed") == "1":
            aed_conversion = utils.get_aed_conversion(invoice)

        return super().get_context_data(
            pagesize='A4',
            filename=f"{invoice}.pdf",
            title=str(invoice),
            invoice=invoice,
            show_po=show_po,
            aed_conversion=aed_conversion,
            **kwargs
        )


# Version 3 — PDF download (alternate template)
class GenerateInvoice2View(PDFTemplateView):
    template_name = "invoice_template2.html"

    def get_context_data(self, **kwargs):
        invoice = utils.int_to_invoice(self.kwargs['pk'])
        utils.invoice_amount_calculation(invoice)

        return super(GenerateInvoice2View, self).get_context_data(
            pagesize='A4',
            filename="{}.pdf".format(invoice, invoice),
            title='{}'.format(invoice),
            invoice=invoice,
            **kwargs)


class AppointmentLetterPdfView(PDFTemplateView):
    template_name = "appointment_letter_pdf.html"

    def get_context_data(self, **kwargs):
        return super(AppointmentLetterPdfView, self).get_context_data(
            pagesize='A4',
            **kwargs)






































































