from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from core.mixins import ModulePermissionMixin
from core.models import Branch
from masters.models import ExpenseParticular, Product, Staff
from reports.dsr_validation import INCOME_FIELD_NAMES, validate_dsr_totals
from reports.export_utils import build_dsr_display_excel, excel_response
from reports.pdf_utils import build_dsr_display_pdf, build_incentive_pdf, build_yearly_pdf
from reports.models import DailySalesReport, DsrStaffLine, PettyCashTransaction
from reports.petty_cash_utils import build_petty_cash_report
from reports.inventory_report import (
    REPORT_TYPES as INVENTORY_REPORT_TYPES,
    build_report as build_inventory_report,
    default_from_date,
    default_to_date,
    parse_branch_id,
)
from reports.sales_report import (
    MONTH_LABELS,
    aggregate_dsr_queryset,
    aggregated_to_display_values,
    build_yearly_rows,
    calendar_year_choices,
    financial_year_choices,
    financial_year_range,
    month_date_range,
    monthly_period_label,
    parse_report_month_params,
    report_to_display_values,
)
from reports.incentive_report import (
    PERIOD_TYPES as INCENTIVE_PERIOD_TYPES,
    build_incentive_report,
)
from reports.staff_performance_report import (
    PERIOD_TYPES as STAFF_PERF_PERIOD_TYPES,
    build_staff_performance_report,
    period_label_for as staff_perf_period_label,
)


def get_user_branches(user):
    if user.is_central():
        return Branch.objects.filter(active=True)
    return user.branches.filter(active=True)


def _master_list(queryset):
    return [{"id": obj.pk, "name": str(obj)} for obj in queryset]


def _post_decimal(request, key, default="0"):
    text = (request.POST.get(key) or default).strip()
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def _post_int(request, key, default="0"):
    text = (request.POST.get(key) or default).strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _parse_dsr_staff_lines(request):
    staff_ids = request.POST.getlist("staff_id")
    amounts = request.POST.getlist("staff_amount")
    lines = []
    for index, staff_id in enumerate(staff_ids):
        staff_id = (staff_id or "").strip()
        amount_text = (amounts[index] if index < len(amounts) else "").strip()
        if not staff_id or not amount_text:
            continue
        try:
            amount = Decimal(amount_text)
        except InvalidOperation:
            continue
        if amount <= 0:
            continue
        lines.append({"staff_id": int(staff_id), "amount": amount})
    return lines


def _dsr_data_from_post(request):
    data = {name: _post_decimal(request, name) for name in INCOME_FIELD_NAMES}
    data.update({
        "male_walkins": _post_int(request, "male_walkins"),
        "male_income": _post_decimal(request, "male_income"),
        "female_walkins": _post_int(request, "female_walkins"),
        "female_income": _post_decimal(request, "female_income"),
        "kids_walkins": _post_int(request, "kids_walkins"),
        "kids_income": _post_decimal(request, "kids_income"),
        "card_payment": _post_decimal(request, "card_payment"),
        "upi_payment": _post_decimal(request, "upi_payment"),
        "cash_payment": _post_decimal(request, "cash_payment"),
        "calls_done": _post_int(request, "calls_done"),
        "zooty_appointment": _post_int(request, "zooty_appointment"),
        "google_appointment": _post_int(request, "google_appointment"),
        "just_dial": _post_int(request, "just_dial"),
        "status_story": request.POST.get("status_story", "").strip(),
        "broadcast": _post_int(request, "broadcast"),
        "google_reviews_request": request.POST.get("google_reviews_request", "").strip(),
        "new_clients": _post_int(request, "new_clients"),
    })
    return data


def _staff_lines_for_json(staff_line_dicts):
    if not staff_line_dicts:
        return []
    staff_ids = [line["staff_id"] for line in staff_line_dicts]
    staff_map = {
        s.pk: s.name for s in Staff.objects.filter(pk__in=staff_ids)
    }
    return [
        {
            "staff_id": line["staff_id"],
            "staff_name": staff_map.get(line["staff_id"], ""),
            "amount": str(line["amount"]),
        }
        for line in staff_line_dicts
    ]


