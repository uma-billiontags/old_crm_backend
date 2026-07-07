
# utils.py - this file contains invoice amount calculation engine.

from annoying.functions import get_object_or_None
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Sum, Max

from insertion_order.models import IODetails
from invoices import models
from categories.models import AedExchangeRateMonth, AedExchangeRate

# Added by me
import io
import calendar
import xlsxwriter

# Added by me
def generate_bulk_invoice_campaign_report(invoices):
    """
    Same layout as generate_invoice_campaign_report (merged Company/Campaign
    cells + Total row), but sources line items across MULTIPLE invoices —
    used when several invoices are emailed together as one batch.
    """
    from itertools import groupby
    from insertion_order.templatetags.reports import (
        line_item_summary,
        month_year_iter,
    )

    billing_items = list(models.BillingLineItems.objects.filter(
        invoice__in=invoices
    ).select_related(
        "line_item__io__sub_campaign__campaign__company",
        "line_item__ad_type",
        "line_item__ethinicity",
        "invoice",
    ))

    billing_items.sort(key=lambda bi: (
        bi.line_item.io.sub_campaign.campaign.company.name,
        bi.line_item.io.sub_campaign.name,
        bi.line_item.id,
    ))

    io_details = [bi.line_item for bi in billing_items]
    invoice_dates = [inv.invoice_on for inv in invoices]

    if io_details:
        range_start = min(d.start_date for d in io_details)
    else:
        range_start = min(inv.invoice_from for inv in invoices)
    
    range_end = max(inv.invoice_to for inv in invoices)   # cap at the latest invoice's own month

    reporting_dates = list(month_year_iter(
        range_start.month, range_start.year, range_end.month, range_end.year
    ))

    first_company = invoices[0].company
    currency_code = first_company.billing_currency.iso_code_3 if first_company.billing_currency else ""

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Summary")

    header_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#D9E1F2', 'font_size': 10, 'text_wrap': True,
    })
    cell_format = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10,
    })
    merge_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        'font_size': 10, 'text_wrap': True,
    })
    money_format = workbook.add_format({
        'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0.00',
    })
    num_format = workbook.add_format({
        'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0',
    })
    total_label_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        'font_size': 10, 'bg_color': '#F2F2F2',
    })
    total_money_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'right', 'valign': 'vcenter',
        'font_size': 10, 'num_format': '#,##0.00', 'bg_color': '#F2F2F2',
    })
    total_num_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'right', 'valign': 'vcenter',
        'font_size': 10, 'num_format': '#,##0', 'bg_color': '#F2F2F2',
    })

    headers = [
        "Company", "Campaign Name", "IO Name", "Flight Dates", "Ad-Format", "Ethnicity",
        "Billable Impressions", "CPM ({})".format(currency_code), "Budget Given ({})".format(currency_code),
    ]
    for reporting_date in reporting_dates:
        label = reporting_date.strftime("%B %Y")
        headers += [
            "Billable Impressions - {}".format(label),
            "Total Impressions - {}".format(label),
            "Amount Spent - {} ({})".format(label, currency_code),
        ]
    headers += ["Amount Pending ({})".format(currency_code), "Billable Impressions Pending"]

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    worksheet.set_column(0, len(headers) - 1, 20)

    total_billable_impression = 0
    total_budget_given = 0
    total_amount_pending = 0
    total_billable_pending = 0
    month_totals = [{"billable": 0, "delivered": 0, "amount": 0} for _ in reporting_dates]

    def group_key(bi):
        io_detail = bi.line_item
        return (io_detail.io.sub_campaign.campaign.company_id, io_detail.io.sub_campaign_id)

    row = 1
    for _, group in groupby(billing_items, key=group_key):
        group = list(group)
        group_start_row = row
        first_io = group[0].line_item
        company = first_io.io.sub_campaign.campaign.company
        campaign_label = first_io.io.sub_campaign.name

        for billing_item in group:
            io_detail = billing_item.line_item
            reports = line_item_summary(io_detail, reporting_dates)

            col = 2
            worksheet.write(row, col, io_detail.description, cell_format); col += 1
            worksheet.write(row, col, "{} - {}".format(
                io_detail.start_date.strftime("%b %d, %Y"), io_detail.end_date.strftime("%b %d, %Y")
            ), cell_format); col += 1
            worksheet.write(row, col, str(io_detail.ad_type), cell_format); col += 1
            worksheet.write(row, col, str(io_detail.ethinicity), cell_format); col += 1
            worksheet.write(row, col, io_detail.volume, num_format); col += 1
            worksheet.write(row, col, io_detail.unit_cost, money_format); col += 1
            worksheet.write(row, col, io_detail.net_cost, money_format); col += 1

            for i, month_report in enumerate(reports['month']):
                worksheet.write(row, col, month_report['billable_impression'], num_format); col += 1
                worksheet.write(row, col, month_report['delivered_impression'], num_format); col += 1
                worksheet.write(row, col, month_report['amount'], money_format); col += 1
                month_totals[i]["billable"] += month_report['billable_impression']
                month_totals[i]["delivered"] += month_report['delivered_impression']
                month_totals[i]["amount"] += month_report['amount']

            worksheet.write(row, col, reports['balance_amount'], money_format); col += 1
            worksheet.write(row, col, reports['balance_impression'], num_format); col += 1

            total_billable_impression += io_detail.volume
            total_budget_given += io_detail.net_cost
            total_amount_pending += reports['balance_amount']
            total_billable_pending += reports['balance_impression']

            row += 1

        group_end_row = row - 1
        if group_end_row > group_start_row:
            worksheet.merge_range(group_start_row, 0, group_end_row, 0, company.name, merge_format)
            worksheet.merge_range(group_start_row, 1, group_end_row, 1, campaign_label, merge_format)
        else:
            worksheet.write(group_start_row, 0, company.name, merge_format)
            worksheet.write(group_start_row, 1, campaign_label, merge_format)

    worksheet.merge_range(row, 0, row, 5, "Total", total_label_format)
    worksheet.write(row, 6, total_billable_impression, total_num_format)
    worksheet.write(row, 7, "", total_label_format)
    worksheet.write(row, 8, total_budget_given, total_money_format)
    col = 9
    for mt in month_totals:
        worksheet.write(row, col, mt["billable"], total_num_format); col += 1
        worksheet.write(row, col, mt["delivered"], total_num_format); col += 1
        worksheet.write(row, col, mt["amount"], total_money_format); col += 1
    worksheet.write(row, col, total_amount_pending, total_money_format); col += 1
    worksheet.write(row, col, total_billable_pending, total_num_format)

    workbook.close()
    output.seek(0)
    return output.read()

