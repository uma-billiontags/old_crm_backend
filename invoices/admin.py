import calendar
from datetime import datetime, timedelta, date
from collections import Counter

from daterangefilter.filters import PastDateRangeFilter
from django import forms
from django.contrib import admin
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import path
from django.utils.safestring import mark_safe
from django_admin_listfilter_dropdown.filters import ChoiceDropdownFilter

from categories.admin import admin_site
from insertion_order.models import Campaigns
from invoices import models, utils
from invoices.utils import perform_operation
from django.shortcuts import render


from django.http import JsonResponse
from company_details.models import CompanyDetails
from insertion_order.models import Campaigns, IODetails





# ---------------------------------------------------------------------------
# Inline Admins
# ---------------------------------------------------------------------------

class BillingLineItemsAdminInline(admin.StackedInline):
    model = models.BillingLineItems
    fields = (
        "line_item", "description", "volume",
        "unit_cost", "ad_metrics", "net_cost", "discount", "billing_cost",
    )
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False


class PaymentHistoryAdminInline(admin.StackedInline):
    model = models.PaymentHistory
    fields = (("mode_of_payment", "amount", "date", "additional_info"), ("created_on",))
    readonly_fields = ("mode_of_payment", "amount", "date", "additional_info", "created_on")
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Proxy Models (No new database tables, just different admin views based on invoice status) # Sidebar views 
# ---------------------------------------------------------------------------

# ADMIN SIDE BAR SHOWS: (INVOICE AND PAYMENT STATUS)

class NotPaid(models.Invoices): # unpaid, not overdue
    class Meta:
        proxy = True
        verbose_name = "Not Paid"
        verbose_name_plural = "Not Paid Invoices"


class NotPaidOverDue(models.Invoices): # unpaid, and overdue 
    class Meta:
        proxy = True
        verbose_name = "Not Paid and Overdue"
        verbose_name_plural = "Not Paid and Overdue Invoices"


class PartiallyPaid(models.Invoices):   # partially paid, not overdue
    class Meta:
        proxy = True
        verbose_name = "Partially Paid"
        verbose_name_plural = "Partially Paid Invoices"


class PartiallyPaidOverDue(models.Invoices): # partially paid AND overdue
    class Meta:
        proxy = True
        verbose_name = "Partially Paid and OverDue"
        verbose_name_plural = "Partially Paid and OverDue Invoices"


class FullyPaid(models.Invoices): # fully paid
    class Meta:
        proxy = True
        verbose_name = "Fully Paid"
        verbose_name_plural = "Fully Paid Invoices"


class AllInvoice(models.Invoices):  # all invoices regardless of payment status - for admin users with permission to see all invoices
    class Meta:
        proxy = True
        verbose_name = "All Invoice"
        verbose_name_plural = "All Invoices"


# ---------------------------------------------------------------------------
# Invoice Form — dynamic contact_person & campaigns filtered by company
# ---------------------------------------------------------------------------

# Smart dynamic form that filters contact_person and campaigns based on the selected company. It also takes into account the invoice date to filter campaigns active during that month, and user group (juniors see a filtered dropdown, seniors see a flat list).
# Senior logic

# class InvoiceAdminForm(forms.ModelForm):

#     invoice_month = forms.ChoiceField(choices=[])
#     class Meta:
#         model = models.Invoices
#         fields = "__all__"

#     class Media:
#         js = ("custom_admin/js/invoice_dynamic_filter.js",
#               "custom_admin/js/invoice_month.js",
#               "custom_admin/js/invoice_generate_button.js",
#              )
            

#     def __init__(self, *args, **kwargs):
#         from datetime import date

#         # `request` is injected by InvoicesAdmin.get_form() via the wrapper subclass
#         request = kwargs.pop("request", None)
#         super().__init__(*args, **kwargs)


#         months = []
#         today = date.today()
#         for i in range(24):
#             year = today.year
#             month = today.month - i

#             while month <= 0:
#                 month += 12
#                 year -= 1

#             value = f"{year}-{month:02d}-01"
#             label = date(year, month, 1).strftime("%B %Y")
#             months.append((value, label))
#         self.fields["invoice_month"].choices = months



#         # Default: all active contacts
#         if self.fields.get("contact_person"):
#             self.fields.get("contact_person").queryset = (
#                 models.CompanyContacts.objects.filter(is_active=True).select_related("company")
#             )

#             company = self._resolve_company(request)
#             invoice_date = self._resolve_invoice_date(request)
#             if company:
                
#                 # Add this (18/06)
#                 self.fields["contact_person"].initial = company.default_contact_person
#                 self.fields["from_company_address"].initial = (company.default_invoice_address)
#                 self.fields["from_company_bank"].initial = (company.default_invoice_bank)
#                 self.fields["authorized_person"].initial = (company.default_authorized_person)
                

#                 self._filter_by_company(company, invoice_date=invoice_date)

#                 if request is not None:
#                     is_junior = request.user.groups.filter(name="Juniors_logins").exists()
#                     contact_qs = self.fields["contact_person"].queryset

#                     if company:
#                         # Always scope to company first
#                         contact_qs = contact_qs.filter(company=company, is_active=True)

#                     if is_junior:
#                         # Juniors get a queryset
#                         self.fields["contact_person"].queryset = contact_qs
#                     else:
#                         # Seniors get a flat choices list
#                         self.fields["contact_person"].choices = [("", "-------")] + [
#                             (x.id, x.name) for x in contact_qs
#                         ]


#     def _resolve_company(self, request):
#         """
#         Return a CompanyDetails instance resolved from one of three sources
#         (checked in priority order):
#           1. Existing invoice instance  — edit view
#           2. POST body                  — form submitted
#           3. GET query param            — add view with ?company=42
#         """
#         from company_details.models import CompanyDetails

#         # 1. Editing an existing invoice
#         if self.instance and self.instance.pk:
#             return self.instance.company

#         # 2. POST submit
#         company_id = self.data.get("company")

#         # 3. GET ?company=42  (self.data is empty on GET requests)
#         if not company_id and request is not None:
#             company_id = request.GET.get("company")