def _form_values(edit_report=None, posted=None):
    if posted:
        return posted
    if edit_report:
        return {
            "branch_id": str(edit_report.branch_id),
            "report_date": edit_report.report_date.isoformat(),
            **{name: str(getattr(edit_report, name)) for name in INCOME_FIELD_NAMES},
            "male_walkins": str(edit_report.male_walkins),
            "male_income": str(edit_report.male_income),
            "female_walkins": str(edit_report.female_walkins),
            "female_income": str(edit_report.female_income),
            "kids_walkins": str(edit_report.kids_walkins),
            "kids_income": str(edit_report.kids_income),
            "card_payment": str(edit_report.card_payment),
            "upi_payment": str(edit_report.upi_payment),
            "cash_payment": str(edit_report.cash_payment),
            "calls_done": str(edit_report.calls_done),
            "zooty_appointment": str(edit_report.zooty_appointment),
            "google_appointment": str(edit_report.google_appointment),
            "just_dial": str(edit_report.just_dial),
            "status_story": edit_report.status_story,
            "broadcast": str(edit_report.broadcast),
            "google_reviews_request": edit_report.google_reviews_request,
            "new_clients": str(edit_report.new_clients),
        }
    return {
        "branch_id": "",
        "report_date": timezone.localdate().isoformat(),
        **{name: "0" for name in INCOME_FIELD_NAMES},
        "male_walkins": "0",
        "male_income": "0",
        "female_walkins": "0",
        "female_income": "0",
        "kids_walkins": "0",
        "kids_income": "0",
        "card_payment": "0",
        "upi_payment": "0",
        "cash_payment": "0",
        "calls_done": "0",
        "zooty_appointment": "0",
        "google_appointment": "0",
        "just_dial": "0",
        "status_story": "",
        "broadcast": "0",
        "google_reviews_request": "",
        "new_clients": "0",
    }