# Added by me
def generate_invoice_campaign_report(invoice):
    """
    Builds an in-memory Excel workbook matching the exact structure of the
    'Invoice Summary' Download Excel button (merged Company/Campaign cells
    + Total row), scoped to only the line items included in this invoice.
    Returns raw bytes, ready to attach to an email.
    """

    from itertools import groupby
    from insertion_order.templatetags.reports import (
        line_item_summary,
        month_year_iter,
    )

    billing_items = list(invoice.line_items.select_related(
        "line_item__io__sub_campaign__campaign__company",
        "line_item__ad_type",
        "line_item__ethinicity",
    ).all())

    # Sort so rows land in the same order the grouping/merging expects
    billing_items.sort(key=lambda bi: (
        bi.line_item.io.sub_campaign.campaign.company.name,
        bi.line_item.io.sub_campaign.name,
        bi.line_item.id,
    ))

    io_details = [bi.line_item for bi in billing_items]

    if io_details:
        range_start = min(d.start_date for d in io_details)
    else:
        range_start = invoice.invoice_from
    range_end = invoice.invoice_to   # cap at this invoice's own month, don't extend into future months

    reporting_dates = list(month_year_iter(
        range_start.month, range_start.year, range_end.month, range_end.year
    ))

    currency_code = invoice.company.billing_currency.iso_code_3 if invoice.company.billing_currency else ""

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Summary")

    header_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#D9E1F2', 'font_size': 10, 'text_wrap': True,
    })
    cell_format = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10,
    })
    merge_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        'font_size': 10, 'text_wrap': True,
    })
    money_format = workbook.add_format({
        'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0.00',
    })
    num_format = workbook.add_format({
        'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0',
    })
    total_label_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
        'font_size': 10, 'bg_color': '#F2F2F2',
    })
    total_money_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'right', 'valign': 'vcenter',
        'font_size': 10, 'num_format': '#,##0.00', 'bg_color': '#F2F2F2',
    })
    total_num_format = workbook.add_format({
        'bold': True, 'border': 1, 'align': 'right', 'valign': 'vcenter',
        'font_size': 10, 'num_format': '#,##0', 'bg_color': '#F2F2F2',
    })

    headers = [
        "Company", "Campaign Name", "IO Name", "Flight Dates", "Ad-Format", "Ethnicity",
        "Billable Impressions", "CPM ({})".format(currency_code), "Budget Given ({})".format(currency_code),
    ]
    for reporting_date in reporting_dates:
        label = reporting_date.strftime("%B %Y")
        headers += [
            "Billable Impressions - {}".format(label),
            "Total Impressions - {}".format(label),
            "Amount Spent - {} ({})".format(label, currency_code),
        ]
    headers += ["Amount Pending ({})".format(currency_code), "Billable Impressions Pending"]

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    worksheet.set_column(0, len(headers) - 1, 20)

    # ---- Running totals for the Total row ----
    total_billable_impression = 0
    total_budget_given = 0
    total_amount_pending = 0
    total_billable_pending = 0
    month_totals = [{"billable": 0, "delivered": 0, "amount": 0} for _ in reporting_dates]

    def group_key(bi):
        io_detail = bi.line_item
        return (io_detail.io.sub_campaign.campaign.company_id, io_detail.io.sub_campaign_id)

    row = 1
    for _, group in groupby(billing_items, key=group_key):
        group = list(group)
        group_start_row = row
        first_io = group[0].line_item
        company = first_io.io.sub_campaign.campaign.company
        campaign_label = first_io.io.sub_campaign.name

        for billing_item in group:
            io_detail = billing_item.line_item
            reports = line_item_summary(io_detail, reporting_dates)

            col = 2
            worksheet.write(row, col, io_detail.description, cell_format); col += 1
            worksheet.write(row, col, "{} - {}".format(
                io_detail.start_date.strftime("%b %d, %Y"), io_detail.end_date.strftime("%b %d, %Y")
            ), cell_format); col += 1
            worksheet.write(row, col, str(io_detail.ad_type), cell_format); col += 1
            worksheet.write(row, col, str(io_detail.ethinicity), cell_format); col += 1
            worksheet.write(row, col, io_detail.volume, num_format); col += 1
            worksheet.write(row, col, io_detail.unit_cost, money_format); col += 1
            worksheet.write(row, col, io_detail.net_cost, money_format); col += 1

            for i, month_report in enumerate(reports['month']):
                worksheet.write(row, col, month_report['billable_impression'], num_format); col += 1
                worksheet.write(row, col, month_report['delivered_impression'], num_format); col += 1
                worksheet.write(row, col, month_report['amount'], money_format); col += 1
                month_totals[i]["billable"] += month_report['billable_impression']
                month_totals[i]["delivered"] += month_report['delivered_impression']
                month_totals[i]["amount"] += month_report['amount']

            worksheet.write(row, col, reports['balance_amount'], money_format); col += 1
            worksheet.write(row, col, reports['balance_impression'], num_format); col += 1

            total_billable_impression += io_detail.volume
            total_budget_given += io_detail.net_cost
            total_amount_pending += reports['balance_amount']
            total_billable_pending += reports['balance_impression']

            row += 1

        group_end_row = row - 1
        if group_end_row > group_start_row:
            worksheet.merge_range(group_start_row, 0, group_end_row, 0, company.name, merge_format)
            worksheet.merge_range(group_start_row, 1, group_end_row, 1, campaign_label, merge_format)
        else:
            worksheet.write(group_start_row, 0, company.name, merge_format)
            worksheet.write(group_start_row, 1, campaign_label, merge_format)

    # ---- Total row ----
    worksheet.merge_range(row, 0, row, 5, "Total", total_label_format)
    worksheet.write(row, 6, total_billable_impression, total_num_format)
    worksheet.write(row, 7, "", total_label_format)
    worksheet.write(row, 8, total_budget_given, total_money_format)
    col = 9
    for mt in month_totals:
        worksheet.write(row, col, mt["billable"], total_num_format); col += 1
        worksheet.write(row, col, mt["delivered"], total_num_format); col += 1
        worksheet.write(row, col, mt["amount"], total_money_format); col += 1
    worksheet.write(row, col, total_amount_pending, total_money_format); col += 1
    worksheet.write(row, col, total_billable_pending, total_num_format)

    workbook.close()
    output.seek(0)
    return output.read()

