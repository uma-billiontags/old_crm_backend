from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.db.models import Sum
from django.contrib import admin
from django import forms
import re  # Added by me
from django.core.validators import validate_email  # Added by me


from categories.admin import admin_site
from . import models

 

# Custom Form with Wallet Top-up

# The form adds an extra field add_wallet_points that doesn't exist in the model — it's used to top up the wallet when saving.
class CompanyDetailsForm(forms.ModelForm):
    add_wallet_points = forms.IntegerField(required=False, label="TopUp Wallet Amount",
                                           help_text="Wallet Amount Currency Based on Company's Billing Currency")
    model = models.CompanyDetails

    def clean_email(self):
        if models.User.objects.filter(username=self.cleaned_data['email']).exclude(
                username=self.instance.user.email if self.instance.pk else ""):
            raise ValidationError('Email Id already exists')
        return self.cleaned_data['email']
    
    # Added by me
    # ------------------------------------------------------------------
    # Domain validation for Default Email To / Default Email CC
    # ------------------------------------------------------------------


    
    @staticmethod
    def _extract_domain(email):
        email = (email or "").strip().lower()
        if "@" not in email:
            return None
        return email.split("@")[-1]
    
    @staticmethod
    def _validate_email_list_syntax(value):
        """
        Checked FIRST, before any domain logic. Raises ValidationError on:
          - leading/trailing comma
          - consecutive commas ("," ",")
          - an individual email ending with a full stop
          - an individual email that isn't a valid email address
        Returns the list of stripped individual emails if syntax is OK.
        """
        raw = (value or "").strip()
        if not raw:
            return []

        if raw.startswith(","):
            raise ValidationError("Email list cannot start with a comma.")
        if raw.endswith(","):
            raise ValidationError("Email list cannot end with a comma.")
        if re.search(r",\s*,", raw):
            raise ValidationError(
                "Only one comma is allowed between two email addresses "
                "(found consecutive commas)."
            )

        emails = [e.strip() for e in raw.split(",")]
        for email in emails:
            if not email:
                raise ValidationError("Found an empty email address between commas.")
            if email.endswith("."):
                raise ValidationError("'{}' should not end with a full stop.".format(email))
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("'{}' is not a valid email address.".format(email))

        return emails
    
    def _get_allowed_domains(self):
        """
        Domains this company is allowed to use for default_email_send_to /
        default_email_send_cc, derived from Company Contacts:

          1. Contacts already saved in the DB (edit mode).
          2. Contacts being added/edited right now in the Company Contacts
             inline on THIS same page submission (works for both add & edit,
             since the inline formset is part of the same POST).

        Returns an empty set if the company has no contacts at all (existing
        or new) -- callers should treat an empty set as "no restriction".
        """
        if getattr(self, "_allowed_domains_cache", None) is not None:
            return self._allowed_domains_cache

        domains = set()

        # 1. Existing saved contacts (only applies when editing)
        if self.instance and self.instance.pk:
            existing_emails = models.CompanyContacts.objects.filter(
                company=self.instance
            ).values_list("email", flat=True)
            for email in existing_emails:
                domain = self._extract_domain(email)
                if domain:
                    domains.add(domain)

        # 2. Contacts being submitted right now via the "Company Contacts" inline
        #    Default inline prefix = model_name = "companycontacts"
        data = self.data or {}
        prefix = "companycontacts"
        total_forms_key = "{}-TOTAL_FORMS".format(prefix)
        
        if total_forms_key in data:
            try:
                total_forms = int(data.get(total_forms_key) or 0)
            except (TypeError, ValueError):
                total_forms = 0

            for i in range(total_forms):
                row_prefix = "{}-{}".format(prefix, i)

                # Skip rows the user marked for deletion
                if data.get("{}-DELETE".format(row_prefix)):
                    continue

                email = data.get("{}-email".format(row_prefix), "")
                domain = self._extract_domain(email)
                if domain:
                    domains.add(domain)
        
        self._allowed_domains_cache = domains
        return domains
    
    def _clean_default_email_field(self, field_name):
        value = self.cleaned_data.get(field_name)
        if not value:
            return value

        # 1. SYNTAX CHECK FIRST — commas / full stops / basic format.
        #    If this raises, domain logic below never runs, so the user
        #    only ever sees the syntax error, not a misleading domain error.
        emails = self._validate_email_list_syntax(value)

        # 2. Domain check — only reached if syntax was clean
        allowed_domains = self._get_allowed_domains()

        # No contacts at all (existing or new) -> no restriction
        if not allowed_domains:
            return value
        
        invalid_emails = [
            e for e in emails if self._extract_domain(e) not in allowed_domains
        ]
        if invalid_emails:
            raise ValidationError(
                "These email(s) don't match any Company Contact's domain "
                "({}): {}".format(
                    ", ".join(sorted(allowed_domains)),
                    ", ".join(invalid_emails),
                )
            )
        return value
    
    def clean_default_email_send_to(self):
        return self._clean_default_email_field("default_email_send_to")

    def clean_default_email_send_cc(self):
        return self._clean_default_email_field("default_email_send_cc")