#         if company_id:
#             try:
#                 return CompanyDetails.objects.get(pk=company_id)
#             except (CompanyDetails.DoesNotExist, ValueError):
#                 pass

#         return None

#     def _resolve_invoice_date(self, request):
#         """
#         Resolve invoice_on date from:
#           1. Existing invoice instance  — edit view
#           2. POST body                  — form submitted
#           3. GET query param            — ?invoice_on=2026-04-01
#           4. Current month              — fallback
#         """
#         # 1. Editing existing invoice
#         # if self.instance and self.instance.pk and self.instance.invoice_on:
#         #     return self.instance.invoice_on

#         if self.instance and self.instance.pk and self.instance.invoice_month:
#             #return datetime.strptime(invoice_month,"%Y-%m-%d").date()
#             return datetime.strptime(str(self.instance.invoice_month),"%Y-%m-%d").date()
#             #return self.instance.invoice_month


#         # 2. POST submit
#         # invoice_on = self.data.get("invoice_on")

#         invoice_month = self.data.get("invoice_month")

#         # 3. GET param
#         # if not invoice_on and request is not None:
#         #     invoice_on = request.GET.get("invoice_on")

#         if not invoice_month and request is not None:
#             invoice_month = request.GET.get("invoice_month")

#         # if invoice_on:
#         #     try:
#         #         return datetime.strptime(str(invoice_on), "%Y-%m-%d").date()
#         #     except ValueError:
#         #         pass
        

#         if invoice_month:
#             try:
#                 return datetime.strptime(
#                     invoice_month + "-01",
#                     "%Y-%m-%d"
#                     ).date()
#             except ValueError:
#                 pass

    

#         # 4. Fallback — current month
#         return datetime.today().date()

#     def _filter_by_company(self, company, invoice_date=None):         # When you select company = PepsiCo:
#         """Narrow contact_person and campaigns to those belonging to *company*."""

#         today = invoice_date if invoice_date else datetime.today().date()


#         start_of_month = today.replace(day=1)
#         last_day = calendar.monthrange(today.year, today.month)[1]
#         end_of_month = today.replace(day=last_day)
        
#         # Contact person shows only PepsiCo contacts
#         self.fields["contact_person"].queryset = models.CompanyContacts.objects.filter(company=company, is_active=True)
        
#         # Campaigns shows only PepsiCo campaigns 
#         # running in the invoice month
#         self.fields["campaigns"].queryset = Campaigns.objects.filter(
#             company=company, is_active=True, start_date__lte=end_of_month, end_date__gte=start_of_month).order_by("name")
        


