

import calendar
from datetime import timedelta, datetime, date

from django import template
from django.db.models import Avg, Sum
from django.db.models.functions import Coalesce

from clientrequests.models import LineItemRequest
from insertion_order import models
from insertion_order.models import IODetails, LineItemsReports
from insertion_order.templatetags.dashboard import line_item_budget_calculator

register = template.Library()


@register.simple_tag
def report_value(line_item, date):
    try:
        report = models.LineItemsReports.objects.get(line_item=line_item, report_on=date)
        return {"impression": report.impression, "clicks": report.clicks, "budget": report.budget,
                "ctr": report.ctr_calculation()}
    except:
        return {"impression": 0, "clicks": 0, "budget": 0, "ctr": 0}


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


@register.simple_tag()
def line_item_report(line_tem):
    data = dict()
    today = datetime.today().date()
    data['billing_currency'] = line_tem.io.sub_campaign.campaign.company.billing_currency.iso_code_3
    data['total_days'] = (line_tem.end_date - line_tem.start_date).days + 1
    report_days = models.LineItemsReports.objects.filter(line_item=line_tem, report_on__gte=line_tem.start_date,
                                                         report_on__lte=line_tem.end_date).count()
    data['report_days'] = report_days if report_days else 0

    # Remaining days, anchored to the real current date rather than to which
    # report rows exist or to day-of-month subtraction:
    #   - campaign already ended      -> 0 days left
    #   - campaign hasn't started yet -> the whole campaign is still ahead
    #   - otherwise                   -> days from today to end_date, inclusive of today
    if today > line_tem.end_date:
        data['remaining_days'] = 0
    elif today < line_tem.start_date:
        data['remaining_days'] = data['total_days']
    else:
        data['remaining_days'] = (line_tem.end_date - today).days + 1

    data['archived_impressions'] = line_tem.total_impression()
    data['total_impressions'] = line_tem.volume
    remaining_impressions = line_tem.volume - data['archived_impressions']
    data['remaining_impressions'] = remaining_impressions if remaining_impressions > 0 else 0

    # Dynamic daily target = what's left to deliver / days left to deliver it.
    # (Swap round() for math.ceil() here if you'd rather pace slightly ahead
    # than risk under-delivering by end_date.)
    if data['remaining_days'] > 0:
        data['daily_target'] = round(data['remaining_impressions'] / data['remaining_days'])
    else:
        data['daily_target'] = 0

    data['reports'] = []

    if line_tem.start_date == line_tem.end_date:
        try:
            reports = models.LineItemsReports.objects.get(line_item=line_tem, report_on=line_tem.start_date)
            report = {
                "impression": reports.impression, "clicks": reports.clicks,
                "viewable_impression": reports.viewable_impression,
                "measurable_impression": reports.measurable_impression,
                "video_start": reports.video_start,
                "video_end": reports.video_end,

                "budget": (reports.impression / 1000) * reports.line_item.unit_cost,
                "ctr": reports.ctr_calculation(), "viewability": reports.viewability(),
                "video_completion_rate": reports.video_completion_rate(),
            }
        except:
            report = {"impression": 0, "clicks": 0, "budget": 0, "ctr": 0, "viewability": 0, "video_completion_rate": 0,
                      "viewable_impression": 0, "measurable_impression": 0, "video_start": 0, "video_end": 0, }
        report['date'] = line_tem.start_date
        data['reports'].append(report)
    else:
        for single_date in daterange(line_tem.start_date, line_tem.end_date + timedelta(days=1)):
            try:
                reports = models.LineItemsReports.objects.get(line_item=line_tem, report_on=single_date)
                report = {"impression": reports.impression, "clicks": reports.clicks,
                          "budget": (reports.impression / 1000) * reports.line_item.unit_cost,
                          "ctr": reports.ctr_calculation(), "viewability": reports.viewability(),
                          "video_completion_rate": reports.video_completion_rate(),
                          "viewable_impression": reports.viewable_impression,
                          "measurable_impression": reports.measurable_impression,
                          "video_start": reports.video_start,
                          "video_end": reports.video_end,
                          }
            except:
                report = {"impression": 0, "clicks": 0, "budget": 0, "ctr": 0, "viewability": 0,
                          "video_completion_rate": 0,
                          "viewable_impression": 0, "measurable_impression": 0, "video_start": 0, "video_end": 0, }
            report['date'] = single_date
            data['reports'].append(report)

    return data


