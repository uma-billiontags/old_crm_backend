from django.contrib.auth.models import User
from django.db import models
from django.core.validators import validate_email # Added by me
from django.core.exceptions import ValidationError #Added by me

from categories.models import Country, Roles, PaymentTerms, InvoiceCompanyAddress, InvoiceBankDetails, InvoiceAuthorizedPerson

PAYMENT_TERM = (
    ("Pre Payment", "Pre Payment"),
    ("Post Payment", "Post Payment"),
)

# Added by me
def validate_comma_separated_emails(value):
    """Validates each email in a comma-separated list."""
    emails = [e.strip() for e in value.split(",") if e.strip()]
    for email in emails:
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError(f"'{email}' is not a valid email address.")
        

class CompanyDetails(models.Model):
    objects = None
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company")   # Django login account
    client_id = models.CharField(max_length=60)   # auto generated client id (C0001, C0002, ...)
    report_id = models.CharField(max_length=60, blank=True, null=True, verbose_name="Reporting ID")
    name = models.CharField(max_length=120, unique=True) # Company name should be unique to avoid confusion in reports and invoices
    phone_number = models.CharField(max_length=15, blank=True, null=True) 
    email = models.EmailField() 
    address_line_1 = models.CharField(max_length=120)
    address_line_2 = models.CharField(max_length=120, blank=True, null=True)
    zipcode = models.CharField(max_length=8)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="company_country")
    billing_currency = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="billing_currency")
    gst_no = models.CharField(max_length=40, blank=True, null=True)
    cin_no = models.CharField(max_length=50, blank=True, null=True)
    is_domestic = models.BooleanField()

    enable_aed_invoice = models.BooleanField(
        default=False,
        verbose_name="Enable AED Invoice",
        help_text="If checked, an additional 'View AED Invoice' PDF option will be shown for this company's invoices."
    )


    wallet_amount = models.PositiveIntegerField(default=0, verbose_name="Wallet Available Amount")
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TERM)
    payment_term = models.ForeignKey(PaymentTerms, on_delete=models.CASCADE, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # New Field add
    INVOICE_TYPE = (("single", "Single Invoice"),("multiple", "Multiple Invoice"),)
    default_contact_person = models.ForeignKey('CompanyContacts',blank=True,null=True,on_delete=models.SET_NULL,related_name="default_invoice_contact",verbose_name="Contact person")
    invoice_type = models.CharField(max_length=20,choices=INVOICE_TYPE,default="single")
    default_invoice_address = models.ForeignKey(InvoiceCompanyAddress,blank=True,null=True,on_delete=models.SET_NULL, verbose_name="From company address")
    default_invoice_bank = models.ForeignKey(InvoiceBankDetails,blank=True,null=True,on_delete=models.SET_NULL, verbose_name="From bank account")
    default_authorized_person = models.ForeignKey(InvoiceAuthorizedPerson,blank=True,null=True,on_delete=models.SET_NULL, verbose_name = 'Authorized person')

    # Added by me
    default_email_send_to = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="Default Email To",
        # help_text="Comma-separated email addresses (e.g. a@x.com, b@x.com)",
        validators=[validate_comma_separated_emails],
    )
    default_email_send_cc = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="Default Email CC",
        # help_text="Comma-separated email addresses (e.g. a@x.com, b@x.com)",
        validators=[validate_comma_separated_emails],
    )
    
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_company_details"
        verbose_name = "Company Details"
        verbose_name_plural = "Company Details"
        ordering = ["-client_id"]

    def __str__(self):
        return self.name


# People at client company who will be in touch with us for campaign related communication, invoicing etc. Each contact person will have a separate login account (if needed in future)
class CompanyContacts(models.Model):
    objects = None
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True, related_name="company_contact_user")  # Django login account for company contact person (if needed in future)
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE)  # which company they belong to
    name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()
    destination = models.ForeignKey(Roles, on_delete=models.CASCADE, verbose_name="Designation")   # their job role/designation
    digital_signature = models.ImageField(upload_to="company-user-signature", blank=True, null=True)   # their signature image
    address_line_1 = models.CharField(max_length=120)
    address_line_2 = models.CharField(max_length=120, blank=True, null=True)
    zipcode = models.CharField(max_length=8)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_company_contacts"
        verbose_name = "Company Contacts"
        verbose_name_plural = "Company Contacts"

    def __str__(self):
        return "{}-CP{:04d}".format(self.company.client_id, self.pk)

    def get_id_name(self):
        return "{}-CP{:04d}".format(self.company.client_id, self.pk)


# It contains multiple addresses for a company (billing address, registered address, etc.)
class CompanyAddress(models.Model):
    objects = None
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE)
    address_line_1 = models.CharField(max_length=120)
    address_line_2 = models.CharField(max_length=120, blank=True, null=True)
    zipcode = models.CharField(max_length=8)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_company_address"
        verbose_name = "Company Address"
        verbose_name_plural = "Company Address"

    # def __str__(self):
    #     return self.company
    
    def __str__(self):
        return str(self.company)   # change this line 
    

# Wallet transaction log 
class CompanyWalletHistory(models.Model):
    objects = None
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, related_name="wallet_history")
    description = models.CharField(max_length=255)
    amount = models.FloatField()
    is_credit = models.BooleanField()  # True=money added, False=money deducted
    created_on = models.DateField(auto_now_add=True) 

    class Meta:
        db_table = "tbl_company_wallet_history"
        verbose_name = "Wallet History"
        verbose_name_plural = "Wallet History"

    def __str__(self):
        return self.description