class CompanyDetailsAdminForm(CompanyDetailsForm):

    class Meta:
        model = models.CompanyDetails
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            contacts = models.CompanyContacts.objects.filter(
                company=self.instance
            )

            self.fields["default_contact_person"].queryset = contacts
            self.fields["default_contact_person"].label_from_instance = (
                lambda obj: obj.name
            )



# This function is used to display the wallet transaction history link in the admin list view. It generates a URL that points to the CompanyWalletHistory admin page, filtered by the current company. 
@admin.register(models.CompanyWalletHistory, site=admin_site)
class CompanyWalletHistoryAdminLine(admin.ModelAdmin):
    list_display = ("created_on", "description", "amount", "is_credit")
    list_filter = ("is_credit",)
    date_hierarchy = "created_on"

    # def get_queryset(self, request):
    #     qs = super(CompanyWalletHistoryAdminLine, self).get_queryset(request)
    #     if request.user.

    def has_add_permission(self, request):
        return False    # cannot add manually

    def has_delete_permission(self, request, obj=None):
        return False  # cannot delete

    def has_change_permission(self, request, obj=None):
        return False  # cannot edit

    def has_module_permission(self, request):
        return False   # hidden from sidebar!


class CompanyContactsAdminInline(admin.StackedInline):
    model = models.CompanyContacts
    fields = (("name", "phone_number"), ("email", "destination"), "digital_signature",
              "address_line_1", "address_line_2", ("country", "zipcode"), "is_active")
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False


class CompanyAddressAdminInline(admin.StackedInline):
    model = models.CompanyAddress
    fields = ("address_line_1", "address_line_2", ("country", "zipcode"), "is_active",)


# Auto-Creates Django User on Company Save