# Django ModelForm used in the Django Admin for the Invoices model.
class InvoiceAdminForm(forms.ModelForm):
    invoice_month = forms.ChoiceField(choices=[])       # custom dropdown field of months

    #  One smart field — % or amount accept
    additional_discount = forms.CharField(   # discount field (instead of using decimel field we use text field. so use 100 or 10%)
        required=False,
        label="Offers or Discount",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. 100 or 10%",
            "id": "id_additional_discount",
            "style": "width:150px;"
        })
    )

    class Meta:
        model = models.Invoices
        fields = "__all__"

    class Media:
        js = (
            "custom_admin/js/invoice_dynamic_filter.js",
            "custom_admin/js/invoice_month.js",
            "custom_admin/js/invoice_generate_button.js",
            "custom_admin/js/invoice_discount_sync.js",
        )

    def __init__(self, *args, **kwargs):
        from datetime import date
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Edit page -- existing value show
        if self.instance and self.instance.pk:
            discount = self.instance.additional_discount or 0
            if discount > 0:
                # Direct amount-
                self.fields["additional_discount"].initial = discount

        months = []
        today = date.today()
        for i in range(24):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            value = f"{year}-{month:02d}-01"
            label = date(year, month, 1).strftime("%B %Y")
            months.append((value, label))
        self.fields["invoice_month"].choices = months

        if self.fields.get("contact_person"):
            self.fields["contact_person"].queryset = (
                models.CompanyContacts.objects.filter(is_active=True).select_related("company")
            )
            company = self._resolve_company(request)
            invoice_date = self._resolve_invoice_date(request)
            if company:
                self.fields["contact_person"].initial = company.default_contact_person
                self.fields["from_company_address"].initial = company.default_invoice_address
                self.fields["from_company_bank"].initial = company.default_invoice_bank
                self.fields["authorized_person"].initial = company.default_authorized_person
                self._filter_by_company(company, invoice_date=invoice_date)

                if request is not None:
                    is_junior = request.user.groups.filter(name="Juniors_logins").exists()
                    contact_qs = self.fields["contact_person"].queryset
                    if company:
                        contact_qs = contact_qs.filter(company=company, is_active=True)
                    if is_junior:
                        self.fields["contact_person"].queryset = contact_qs
                    else:
                        self.fields["contact_person"].choices = [("", "-------")] + [
                            (x.id, x.name) for x in contact_qs
                        ]

    def clean(self):
        cleaned_data = super().clean()
        discount_input = (cleaned_data.get("additional_discount") or "").strip()

        billing_amount = 0
        if self.instance and self.instance.pk:
            billing_amount = self.instance.billing_amount or 0

        final_discount = 0

        if discount_input:
            #  % symbol → percentage mode
            if discount_input.endswith("%"):
                try:
                    pct = float(discount_input.rstrip("%").strip())
                    if billing_amount > 0:
                        final_discount = round((billing_amount * pct) / 100, 2)
                    else:
                        final_discount = 0
                except ValueError:
                    raise forms.ValidationError(
                        "Invalid percentage value. e.g. 10%"
                    )
            #  % → direct amount mode
            else:
                try:
                    final_discount = round(float(discount_input), 2)
                except ValueError:
                    raise forms.ValidationError(
                        "Invalid discount value. Enter amount (e.g. 100) or % (e.g. 10%)"
                    )

        #  Validation — discount > billing?
        if billing_amount > 0 and final_discount > billing_amount:
            raise forms.ValidationError(
                f"Discount ({final_discount}) cannot exceed "
                f"billing amount ({billing_amount})."
            )

        cleaned_data["additional_discount"] = final_discount
        return cleaned_data

    def _resolve_company(self, request):
        """
        Return a CompanyDetails instance resolved from one of three sources
        (checked in priority order):
          1. Existing invoice instance  — edit view
          2. POST body                  — form submitted
          3. GET query param            — add view with ?company=42
        """
        from company_details.models import CompanyDetails

        # 1. Editing an existing invoice
        if self.instance and self.instance.pk:
            return self.instance.company

        # 2. POST submit
        company_id = self.data.get("company")

        # 3. GET ?company=42  (self.data is empty on GET requests)
        if not company_id and request is not None:
            company_id = request.GET.get("company")

        if company_id:
            try:
                return CompanyDetails.objects.get(pk=company_id)
            except (CompanyDetails.DoesNotExist, ValueError):
                pass

        return None

    def _resolve_invoice_date(self, request):
        """
        Resolve invoice_on date from:
          1. Existing invoice instance  — edit view
          2. POST body                  — form submitted
          3. GET query param            — ?invoice_on=2026-04-01
          4. Current month              — fallback
        """
        # 1. Editing existing invoice
        # if self.instance and self.instance.pk and self.instance.invoice_on:
        #     return self.instance.invoice_on

        if self.instance and self.instance.pk and self.instance.invoice_month:
            #return datetime.strptime(invoice_month,"%Y-%m-%d").date()
            return datetime.strptime(str(self.instance.invoice_month),"%Y-%m-%d").date()
            #return self.instance.invoice_month


        # 2. POST submit
        # invoice_on = self.data.get("invoice_on")

        invoice_month = self.data.get("invoice_month")

        # 3. GET param
        # if not invoice_on and request is not None:
        #     invoice_on = request.GET.get("invoice_on")

        if not invoice_month and request is not None:
            invoice_month = request.GET.get("invoice_month")

        # if invoice_on:
        #     try:
        #         return datetime.strptime(str(invoice_on), "%Y-%m-%d").date()
        #     except ValueError:
        #         pass


        if invoice_month:
            try:
                return datetime.strptime(
                    invoice_month + "-01",
                    "%Y-%m-%d"
                    ).date()
            except ValueError:
                pass

    

        # 4. Fallback — current month
        return datetime.today().date()

    def _filter_by_company(self, company, invoice_date=None):         # When you select company = PepsiCo:
        """Narrow contact_person and campaigns to those belonging to *company*."""

        today = invoice_date if invoice_date else datetime.today().date()


        start_of_month = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_of_month = today.replace(day=last_day)
        
        # Contact person shows only PepsiCo contacts
        self.fields["contact_person"].queryset = models.CompanyContacts.objects.filter(company=company, is_active=True)
        
        # Campaigns shows only PepsiCo campaigns 
        # running in the invoice month
        self.fields["campaigns"].queryset = Campaigns.objects.filter(
            company=company, is_active=True, start_date__lte=end_of_month, end_date__gte=start_of_month).order_by("name")
        
        today = invoice_date if invoice_date else datetime.today().date()
        start_of_month = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_of_month = today.replace(day=last_day)
        self.fields["contact_person"].queryset = models.CompanyContacts.objects.filter(
            company=company, is_active=True
        )
        self.fields["campaigns"].queryset = Campaigns.objects.filter(
            company=company,
            is_active=True,
            start_date__lte=end_of_month,
            end_date__gte=start_of_month
        ).order_by("name")    






# ---------------------------------------------------------------------------
# Client-facing Invoice Admin (read-only view for client users)
# ---------------------------------------------------------------------------