def int_to_invoice(pk):
    try:
        return models.Invoices.objects.get(pk=pk)
    except ObjectDoesNotExist:
        raise ValidationError("Invalid ID")


def perform_operation(queryset, new_set):
    old_set = set(queryset)
    new_set = set(new_set)

    deleted_set = old_set.difference(new_set)
    added_set = new_set.difference(old_set)

    return deleted_set, added_set


def metrics_amount_calculation(line_item, volume=0):
    volume = 0 if volume is None else volume
    if line_item.ad_metrics.id == 1:
        net_cost = round((volume / 1000) * line_item.unit_cost, 2)
    else:
        net_cost = round(volume * line_item.unit_cost, 2)
    return net_cost


def invoice_amount_calculation(invoice, deleted_set=None):
    total_discount = 0
    total_amount = 0
    total_billing_amount = 0

    old_line_items = models.BillingLineItems.objects.filter(invoice=invoice)
    # Get all line items that are relevant for the invoice based on the campaigns linked to the invoice 
    # and the invoice month. This is used to determine which line items to add, update or delete when invoice details are updated (e.g. if campaign is removed from invoice, or if line item metrics have changed such that it no longer falls within the invoice month)
    line_items = IODetails.objects.filter(io__sub_campaign__campaign__in=invoice.campaigns.all(),
                                          reports__report_on__year=invoice.invoice_on.year,
                                          reports__report_on__month=invoice.invoice_on.month).distinct() # Only line items that have reports in June 2026 

    new_line_items = models.BillingLineItems.objects.filter(invoice=invoice, line_item__in=line_items)
    deleted_set, added_set = perform_operation(old_line_items, new_line_items)
    
    # Delete line items that are no longer relevant (e.g. if campaign is removed from invoice, or if line item metrics have changed such that it no longer falls within the invoice month)
    if deleted_set:
        for line_item in deleted_set:
            line_item.delete()

    for campaign in invoice.campaigns.all():

        line_items = IODetails.objects.filter(io__sub_campaign__campaign=campaign,
                                              reports__report_on__year=invoice.invoice_on.year,
                                              reports__report_on__month=invoice.invoice_on.month).distinct()

        for line_item in line_items:
            discount = 0

            report_dict = dict()
            if line_item.ad_metrics.id in [1, 3]:
                volume = line_item.reports.filter(report_on__month=invoice.invoice_on.month,
                                                  report_on__year=invoice.invoice_on.year).aggregate(
                    impression=Sum('impression'))['impression']
                net_cost = metrics_amount_calculation(line_item, volume)
                previous_volume = line_item.reports.exclude(report_on__gte=invoice.invoice_from).aggregate(
                    impression=Sum('impression'))['impression']
                previous_spent = metrics_amount_calculation(line_item, previous_volume)

            else: 
                # calculate volume for each line item 

                volume = line_item.reports.filter(report_on__month=invoice.invoice_on.month,
                                                  report_on__year=invoice.invoice_on.year).aggregate(
                    clicks=Sum('clicks'))['clicks']
                net_cost = metrics_amount_calculation(line_item, volume)
                previous_volume = line_item.reports.exclude(report_on__gte=invoice.invoice_from).aggregate(
                    clicks=Sum('clicks'))['clicks']
                
                # previous month spend
                previous_spent = metrics_amount_calculation(line_item, previous_volume)

            report = get_object_or_None(models.BillingLineItems, description=line_item.description, invoice=invoice,
                                        line_item=line_item)

            # this month + previous month total
            overall_spent = round(net_cost + previous_spent, 2)

            # If total spent > booked amount for the line item, then give discount such that billing cost = total spent (but discount cannot exceed net cost)
            if overall_spent > round(line_item.net_cost, 2):
                discount = round(overall_spent, 2) - round(line_item.net_cost, 2)
       
           # Discount can't be more than this month cost
            if net_cost < discount:
                discount = net_cost

            billing_cost = round(net_cost - discount, 2)
            total_billing_amount += billing_cost
            total_amount += net_cost

            report_dict['invoice'] = invoice
            report_dict['description'] = line_item.description
            report_dict['line_item'] = line_item
            report_dict['ethinicity'] = line_item.ethinicity
            report_dict['start_date'] = line_item.start_date
            report_dict['end_date'] = line_item.end_date
            report_dict['ad_type'] = line_item.ad_type
            report_dict['ad_metrics'] = line_item.ad_metrics
            report_dict['unit_cost'] = line_item.unit_cost
            report_dict['volume'] = volume
            report_dict['net_cost'] = net_cost
            report_dict['billing_cost'] = billing_cost
            report_dict['discount'] = round(discount, 2)

            if report:
                report_dict.pop("invoice")
                report_dict.pop("line_item")
                report.__dict__.update(**report_dict)
            else:
                report = models.BillingLineItems.objects.create(**report_dict)
            report.save()
            total_discount += discount

    invoice.total_discount = round(total_discount, 2)
    invoice.total_amount = round(total_amount, 2)

    # Calculate GST and VAT tax amounts based on the total billing amount after discount. 
    if invoice.vat_tax:
        invoice.vat_tax_amount = round(((total_billing_amount/100)*invoice.vat_tax), 2)

    if invoice.gst:
        invoice.gst_amount = round(((total_billing_amount/100)*invoice.gst), 2)    # ₹48,000 * 18% = ₹8,640

    invoice.billing_amount = round(invoice.gst_amount + invoice.vat_tax_amount + total_billing_amount, 2)   # ₹48,000 + ₹8,640 = ₹56,640 final invoice amount
    invoice.save()
    return


