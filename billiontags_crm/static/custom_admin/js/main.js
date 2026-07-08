
function comfirmModel(type, id, balance) {
    var model = $('#myModal');
    var model_text = "";
    var confirm_action_url = "";
    switch (type) {
        case 1:
            model_text = `Really Do You want Rest Password a Employee`;
            model = $('#ProfileModal');
            confirm_action_url = `${id}/update_payment/`;
            break;


        default:
            model_text = "Really Do You complete this action";
            confirm_action_url = "/";
            break;
    }

    model.modal('show');
    $('#move_order_id').attr("action", confirm_action_url);
    $('#model-text').text(model_text)
    $('#amount').attr("max", balance)
}

function downloadCampaigns(element) {
    console.log("Function called")
    element.disabled = true

    $.ajax({
        url: `/insertion_order/bulk-upload/download-report/`,
        method: 'GET',
        success: function (response) {
            var encodedUri = 'data:application/csv;charset=utf-8,' + encodeURIComponent(response);
            var link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("id", "download")
            link.setAttribute("download", "Report.csv");
            link.innerHTML = "Download Report";
            document.body.appendChild(link);
            link.click();
            element.disabled = false
            link.remove();
        },
        error: function (response) {
            console.log(response)
            element.disabled = false
        }
    });
}

function handleRadioClick(myRadio) {
    $(`input[value='${myRadio.value}'].line-item-radio`).prop('checked', true)
}

function statusChangeClick(myRadio){
    const selected_value = myRadio.value
    const current_value = myRadio.getAttribute("data-status")
    const line_item_id = myRadio.getAttribute("name")

    if(selected_value != current_value){
        $('#exampleModalLongTitle').text("Reason for " + selected_value + " Line Item")
        $('#exampleModal').modal('show');
        $('#modelSubmit').attr("onclick", `onSubmitModel('${myRadio.id}', '${selected_value}', '${line_item_id}')`)
    }
}

function onSubmitModel(element_id, selected_value, line_item_id){
    const reason_value = $('#modelReason').val()
    $(`#${element_id}`).parent().parent().parent().next("td").text(reason_value + " "+selected_value )
      $.ajax({
        url: `/insertion_order/line-item/${line_item_id}/`,
        method: 'POST',
        headers: {
            'Content-Type':'application/json',
        },
        data:JSON.stringify({
            "status": selected_value,
            "reason": reason_value
        }),
        success: function (response) {
             location.reload();
        },
        error: function (response) {
            console.log(response)
        }
        });

    $('#exampleModal').modal('hide');
}


// Added by me
var currentSendEmailInvoiceId = null;

function openSendEmailModal(invoiceId) {
    // If more than one invoice is currently checked, treat this click as a
    // bulk send request — regardless of which row's "Send Email" button
    // triggered it — and reuse the existing bulk preview/send flow.
    var checkedCount = getStoredSelection().length; 
    if (checkedCount > 1) {
        openBulkSendEmailModal();
        return;
    }
    currentSendEmailInvoiceId = invoiceId;
    emailBodyDirty = false;

    // Reset modal state
    $('#sendEmailError').hide();
    $('#se_email_setup').hide();   // Added by me
    $('#sendEmailContent').hide();
    $('#sendEmailConfirmBtn').hide();

    $('#SendEmailModal').modal('show');

    $.ajax({
        url: invoiceId + '/send-email-preview/',
        method: 'GET',
        success: function (data) {
            if (!data.status) {
                $('#sendEmailError').text(data.message).show();
                if (data.needs_email_setup) {                       // Added by me
                    currentEmailSetupCompanyId = data.company_id;
                    currentEmailSetupRetryFn = function () { openSendEmailModal(invoiceId); };
                    $('#se_setup_to').val(data.default_email_send_to || '');
                    $('#se_setup_cc').val(data.default_email_send_cc || '');
                    $('#se_email_setup').show();
                }
                return;
            }

            $('#se_invoice_no').text(data.invoice_no);
            $('#se_company').text(data.company);
            $('#se_to').text(data.to.join(', '));  
            $('#se_cc').text(data.cc.length ? data.cc.join(', ') : '(none)');

            $('#se_show_campaign_checkbox').prop('checked', !!data.show_campaign_name);  // Added
            $('#se_subject').val(data.subject); 
            currentEmailBodyWith = data.email_body_html_with_campaign;       
            currentEmailBodyWithout = data.email_body_html_without_campaign; 
            renderEmailBodyPreview();

            $('#se_campaigns').empty();
            data.campaigns.forEach(function (c) {
                $('#se_campaigns').append('<li>' + c + '</li>');
            });
            
            toggleCampaignsVisibility(); 

            $('#se_attachments').empty();
            data.attachments.forEach(function (a) {
                $('#se_attachments').append('<li>' + a + '</li>');
            });

            $('#sendEmailContent').show();
            $('#sendEmailConfirmBtn').show();
        },
        error: function () {
            $('#sendEmailError').text('Failed to load email details. Please try again.').show();
        }
    });
}

