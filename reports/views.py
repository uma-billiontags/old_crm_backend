import calendar
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, F, Max
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Coalesce
from django.views import generic

from categories.admin import admin_site
from company_details.models import CompanyDetails
from insertion_order.models import IODetails, Campaigns, SubCampaign, InsertionOrders
from insertion_order.templatetags.reports import month_year_iter

# This function returns a list of line items that are underpacing and overpacing based on actual delivery vs expected delivery

def get_pacing_data(pacing_type, filter_dict={}):
    today = datetime.today().date()

    report_date = IODetails.objects.aggregate(
        max_date=Max('reports__report_on')
    )['max_date']

    if not report_date:
        return []

    result = []

    for li in IODetails.objects.filter(
            end_date__gte=today,
            **filter_dict).order_by("end_date"):

        report = li.reports.filter(report_on=report_date).first()

        if not report or report.impression <= 0:
            continue

        today = datetime.today().date()
        if today > li.end_date:
            remaining_days = 0
        elif today < li.start_date:
            remaining_days = (li.end_date - li.start_date).days + 1
        else:
            remaining_days = (li.end_date - today).days + 1
            archived_impressions = li.total_impression()
            remaining_impressions = max(li.volume - archived_impressions,0)
            daily_target = round(remaining_impressions / remaining_days) if remaining_days > 0 else 0


        if daily_target <= 0:
            continue

        # UNDER PACING
        if pacing_type == 'under' and daily_target > report.impression:

            pct = round(
                ((daily_target - report.impression) / daily_target) * 100
            )

            result.append({
                "object": li,
                "value": -pct,
                "daily_target": daily_target,
                "last_date": report.impression,
                "differance": daily_target - report.impression,
                "report_date": report.report_on,
            })

        # OVER PACING
        elif pacing_type == 'over' and daily_target < report.impression:

            pct = round(
                ((report.impression - daily_target) / daily_target) * 100
            )

            result.append({
                "object": li,
                "value": pct,
                "daily_target": daily_target,
                "last_date": report.impression,
                "differance": report.impression - daily_target,
                "report_date": report.report_on,
            })

    return result




class UnderPacingLineItem(LoginRequiredMixin, generic.TemplateView):
    login_url = '/'
    template_name = "reports/under_pacing_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Under Pacing Report'
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context['pacing'] = "Under"
        context['company_details'] = CompanyDetails.objects.filter(is_active=True)

        filter_dict = {}
        if self.request.GET.get('company_name'):
            context['selected_company'] = int(self.request.GET.get('company_name'))
            context['campaigns'] = Campaigns.objects.filter(
                company=context['selected_company'], is_active=True)
            filter_dict['io__sub_campaign__campaign__company'] = context['selected_company']
        if self.request.GET.get('campaign'):
            context['selected_campaign'] = int(self.request.GET.get('campaign'))
            context['sub_campaigns'] = SubCampaign.objects.filter(
                campaign=int(self.request.GET.get('campaign')), is_active=True)
            filter_dict['io__sub_campaign__campaign'] = context['selected_campaign']
        if self.request.GET.get('sub_campaign'):
            context['selected_sub_campaign'] = int(self.request.GET.get('sub_campaign'))
            filter_dict['io__sub_campaign'] = context['selected_sub_campaign']

        context['my_list'] = get_pacing_data('under', filter_dict)
        return context




class OverPacingLineItem(LoginRequiredMixin, generic.TemplateView):
    login_url = '/'
    template_name = "reports/under_pacing_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Over Pacing Report'
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context['pacing'] = "Over"
        context['company_details'] = CompanyDetails.objects.filter(is_active=True)

        filter_dict = {}
        if self.request.GET.get('company_name'):
            context['selected_company'] = int(self.request.GET.get('company_name'))
            context['campaigns'] = Campaigns.objects.filter(
                company=context['selected_company'], is_active=True)
            filter_dict['io__sub_campaign__campaign__company'] = context['selected_company']
        if self.request.GET.get('campaign'):
            context['selected_campaign'] = int(self.request.GET.get('campaign'))
            context['sub_campaigns'] = SubCampaign.objects.filter(
                campaign=int(self.request.GET.get('campaign')), is_active=True)
            filter_dict['io__sub_campaign__campaign'] = context['selected_campaign']
        if self.request.GET.get('sub_campaign'):
            context['selected_sub_campaign'] = int(self.request.GET.get('sub_campaign'))
            filter_dict['io__sub_campaign'] = context['selected_sub_campaign']

        context['my_list'] = get_pacing_data('over', filter_dict)
        return context