@admin.register(models.CompanyDetails, site=admin_site)
class CompanyDetailsAdmin(admin.ModelAdmin):
    

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "default_contact_person":
            object_id = request.resolver_match.kwargs.get("object_id")

            if object_id:
                kwargs["queryset"] = models.CompanyContacts.objects.filter(
                    company_id=object_id
                )

            field = super().formfield_for_foreignkey(
                db_field,
                request,
                **kwargs
            )

            field.label_from_instance = lambda obj: obj.name
            return field

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )

    list_display = ("client_id", "name", "phone_number", "payment_type", "payment_term", "country",
                    "company_billing_currency", "is_active", "wallet_amount", "credited_amount", "debited_amount",
                    "view_history")

    readonly_fields = ("created_on", "wallet_amount", 'credited_amount', "debited_amount", "client_id")
    search_fields = ("name",)
    #form = CompanyDetailsForm
    form = CompanyDetailsAdminForm
    list_filter = ("payment_type", "payment_term", "country")
    inlines = [CompanyContactsAdminInline, CompanyAddressAdminInline]
    fieldsets = (
    ("", {
        "fields": (
            ("client_id", "report_id"),
            ("name", "phone_number", "email"),
            "address_line_1",
            "address_line_2",
            ("country", "zipcode"),
            ("payment_type", "payment_term", "billing_currency"),
            ("gst_no", "cin_no"),
            ("is_domestic", "is_active", "enable_aed_invoice"),
            
            # add this fields 

            (
                "default_invoice_address",
                "default_invoice_bank",
                "default_authorized_person"
            ),

            (
                "default_contact_person",
                "invoice_type"
            ),
            
             # Added by me
            (
            "default_email_send_to",
            "default_email_send_cc",
            "show_campaign_name_in_email"
            ),  

            "created_on",
        )
    }),
    ("Wallet Details", {
        "fields": (
            ("wallet_amount", "credited_amount", "debited_amount"),
            "add_wallet_points"
        )
    })
)

    def save_model(self, request, obj, form, change):
        if not change:  # only on NEW company creation

            # Step 1: Create Django login account
            obj.user = models.User.objects.create_user(username=form.cleaned_data['email'],      # email as username
                                                       email=form.cleaned_data['email'], first_name=obj.name,
                                                       password=obj.email, is_staff=True)
            
            # Step 2: Add to Clients group (id=2)
            group = Group.objects.get(id=2)
            obj.user.groups.add(group)

            # Step 3: Auto-generate client_id
            object_id = models.CompanyDetails.objects.latest("id") if models.CompanyDetails.objects.latest(
                "id") else None
            if object_id:
                counter = int(object_id.client_id.replace("CL", ""))
            else:
                counter = 0
            obj.client_id = "CL{:05d}".format(counter + 1)
        #super(CompanyDetailsAdmin, self).save_model(request, obj, form, change)
        admin.ModelAdmin.save_model(self, request, obj, form, change)
        if form.cleaned_data.get("add_wallet_points"):
            amount = form.cleaned_data.get("add_wallet_points", 0)
            obj.wallet_amount += amount
            description = "{amount} has added to wallet from Billiontags Team".format(amount=amount)
            models.CompanyWalletHistory.objects.create(company=obj, description=description, amount=amount,
                                                       is_credit=True)
        obj.save()
    
    # Auto-Creates User for Each Contact Too
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if formset.model._meta.object_name == "CompanyContacts":
                try:
                    user = models.User.objects.get(username=instance.email)
                except:
                    user = models.User.objects.create_user(username=instance.email,
                                                           email=instance.email, first_name=instance.name,
                                                           password=instance.email, is_staff=True)
                    group = Group.objects.get(id=2)
                    user.groups.add(group)
                instance.user = user
            instance.save()
        formset.save_m2m()


    def has_delete_permission(self, request, obj=None):
        return False

    def credited_amount(self, obj):
        # SUM of all credit transactions
        return obj.wallet_history.filter(is_credit=True).aggregate(amount=Sum("amount"))['amount']   # Example: ₹75,000 total topped up

    def debited_amount(self, obj):
          # SUM of all debit transactions
        return obj.wallet_history.filter(is_credit=False).aggregate(amount=Sum("amount"))['amount']   # Example: ₹30,000 total spent

    def company_billing_currency(self, obj):
        return obj.billing_currency.currency_symbols       # Example: "₹" or "$"

    def view_history(self, obj):
         # Link to wallet transaction history
        return mark_safe("<a href='/company_details/companywallethistory/?company={}' "
                         "class='btn btn-sm btn-outline-dark'>History</a>".format(obj.id))

    credited_amount.short_description = "Total Credited Amount"
    debited_amount.short_description = "Total Debited Amount"
    company_billing_currency.short_description = "Billing Currency"
    view_history.short_description = "Wallet Transactions"