// Added by me
var currentEmailBodyWith = "";
var currentEmailBodyWithout = "";
var emailBodyDirty = false;

$(document).on('input', '#se_email_body_editor', function () {
    emailBodyDirty = true;   // user started typing -> stop auto-regenerating on checkbox toggle
});

function renderEmailBodyPreview() {
    if (emailBodyDirty) return;
    var showCampaign = $('#se_show_campaign_checkbox').is(':checked');
    $('#se_email_body_editor').html(showCampaign ? currentEmailBodyWith : currentEmailBodyWithout);
}

function toggleCampaignsVisibility() {
    if ($('#se_show_campaign_checkbox').is(':checked')) {
        $('#se_campaigns_wrapper').show();
    } else {
        $('#se_campaigns_wrapper').hide();
    }
    renderEmailBodyPreview();   // Added by me
}

$(document).on('change', '#se_show_campaign_checkbox', toggleCampaignsVisibility);

// Added by me
function approveInvoiceAjax(invoiceId, btnElement) {
    var $btn = $(btnElement);
    $btn.prop('disabled', true).text('Approving...');

    $.ajax({
        url: invoiceId + '/approve-invoice/',
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        success: function () {
            $btn.replaceWith('<span class="btn btn-sm btn-outline-success">Approved</span>');
            $('#sendEmailBtn_' + invoiceId)
                .prop('disabled', false)
                .removeAttr('title')
                .removeClass('btn-outline-secondary')
                .addClass('btn-outline-primary')
                .attr('onclick', 'openSendEmailModal(' + invoiceId + ')')
                .text('Send Email');
        },
        error: function () {
            $btn.prop('disabled', false).text('Approve Invoice');
            alert('Failed to approve invoice. Please try again.');
        }
    });
}

function confirmSendEmail() {
    if (!currentSendEmailInvoiceId) return;

    setSendEmailLoading(true);

    $.ajax({
        url: currentSendEmailInvoiceId + '/send-email/',
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        data: {
            show_campaign_name: $('#se_show_campaign_checkbox').is(':checked'),
            subject: $('#se_subject').val(),
            email_body: $('#se_email_body_editor').html()   // Added by me
        },
        success: function (data) {
            setSendEmailLoading(false);
            $('#SendEmailModal').modal('hide');
            alert(data.message);   // will be replaced with a nicer toast in a later step if you'd like
            location.reload();
        },
        error: function () {
            setSendEmailLoading(false);
            alert('Something went wrong sending the email.');
        }
    });
}

// Standard Django CSRF cookie reader (skip if you already have this helper elsewhere in main.js)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
// Added by me -- persist checkbox selection across pagination
// (Django admin pagination is a full page reload, so the DOM alone
// can't remember what was checked on a previous page)
var SELECTED_STORAGE_KEY = 'invoice_selected_ids';

function getStoredSelection() {
    try {
        return JSON.parse(sessionStorage.getItem(SELECTED_STORAGE_KEY) || '[]');
    } catch (e) {
        return [];
    }
}

function setStoredSelection(ids) {
    sessionStorage.setItem(SELECTED_STORAGE_KEY, JSON.stringify(ids));
}

function persistCheckboxChange(checkboxEl) {
    var id = String($(checkboxEl).val());
    var stored = getStoredSelection();
    if (checkboxEl.checked) {
        if (stored.indexOf(id) === -1) stored.push(id);
    } else {
        stored = stored.filter(function (v) { return v !== id; });
    }
    setStoredSelection(stored);
}