def get_aed_conversion(invoice):
    """
    Returns a dict with AED converted amount + rate used, or None if:
      - company has not enabled AED invoice
      - no matching exchange rate found for invoice month/currency
    """
    company = invoice.company

    # Step 1: check if company has AED invoice enabled
    if not getattr(company, "enable_aed_invoice", False):
        return None

    # Step 2: get billing currency code (e.g. "AUD", "USD", "CAD")
    currency_code = company.billing_currency.iso_code_3

    # Skip conversion if company already bills in AED
    if currency_code == "AED":
        return None

    # Step 3: find the exchange rate month matching invoice period end (invoice_to)
    invoice_month = invoice.invoice_to.month
    invoice_year = invoice.invoice_to.year

    rate_month = AedExchangeRateMonth.objects.filter(
        month=invoice_month,
        year=invoice_year
    ).first()

    if not rate_month:
        return None

    # Step 4: get the exchange rate for that currency in that month
    rate_obj = AedExchangeRate.objects.filter(
        month=rate_month,
        currency__code=currency_code,
        is_active=True
    ).first()

    if not rate_obj:
        return None

    # Step 5: calculate the AED converted amount
    original_amount = invoice.total_pay_amount()
    exchange_rate = float(rate_obj.exchange_rate)
    aed_amount = round(original_amount * exchange_rate, 2)

    return {
        "original_amount": original_amount,
        "original_currency": currency_code,
        "exchange_rate": exchange_rate,
        "aed_amount": aed_amount,
        "effective_date": rate_obj.effective_date,
    }






























