@admin.register(models.Invoices, site=admin_site)
class ClientInvoicesAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_no", "invoice_on", "billing_period", "month_of_billing",
        "due_date", "total_volume", "total_pay_amount", "total_paid",
        "status", "view_invoice",
    )
    list_display_links = None
    search_fields = ("invoice_no",)
    list_filter = (
        ("invoice_on", PastDateRangeFilter),
        ("status", ChoiceDropdownFilter),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(pk=2).exists():  # Client
            if hasattr(request.user, "company_contact_user"):
                return qs.filter(
                    company=request.user.company_contact_user.company,
                    is_approved=True,  # only show approved invoices to clients
                )
            return qs.filter(company__user=request.user, is_approved=True)
        return qs

    def billing_period(self, obj):
        return mark_safe(
            "{} <b>to</b> {}".format(
                obj.invoice_from.strftime("%d %b, %y"),
                obj.invoice_to.strftime("%d %b, %y"),
            )
        )

    billing_period.short_description = "Billing Period"

    def month_of_billing(self, obj):
        return obj.invoice_from.strftime("%b, %y")

    month_of_billing.short_description = "Month of Billing"

    def view_invoice(self, obj):
        return mark_safe(
            "<a href='/generate-invoice-new/{id}/' target='_blank' "
            "class='btn btn-sm btn-outline-secondary'>View PDF Invoice</a>".format(id=obj.id)
        )

    view_invoice.short_description = "View Invoice"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["mode_of_payment"] = models.ModeOfPayment.objects.filter(is_active=True)

        qs = self.get_queryset(request)
        totals = qs.aggregate(
            billing_amount=Sum("billing_amount"),
            paid_amount=Sum("payment_history__amount"),
            discount_applied=Sum("additional_discount"),
        )

        billing_amount = totals["billing_amount"] or 0
        paid_amount = totals["paid_amount"] or 0
        discount_applied = totals["discount_applied"] or 0

        extra_context.update(
            total_invoice=round(billing_amount, 2),
            total_invoice_paid_amount=round(paid_amount, 2),
            total_invoice_balance_amount=round(billing_amount - paid_amount, 2),
            total_invoice_discount_applied=round(discount_applied, 2),
        )
        return super().changelist_view(request, extra_context=extra_context)


# ---------------------------------------------------------------------------
# Main Invoice Admin (staff view)
# ---------------------------------------------------------------------------

@admin.register(NotPaid, NotPaidOverDue, PartiallyPaid, PartiallyPaidOverDue, FullyPaid, AllInvoice, site=admin_site)
class InvoicesAdmin(admin.ModelAdmin):
   
    search_fields = ("invoice_no",)
    date_hierarchy = "invoice_on"
    change_list_template = "invoice_list_template.html"
    inlines = [BillingLineItemsAdminInline, PaymentHistoryAdminInline]
    filter_horizontal = ("campaigns",)

    fieldsets = (
        (None, {
            "fields": (
                #("invoice_on", "company", "contact_person"),
                ("invoice_month", "company", "contact_person"),
                ("additional_discount", "gst", "vat_tax"),
                ("from_company_address", "from_company_bank", "authorized_person"),
                "campaigns",

            )
        }),
    )

    # ------------------------------------------------------------------
    # Inject request into InvoiceAdminForm
    # ------------------------------------------------------------------

    def get_form(self, request, obj=None, **kwargs):
        """
        Wraps InvoiceAdminForm in a subclass that automatically passes
        `request` as a kwarg, giving the form access to both
        request.GET (?company=42) and request.POST.
        """
        kwargs.setdefault("form", InvoiceAdminForm)
        FormClass = super().get_form(request, obj, **kwargs)

        _request = request  # capture in closure

        class InvoiceAdminFormWithRequest(FormClass):
            def __init__(self, *args, **inner_kwargs):
                inner_kwargs.setdefault("request", _request)
                super().__init__(*args, **inner_kwargs)

        return InvoiceAdminFormWithRequest

    # ------------------------------------------------------------------
    # List display — differs for client vs staff
    # ------------------------------------------------------------------

    def get_list_display(self, request):
        base = (
            "invoice_no", "company", "contact_person", "invoice",
            "due_date", "total_amount", "additional_discount",
            "additional_discount_per", "total_discount",
            "total_pay_amount", "total_paid", "balance_amount",
        )
        if request.user.groups.filter(pk=2).exists():
            return base + ("view_io",)
        return base + ("invoice_approval", "view_io", "update_payment")

    # ------------------------------------------------------------------
    # Extra URLs
    # ------------------------------------------------------------------

    def get_urls(self):
        custom = [
            path("invoice-reconciliation/", self.admin_site.admin_view(self.invoice_reconciliation), name="invoice_reconciliation",),
            path("generate-auto-invoice/", self.admin_site.admin_view(self.generate_auto_invoice), name="generate_auto_invoice"),
            path("generate-monthly-invoices/", self.admin_site.admin_view(self.generate_monthly_invoices), name="generate_monthly_invoices"),  # ✅ add this
            path("<int:pk>/update_payment/", self.admin_site.admin_view(self.update_payment_view)),
            path("<int:pk>/approve-invoice/", self.admin_site.admin_view(self.approve_invoice_view)),
        ]
        return custom + super().get_urls()
    
    
    #invoice reconciliation view for admin users to see the invoice summary and reconciliation report
    def invoice_reconciliation(self, request):
        print("Invoice Reconciliation View Called")
        context = dict(
            self.admin_site.each_context(request),
        )

        return render(request, "reports/invoice_summary_reconciliation.html",context,)
    




    # ------------------------------------------------------------------
    # Custom views
    # ------------------------------------------------------------------

    # Approve invoice (manager action) — sets is_approved=True, which makes the invoice visible to client users in their portal
    def approve_invoice_view(self, request, pk):
        invoice = utils.int_to_invoice(pk)
        invoice.is_approved = True
        invoice.save(update_fields=["is_approved"])
        return redirect("../..")
    

    # CRM INVOICE AUTOMATION
    def create_invoice(
            self,
            company,
            invoice_month,
            campaigns,
            contact_person=None,  # Add this field (22/06/2026)
            existing_invoice=None # Add this field 
    ):
        if existing_invoice:
            invoice = existing_invoice
        else:
            invoice = models.Invoices()

        last_day = calendar.monthrange(invoice_month.year,invoice_month.month)[1]
        

        invoice.company = company
        invoice.invoice_type = company.invoice_type

        invoice.contact_person = (contact_person if contact_person else company.default_contact_person) # add this field
        invoice.from_company_address = (company.default_invoice_address)
        invoice.from_company_bank = (company.default_invoice_bank)
        invoice.authorized_person = (company.default_authorized_person)

        invoice.invoice_month = invoice_month

        invoice.invoice_on = date(
            invoice_month.year,
            invoice_month.month,
            last_day
        )

        invoice.invoice_from = date(
            invoice_month.year,
            invoice_month.month,
            1
        )

        invoice.invoice_to = date(
            invoice_month.year,
            invoice_month.month,
            last_day
        )

        payment_term_days = 7

        if company.payment_term:
            payment_term_days = (
                company.payment_term.days
            )

        invoice.due_date = (
            invoice.invoice_to +
            timedelta(days=payment_term_days)
        )

        # Generate invoice number only for NEW invoices 
        if not invoice.pk:
            invoice.invoice_no = self._generate_invoice_no(invoice)
        invoice.save()

        # Remove the old lineitems only when regenerating 
        if existing_invoice:
            models.BillingLineItems.objects.filter(invoice=invoice).delete()

        invoice.campaigns.set(campaigns)

        utils.invoice_amount_calculation(invoice)

        return invoice
    

    def generate_auto_invoice(self, request):
        company_id = request.POST.get("company")
        invoice_month = request.POST.get("invoice_month")

        if not company_id:
            return JsonResponse({"status": False,"message": "Select company"})

        company = CompanyDetails.objects.get(pk=company_id)
        invoice_month = datetime.strptime(invoice_month,"%Y-%m-%d").date()
        
        start_date = invoice_month.replace(day=1)
        last_day = calendar.monthrange(invoice_month.year,invoice_month.month)[1]
        end_date = invoice_month.replace(day=last_day)

        # Get all the active campaigns for that month 
        campaigns = Campaigns.objects.filter(
            company=company,
            is_active=True,
            start_date__lte=end_date,
            end_date__gte=start_date
        )

        if not campaigns.exists():
            return JsonResponse({
                "status": False,
                "message": "No active campaigns found for this company in the selected month"
            })
        
        
        created_count = 0
        updated_count = 0 

        # ===============================
        # SINGLE TYPE
        # ===============================
        if company.invoice_type == "single":
            # Priority 1: company default
            if company.default_contact_person:
                contact_person = company.default_contact_person
            
            # Priority 2: most common IO contact person
            else:
                contact_person = None  
                contact_person_ids = list(
                    IODetails.objects.filter(
                        io__sub_campaign__campaign__in=campaigns,
                        reports__report_on__year=invoice_month.year,
                        reports__report_on__month=invoice_month.month,
                        io__contact_person__isnull=False
                    ).values_list("io__contact_person_id", flat=True)
                )
                if contact_person_ids:
                    most_common_contact_id = Counter(contact_person_ids).most_common(1)[0][0]
                    contact_person = models.CompanyContacts.objects.filter(
                        pk=most_common_contact_id
                    ).first()

            from django.db.models import Q
            month_start = invoice_month.replace(day=1)
            last_day = calendar.monthrange(invoice_month.year, invoice_month.month)[1]
            month_end = invoice_month.replace(day=last_day)

            existing_invoice = models.Invoices.objects.filter(
                company=company,
                #invoice_month=invoice_month,
                invoice_type="single"
            ).filter(
                Q(invoice_month=month_start) |
                Q(
                    invoice_month__isnull=True,
                    invoice_on__gte=month_start,
                    invoice_on__lte=month_end
                )
            ).first()
            

            self.create_invoice(
                company=company,
                invoice_month=invoice_month,
                campaigns=campaigns,
                contact_person=contact_person,
                existing_invoice=existing_invoice
            )
            return JsonResponse({
                "status": True,
                "message": "Invoice updated" if existing_invoice else "1 Invoice generated"
            })
        

        # ===============================
        # MULTIPLE TYPE
        # ===============================
        else:
        
            for campaign in campaigns:
                existing_invoice = models.Invoices.objects.filter(
                    company=company,
                    invoice_month=invoice_month,
                    invoice_type="multiple",
                    campaigns__id=campaign.id
                ).distinct().first()


                has_data = IODetails.objects.filter(
                    io__sub_campaign__campaign=campaign,
                    reports__report_on__year=invoice_month.year,
                    reports__report_on__month=invoice_month.month
                ).exists()

                if not has_data:
                    continue

                # Priority 1: company default
                if company.default_contact_person:
                    contact_person = company.default_contact_person
                
                # Priority 2: IO contact person
                else:
                    contact_person = None
                    io_detail = IODetails.objects.filter(
                        io__sub_campaign__campaign=campaign,
                        reports__report_on__year=invoice_month.year,
                        reports__report_on__month=invoice_month.month
                    ).select_related("io__contact_person").first()

                    if io_detail and io_detail.io and io_detail.io.contact_person:
                        contact_person = io_detail.io.contact_person
                self.create_invoice(
                    company,
                    invoice_month,
                    [campaign],
                    contact_person=contact_person,
                    existing_invoice=existing_invoice
                )

                if existing_invoice:
                    updated_count += 1
                else:
                    created_count += 1

            if created_count == 0 and updated_count == 0:
                return JsonResponse({"status": False, "message": "No billable campaigns found"})

            if created_count > 0 and updated_count == 0:
                message = f"{created_count} invoice(s) generated"
            elif updated_count > 0 and created_count == 0:
                message = f"{updated_count} invoice(s) updated"
            else:
                message = f"{created_count} invoice(s) generated, {updated_count} invoice(s) updated"

            return JsonResponse({"status": True, "message": message})
                


    # def generate_monthly_invoices(self, request):
    #     invoice_month = request.POST.get("invoice_month")
    #     if not invoice_month:
    #         return JsonResponse({
    #             "status": False,
    #             "message": "Select invoice month"
    #         })

    #     try:
    #         invoice_month = datetime.strptime(invoice_month, "%Y-%m-%d").date()
    #     except ValueError:
    #         return JsonResponse({
    #             "status": False,
    #             "message": "Invalid invoice month format"
    #         })

    #     start_date = invoice_month.replace(day=1)
    #     last_day = calendar.monthrange(invoice_month.year, invoice_month.month)[1]
    #     end_date = invoice_month.replace(day=last_day)

    #     # Get all active companies
    #     companies = CompanyDetails.objects.filter(is_active=True)

    #     total_created = 0
    #     total_updated = 0
    #     skipped_companies = []

    #     for company in companies:

    #         # Get active campaigns for this company in the selected month
    #         campaigns = Campaigns.objects.filter(
    #             company=company,
    #             is_active=True,
    #             start_date__lte=end_date,
    #             end_date__gte=start_date
    #         )

    #         if not campaigns.exists():
    #             skipped_companies.append(f"{company.name} (no campaigns)")
    #             continue

    #         # ===============================
    #         # SINGLE INVOICE — one invoice for all campaigns
    #         # ===============================
    #         if company.invoice_type == "single":

    #             # Check if ANY campaign has IO data this month
    #             has_any_data = IODetails.objects.filter(
    #                 io__sub_campaign__campaign__in=campaigns,
    #                 reports__report_on__year=invoice_month.year,
    #                 reports__report_on__month=invoice_month.month
    #             ).exists()

    #             if not has_any_data:
    #                 skipped_companies.append(f"{company.name} (no IO data)")
    #                 continue

    #             # if company.default_contact_person:
    #             #     contact_person = company.default_contact_person
    #             # else:
    #             #     contact_person_ids = list(
    #             #         IODetails.objects.filter(
    #             #             io__sub_campaign__campaign__in=campaigns,
    #             #             reports__report_on__year=invoice_month.year,
    #             #             reports__report_on__month=invoice_month.month,
    #             #             io__contact_person__isnull=False
    #             #         ).values_list("io__contact_person_id", flat=True)
    #             #     )
    #             #     contact_person = None
    #             #     if contact_person_ids:
    #             #         most_common_id = Counter(contact_person_ids).most_common(1)[0][0]
    #             #         contact_person = models.CompanyContacts.objects.filter(
    #             #             pk=most_common_id
    #             #         ).first()




    #             # Find the most common contact_person across all IO details this month
    #             contact_person = None
    #             contact_person_ids = list(
    #                 IODetails.objects.filter(
    #                     io__sub_campaign__campaign__in=campaigns,
    #                     reports__report_on__year=invoice_month.year,
    #                     reports__report_on__month=invoice_month.month,
    #                     io__contact_person__isnull=False
    #                 ).values_list("io__contact_person_id", flat=True)
    #             )

    #             if contact_person_ids:
    #                 most_common_id = Counter(contact_person_ids).most_common(1)[0][0]
    #                 contact_person = models.CompanyContacts.objects.filter(
    #                     pk=most_common_id
    #                 ).first()

    #             # Fallback to company default if still None
    #             if not contact_person:
    #                 contact_person = company.default_contact_person

    #             # Check for existing invoice to update
    #             existing_invoice = models.Invoices.objects.filter(
    #                 company=company,
    #                 invoice_month=invoice_month,
    #                 invoice_type="single"
    #             ).first()

    #             self.create_invoice(
    #                 company=company,
    #                 invoice_month=invoice_month,
    #                 campaigns=campaigns,
    #                 contact_person=contact_person,
    #                 existing_invoice=existing_invoice
    #             )

    #             if existing_invoice:
    #                 total_updated += 1
    #             else:
    #                 total_created += 1

    #         # ===============================
    #         # MULTIPLE INVOICES — one invoice per campaign
    #         # ===============================
    #         else:
    #             company_had_any_invoice = False

    #             for campaign in campaigns:

    #                 # Skip campaign if no IO data this month
    #                 has_data = IODetails.objects.filter(
    #                     io__sub_campaign__campaign=campaign,
    #                     reports__report_on__year=invoice_month.year,
    #                     reports__report_on__month=invoice_month.month
    #                 ).exists()

    #                 if not has_data:
    #                     continue  # skip this campaign, check next


    #                 # if company.default_contact_person:
    #                 #     contact_person = company.default_contact_person
    #                 # else:
    #                 #     io_detail = IODetails.objects.filter(
    #                 #         io__sub_campaign__campaign=campaign,
    #                 #         reports__report_on__year=invoice_month.year,
    #                 #         reports__report_on__month=invoice_month.month
    #                 #     ).select_related("io__contact_person").first()

    #                 #     contact_person = None
    #                 #     if io_detail and io_detail.io and io_detail.io.contact_person:
    #                 #         contact_person = io_detail.io.contact_person





    #                 # Get contact_person from IO detail
    #                 contact_person = None
    #                 io_detail = IODetails.objects.filter(
    #                     io__sub_campaign__campaign=campaign,
    #                     reports__report_on__year=invoice_month.year,
    #                     reports__report_on__month=invoice_month.month
    #                 ).select_related("io__contact_person").first()

    #                 if io_detail and io_detail.io and io_detail.io.contact_person:
    #                     contact_person = io_detail.io.contact_person

    #                 # Fallback to company default if still None
    #                 if not contact_person:
    #                     contact_person = company.default_contact_person

    #                 # Check for existing invoice for this specific campaign
    #                 existing_invoice = models.Invoices.objects.filter(
    #                     company=company,
    #                     invoice_month=invoice_month,
    #                     invoice_type="multiple",
    #                     campaigns__id=campaign.id
    #                 ).distinct().first()

    #                 self.create_invoice(
    #                     company=company,
    #                     invoice_month=invoice_month,
    #                     campaigns=[campaign],
    #                     contact_person=contact_person,
    #                     existing_invoice=existing_invoice
    #                 )

    #                 company_had_any_invoice = True

    #                 if existing_invoice:
    #                     total_updated += 1
    #                 else:
    #                     total_created += 1

    #             if not company_had_any_invoice:
    #                 skipped_companies.append(f"{company.name} (no IO data in any campaign)")

    #     # ===============================
    #     # Final response
    #     # ===============================
    #     if total_created == 0 and total_updated == 0:
    #         return JsonResponse({
    #             "status": False,
    #             "message": (
    #                 f"No invoices generated. "
    #                 f"Skipped {len(skipped_companies)} company(s): "
    #                 f"{', '.join(skipped_companies)}"
    #             )
    #         })

    #     parts = []
    #     if total_created > 0:
    #         parts.append(f"{total_created} invoice(s) created")
    #     if total_updated > 0:
    #         parts.append(f"{total_updated} invoice(s) updated")
    #     if skipped_companies:
    #         parts.append(f"{len(skipped_companies)} company(s) skipped")

    #     return JsonResponse({
    #         "status": True,
    #         "message": ", ".join(parts)
    #     })

    
    def generate_monthly_invoices(self, request):
        from django.db.models import Q

        invoice_month = request.POST.get("invoice_month")
        if not invoice_month:
            return JsonResponse({"status": False, "message": "Select invoice month"})

        try:
            invoice_month = datetime.strptime(invoice_month, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"status": False, "message": "Invalid invoice month format"})

        # Month range — campaign filter + duplicate check both use pannuvom
        month_start = invoice_month.replace(day=1)
        last_day = calendar.monthrange(invoice_month.year, invoice_month.month)[1]
        month_end = invoice_month.replace(day=last_day)

        companies = CompanyDetails.objects.filter(is_active=True)

        total_created = 0
        total_updated = 0
        skipped_companies = []

        for company in companies:

            campaigns = Campaigns.objects.filter(
                company=company,
                is_active=True,
                start_date__lte=month_end,
                end_date__gte=month_start
            )

            if not campaigns.exists():
                skipped_companies.append(f"{company.name} (no campaigns)")
                continue

            # ===============================
            # SINGLE — one invoice for all campaigns
            # ===============================
            if company.invoice_type == "single":

                has_any_data = IODetails.objects.filter(
                    io__sub_campaign__campaign__in=campaigns,
                    reports__report_on__year=invoice_month.year,
                    reports__report_on__month=invoice_month.month
                ).exists()

                if not has_any_data:
                    skipped_companies.append(f"{company.name} (no IO data)")
                    continue

                #  Priority 1: company default
                #  Priority 2: most common IO contact
                if company.default_contact_person:
                    contact_person = company.default_contact_person
                else:
                    contact_person = None
                    contact_person_ids = list(
                        IODetails.objects.filter(
                            io__sub_campaign__campaign__in=campaigns,
                            reports__report_on__year=invoice_month.year,
                            reports__report_on__month=invoice_month.month,
                            io__contact_person__isnull=False
                        ).values_list("io__contact_person_id", flat=True)
                    )
                    if contact_person_ids:
                        most_common_id = Counter(contact_person_ids).most_common(1)[0][0]
                        contact_person = models.CompanyContacts.objects.filter(
                            pk=most_common_id
                        ).first()

                #  Duplicate check — old (NULL) + new records both handle
                existing_invoice = models.Invoices.objects.filter(
                    company=company,
                    invoice_type="single"
                ).filter(
                    Q(invoice_month=month_start) |
                    Q(
                        invoice_month__isnull=True,
                        invoice_on__gte=month_start,
                        invoice_on__lte=month_end
                    )
                ).first()

                self.create_invoice(
                    company=company,
                    invoice_month=invoice_month,
                    campaigns=campaigns,
                    contact_person=contact_person,
                    existing_invoice=existing_invoice
                )

                if existing_invoice:
                    total_updated += 1
                else:
                    total_created += 1

            # ===============================
            # MULTIPLE — one invoice per campaign
            # ===============================
            else:
                company_had_any_invoice = False

                for campaign in campaigns:

                    has_data = IODetails.objects.filter(
                        io__sub_campaign__campaign=campaign,
                        reports__report_on__year=invoice_month.year,
                        reports__report_on__month=invoice_month.month
                    ).exists()

                    if not has_data:
                        continue

                    # ✅ Priority 1: company default
                    # ✅ Priority 2: IO contact person
                    if company.default_contact_person:
                        contact_person = company.default_contact_person
                    else:
                        contact_person = None
                        io_detail = IODetails.objects.filter(
                            io__sub_campaign__campaign=campaign,
                            reports__report_on__year=invoice_month.year,
                            reports__report_on__month=invoice_month.month
                        ).select_related("io__contact_person").first()

                        if io_detail and io_detail.io and io_detail.io.contact_person:
                            contact_person = io_detail.io.contact_person

                    # ✅ Duplicate check — old (NULL) + new records both handle
                    existing_invoice = models.Invoices.objects.filter(
                        company=company,
                        invoice_type="multiple",
                        campaigns__id=campaign.id
                    ).filter(
                        Q(invoice_month=month_start) |
                        Q(
                            invoice_month__isnull=True,
                            invoice_on__gte=month_start,
                            invoice_on__lte=month_end
                        )
                    ).distinct().first()

                    self.create_invoice(
                        company=company,
                        invoice_month=invoice_month,
                        campaigns=[campaign],
                        contact_person=contact_person,
                        existing_invoice=existing_invoice
                    )

                    company_had_any_invoice = True

                    if existing_invoice:
                        total_updated += 1
                    else:
                        total_created += 1

                if not company_had_any_invoice:
                    skipped_companies.append(f"{company.name} (no IO data in any campaign)")

        # ===============================
        # Final response
        # ===============================
        if total_created == 0 and total_updated == 0:
            return JsonResponse({
                "status": False,
                "message": (
                    f"No invoices generated. "
                    f"Skipped {len(skipped_companies)} company(s): "
                    f"{', '.join(skipped_companies)}"
                )
            })

        parts = []
        if total_created > 0:
            parts.append(f"{total_created} invoice(s) created")
        if total_updated > 0:
            parts.append(f"{total_updated} invoice(s) updated")
        if skipped_companies:
            parts.append(f"{len(skipped_companies)} company(s) skipped")

        return JsonResponse({"status": True, "message": ", ".join(parts)})





    # update payment view — allows staff to add a payment transaction for the invoice. This is an inline form separate from the main invoice edit form, and is accessible via the "Update Payment" button in the list display. When a new payment is added, it also checks if the total paid amount has reached or exceeded the total payable amount, and if so, automatically updates the invoice status to "Paid".
    def update_payment_view(self, request, pk):
        if request.method == "POST":
            invoice = utils.int_to_invoice(pk)
            models.PaymentHistory.objects.create(
                mode_of_payment_id=request.POST["mode_of_payment"],
                amount=request.POST["amount"],
                date=request.POST["date"],
                invoice=invoice,
                additional_info=request.POST.get("additional_info", ""),
            )
            paid = invoice.payment_history.aggregate(amount=Sum("amount"))["amount"] or 0
             # Auto-update status
            invoice.status = "Paid" if paid >= invoice.total_pay_amount() else "Partial Paid"
            invoice.save(update_fields=["status"])
        return redirect("../..")
    