function restoreCheckboxSelection() {
    var stored = getStoredSelection();
    if (!stored.length) return;
    $('input.action-select').each(function () {
        if (stored.indexOf(String($(this).val())) !== -1) {
            $(this).prop('checked', true);
        }
    });
    // let Django's own actions.js recompute its per-page "N selected" label
    $('input.action-select:first').trigger('change');
}

function updateBulkSendButton() {
    var count = getStoredSelection().length;
    $('#bulkSendEmailBtn')
        .prop('disabled', count === 0)
        .text(count > 0 ? 'Send Email (' + count + ' Selected)' : 'Send Email (Selected Invoices)');
}

// Added by me -- forcefully strips any highlight from one row
function forceClearRowHighlight(tr) {
    tr.classList.remove('selected');
    tr.style.setProperty('background-color', 'transparent', 'important');
    tr.style.setProperty('color', 'inherit', 'important');
    tr.querySelectorAll('td, th, a').forEach(function (el) {
        el.style.setProperty('background-color', 'transparent', 'important');
        el.style.setProperty('color', 'inherit', 'important');
    });
}

function removeSelectedRowHighlight() {
    document.querySelectorAll('#changelist-form tbody tr').forEach(forceClearRowHighlight);
}

// Added by me -- watches every row for class/style changes (e.g. from
// Django/Suit's own actions.js re-highlighting rows after page load) and
// immediately neutralizes it the instant it happens, no matter when
var rowHighlightObserver = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
        forceClearRowHighlight(m.target);
    });
});

// Added by me -- forcefully strips any highlight from one row
function forceClearRowHighlight(tr) {
    tr.classList.remove('selected');
    tr.style.setProperty('background-color', 'transparent', 'important');
    tr.style.setProperty('color', 'inherit', 'important');
    tr.querySelectorAll('td, th, a').forEach(function (el) {
        el.style.setProperty('background-color', 'transparent', 'important');
        el.style.setProperty('color', 'inherit', 'important');
    });
}

function removeSelectedRowHighlight() {
    document.querySelectorAll('#changelist-form tbody tr').forEach(forceClearRowHighlight);
}

// Added by me -- watch ONLY the "class" attribute (that's what Django/Suit's
// own actions.js toggles to mark a row "selected"). We deliberately do NOT
// watch "style", since forceClearRowHighlight itself writes to style --
// watching it too would make the observer trigger itself in an infinite loop.
var rowHighlightObserver = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
        if (m.target.classList.contains('selected')) {
            forceClearRowHighlight(m.target);
        }
    });
});

$(document).ready(function () {
    if (isPageReload()) {
        setStoredSelection([]);
    }
    restoreCheckboxSelection();
    updateBulkSendButton();
    removeSelectedRowHighlight();

    // Added by me -- keep watching every row for re-applied highlighting
    document.querySelectorAll('#changelist-form tbody tr').forEach(function (tr) {
        rowHighlightObserver.observe(tr, { attributes: true, attributeFilter: ['class'] });
    });

    $(document).on('change', 'input.action-select', function () {
        persistCheckboxChange(this);
        updateBulkSendButton();
        removeSelectedRowHighlight();
    });

    $(document).on('change', '#action-toggle', function () {
        $('input.action-select').each(function () {
            persistCheckboxChange(this);
        });
        updateBulkSendButton();
        removeSelectedRowHighlight();
    });
});

var currentBulkInvoiceIds = [];

function openBulkSendEmailModal() {
    currentBulkInvoiceIds = getStoredSelection();
    if (!currentBulkInvoiceIds.length) return;

    $('#sendEmailError').hide();
    $('#se_email_setup').hide();   // Added by me
    $('#sendEmailContent').hide();
    $('#sendEmailConfirmBtn').hide();
    $('#SendEmailModal').modal('show');

    $.ajax({
        url: 'send-bulk-email-preview/?ids=' + currentBulkInvoiceIds.join(','),
        method: 'GET',
        success: function (data) {
            if (!data.status) {
                $('#sendEmailError').text(data.message).show();
                if (data.needs_email_setup) {                       // Added by me
                    currentEmailSetupCompanyId = data.company_id;
                    currentEmailSetupRetryFn = function () { openBulkSendEmailModal(); };
                    $('#se_setup_to').val(data.default_email_send_to || '');
                    $('#se_setup_cc').val(data.default_email_send_cc || '');
                    $('#se_email_setup').show();
                }
                return;
            }
            $('#se_invoice_no').text(data.invoice_no);
            $('#se_company').text(data.company);
            $('#se_to').text(data.to.join(', '));
            $('#se_cc').text(data.cc.length ? data.cc.join(', ') : '(none)');

            $('#se_show_campaign_checkbox').prop('checked', !!data.show_campaign_name);  // Added

            $('#se_subject').val(data.subject);   

            $('#se_campaigns').empty();
            data.campaigns.forEach(function (c) { $('#se_campaigns').append('<li>' + c + '</li>'); });
            toggleCampaignsVisibility();  

            $('#se_attachments').empty();
            data.attachments.forEach(function (a) { $('#se_attachments').append('<li>' + a + '</li>'); });
            $('#sendEmailContent').show();
            $('#sendEmailConfirmBtn').show().attr('onclick', 'confirmBulkSendEmail()');
        },
        error: function () { $('#sendEmailError').text('Failed to load email details. Please try again.').show(); }
    });
}