class ReportNotLineItem(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "reports/report_not_available.html"
    paginate_by = 20

    def get_queryset(self):
        today = datetime.today().date()
        return IODetails.objects.filter(
            start_date__lte=today, end_date__gte=today
        ).exclude(reports__report_on=today - timedelta(days=1)).order_by("-end_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({"date": datetime.today() - timedelta(days=1)})
        return context


# class InvoiceSummaryReconciliationView(LoginRequiredMixin, generic.ListView):

#     login_url = '/'
#     # template_name = "reports/invoice_summary.html"
#     template_name = "reports/invoice_summary_reconciliation.html"

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.company = None
    

#     def get_queryset(self):
#         today = datetime.today()
#         if self.request.GET.get('company') and self.request.GET.get('date'):
#             today = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')
#             self.company = CompanyDetails.objects.get(name=self.request.GET.get('company'))
#         else:
#             self.company = None
#         month_start = today.replace(day=1)
#         month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
#         qs = InsertionOrders.objects.filter(
#             start_date__lte=month_end, end_date__gte=month_start).order_by("sub_campaign__campaign__company__name", "-created_on")
#         if self.company:
#             qs = qs.filter(sub_campaign__campaign__company=self.company)
#         return qs


#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         self.request.current_app = 'Publisher_admin'
#         context.update(admin_site.each_context(self.request))
#         context.update({'company': CompanyDetails.objects.filter(is_active=True)})
#         # context.update({'title': 'Line Item Performance'})
#         context.update({'title': 'Invoice Summary Reconciliation'})
    

#         if self.request.GET.get('company') and self.request.GET.get('date'):
#             invoice_on = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')
#             context.update({"invoice_on": invoice_on})
#             # Plain `date` (not `datetime`) version of invoice_on's month, so the
#             # template can compare it directly against reporting_dates entries
#             # (which are also plain `date` objects) with <=, ==, etc.
#             context.update({"invoice_month": invoice_on.date().replace(day=1)})

#             qs = self.get_queryset()
#             start_date = qs.dates('start_date', 'month').first()

#             # ── FIX: previously reporting_dates stopped at invoice_on's month,
#             # so July/August never appeared even when the matched orders'
#             # flight dates (e.g. Jun 8 - Aug 31) ran well past June.
#             # Now we extend the range through the LATEST end_date month among
#             # the orders active in the selected month, so every month of the
#             # flight gets a column (with planned/pending values) even before
#             # actual delivery data exists for those future months.
#             last_end_date = qs.dates('end_date', 'month').last()

#             if start_date:
#                 range_end = invoice_on
#                 if last_end_date and (last_end_date.year, last_end_date.month) > (invoice_on.year, invoice_on.month):
#                     range_end = last_end_date

#                 reporting_dates = [x for x in month_year_iter(
#                     start_date.month, start_date.year, range_end.month, range_end.year)]
#                 context.update({"reporting_dates": reporting_dates})
#             context.update({"currency": self.company})
#         return context
    

class InvoiceSummaryReconciliationView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "reports/invoice_summary_reconciliation.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.company = None

    def get_queryset(self):
        today = datetime.today()

        # DATE now drives the month filter on its own — company is optional.
        if self.request.GET.get('date'):
            today = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')

        if self.request.GET.get('company'):
            self.company = CompanyDetails.objects.get(name=self.request.GET.get('company'))
        else:
            self.company = None

        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        qs = InsertionOrders.objects.filter(
            start_date__lte=month_end, end_date__gte=month_start
        ).order_by("sub_campaign__campaign__company__name", "-created_on")

        if self.company:
            qs = qs.filter(sub_campaign__campaign__company=self.company)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'company': CompanyDetails.objects.filter(is_active=True)})
        context.update({'title': 'Invoice Summary Reconciliation'})

        # Enrichment (reporting_dates / invoice_month / planned-variance-pacing)
        # now triggers off DATE ALONE. Company stays optional:
        #   - date only        -> all companies, this requirement (case 3)
        #   - company + date   -> single company (already working, case 2)
        #   - neither          -> plain listing, no pacing columns (case 1)
        if self.request.GET.get('date'):
            invoice_on = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')
            context.update({"invoice_on": invoice_on})
            context.update({"invoice_month": invoice_on.date().replace(day=1)})

            qs = self.get_queryset()
            start_date = qs.dates('start_date', 'month').first()
            last_end_date = qs.dates('end_date', 'month').last()

            if start_date:
                range_end = invoice_on
                if last_end_date and (last_end_date.year, last_end_date.month) > (invoice_on.year, invoice_on.month):
                    range_end = last_end_date

                reporting_dates = [x for x in month_year_iter(
                    start_date.month, start_date.year, range_end.month, range_end.year)]
                context.update({"reporting_dates": reporting_dates})

            # None when no company selected — template's {{currency.*}} lookups
            # simply render blank (Django no-ops attribute access on None),
            # matching image 1's blank "CPM ()" / "Budget Given ()" headers.
            context.update({"currency": self.company})
        return context





