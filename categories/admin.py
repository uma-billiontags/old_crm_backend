

# The Entire UI of This CRM


from django.contrib import admin
from django.contrib.admin import AdminSite  # custom admin panel 

from categories import models
from categories.models import PerformanceSubCategory, PerformanceCategory, InvoiceBankDetails, InvoiceCompanyAddress, \
    InvoiceAuthorizedPerson
from categories.models import Currency


# Custom Admin Site

# Role based dashboard 
class PublisherAdminSite(AdminSite):
    site_title = "Billiontags"
    site_header = "Billiontags"
    index_title = "Billiontags"
    site_url = None


# Step 1 — Different homepage (from categories/admin.py)
    def index(self, request, extra_context=None):
        extra_context = extra_context if extra_context else {}
        if request.user.groups.filter(name__in=["Clients"]):
            self.index_template = "client-dashboard.html"
        else:
            self.index_template = None
            if request.user.is_superuser:
                self.index_template = "welcome.html"

        return super(PublisherAdminSite, self).index(request, extra_context)
admin_site = PublisherAdminSite(name='Publisher_admin')


class EthnicityAminInline(admin.StackedInline):
    model = models.Ethnicity
    fields = ("title",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Country, site=admin_site) # registers to CUSTOM site
class CountryAdmin(admin.ModelAdmin):
    list_display = ("title", "iso_code_2", "iso_code_3", "currency_symbols", "is_active", "created_on")
    search_fields = ("title", "iso_code_2")
    inlines = [EthnicityAminInline]
    fieldsets = (
        ('Basic info', {
            'fields': (('title', "dail_code"), ("iso_code_2", "iso_code_3", "currency_symbols"), 'image', "is_active")
        }),)

    def has_delete_permission(self, request, obj=None):    # NOBODY can delete — data safety
        return False


@admin.register(models.PaymentTerms, site=admin_site)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("title", "days", "is_active", "created_on")
    search_fields = ("title",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.AdsFormats, models.Metrics, site=admin_site)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_on")
    search_fields = ("title",)

    def has_delete_permission(self, request, obj=None):
        return False


class RolesAdminInline(admin.StackedInline):
    model = models.Roles
    fields = ("title", "is_active")


@admin.register(models.Teams, site=admin_site)
class TeamsAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company", "is_active", "created_on")

    inlines = [RolesAdminInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.ModeOfPayment, site=admin_site)
class ModeOfPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active")

    def has_delete_permission(self, request, obj=None):
        return False


class MediaTypeCategoryAdminInline(admin.StackedInline):
    model = models.MediaTypeCategory
    fields = (("title", "is_active"),)
    extra = 0
    min_num = 1

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.MediaTypeSuperCategory, site=admin_site)
class MediaTypeSuperCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_on")
    search_fields = ("title",)
    list_filter = ("is_active",)
    inlines = [MediaTypeCategoryAdminInline]

    def has_delete_permission(self, request, obj=None):
        return False


class MediaTypeSubCategoryAdminInline(admin.StackedInline):
    model = models.MediaTypeSubCategory
    fields = (("title", "is_active"),)
    extra = 0
    min_num = 1

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.MediaTypeCategory, site=admin_site)
class MediaTypeCategoryAdmin(admin.ModelAdmin):
    list_display = ("category", "title", "is_active", "created_on")
    search_fields = ("title",)
    list_filter = ("is_active",)
    inlines = [MediaTypeSubCategoryAdminInline]

    def has_delete_permission(self, request, obj=None):
        return False


class PerformanceSubCategoryInline(admin.StackedInline):
    model = PerformanceSubCategory
    fields = ("title", "is_active")


@admin.register(PerformanceCategory, site=admin_site)
class PerformanceCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active")
    list_display_links = ("title", "is_active")
    inlines = [PerformanceSubCategoryInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InvoiceBankDetails, site=admin_site)
class InvoiceBankDetailsAdmin(admin.ModelAdmin):
    list_display = ("bank_name", "ifsc_code", "swift_code", "account_number", "is_active")
    list_display_links = ("bank_name", "ifsc_code", "swift_code", "account_number", "is_active")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InvoiceCompanyAddress, site=admin_site)
class InvoiceBankDetailsAdmin(admin.ModelAdmin):
    list_display = ("company_name", "address_line_1", "address_line_2", "city", "state_name", "is_active")
    list_display_links = ("company_name", "address_line_1", "address_line_2", "city", "state_name", "is_active")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InvoiceAuthorizedPerson, site=admin_site)
class InvoiceBankDetailsAdmin(admin.ModelAdmin):
    list_display = ("id", "name",)

    def has_delete_permission(self, request, obj=None):
        return False
    


# # Add this

from categories.models import AedExchangeRateMonth, AedExchangeRate    # <-- add this import
from django import forms
import calendar
from datetime import date


class AedExchangeRateInlineForm(forms.ModelForm):
    class Meta:
        model = models.AedExchangeRate
        fields = ("currency", "exchange_rate", "is_active")
           # effective_date REMOVED — auto-calculated, never shown


class AedExchangeRateInline(admin.TabularInline):
    model = models.AedExchangeRate
    form = AedExchangeRateInlineForm
    fields = ("currency", "exchange_rate", "is_active")
      # effective_date not shown to admin at all
    extra = 1

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AedExchangeRateMonth, site=admin_site)
class AedExchangeRateMonthAdmin(admin.ModelAdmin):
    list_display = ("month", "year", "created_on")
    list_filter = ("year", "month")
    inlines = [AedExchangeRateInline]

    class Media:
        css = {
            "all": ("custom_admin/css/custom.css",)
        }


    def has_delete_permission(self, request, obj=None):
        return False

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        month_obj = form.instance
        last_day = calendar.monthrange(month_obj.year, month_obj.month)[1]
        end_date = date(month_obj.year, month_obj.month, last_day)

        for instance in instances:
            instance.effective_date = end_date   # auto-set here, form never asks for it
            instance.save()

        formset.save_m2m()


@admin.register(Currency, site=admin_site)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    #print("Currency Admin Loaded")
    search_fields = ("code", "name")

    def has_delete_permission(self, request, obj=None):
        return False