@register.simple_tag()
def insertion_order_report(insertion_order):
    data = dict()
    today = datetime.today().date()
    data['billing_currency'] = insertion_order.sub_campaign.campaign.company.billing_currency.currency_symbols
    data['total_days'] = (insertion_order.end_date - insertion_order.start_date).days + 1

    if today > insertion_order.end_date:
        data['remaining_days'] = 0
    elif today < insertion_order.start_date:
        data['remaining_days'] = data['total_days']
    else:
        data['remaining_days'] = (insertion_order.end_date - today).days + 1

    data['archived_impressions'] = insertion_order.total_impression()
    data['total_impressions'] = insertion_order.total_impressions()
    total_clicks = insertion_order.total_clicks()
    data['booked_ctr'] = insertion_order.io_details.aggregate(ctr=Avg("avg_ctr"))['ctr']
    try:
        data['delivered_ctr'] = round((total_clicks / data['archived_impressions']) * 100, 2)
    except:
        data['delivered_ctr'] = 0

    data['net_cost'] = insertion_order.total_cost()
    remaining_impressions = data['total_impressions'] - data['archived_impressions']
    data['remaining_impressions'] = remaining_impressions if remaining_impressions > 0 else 0

    if data['remaining_days'] > 0:
        data['daily_target'] = round(data['remaining_impressions'] / data['remaining_days'])
    else:
        data['daily_target'] = 0
    return data


@register.simple_tag()
def line_item_request_status(line_item):
    data = {}
    request = LineItemRequest.objects.filter(line_item=line_item).first()
    if request:
        data['status'] = request.status
        data['reason'] = request.reason
        data['created_on'] = request.created_on
        data['request_status'] = request.request_status

    return data


def month_year_iter(start_month, start_year, end_month, end_year):
    ym_start = 12 * start_year + start_month - 1
    ym_end = 12 * end_year + end_month
    for ym in range(ym_start, ym_end):
        y, m = divmod(ym, 12)
        yield date(year=y, month=m + 1, day=1)


# ----------------------------------------------------------------------------
# Dynamic carry-forward planned impression calculator
#
#   remaining_volume = booked_volume - cumulative_effective_delivered_so_far
#   remaining_days    = flight_end - max(this_month_start, flight_start) + 1
#   days_this_month   = min(month_end, flight_end) - max(month_start, flight_start) + 1
#   planned           = (days_this_month / remaining_days) * remaining_volume
#
# "cumulative_effective_delivered" uses REAL delivered impressions for any
# month that has already reported. For a month that hasn't reported yet, it
# assumes that month delivers exactly its own planned figure (i.e. "on
# track") so the carry-forward still reconciles cleanly to future months.
#
# Practical effect: if July hasn't reported yet, August's plan simply
# mirrors July's plan (both split the remaining volume evenly across the
# remaining time). The moment July's real report lands, August is
# recalculated using the real number instead of the assumption — no manual
# changes needed, it just self-corrects on the next page load.
# ----------------------------------------------------------------------------
def _calculate_planned_impressions_all(line_item, all_reporting_dates):
    """
    Returns {date(year, month, 1): planned_impression, ...} for every month
    in all_reporting_dates, processed in chronological order so each month's
    plan can depend on the (real-or-assumed) delivery of the months before it.
    """
    volume = line_item.volume
    start_date = line_item.start_date
    end_date = line_item.end_date

    sorted_months = sorted(set(date(d.year, d.month, 1) for d in all_reporting_dates))

    planned_by_month = {}
    cumulative_effective_delivered = 0

    for target_month_start in sorted_months:

        # Flight already finished before this month started
        if target_month_start > end_date:
            planned_by_month[target_month_start] = 0
            continue

        remaining_volume = max(volume - cumulative_effective_delivered, 0)

        remaining_start = max(target_month_start, start_date)
        if remaining_start > end_date or remaining_volume == 0:
            planned_by_month[target_month_start] = 0
            continue

        remaining_days = (end_date - remaining_start).days + 1
        if remaining_days <= 0:
            planned_by_month[target_month_start] = 0
            continue

        last_day = calendar.monthrange(target_month_start.year, target_month_start.month)[1]
        target_month_end = date(target_month_start.year, target_month_start.month, last_day)

        month_start_in_flight = max(target_month_start, start_date)
        month_end_in_flight = min(target_month_end, end_date)

        if month_start_in_flight > month_end_in_flight:
            planned_by_month[target_month_start] = 0
            continue

        days_this_month = (month_end_in_flight - month_start_in_flight).days + 1
        month_planned = round((days_this_month / remaining_days) * remaining_volume)
        planned_by_month[target_month_start] = month_planned

        # Has this month actually reported anything yet?
        agg = line_item.reports.filter(
            report_on__year=target_month_start.year,
            report_on__month=target_month_start.month
        ).aggregate(total=Sum('impression'))

        if agg['total'] is not None:
            # Real data exists -> use it for downstream months' carry-forward
            cumulative_effective_delivered += agg['total']
        else:
            # No report yet -> assume on-plan delivery so future months still
            # reconcile; self-corrects automatically once real data arrives
            cumulative_effective_delivered += month_planned

    return planned_by_month