function confirmBulkSendEmail() {
    if (!currentBulkInvoiceIds.length) return;

    setSendEmailLoading(true);

    $.ajax({
        url: 'send-bulk-email/',
        method: 'POST',
        data: {
            show_campaign_name: $('#se_show_campaign_checkbox').is(':checked'),
            subject: $('#se_subject').val(),
            email_body: $('#se_email_body_editor').html()   // Added by me
        },
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        success: function (data) {
            setSendEmailLoading(false);
            $('#SendEmailModal').modal('hide');
            alert(data.message);
            setStoredSelection([]);
            location.reload();
        },
        error: function () {
            setSendEmailLoading(false);
            alert('Something went wrong sending the email.');
        }
    });
}

function setSendEmailLoading(isLoading) {
    $('#sendEmailConfirmBtn').prop('disabled', isLoading);
    $('#sendEmailSpinner').toggle(isLoading);
    $('#sendEmailBtnText').text(isLoading ? 'Sending...' : 'Confirm & Send');

    // Prevent the modal being dismissed mid-send via backdrop click or Cancel
    if (isLoading) {
        $('#SendEmailModal').modal({ backdrop: 'static', keyboard: false });
        $('#SendEmailModal .modal-footer .btn-outline-secondary').prop('disabled', true);
    } else {
        $('#SendEmailModal').modal({ backdrop: true, keyboard: true });
        $('#SendEmailModal .modal-footer .btn-outline-secondary').prop('disabled', false);
    }
}

// Added by me
var currentEmailSetupCompanyId = null;
var currentEmailSetupRetryFn = null;

function saveCompanyEmailsAndRetry() {
    $('#se_setup_to_error').hide();
    $('#se_setup_cc_error').hide();

    var toValue = $('#se_setup_to').val().trim();
    var ccValue = $('#se_setup_cc').val().trim();

    if (!toValue) {
        $('#se_setup_to_error').text('Default Email To is required.').show();
        return;
    }

    $('#se_setup_save_btn').prop('disabled', true).text('Saving...');

    $.ajax({
        url: 'save-company-emails/' + currentEmailSetupCompanyId + '/',
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        data: {
            default_email_send_to: toValue,
            default_email_send_cc: ccValue
        },
        success: function (data) {
            $('#se_setup_save_btn').prop('disabled', false).text('Save & Continue');
            if (!data.status) {
                var target = data.field === 'cc' ? '#se_setup_cc_error' : '#se_setup_to_error';
                $(target).text(data.message).show();
                return;
            }
            $('#se_email_setup').hide();
            $('#sendEmailError').hide();
            if (currentEmailSetupRetryFn) currentEmailSetupRetryFn();
        },
        error: function () {
            $('#se_setup_save_btn').prop('disabled', false).text('Save & Continue');
            $('#se_setup_to_error').text('Something went wrong. Please try again.').show();
        }
    });
}

// Distinguishes a manual refresh (F5, reload button) from
// normal navigation (clicking a pagination link), which the browser
// reports differently via the Navigation Timing API
function isPageReload() {
    try {
        var entries = performance.getEntriesByType('navigation');
        if (entries && entries.length && entries[0].type) {
            return entries[0].type === 'reload';
        }
    } catch (e) {}
    // Fallback for older browsers
    if (performance.navigation) {
        return performance.navigation.type === performance.navigation.TYPE_RELOAD;
    }
    return false;
}