# # utils.py - this file contains invoice amount calculation engine.

# from annoying.functions import get_object_or_None
# from django.core.exceptions import ObjectDoesNotExist, ValidationError
# from django.db.models import Sum, Max

# from insertion_order.models import IODetails
# from invoices import models
# from categories.models import AedExchangeRateMonth, AedExchangeRate


# def int_to_invoice(pk):
#     try:
#         return models.Invoices.objects.get(pk=pk)
#     except ObjectDoesNotExist:
#         raise ValidationError("Invalid ID")


# def perform_operation(queryset, new_set):
#     old_set = set(queryset)
#     new_set = set(new_set)

#     deleted_set = old_set.difference(new_set)
#     added_set = new_set.difference(old_set)

#     return deleted_set, added_set


# def metrics_amount_calculation(line_item, volume=0):
#     volume = 0 if volume is None else volume
#     if line_item.ad_metrics.id == 1:
#         net_cost = round((volume / 1000) * line_item.unit_cost, 2)
#     else:
#         net_cost = round(volume * line_item.unit_cost, 2)
#     return net_cost


# def invoice_amount_calculation(invoice, deleted_set=None):
#     total_discount = 0
#     total_amount = 0
#     total_billing_amount = 0

#     old_line_items = models.BillingLineItems.objects.filter(invoice=invoice)
#     # Get all line items that are relevant for the invoice based on the campaigns linked to the invoice 
#     # and the invoice month. This is used to determine which line items to add, update or delete when invoice details are updated (e.g. if campaign is removed from invoice, or if line item metrics have changed such that it no longer falls within the invoice month)
#     line_items = IODetails.objects.filter(io__sub_campaign__campaign__in=invoice.campaigns.all(),
#                                           reports__report_on__year=invoice.invoice_on.year,
#                                           reports__report_on__month=invoice.invoice_on.month).distinct() # Only line items that have reports in June 2026 

