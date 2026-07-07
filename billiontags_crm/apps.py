from suit.apps import DjangoSuitConfig
from suit.menu import ParentItem, ChildItem


class SuitConfig(DjangoSuitConfig):
    layout = 'horizontal'

    menu = (
        ParentItem('Companies', children=[
            ChildItem(model='company_details.companydetails'),
        ], icon='fa fa-leaf'),
        ParentItem('Campaigns', children=[
            ChildItem(model='insertion_order.campaigns'),
            ChildItem(model='insertion_order.subcampaign'),
            ChildItem(model='insertion_order.insertionorders'),
            ChildItem(model='insertion_order.lineitemsreports'),
            ChildItem(model='insertion_order.lineitemsperformance'),
            ChildItem('Bulk Upload Report', url='/insertion_order/bulk-upload/',
                      permissions=['reports.view_lineitemunderpacing']),
            ChildItem(' Performance of LineItems ', url='/insertion_orders/line-items/',
                      permissions=['invoices.view_allinvoice']),
        ], icon='fa fa-leaf'),
        ParentItem('Invoice & Payment', children=[
            ChildItem(model='invoices.invoices',
                      permissions=['invoices.view_invoices']),
            ChildItem(model='invoices.notpaid',
                      permissions=['invoices.add_notpaid', 'invoices.change_notpaid', 'invoices.delete_notpaid',
                                   'invoices.view_notpaid']),
            ChildItem(model='invoices.notpaidoverdue',
                      permissions=['invoices.add_notpaidoverdue', 'invoices.change_notpaidoverdue',
                                   'invoices.delete_notpaidoverdue',
                                   'invoices.view_notpaidoverdue']),
            ChildItem(model='invoices.partiallypaid',
                      permissions=['invoices.add_partiallypaid', 'invoices.change_partiallypaid',
                                   'invoices.delete_partiallypaid',
                                   'invoices.view_partiallypaid']),
            ChildItem(model='invoices.partiallypaidoverdue',
                      permissions=['invoices.add_partiallypaidoverdue', 'invoices.change_partiallypaidoverdue',
                                   'invoices.delete_partiallypaidoverdue',
                                   'invoices.view_partiallypaidoverdue']),
            ChildItem(model='invoices.fullypaid',
                      permissions=['invoices.add_fullypaid', 'invoices.change_fullypaid',
                                   'invoices.delete_fullypaid',
                                   'invoices.view_fullypaid']),
            ChildItem(model='invoices.allinvoice', permissions=['invoices.add_allinvoice', 'invoices.change_allinvoice',
                                                                'invoices.delete_allinvoice',
                                                                'invoices.view_allinvoice']),
            ChildItem('Invoice Summary', url='/reports/invoice-summary/',
                      permissions=['invoices.view_allinvoice']),

            
            ChildItem('Invoice Reconciliation', url='/reports/invoice-summary-reconciliation/',permissions=['invoices.view_allinvoice']),

        ], icon='fa fa-leaf'),
        ParentItem('Categories', children=[
            ChildItem(model='categories.invoicebankdetails'),
            ChildItem(model='categories.invoicecompanyaddress'),
            ChildItem(model='categories.invoiceauthorizedperson'),
            ChildItem(model='categories.adsformats'),
            ChildItem(model='categories.country'),
            ChildItem(model='categories.ethnicity'),
            ChildItem(model='categories.metrics'),
            ChildItem(model='categories.mediatypesupercategory'),
            ChildItem(model='categories.mediatypecategory'),
            ChildItem(model='categories.modeofpayment'),
            ChildItem(model='categories.paymentterms'),
            ChildItem(model='categories.roles'),
            ChildItem(model='categories.teams'),
            ChildItem(model='categories.performancecategory'),
            ChildItem(model='categories.currency', label="Currency"),
            ChildItem(model='categories.aedexchangeratemonth', label="AED Exchange Rates"),
        ], icon='fa fa-leaf'),
        ParentItem('Invoice Reports', children=[
            ChildItem('Not Generated Invoice', url='/reports/invoice-not-yet-generated/',
                      permissions=['reports.view_lineitemunderpacing']),
            ChildItem('Over Delivered', url='/reports/invoice-over-delivered/',
                      permissions=['reports.view_lineitemunderpacing']),
            ChildItem('Under Delivered', url='/reports/invoice-under-delivered/',
                      permissions=['reports.view_lineitemunderpacing']),
        ], icon='fa fa-leaf', ),
        ParentItem('Tickets', children=[
            ChildItem(model='clientrequests.lineitemrequest', label="Tickets"),
            ChildItem(model='clientrequests.campaignrequest', label="New Campaign Request"),
        ], icon='fa fa-leaf', ),
        ParentItem('Reports', children=[

            ChildItem('Under Pacing', url='/reports/under-pacing/', permissions=['reports.view_lineitemunderpacing']),
            ChildItem('Over Pacing', url='/reports/over-pacing/', permissions=['reports.view_lineitemunderpacing']),
            ChildItem('Not Uploaded Report', url='/reports/not-uploaded/',
                      permissions=['reports.view_lineitemunderpacing']),
        ], icon='fa fa-leaf', ),

        ParentItem('Analytics', children=[
            ChildItem('Spend Summary', url='/analytics/spend/', permissions=['invoices.view_allinvoice']),
            ChildItem('Company wise Forecasting', url='/analytics/company-forecasting/',
                      permissions=['invoices.view_allinvoice']),
            ChildItem('Campaign wise Forecasting', url='/analytics/campaign-forecasting/',
                      permissions=['invoices.view_allinvoice']),
        ], icon='fa fa-leaf', ),
    )