# Workflow of update_payment_view:
# Invoice total: ₹52,000

# Payment 1 recorded: ₹25,000
#   → paid(25000) < total(52000)
#   → status = "Partial Paid"

# Payment 2 recorded: ₹27,000
#   → paid(52000) >= total(52000)
#   → status = "Paid" 



    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def has_change_permission(self, request, obj=None):
        return self.model.__name__ not in ("FullyPaid", "AllInvoice")

    def has_delete_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------
    # Save logic (Auto calculation on save, auto-generate invoice number, and handle campaign-invoice relationships)
    # ------------------------------------------------------------------
 

 # Add this line (18/06)
    def save_model(self, request, obj, form, change):
        
        if obj.invoice_month:
            year = obj.invoice_month.year
            month = obj.invoice_month.month

            last_day = calendar.monthrange(year, month)[1]
            obj.invoice_on = date(
                year,
                month,
                last_day
                )
        print("invoice_month =", obj.invoice_month)
        print("invoice_on =", obj.invoice_on)


        # Step 1: Auto-set billing period from invoice date (e.g. invoice_on = June 1 --> invoice_from = June 1, invoice_to = June 30)
        last_day = calendar.monthrange(obj.invoice_on.year, obj.invoice_on.month)[1]
        obj.invoice_from = datetime(obj.invoice_on.year, obj.invoice_on.month, 1)
        obj.invoice_to = datetime(obj.invoice_on.year, obj.invoice_on.month, last_day)
        payment_term_days = 7
        if obj.company.payment_term:

            # Step 2: Auto-calculate due date from payment terms (e.g. invoice_to = June 30 + payment_term = 7 days --> due_date = July 7)
            payment_term_days = obj.company.payment_term.days
        obj.due_date = obj.invoice_to + timedelta(days=payment_term_days)

        deleted_set = None

         # Step 3: Auto-generate invoice number

        # if not change:
        #     obj.invoice_no = self._generate_invoice_no(obj.company)  # Add this line (18/06)

        if not change:
            obj.invoice_no = self._generate_invoice_no(obj)   # "BTU2600001"
        else:
            old_campaigns = obj.campaigns.all()
            new_campaigns = form.cleaned_data["campaigns"].all()
            deleted_set, _ = perform_operation(old_campaigns, new_campaigns)
        
   
        

        # Step 4: Calculate all line item amounts
        super().save_model(request, obj, form, change)
        utils.invoice_amount_calculation(obj, deleted_set)

    @staticmethod
    def _generate_invoice_no(obj):
        prefix = "BT{}{}".format("U" if obj.company.is_domestic else "U", datetime.today().strftime("%y"))
        last = models.Invoices.objects.filter(invoice_no__icontains=prefix).last()
        count = int(last.invoice_no.replace(prefix, "")) if last else 0
        return "{}{:04d}".format(prefix, count + 1)

