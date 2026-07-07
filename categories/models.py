import base64
import os

from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.text import slugify

TEAM_CHOICES = (
    ("Billiontags", "Billiontags"),
    ("Client", "Client")
)


def upload_to_title_images(instance, filename):
    basename, file_extension = os.path.splitext(filename)
    slug = slugify(instance.title)
    folder_name = slugify(instance.__class__.__name__)

    file_extension = file_extension if file_extension else ".jpg"

    new_filename = "%s%s" % (slug, file_extension)

    return "product/%s/%s/%s" % (folder_name, slug, new_filename)


class Country(models.Model):
    objects = None
    title = models.CharField(max_length=120, unique=True)
    dail_code = models.IntegerField()
    iso_code_2 = models.CharField(max_length=2, validators=[MinLengthValidator(2)], verbose_name="Country Code")
    iso_code_3 = models.CharField(max_length=3, validators=[MinLengthValidator(3)], verbose_name="Currency Code")
    currency_symbols = models.CharField(max_length=5)
    image = models.ImageField(upload_to=upload_to_title_images, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_country"        # Db table name 
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.title


# Tracks ethnicities per country — used for audience targeting in ad campaigns.
class Ethnicity(models.Model):
    objects = None
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_country_ethnicity"
        verbose_name = "Ethnicity"
        verbose_name_plural = "Ethnicity"
        unique_together = ("country", "title")     # same ethnicity name can't repeat per country

    def __str__(self):
        return self.title

# Used in invoices to define when payment is due.
class PaymentTerms(models.Model):
    objects = None
    title = models.CharField(max_length=50, unique=True)
    days = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_payment_terms"
        verbose_name = "Payment Term"
        verbose_name_plural = 'Payment Terms'

    def __str__(self):
        return self.title

# e.g. Banner, Video, Native Simple lookup table for ad format types used in insertion orders.
class AdsFormats(models.Model):
    objects = None
    title = models.CharField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_ads_formats"
        verbose_name = "Ad Format"
        verbose_name_plural = "Ad Format"

    def __str__(self):
        return self.title

#  e.g. CPM, CPC, CPL KPI metrics used in campaigns.
class Metrics(models.Model):
    objects = None
    title = models.CharField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_metrics"
        verbose_name = "Metrics"
        verbose_name_plural = "Metrics"

    def __str__(self):
        return self.title


# 3 level----> SuperCategory:  Digital
#                 Category:   Social Media
#                     SubCategory: Facebook, Instagram, YouTube

class MediaTypeSuperCategory(models.Model):
    objects = None
    title = models.CharField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_media_type_super_category"
        verbose_name = "Media Type Super Category"
        verbose_name_plural = "Media Type Super Categories"

    def __str__(self):
        return self.title


class MediaTypeCategory(models.Model):
    objects = None
    category = models.ForeignKey(MediaTypeSuperCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_media_type_category"
        verbose_name = "Media Type Category"
        verbose_name_plural = "Media Type Categories"

    def __str__(self):
        return self.title


class MediaTypeSubCategory(models.Model):
    objects = None
    category = models.ForeignKey(MediaTypeCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_media_type_sub_category"
        verbose_name = "Media Type Sub Category"
        verbose_name_plural = "Media Type Sub Categories"

    def __str__(self):
        return "{} - {} - {}".format(self.category.category.title, self.category.title, self.title)


# Teams + Roles — Internal org structure
class Teams(models.Model):
    objects = None
    title = models.CharField(max_length=120)
    company = models.CharField(max_length=20, choices=TEAM_CHOICES)   # Teams + Roles — Internal org structure
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_teams_details"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        unique_together = ("title", "company")

    def __str__(self):
        return self.title

# (e.g. Team: Sales → Roles: Manager, Executive)
class Roles(models.Model):
    objects = None
    team = models.ForeignKey(Teams, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_teams_role"
        verbose_name = "Teams Role"
        unique_together = ("team", "title")

    def __str__(self):
        return "{} -{}".format(self.team, self.title)

# e.g. Bank Transfer, Cheque, UPI
class ModeOfPayment(models.Model):
    objects = None
    title = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tbl_mode_of_payment"
        verbose_name = "Mode of Payment"
        verbose_name_plural = "Mode of Payment"

    def __str__(self):
        return self.title


# PerformanceCategory + PerformanceSubCategory — 2-level hierarchy
# Used to categorize campaign performance metrics.

class PerformanceCategory(models.Model):
    objects = None
    title = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tbl_performance_category"

    def __str__(self):
        return self.title


class PerformanceSubCategory(models.Model):
    objects = None
    category = models.ForeignKey(PerformanceCategory, on_delete=models.CASCADE, related_name="subcategory")
    title = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tbl_item_performance"

    def __str__(self):
        return self.title

# Multiple bank accounts supported (Indian + international — IFSC for India, SWIFT/IBAN for international).
class InvoiceBankDetails(models.Model):
    objects = None
    nick_name = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=100, unique=True)
    swift_code = models.CharField(max_length=100, blank=True, null=True)
    iban_number = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=100, unique=True)
    bank_address = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tbl_invoice_bank_details"

    def __str__(self):
        return "{}-{}".format(self.bank_name, self.nick_name)


#  Billing address with Indian tax numbers
class InvoiceCompanyAddress(models.Model):
    objects = None
    company_name = models.CharField(max_length=200)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state_name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=30, blank=True, null=True)
    gst_number = models.CharField(max_length=80, blank=True, null=True)
    cin_number = models.CharField(max_length=80, blank=True, null=True)
    tan_number = models.CharField(max_length=80, blank=True, null=True)
    trn_number = models.CharField(max_length=80, blank=True, null=True)
    license_number = models.CharField(max_length=80, blank=True, null=True)
    sac_number = models.CharField(max_length=80, blank=True, null=True)
    ct_number = models.CharField(max_length=80, blank=True, null=True)
    is_active = models.BooleanField(default=True, )

    class Meta:
        db_table = "tbl_invoice_company_details"

    def __str__(self):
        return self.company_name


class InvoiceAuthorizedPerson(models.Model):
    objects = None
    name = models.CharField(max_length=255, unique=True)
    person_sign = models.ImageField(upload_to="authorized_person", verbose_name="Person Sign")   # signature image
    company_logo_sign = models.ImageField(upload_to="authorized_person_logo", verbose_name="Company Seal") # company seal image

    def __str__(self):
        return self.name

    def person_sign_data(self):
        with open(self.person_sign.path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
             # converts image to base64 string
            return "data:image/png;base64," + encoded_string.decode('utf-8')

    def company_logo_sign_data(self):
        with open(self.company_logo_sign.path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            return "data:image/png;base64," + encoded_string.decode('utf-8')



# Add this 
import calendar
from django.core.validators import MinValueValidator

# ... existing imports already unga file la irukku

class AedExchangeRateMonth(models.Model):
    objects = None

    MONTH_CHOICES = (
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December"),
    )

    month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    year = models.PositiveSmallIntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_aed_exchange_rate_month"
        verbose_name = "AED Exchange Rate Month"
        verbose_name_plural = "AED Exchange Rate Months"
        unique_together = ("month", "year")
        ordering = ("year", "month")

    def __str__(self):
        return "{} {}".format(dict(self.MONTH_CHOICES).get(self.month), self.year)


class AedExchangeRate(models.Model):
    objects = None

    # CURRENCY_CHOICES = (
    #     ("USD", "USD"),
    #     ("AUD", "AUD"),
    #     ("CAD", "CAD"),
    #     ("EUR", "EUR"),
    #     ("NZD", "NZD"),    
    # )

    month = models.ForeignKey(
        AedExchangeRateMonth,
        on_delete=models.CASCADE,
        related_name="rates"
    )
    #currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    currency = models.ForeignKey("Currency", on_delete=models.PROTECT, limit_choices_to={"is_active": True})
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6,
        validators=[MinValueValidator(0)]
    )
    effective_date = models.DateField(
        help_text="CBUAE end-of-month date, eg: 2026-05-31"
    )
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_aed_exchange_rate"
        verbose_name = "AED Exchange Rate"
        verbose_name_plural = "AED Exchange Rates"
        unique_together = ("month", "currency")

    def __str__(self):
        return "{} - {} - {}".format(self.month, self.currency, self.exchange_rate)
    


# Add Currency 

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"

    def __str__(self):
        return self.code