class InvoiceSummaryReportView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "reports/invoice_summary.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.company = None

    def get_queryset(self):
        today = datetime.today()
        if self.request.GET.get('company') and self.request.GET.get('date'):
            today = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')
            self.company = CompanyDetails.objects.get(name=self.request.GET.get('company'))
        else:
            self.company = None
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        qs = InsertionOrders.objects.filter(
            start_date__lte=month_end, end_date__gte=month_start).order_by("sub_campaign__campaign__company__name", "-created_on")
        
        if self.company:
            qs = qs.filter(sub_campaign__campaign__company=self.company)
        return qs
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'company': CompanyDetails.objects.filter(is_active=True)})
        context.update({'title': 'Line Item Performance'})
        if self.request.GET.get('company') and self.request.GET.get('date'):
            invoice_on = datetime.strptime(self.request.GET.get('date'), '%Y-%m-%d')
            context.update({"invoice_on": invoice_on})
            start_date = self.get_queryset().dates('start_date', 'month').first()
            if start_date:
                reporting_dates = [x for x in month_year_iter(
                    start_date.month, start_date.year, invoice_on.month, invoice_on.year)]
                context.update({"reporting_dates": reporting_dates})
            context.update({"currency": self.company})
        return context



class SpendSummaryView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "analytics/spend_summary.html"

    def get_queryset(self):
        if self.request.GET.get('company'):
            return CompanyDetails.objects.filter(is_active=True, id=self.request.GET.get('company'))
        return CompanyDetails.objects.filter(is_active=True).order_by("-created_on").annotate(
            impression=Sum('campaigns__sub_campaign__insertion_order__io_details__reports__impression')
        ).order_by("-impression")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'title': 'Spend Summary'})
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'companies': CompanyDetails.objects.filter(is_active=True)})
        if self.request.GET.get('end_date') and self.request.GET.get('start_date'):
            context.update({"end_date": datetime.strptime(self.request.GET.get('end_date'), '%Y-%m-%d')})
            context.update({"start_date": datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d')})
        else:
            context.update({"end_date": datetime.today() - timedelta(days=1)})
            context.update({"start_date": datetime.today() - timedelta(days=1)})
        return context


class CompanyForecastingSummaryView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "analytics/company-forecasting.html"

    def get_queryset(self):
        if self.request.GET.get('company'):
            return CompanyDetails.objects.filter(is_active=True, id=self.request.GET.get('company'))
        return CompanyDetails.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'title': 'Company wise Forecasting'})
        end_date = CompanyDetails.objects.filter(is_active=True).dates('campaigns__end_date', 'month').last()
        if end_date:
            context.update({"reporting_dates": [x for x in month_year_iter(
                datetime.today().month, datetime.today().year, end_date.month, end_date.year)]})
        return context