# Add this (18/06)
    # @staticmethod
    # def _generate_invoice_no(company):
    #     prefix = "BT{}{}".format("U" if company.is_domestic else "U", datetime.today().strftime("%y"))
    #     last = models.Invoices.objects.filter(invoice_no__icontains=prefix).last()
    #     count = int(last.invoice_no.replace(prefix, "")) if last else 0
    #     return "{}{:04d}".format(prefix, count + 1)

    # ------------------------------------------------------------------
    # Queryset filtering by proxy model name
    # ------------------------------------------------------------------
    

    # Each proxy model (NotPaid, PartiallyPaid, etc) corresponds to a specific filter on the base Invoices queryset. By checking self.model.__name__, we can determine which proxy model is being accessed and apply the appropriate filters to return only the relevant invoices for that view.
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        today = datetime.today()

        if request.user.groups.filter(pk=2).exists():
            qs = qs.filter(company__user=request.user)

        filters = {   # each filter automatically 
            "NotPaid": dict(status="Not Paid", due_date__gte=today),
            "NotPaidOverDue": dict(status="Not Paid", due_date__lt=today),
            "PartiallyPaid": dict(status="Partial Paid", due_date__gte=today),
            "PartiallyPaidOverDue": dict(status="Partial Paid", due_date__lt=today),
            "FullyPaid": dict(status="Paid"),
        }
        return qs.filter(**filters.get(self.model.__name__, {}))

    # ------------------------------------------------------------------
    # Changelist aggregates
    # ------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["mode_of_payment"] = models.ModeOfPayment.objects.filter(is_active=True)

        qs = self.get_queryset(request)
        totals = qs.aggregate(
            billing_amount=Sum("billing_amount"),
            paid_amount=Sum("payment_history__amount"),
            discount_applied=Sum("additional_discount"),
        )

        billing_amount_by_currency = (
            qs.values(
                "company__billing_currency__currency_symbols",
                "company__billing_currency__iso_code_3",
            ).annotate(
                billing_amount=Sum("billing_amount"),
                discount=Sum("additional_discount"),
                payment=Coalesce(Sum("payment_history__amount"), 0),
            )
        )

        billing_amount = totals["billing_amount"] or 0
        paid_amount = totals["paid_amount"] or 0
        discount_applied = totals["discount_applied"] or 0

        extra_context.update(
            total_invoice=round(billing_amount, 2),
            total_invoice_paid_amount=round(paid_amount, 2),
            total_invoice_balance_amount=round(billing_amount - paid_amount, 2),
            total_invoice_discount_applied=round(discount_applied, 2),
            invoice=billing_amount_by_currency,
        )
        return super().changelist_view(request, extra_context=extra_context)

    # ------------------------------------------------------------------
    # Custom list columns
    # ------------------------------------------------------------------

    def invoice(self, obj):
        return mark_safe(
            "{} <b>to</b> {}".format(
                obj.invoice_from.strftime("%d %b, %y"),
                obj.invoice_to.strftime("%d %b, %y"),
            )
        )

    invoice.short_description = "Invoice Period"

    def view_io(self, obj):
        return mark_safe(
            "<a href='/generate-invoice-new/{id}/' target='_blank' "
            "class='btn btn-sm btn-outline-secondary'>View PDF Invoice</a>".format(id=obj.id)
        )

    view_io.short_description = "View Invoice"

    def invoice_approval(self, obj):
        if not obj.is_approved:
            return mark_safe(
                "<a href='{id}/approve-invoice/' "
                "class='btn btn-sm btn-outline-secondary'>Approve Invoice</a>".format(id=obj.id)
            )
        return mark_safe("<span class='btn btn-sm btn-outline-success'>Approved</span>")

    invoice_approval.short_description = "Manager Approval"

 
    
    def update_payment(self, obj):
        return mark_safe(
            "<a class='btn btn-sm btn-outline-secondary' "
            "onClick=\"confirmModal(1, {id}, {balance})\">Update Payment</a>".format(
                id=obj.id, balance=obj.balance_amount()
            )
        )

    update_payment.short_description = "Update Payment"













































