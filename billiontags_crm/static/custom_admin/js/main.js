
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
    var checkedCount = $('input.action-select:checked').length;
    if (checkedCount > 1) {
        openBulkSendEmailModal();
        return;
    }
    currentSendEmailInvoiceId = invoiceId;

    // Reset modal state
    $('#sendEmailError').hide();
    $('#sendEmailContent').hide();
    $('#sendEmailConfirmBtn').hide();

    $('#SendEmailModal').modal('show');

    $.ajax({
        url: invoiceId + '/send-email-preview/',
        method: 'GET',
        success: function (data) {
            if (!data.status) {
                $('#sendEmailError').text(data.message).show();
                return;
            }

            $('#se_invoice_no').text(data.invoice_no);
            $('#se_company').text(data.company);
            $('#se_to').text(data.to.join(', '));
            $('#se_cc').text(data.cc.length ? data.cc.join(', ') : '(none)');

            $('#se_campaigns').empty();
            data.campaigns.forEach(function (c) {
                $('#se_campaigns').append('<li>' + c + '</li>');
            });

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

function confirmSendEmail() {
    if (!currentSendEmailInvoiceId) return;

    setSendEmailLoading(true);

    $.ajax({
        url: currentSendEmailInvoiceId + '/send-email/',
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
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

function updateBulkSendButton() {
    var checkedCount = $('input.action-select:checked').length;
    $('#bulkSendEmailBtn').prop('disabled', checkedCount === 0);
}

// Django/Suit's own actions.js adds a "selected" class + inline highlight
// styling to checked rows. We don't want that visual treatment on this
// page, so strip it back off right after it gets applied.
function removeSelectedRowHighlight() {
    $('#changelist-form tbody tr').removeClass('selected');
}

$(document).ready(function () {
    updateBulkSendButton();
    removeSelectedRowHighlight();
    $(document).on('change', 'input.action-select, #action-toggle', function () {
        updateBulkSendButton();
        removeSelectedRowHighlight();
    });
});

var currentBulkInvoiceIds = [];

function openBulkSendEmailModal() {
    currentBulkInvoiceIds = $('input.action-select:checked').map(function () { return $(this).val(); }).get();
    if (!currentBulkInvoiceIds.length) return;

    $('#sendEmailError').hide();
    $('#sendEmailContent').hide();
    $('#sendEmailConfirmBtn').hide();
    $('#SendEmailModal').modal('show');

    $.ajax({
        url: 'send-bulk-email-preview/?ids=' + currentBulkInvoiceIds.join(','),
        method: 'GET',
        success: function (data) {
            if (!data.status) { $('#sendEmailError').text(data.message).show(); return; }
            $('#se_invoice_no').text(data.invoice_no);
            $('#se_company').text(data.company);
            $('#se_to').text(data.to.join(', '));
            $('#se_cc').text(data.cc.length ? data.cc.join(', ') : '(none)');
            $('#se_campaigns').empty();
            data.campaigns.forEach(function (c) { $('#se_campaigns').append('<li>' + c + '</li>'); });
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
        data: { ids: currentBulkInvoiceIds.join(',') },
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        success: function (data) {
            setSendEmailLoading(false);
            $('#SendEmailModal').modal('hide');
            alert(data.message);
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