# sum_io_details is used in the template to calculate the total number of IO/line-item rows across all campaigns of one company (for rowspan).
@register.filter  # add
def sum_io_details(items):
    """Total IO/line-item rows across all campaigns of one company (for rowspan)."""
    total = sum(item.io_details.count() for item in items)
    return total or 1






# @register.simple_tag()
# def line_item_summary(line_item, reporting_dates):
@register.simple_tag()
def line_item_reconciliation(line_item, reporting_dates):

    data = dict()
    total_impression = 0
    total_amount = 0
    data['month'] = []

    all_month_dates = [date(d.year, d.month, 1) for d in reporting_dates]
    planned_by_month = _calculate_planned_impressions_all(line_item, all_month_dates)

    for report_on in reporting_dates:

        report = line_item.reports.filter(report_on__month=report_on.month, report_on__year=report_on.year).aggregate(
            impression=Sum('impression'))['impression']
        delivered_impression = report if report else 0

        total_impression += delivered_impression
        if total_impression > line_item.volume:
            impression = delivered_impression - (total_impression - line_item.volume)
            billable_impression = impression if impression > 0 else 0

        else:
            billable_impression = delivered_impression

        amount = round((billable_impression / 1000) * line_item.unit_cost, 2)
        total_amount += amount

        # ── dynamic carry-forward planned impression, variance, pacing ──
        target_month_date = date(report_on.year, report_on.month, 1)
        planned_impression = planned_by_month.get(target_month_date, 0)

        if delivered_impression > 0:
            variance = billable_impression - planned_impression
            if planned_impression > 0:
                pacing_pct = round((variance / planned_impression) * 100)
                if pacing_pct > 2:
                    pacing_label = f"{pacing_pct}% Over"
                elif pacing_pct < -2:
                    pacing_label = f"{abs(pacing_pct)}% Under"
                else:
                    pacing_label = "On Track"
            else:
                pacing_pct = None
                pacing_label = "—"
        else:
            # No delivery reported yet for this month -> nothing to compare against
            variance = None
            pacing_pct = None
            pacing_label = "pending"

        data['month'].append({"report_on": report_on, "amount": amount,
                              'billable_impression': billable_impression,
                              "delivered_impression": delivered_impression,
                              "planned_impression": planned_impression,
                              "variance": variance,
                              "pacing_pct": pacing_pct,
                              "pacing_label": pacing_label,
                              })

    balance_amount = round(line_item.net_cost - total_amount, 2)
    data['balance_amount'] = balance_amount if balance_amount > 0 else 0
    if total_impression > line_item.volume:
        data['balance_impression'] = 0
    else:
        data['balance_impression'] = line_item.volume - total_impression
    return data








@register.simple_tag()
def line_item_summary(line_item, reporting_dates):
    data = dict()
    total_impression = 0
    total_amount = 0
    data['month'] = []
    for report_on in reporting_dates:

        report = line_item.reports.filter(report_on__month=report_on.month, report_on__year=report_on.year).aggregate(
            impression=Sum('impression'))['impression']
        delivered_impression = report if report else 0

        total_impression += delivered_impression
        if total_impression > line_item.volume:
            impression = delivered_impression - (total_impression - line_item.volume)
            billable_impression = impression if impression > 0 else 0

        else:
            billable_impression = delivered_impression

        amount = round((billable_impression / 1000) * line_item.unit_cost, 2)
        total_amount += amount

        data['month'].append({"report_on": report_on, "amount": amount,
                              'billable_impression': billable_impression,
                              "delivered_impression": delivered_impression,
                              })

    balance_amount = round(line_item.net_cost - total_amount, 2)
    data['balance_amount'] = balance_amount if balance_amount > 0 else 0
    if total_impression > line_item.volume:
        data['balance_impression'] = 0
    else:
        data['balance_impression'] = line_item.volume - total_impression
    return data