class DsrView(ModulePermissionMixin, View):
    """Daily sales report entry form."""
    module = "dsr"
    template_name = "reports/dsr_list.html"

    def get_edit_report(self, request):
        edit_id = request.GET.get("edit")
        branch_id = request.GET.get("branch")
        report_date = request.GET.get("date")

        qs = DailySalesReport.objects.select_related("branch").prefetch_related(
            "staff_lines__staff"
        )
        report = None
        if edit_id:
            report = get_object_or_404(qs, pk=edit_id)
        elif branch_id and report_date:
            report = qs.filter(branch_id=branch_id, report_date=report_date).first()

        if report and not request.user.can_access_branch(report.branch_id):
            messages.error(request, "Access denied.")
            return None
        return report

    def recent_reports(self, user):
        qs = DailySalesReport.objects.select_related("branch").order_by(
            "-report_date", "-updated_at"
        )
        if not user.is_central():
            qs = qs.filter(branch_id__in=user.branch_ids())
        return qs[:20]

    def _form_context(
        self,
        request,
        *,
        edit_report=None,
        staff_lines_json=None,
        posted=None,
        validation_errors=None,
    ):
        return {
            "branches": get_user_branches(request.user),
            "staff_list": _master_list(Staff.objects.filter(active=True)),
            "edit_report": edit_report,
            "form_values": _form_values(edit_report=edit_report, posted=posted),
            "staff_lines_json": staff_lines_json or [],
            "validation_errors": validation_errors or [],
            "recent_reports": self.recent_reports(request.user),
            "is_editing": bool(edit_report),
        }

    def get(self, request):
        edit_report = self.get_edit_report(request)
        staff_lines_json = []
        if edit_report:
            staff_lines_json = [
                {
                    "staff_id": line.staff_id,
                    "staff_name": line.staff.name,
                    "amount": str(line.amount),
                }
                for line in edit_report.staff_lines.all()
            ]
        return render(
            request,
            self.template_name,
            self._form_context(
                request,
                edit_report=edit_report,
                staff_lines_json=staff_lines_json,
            ),
        )

    def post(self, request):
        branch_id = int(request.POST.get("branch_id"))
        if not request.user.can_access_branch(branch_id):
            messages.error(request, "Access denied.")
            return redirect("reports:dsr")

        report_date = request.POST.get("report_date")
        staff_lines = _parse_dsr_staff_lines(request)
        dsr_data = _dsr_data_from_post(request)
        staff_amounts = [line["amount"] for line in staff_lines]
        validation_errors = validate_dsr_totals(dsr_data, staff_amounts)

        posted = {
            "branch_id": str(branch_id),
            "report_date": report_date,
            **{name: str(dsr_data[name]) for name in INCOME_FIELD_NAMES},
            "male_walkins": str(dsr_data["male_walkins"]),
            "male_income": str(dsr_data["male_income"]),
            "female_walkins": str(dsr_data["female_walkins"]),
            "female_income": str(dsr_data["female_income"]),
            "kids_walkins": str(dsr_data["kids_walkins"]),
            "kids_income": str(dsr_data["kids_income"]),
            "card_payment": str(dsr_data["card_payment"]),
            "upi_payment": str(dsr_data["upi_payment"]),
            "cash_payment": str(dsr_data["cash_payment"]),
            "calls_done": str(dsr_data["calls_done"]),
            "zooty_appointment": str(dsr_data["zooty_appointment"]),
            "google_appointment": str(dsr_data["google_appointment"]),
            "just_dial": str(dsr_data["just_dial"]),
            "status_story": dsr_data["status_story"],
            "broadcast": str(dsr_data["broadcast"]),
            "google_reviews_request": dsr_data["google_reviews_request"],
            "new_clients": str(dsr_data["new_clients"]),
        }

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return render(
                request,
                self.template_name,
                self._form_context(
                    request,
                    staff_lines_json=_staff_lines_for_json(staff_lines),
                    posted=posted,
                    validation_errors=validation_errors,
                ),
            )

        with transaction.atomic():
            report, created = DailySalesReport.objects.update_or_create(
                branch_id=branch_id,
                report_date=report_date,
                defaults={
                    **{name: dsr_data[name] for name in INCOME_FIELD_NAMES},
                    "male_walkins": dsr_data["male_walkins"],
                    "male_income": dsr_data["male_income"],
                    "female_walkins": dsr_data["female_walkins"],
                    "female_income": dsr_data["female_income"],
                    "kids_walkins": dsr_data["kids_walkins"],
                    "kids_income": dsr_data["kids_income"],
                    "card_payment": dsr_data["card_payment"],
                    "upi_payment": dsr_data["upi_payment"],
                    "cash_payment": dsr_data["cash_payment"],
                    "calls_done": dsr_data["calls_done"],
                    "zooty_appointment": dsr_data["zooty_appointment"],
                    "google_appointment": dsr_data["google_appointment"],
                    "just_dial": dsr_data["just_dial"],
                    "status_story": dsr_data["status_story"],
                    "broadcast": dsr_data["broadcast"],
                    "google_reviews_request": dsr_data["google_reviews_request"],
                    "new_clients": dsr_data["new_clients"],
                    "created_by": request.user,
                },
            )
            report.staff_lines.all().delete()
            for line in staff_lines:
                DsrStaffLine.objects.create(
                    report=report,
                    staff_id=line["staff_id"],
                    amount=line["amount"],
                )

        if created:
            messages.success(request, "Daily sales report saved.")
        else:
            messages.success(request, "Daily sales report updated.")
        return redirect(
            f"{reverse('reports:dsr')}?branch={branch_id}&date={report_date}"
        )


class DsrLoadView(ModulePermissionMixin, View):
    module = "dsr"
    def get(self, request):
        branch_id = request.GET.get("branch_id")
        report_date = request.GET.get("report_date")
        if not branch_id or not report_date:
            return JsonResponse(
                {"error": "branch_id and report_date are required"},
                status=400,
            )
        if not request.user.can_access_branch(int(branch_id)):
            return JsonResponse({"error": "Access denied"}, status=403)

        report = (
            DailySalesReport.objects.filter(
                branch_id=branch_id,
                report_date=report_date,
            )
            .prefetch_related("staff_lines__staff")
            .first()
        )
        if not report:
            return JsonResponse({"found": False})

        staff_lines = [
            {
                "staff_id": line.staff_id,
                "staff_name": line.staff.name,
                "amount": str(line.amount),
            }
            for line in report.staff_lines.all()
        ]
        return JsonResponse({
            "found": True,
            "report_id": report.pk,
            "form": _form_values(edit_report=report),
            "staff_lines": staff_lines,
        })


