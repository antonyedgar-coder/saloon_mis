import csv
import io
from datetime import datetime

from django.http import HttpResponse
from django.utils.dateparse import parse_date


def parse_date_range(request):
    from_date = parse_date(request.GET.get("from_date", "") or "")
    to_date = parse_date(request.GET.get("to_date", "") or "")
    return from_date, to_date


def filter_queryset_by_date(qs, field_name, from_date, to_date):
    if from_date:
        qs = qs.filter(**{f"{field_name}__gte": from_date})
    if to_date:
        qs = qs.filter(**{f"{field_name}__lte": to_date})
    return qs


def filter_queryset_by_datetime_date(qs, field_name, from_date, to_date):
    if from_date:
        qs = qs.filter(**{f"{field_name}__date__gte": from_date})
    if to_date:
        qs = qs.filter(**{f"{field_name}__date__lte": to_date})
    return qs


def csv_response(filename, headers, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def dated_filename(prefix):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def build_filter_urls(request, path):
    from urllib.parse import urlencode

    params = {}
    if request.GET.get("from_date"):
        params["from_date"] = request.GET.get("from_date")
    if request.GET.get("to_date"):
        params["to_date"] = request.GET.get("to_date")
    if request.GET.get("invoice"):
        params["invoice"] = request.GET.get("invoice")
    if request.GET.get("edit"):
        params["edit"] = request.GET.get("edit")
    if request.GET.get("branch"):
        params["branch"] = request.GET.get("branch")

    csv_params = dict(params)
    csv_params["export"] = "csv"
    return {
        "from_date": request.GET.get("from_date", ""),
        "to_date": request.GET.get("to_date", ""),
        "parsed_from_date": parse_date(request.GET.get("from_date", "") or ""),
        "parsed_to_date": parse_date(request.GET.get("to_date", "") or ""),
        "export_csv": request.GET.get("export") == "csv",
        "clear_url": path,
        "csv_url": f"{path}?{urlencode(csv_params)}" if csv_params else f"{path}?export=csv",
        "preserve_invoice": request.GET.get("invoice"),
        "preserve_edit": request.GET.get("edit"),
    }