#     new_line_items = models.BillingLineItems.objects.filter(invoice=invoice, line_item__in=line_items)
#     deleted_set, added_set = perform_operation(old_line_items, new_line_items)
    
#     # Delete line items that are no longer relevant (e.g. if campaign is removed from invoice, or if line item metrics have changed such that it no longer falls within the invoice month)
#     if deleted_set:
#         for line_item in deleted_set:
#             line_item.delete()

#     for campaign in invoice.campaigns.all():

#         line_items = IODetails.objects.filter(io__sub_campaign__campaign=campaign,
#                                               reports__report_on__year=invoice.invoice_on.year,
#                                               reports__report_on__month=invoice.invoice_on.month).distinct()

#         for line_item in line_items:
#             discount = 0

#             report_dict = dict()
#             if line_item.ad_metrics.id in [1, 3]:
#                 volume = line_item.reports.filter(report_on__month=invoice.invoice_on.month,
#                                                   report_on__year=invoice.invoice_on.year).aggregate(
#                     impression=Sum('impression'))['impression']
#                 net_cost = metrics_amount_calculation(line_item, volume)
#                 previous_volume = line_item.reports.exclude(report_on__gte=invoice.invoice_from).aggregate(
#                     impression=Sum('impression'))['impression']
#                 previous_spent = metrics_amount_calculation(line_item, previous_volume)

#             else: 
#                 # calculate volume for each line item 

#                 volume = line_item.reports.filter(report_on__month=invoice.invoice_on.month,
#                                                   report_on__year=invoice.invoice_on.year).aggregate(
#                     clicks=Sum('clicks'))['clicks']
#                 net_cost = metrics_amount_calculation(line_item, volume)
#                 previous_volume = line_item.reports.exclude(report_on__gte=invoice.invoice_from).aggregate(
#                     clicks=Sum('clicks'))['clicks']
                
#                 # previous month spend
#                 previous_spent = metrics_amount_calculation(line_item, previous_volume)