class CampaignForecastingSummaryView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "analytics/campaign-forecasting.html"

    def get_queryset(self):
        if self.request.GET.get('company'):
            return Campaigns.objects.filter(
                is_active=True, status="Live",
                company=self.request.GET.get('company')).order_by("-created_on")
        return Campaigns.objects.filter(id__in=[])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'title': 'Campaign wise Forecasting'})
        context.update({'companies': CompanyDetails.objects.filter(is_active=True)})
        if self.request.GET.get('company'):
            end_date = Campaigns.objects.filter(
                is_active=True, status="Live",
                company=self.request.GET.get('company')).dates('end_date', 'month').last()
            if end_date:
                context.update({"reporting_dates": [x for x in month_year_iter(
                    datetime.today().month, datetime.today().year, end_date.month, end_date.year)]})
        return context


class InvoiceYetNotGeneratedView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "reports/invoice_not_yet_generated.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.company = None

    def get_queryset(self):
        today = datetime.today().date()
        campaigns = Campaigns.objects.filter(
            end_date__lte=today, invoiced_campaign__isnull=True).order_by("-created_on")
        if self.request.GET.get('company'):
            self.company = CompanyDetails.objects.get(name=self.request.GET.get('company'))
            return campaigns.filter(company=self.company).order_by("-created_on")
        return campaigns

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'company': CompanyDetails.objects.filter(is_active=True)})
        context.update({'title': 'Invoice Not Yet Generated'})
        if self.request.GET.get('company'):
            context.update({"currency": self.company})
        context.update({"is_juniors_logins": self.request.user.groups.filter(name="Juniors_logins").exists()})
        return context


class InvoiceUnderDeliveredView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "reports/invoice-under-delivered.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.company = None

    def get_queryset(self):
        today = datetime.today().date()
        io_details = IODetails.objects.annotate(
            impression=Sum('reports__impression')).filter(
            impression__lt=(F('volume') - 1000), end_date__lte=today)
        if self.request.GET.get('company'):
            self.company = CompanyDetails.objects.get(name=self.request.GET.get('company'))
            return io_details.filter(io__sub_campaign__campaign__company=self.company)
        return io_details

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'company': CompanyDetails.objects.filter(is_active=True)})
        context.update({'title': 'Invoice Under Delivered'})
        if self.request.GET.get('company'):
            context.update({"currency": self.company})
        context.update({"is_juniors_logins": self.request.user.groups.filter(name="Juniors_logins").exists()})
        return context


class InvoiceOverDeliveredView(LoginRequiredMixin, generic.ListView):
    login_url = '/'
    template_name = "reports/invoice-over-delivered.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.company = None

    def get_queryset(self):
        today = datetime.today().date()
        io_details = IODetails.objects.annotate(
            impression=Sum('reports__impression')).filter(
            impression__gt=(F('volume') + 1000), end_date__lte=today)
        if self.request.GET.get('company'):
            self.company = CompanyDetails.objects.get(name=self.request.GET.get('company'))
            return io_details.filter(io__sub_campaign__campaign__company=self.company)
        return io_details

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'Publisher_admin'
        context.update(admin_site.each_context(self.request))
        context.update({'company': CompanyDetails.objects.filter(is_active=True)})
        context.update({'title': 'Invoice Over Delivered'})
        if self.request.GET.get('company'):
            context.update({"currency": self.company})
        context.update({"is_juniors_logins": self.request.user.groups.filter(name="Juniors_logins").exists()})
        return context