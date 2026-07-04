function buildExportHref(form, exportType) {
  const periodType = form.querySelector("#period-type")?.value || "daily";
  const branch = form.querySelector('[name="branch"]')?.value || "";
  const date = form.querySelector('[name="report_date"]')?.value || "";
  const year = form.querySelector('[name="report_year"]')?.value || "";
  const monthNum = form.querySelector('[name="report_month_num"]')?.value || "";
  const fy = form.querySelector('[name="financial_year"]')?.value || "";

  let href =
    "?period_type=" +
    encodeURIComponent(periodType) +
    "&branch=" +
    encodeURIComponent(branch) +
    "&export=" +
    encodeURIComponent(exportType);
  if (periodType === "daily") {
    href += "&report_date=" + encodeURIComponent(date);
  } else if (periodType === "monthly") {
    href += "&report_year=" + encodeURIComponent(year);
    href += "&report_month_num=" + encodeURIComponent(monthNum);
  } else if (periodType === "yearly") {
    href += "&financial_year=" + encodeURIComponent(fy);
  }
  return href;
}

function syncSalesReportFilters() {
  const typeSelect = document.getElementById("period-type");
  const form = document.getElementById("sales-report-filters");
  if (!typeSelect || !form) return;

  const periodType = typeSelect.value;
  form.querySelectorAll(".filter-daily").forEach(function (el) {
    el.hidden = periodType !== "daily";
  });
  form.querySelectorAll(".filter-monthly").forEach(function (el) {
    el.hidden = periodType !== "monthly";
  });
  form.querySelectorAll(".filter-yearly").forEach(function (el) {
    el.hidden = periodType !== "yearly";
  });

  const exportXlsx = document.getElementById("export-xlsx");
  const exportPdf = document.getElementById("export-pdf");
  if (exportXlsx) exportXlsx.href = buildExportHref(form, "xlsx");
  if (exportPdf) exportPdf.href = buildExportHref(form, "pdf");
}

document.addEventListener("DOMContentLoaded", function () {
  const typeSelect = document.getElementById("period-type");
  if (!typeSelect) return;
  typeSelect.addEventListener("change", syncSalesReportFilters);
  const form = document.getElementById("sales-report-filters");
  if (form) {
    form.addEventListener("change", syncSalesReportFilters);
  }
  syncSalesReportFilters();
});