#             report = get_object_or_None(models.BillingLineItems, description=line_item.description, invoice=invoice,
#                                         line_item=line_item)

#             # this month + previous month total
#             overall_spent = round(net_cost + previous_spent, 2)

#             # If total spent > booked amount for the line item, then give discount such that billing cost = total spent (but discount cannot exceed net cost)
#             if overall_spent > round(line_item.net_cost, 2):
#                 discount = round(overall_spent, 2) - round(line_item.net_cost, 2)
       
#            # Discount can't be more than this month cost
#             if net_cost < discount:
#                 discount = net_cost

#             billing_cost = round(net_cost - discount, 2)
#             total_billing_amount += billing_cost
#             total_amount += net_cost

#             report_dict['invoice'] = invoice
#             report_dict['description'] = line_item.description
#             report_dict['line_item'] = line_item
#             report_dict['ethinicity'] = line_item.ethinicity
#             report_dict['start_date'] = line_item.start_date
#             report_dict['end_date'] = line_item.end_date
#             report_dict['ad_type'] = line_item.ad_type
#             report_dict['ad_metrics'] = line_item.ad_metrics
#             report_dict['unit_cost'] = line_item.unit_cost
#             report_dict['volume'] = volume
#             report_dict['net_cost'] = net_cost
#             report_dict['billing_cost'] = billing_cost
#             report_dict['discount'] = round(discount, 2)

#             if report:
#                 report_dict.pop("invoice")
#                 report_dict.pop("line_item")
#                 report.__dict__.update(**report_dict)
#             else:
#                 report = models.BillingLineItems.objects.create(**report_dict)
#             report.save()
#             total_discount += discount

#     invoice.total_discount = round(total_discount, 2)
#     invoice.total_amount = round(total_amount, 2)

#     # Calculate GST and VAT tax amounts based on the total billing amount after discount. 
#     if invoice.vat_tax:
#         invoice.vat_tax_amount = round(((total_billing_amount/100)*invoice.vat_tax), 2)

#     if invoice.gst:
#         invoice.gst_amount = round(((total_billing_amount/100)*invoice.gst), 2)    # ₹48,000 * 18% = ₹8,640

#     invoice.billing_amount = round(invoice.gst_amount + invoice.vat_tax_amount + total_billing_amount, 2)   # ₹48,000 + ₹8,640 = ₹56,640 final invoice amount
#     invoice.save()
#     return


# # ADD THIS 
# def get_aed_conversion(invoice):
#     """
#     Returns a dict with AED converted amount + rate used, or None if:
#       - company has not enabled AED invoice
#       - no matching exchange rate found for invoice month/currency
#     """
#     company = invoice.company

#     # Step 1: Company AED invoice enabled-a check pannunga
#     if not getattr(company, "enable_aed_invoice", False):
#         return None

#     # Step 2: Company billing currency edukanum (e.g. "AUD", "USD", "CAD")
#     currency_code = company.billing_currency.iso_code_3

#     # AED company-ku AED conversion தேவை இல்ல
#     if currency_code == "AED":
#         return None

#     # Step 3: Invoice period end date (invoice_to) vachi matching month/year
#     invoice_month = invoice.invoice_to.month
#     invoice_year = invoice.invoice_to.year

#     rate_month = AedExchangeRateMonth.objects.filter(
#         month=invoice_month,
#         year=invoice_year
#     ).first()

#     if not rate_month:
#         return None

#     # Step 4: Andha currency-oda rate edukanum
#     rate_obj = AedExchangeRate.objects.filter(
#         month=rate_month,
#         currency=currency_code,
#         is_active=True
#     ).first()

#     if not rate_obj:
#         return None

#     # Step 5: Calculation
#     original_amount = invoice.total_pay_amount()
#     exchange_rate = float(rate_obj.exchange_rate)
#     aed_amount = round(original_amount * exchange_rate, 2)

#     return {
#         "original_amount": original_amount,
#         "original_currency": currency_code,
#         "exchange_rate": exchange_rate,
#         "aed_amount": aed_amount,
#         "effective_date": rate_obj.effective_date,
#     }