@register.simple_tag()
def spend_summary_company(request, company):
    if request.GET.get('end_date') and request.GET.get('start_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
    else:
        end_date = datetime.today() - timedelta(days=1)
        start_date = datetime.today() - timedelta(days=1)
    total_delivered_impression = 0
    total_delivered_budget = 0

    this_month_planned_impression = 0
    this_month_planned_budget = 0

    yet_to_deliverable_impression = 0
    yet_to_deliverable_budget = 0

    for line_item in IODetails.objects.filter(io__sub_campaign__campaign__company=company, end_date__gte=start_date):

        impression = line_item.reports.filter(report_on__range=[start_date, end_date]).aggregate(
            impression=Coalesce(Sum('impression'), 0))['impression']

        budget = round((impression / 1000) * line_item.unit_cost, 2)

        if start_date.month == end_date.month:
            result = line_item_budget_calculator(line_item)
            this_month_planned_budget += result['budget_this_month']
            this_month_planned_impression += result['this_month_booked']

            if line_item.end_date.month == start_date.month:
                if result['this_month_booked'] < impression:
                    impression = result['this_month_booked']
                    budget = result['budget_this_month']

            deliverable_impression = (result['this_month_booked'] - impression)
            yet_to_deliverable_impression += deliverable_impression
            yet_to_deliverable_budget += round((deliverable_impression / 1000) * line_item.unit_cost, 2)

        total_delivered_impression += impression
        total_delivered_budget += budget

    return {"total_delivered_impression": total_delivered_impression,
            "total_delivered_budget": round(total_delivered_budget, 2),
            "this_month_planned_impression": this_month_planned_impression,
            "this_month_planned_budget": round(this_month_planned_budget, 2),
            "yet_to_deliverable_impression": yet_to_deliverable_impression,
            "yet_to_deliverable_budget": round(yet_to_deliverable_budget, 2)
            }


@register.simple_tag()
def forecasting_summary_company(request, reporting_dates, company=None, campaign=None):
    forecast = []

    total_delivered_impression = 0
    total_billable_impression = 0
    total_delivered_budget = 0
    this_month = datetime.today().replace(day=1)
    if campaign:
        io_details = IODetails.objects.filter(io__sub_campaign__campaign=campaign,
                                              end_date__gte=this_month).order_by("-end_date")
    else:
        io_details = IODetails.objects.filter(io__sub_campaign__campaign__company=company,
                                              end_date__gte=this_month).order_by("-end_date")
    for line_item in io_details:
        delivered_impression = \
            line_item.reports.filter(report_on__month=this_month.month, report_on__year=this_month.year).aggregate(
                impression=Coalesce(Sum('impression'), 0))['impression']

        total_delivered_impression += delivered_impression

        total_impress = line_item.total_impression()
        if total_impress > line_item.volume:
            billable_impression = delivered_impression - (total_impress - line_item.volume)
            total_billable_impression += billable_impression

        else:
            billable_impression = delivered_impression
            total_billable_impression += delivered_impression

        total_delivered_budget += (billable_impression / 1000) * line_item.unit_cost

    for reporting_date in reporting_dates:
        total_impression = 0
        total_budget = 0
        for line_item in io_details:

            previous_delivered_impression = line_item.reports.filter(report_on__lt=this_month.date()).aggregate(
                impression=Coalesce(Sum('impression'), 0))['impression']

            if previous_delivered_impression < line_item.volume:
                delivery_impression = line_item.volume - previous_delivered_impression
                if line_item.end_date > this_month.date() and line_item.end_date > reporting_date:
                    today_remaining_days = (line_item.end_date - this_month.date()).days + 1
                    daily_target = round(delivery_impression / today_remaining_days)

                    reporting_date_end_date = date(reporting_date.year, reporting_date.month,
                                                   calendar.monthrange(reporting_date.year, reporting_date.month)[-1])

                    if line_item.end_date >= reporting_date_end_date:
                        report_month_days = reporting_date_end_date.day

                    else:
                        report_month_days = (line_item.end_date - reporting_date).days + 1

                    impression_daily_target = daily_target * report_month_days
                    total_impression += impression_daily_target
                    total_budget += round((impression_daily_target / 1000) * line_item.unit_cost)

        forecast.append({
            "impression": total_impression,
            "budget": total_budget
        })

    return {
        "impression": total_delivered_impression,
        "billable_impression": total_billable_impression,
        "budget": round(total_delivered_budget, 2),
        "forecast": forecast
    }




































