class PettyCashView(ModulePermissionMixin, View):
    module = "petty_cash"
    template_name = "reports/petty_cash.html"

    def get_transactions(self, user, branch_id=None):
        qs = PettyCashTransaction.objects.select_related("branch", "expense_particular")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if not user.is_central():
            qs = qs.filter(branch_id__in=user.branch_ids())
        return qs

    def _redirect_url(self, branch_id, voucher_type):
        return f"/reports/petty-cash/?branch={branch_id}&type={voucher_type}"

    def get(self, request):
        from django.utils import timezone

        branches = get_user_branches(request.user)
        branch_id = request.GET.get("branch")
        if not branch_id and branches.exists():
            branch_id = str(branches.first().pk)

        voucher_type = request.GET.get("type", "receipt")
        if voucher_type not in ("opening", "receipt", "payment"):
            voucher_type = "receipt"

        txs = self.get_transactions(request.user, branch_id)
        report_rows = build_petty_cash_report(txs)

        return render(
            request,
            self.template_name,
            {
                "branches": branches,
                "selected_branch": branch_id,
                "expense_particulars": ExpenseParticular.objects.filter(active=True),
                "report_rows": report_rows,
                "voucher_type": voucher_type,
                "today": timezone.localdate().isoformat(),
            },
        )

    def post(self, request):
        branch_id = int(request.POST.get("branch_id"))
        voucher_type = request.POST.get("voucher_type", "receipt")
        if not request.user.can_access_branch(branch_id):
            messages.error(request, "Access denied.")
            return redirect(self._redirect_url(branch_id, voucher_type))

        tx_type = request.POST.get("transaction_type")
        amount = request.POST.get("amount") or 0

        if tx_type == PettyCashTransaction.Type.OPENING:
            particulars = (
                request.POST.get("particulars", "").strip() or "Opening balance"
            )
            PettyCashTransaction.objects.create(
                branch_id=branch_id,
                entry_date=request.POST.get("entry_date"),
                transaction_type=PettyCashTransaction.Type.OPENING,
                particulars=particulars,
                amount=amount,
                created_by=request.user,
            )
            messages.success(request, "Opening balance recorded.")
            return redirect(self._redirect_url(branch_id, "opening"))

        if tx_type == PettyCashTransaction.Type.RECEIPT:
            particulars = request.POST.get("particulars", "").strip()
            if not particulars:
                messages.error(request, "Particulars is required for a receipt.")
                return redirect(self._redirect_url(branch_id, "receipt"))
            PettyCashTransaction.objects.create(
                branch_id=branch_id,
                entry_date=request.POST.get("entry_date"),
                transaction_type=PettyCashTransaction.Type.RECEIPT,
                particulars=particulars,
                amount=amount,
                created_by=request.user,
            )
            messages.success(request, "Receipt recorded.")
            return redirect(self._redirect_url(branch_id, "receipt"))

        expense_id = request.POST.get("expense_particular_id")
        if not expense_id:
            name = request.POST.get("expense_search", "").strip()
            expense = ExpenseParticular.objects.filter(name__iexact=name, active=True).first()
            if expense:
                expense_id = expense.pk
        if not expense_id:
            messages.error(request, "Select a valid expense from the list.")
            return redirect(self._redirect_url(branch_id, "payment"))

        PettyCashTransaction.objects.create(
            branch_id=branch_id,
            entry_date=request.POST.get("entry_date"),
            transaction_type=PettyCashTransaction.Type.PAYMENT,
            expense_particular_id=expense_id,
            amount=amount,
            created_by=request.user,
        )
        messages.success(request, "Payment recorded.")
        return redirect(self._redirect_url(branch_id, "payment"))


class ReportsHubView(ModulePermissionMixin, View):
    module = "report_sales"
    template_name = "reports/hub.html"

    def test_func(self):
        from core.module_permissions import has_reports_access

        return has_reports_access(self.request.user)

    def get(self, request):
        from core.module_permissions import user_can

        return render(
            request,
            self.template_name,
            {
                "can_sales": user_can(request.user, "report_sales", "view"),
                "can_staff_perf": user_can(
                    request.user, "report_staff_performance", "view"
                ),
                "can_incentive": user_can(request.user, "report_incentive", "view"),
                "can_inventory_reports": user_can(
                    request.user, "report_inventory", "view"
                ),
            },
        )


class SalesReportView(ModulePermissionMixin, View):
    module = "report_sales"
    template_name = "reports/sales_report.html"
    PERIOD_TYPES = (
        ("daily", "Daily"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )

    def _filtered_queryset(self, user, branch_id):
        qs = DailySalesReport.objects.select_related("branch").prefetch_related(
            "staff_lines__staff"
        )
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        elif not user.is_central():
            qs = qs.filter(branch_id__in=user.branch_ids())
        return qs

    def get(self, request):
        from datetime import datetime

        period_type = request.GET.get("period_type", "daily")
        if period_type not in dict(self.PERIOD_TYPES):
            period_type = "daily"

        branches = get_user_branches(request.user)
        branch_id = request.GET.get("branch")
        if not branch_id and branches.exists():
            branch_id = str(branches.first().pk)

        report_date = request.GET.get("report_date") or timezone.localdate().isoformat()
        report_year = request.GET.get("report_year")
        report_month_num = request.GET.get("report_month_num")
        report_month = parse_report_month_params(
            request.GET.get("report_month"),
            report_year,
            report_month_num,
        )
        if not report_year or not report_month_num:
            year_part, month_part = report_month.split("-")
            report_year = report_year or year_part
            report_month_num = report_month_num or str(int(month_part))
        fy_choices = financial_year_choices()
        financial_year = request.GET.get("financial_year") or (
            fy_choices[0][0] if fy_choices else "2025"
        )
        if fy_choices and financial_year not in dict(fy_choices):
            financial_year = fy_choices[0][0]
        export = request.GET.get("export")

        context = {
            "period_types": self.PERIOD_TYPES,
            "period_type": period_type,
            "branches": branches,
            "selected_branch": branch_id or "",
            "report_date": report_date,
            "report_year": report_year,
            "report_month_num": report_month_num,
            "report_month": report_month,
            "year_choices": calendar_year_choices(),
            "month_choices": MONTH_LABELS,
            "financial_year": financial_year,
            "fy_choices": fy_choices,
            "display": None,
            "yearly_headers": [],
            "yearly_rows": [],
            "not_found": False,
            "yearly_note": "",
            "period_label": "",
        }

        if not branch_id:
            return render(request, self.template_name, context)

        if not request.user.can_access_branch(int(branch_id)):
            messages.error(request, "Access denied for this branch.")
            return render(request, self.template_name, context)

        branch = Branch.objects.get(pk=branch_id)
        qs = self._filtered_queryset(request.user, branch_id)

        if period_type == "daily":
            report = qs.filter(report_date=report_date).first()
            if report:
                display = report_to_display_values(report)
                context["display"] = display
                context["period_label"] = display["period_label"]
                if export == "xlsx":
                    return build_dsr_display_excel(
                        f"sales-daily-{branch.name}-{report_date}.xlsx", display
                    )
                if export == "pdf":
                    return build_dsr_display_pdf(
                        f"sales-daily-{branch.name}-{report_date}.pdf", display
                    )
            else:
                context["not_found"] = True
                context["period_label"] = datetime.strptime(
                    report_date, "%Y-%m-%d"
                ).strftime("%d %b %Y")

        elif period_type == "monthly":
            start, end = month_date_range(report_month)
            month_qs = qs.filter(report_date__gte=start, report_date__lte=end)
            agg = aggregate_dsr_queryset(month_qs)
            label = monthly_period_label(report_month)
            context["period_label"] = label
            if agg:
                display = aggregated_to_display_values(agg, branch.name, label)
                context["display"] = display
                if export == "xlsx":
                    return build_dsr_display_excel(
                        f"sales-monthly-{branch.name}-{report_month}.xlsx", display
                    )
                if export == "pdf":
                    return build_dsr_display_pdf(
                        f"sales-monthly-{branch.name}-{report_month}.pdf", display
                    )
            else:
                context["not_found"] = True

        elif period_type == "yearly":
            fy_start, fy_end = financial_year_range(financial_year)
            year_qs = qs.filter(report_date__gte=fy_start, report_date__lte=fy_end)
            headers, rows = build_yearly_rows(year_qs, financial_year)
            context["yearly_headers"] = headers
            context["yearly_rows"] = rows
            fy_label = dict(fy_choices).get(financial_year, financial_year)
            context["period_label"] = f"Financial year {fy_label}"
            if export == "xlsx":
                return excel_response(
                    f"sales-yearly-{branch.name}-{financial_year}.xlsx",
                    headers,
                    rows,
                )
            if export == "pdf":
                return build_yearly_pdf(
                    f"sales-yearly-{branch.name}-{financial_year}.pdf",
                    branch.name,
                    context["period_label"],
                    headers,
                    rows,
                )
            if not year_qs.exists():
                context["yearly_note"] = "No sales data recorded in this financial year."

        return render(request, self.template_name, context)


class StaffPerformanceReportView(ModulePermissionMixin, View):
    module = "report_staff_performance"
    template_name = "reports/staff_performance_report.html"

    def get(self, request):
        period_type = request.GET.get("period_type", "range")
        if period_type not in dict(STAFF_PERF_PERIOD_TYPES):
            period_type = "range"

        staff_id = request.GET.get("staff", "")
        from_date = request.GET.get("from_date") or default_from_date()
        to_date = request.GET.get("to_date") or default_to_date()
        report_year = request.GET.get("report_year")
        report_month_num = request.GET.get("report_month_num")
        report_month = parse_report_month_params(
            request.GET.get("report_month"),
            report_year,
            report_month_num,
        )
        if not report_year or not report_month_num:
            year_part, month_part = report_month.split("-")
            report_year = report_year or year_part
            report_month_num = report_month_num or str(int(month_part))

        fy_choices = financial_year_choices()
        financial_year = request.GET.get("financial_year") or (
            fy_choices[0][0] if fy_choices else "2025"
        )
        if fy_choices and financial_year not in dict(fy_choices):
            financial_year = fy_choices[0][0]

        run_report = request.GET.get("run") == "1"
        export = request.GET.get("export")
        headers, rows = [], []
        error_message = ""
        period_label = ""

        if period_type == "range" and from_date > to_date:
            error_message = "From date cannot be after to date."
        elif run_report or export:
            headers, rows = build_staff_performance_report(
                period_type=period_type,
                staff_id=int(staff_id) if staff_id else None,
                from_date=from_date,
                to_date=to_date,
                report_month=report_month,
                financial_year=financial_year,
            )
            period_label = staff_perf_period_label(
                period_type,
                from_date=from_date,
                to_date=to_date,
                report_month=report_month,
                financial_year=financial_year,
                fy_choices=fy_choices,
            )
            if export == "xlsx":
                return excel_response(
                    f"staff-performance-{period_type}.xlsx",
                    headers,
                    rows,
                )

        return render(
            request,
            self.template_name,
            {
                "period_types": STAFF_PERF_PERIOD_TYPES,
                "period_type": period_type,
                "staff_list": Staff.objects.filter(active=True).order_by("name"),
                "selected_staff": staff_id,
                "from_date": from_date,
                "to_date": to_date,
                "report_year": report_year,
                "report_month_num": report_month_num,
                "year_choices": calendar_year_choices(),
                "month_choices": MONTH_LABELS,
                "financial_year": financial_year,
                "fy_choices": fy_choices,
                "headers": headers,
                "rows": rows,
                "period_label": period_label,
                "error_message": error_message,
                "ran_report": (run_report or export) and not error_message,
            },
        )


class IncentiveReportView(ModulePermissionMixin, View):
    module = "report_incentive"
    template_name = "reports/incentive_report.html"

    def get(self, request):
        period_type = request.GET.get("period_type", "daily")
        if period_type not in dict(INCENTIVE_PERIOD_TYPES):
            period_type = "daily"

        staff_id = request.GET.get("staff", "")
        report_date = request.GET.get("report_date") or timezone.localdate().isoformat()
        week_start = request.GET.get("week_start") or timezone.localdate().isoformat()
        report_year = request.GET.get("report_year")
        report_month_num = request.GET.get("report_month_num")
        report_month = parse_report_month_params(
            request.GET.get("report_month"),
            report_year,
            report_month_num,
        )
        if not report_year or not report_month_num:
            year_part, month_part = report_month.split("-")
            report_year = report_year or year_part
            report_month_num = report_month_num or str(int(month_part))

        run_report = request.GET.get("run") == "1"
        export = request.GET.get("export")
        headers, rows = [], []
        period_label = ""
        missing_salary = False

        if run_report or export:
            headers, rows, period_label, missing_salary = build_incentive_report(
                period_type=period_type,
                staff_id=int(staff_id) if staff_id else None,
                report_date=report_date,
                week_start=week_start,
                report_month=report_month,
            )
            if export == "xlsx":
                return excel_response(
                    f"incentive-{period_type}.xlsx",
                    headers,
                    rows,
                )
            if export == "pdf":
                return build_incentive_pdf(
                    f"incentive-{period_type}.pdf",
                    period_label,
                    period_type,
                    headers,
                    rows,
                )

        return render(
            request,
            self.template_name,
            {
                "period_types": INCENTIVE_PERIOD_TYPES,
                "period_type": period_type,
                "staff_list": Staff.objects.filter(active=True).order_by("name"),
                "selected_staff": staff_id,
                "report_date": report_date,
                "week_start": week_start,
                "report_year": report_year,
                "report_month_num": report_month_num,
                "year_choices": calendar_year_choices(),
                "month_choices": MONTH_LABELS,
                "headers": headers,
                "rows": rows,
                "period_label": period_label,
                "missing_salary": missing_salary,
                "ran_report": bool(run_report or export),
            },
        )


class InventoryReportView(ModulePermissionMixin, View):
    module = "report_inventory"
    template_name = "reports/inventory_report.html"

    def _branch_options(self, user, report_type):
        branches = get_user_branches(user)
        options = []
        if user.is_central() and report_type in ("statement", "stock-balance"):
            options.append({"value": "central", "label": "Central (HO)"})
        if user.is_central() and report_type in ("receive", "branch-outward"):
            options.append({"value": "", "label": "All branches"})
        options.extend({"value": str(b.pk), "label": b.name} for b in branches)
        return options

    def get(self, request):
        report_type = request.GET.get("report_type", "statement")
        if report_type not in dict(INVENTORY_REPORT_TYPES):
            report_type = "statement"

        branch_raw = request.GET.get("branch")
        if branch_raw is None:
            if report_type in ("statement", "stock-balance"):
                branch_raw = "central" if request.user.is_central() else (
                    str(request.user.branch_ids()[0]) if request.user.branch_ids() else ""
                )
            elif report_type in ("branch-outward", "receive"):
                branch_raw = (
                    "" if request.user.is_central()
                    else (str(request.user.branch_ids()[0]) if request.user.branch_ids() else "")
                )
            else:
                branch_raw = ""

        if branch_raw == "central":
            branch_id = None
            branch_denied = False
        elif not branch_raw:
            branch_id = None
            branch_denied = False
        elif not request.user.can_access_branch(int(branch_raw)):
            branch_id = None
            branch_denied = True
        else:
            branch_id = int(branch_raw)
            branch_denied = False

        product_raw = request.GET.get("product", "")
        product_id = int(product_raw) if product_raw else None

        from_date = request.GET.get("from_date") or default_from_date()
        to_date = request.GET.get("to_date") or default_to_date()
        as_of_date = request.GET.get("as_of_date") or default_to_date()
        run_report = request.GET.get("run") == "1"
        export = request.GET.get("export")

        products = Product.objects.filter(active=True).order_by("name")
        headers, rows = [], []
        error_message = ""

        if branch_denied:
            error_message = "Access denied for the selected branch."
        elif run_report or export:
            if report_type == "stock-balance":
                if not branch_raw:
                    error_message = "Select a branch for stock balance."
                else:
                    headers, rows = build_inventory_report(
                        report_type,
                        branch_id=branch_id,
                        product_id=product_id,
                        from_date=None,
                        to_date=None,
                        as_of_date=as_of_date,
                    )
            elif not product_id:
                error_message = "Select an inventory item."
            elif report_type == "statement" and not branch_raw:
                error_message = "Select a branch."
            else:
                headers, rows = build_inventory_report(
                    report_type,
                    branch_id=branch_id,
                    product_id=product_id,
                    from_date=from_date,
                    to_date=to_date,
                    as_of_date=as_of_date,
                )

        if export == "xlsx" and rows and not error_message:
            return excel_response(f"inventory-{report_type}.xlsx", headers, rows)

        context = {
            "report_types": INVENTORY_REPORT_TYPES,
            "report_type": report_type,
            "branch_options": self._branch_options(request.user, report_type),
            "selected_branch": branch_raw or "",
            "products": products,
            "selected_product": product_raw,
            "from_date": from_date,
            "to_date": to_date,
            "as_of_date": as_of_date,
            "headers": headers,
            "rows": rows,
            "error_message": error_message,
            "ran_report": run_report and not error_message,
        }
        return render(request, self.template_name, context)
