function syncIncentiveFilters() {
  const typeSelect = document.getElementById("incentive-period-type");
  const form = document.getElementById("incentive-filters");
  if (!typeSelect || !form) return;

  const periodType = typeSelect.value;
  form.querySelectorAll(".filter-daily").forEach(function (el) {
    el.hidden = periodType !== "daily";
  });
  form.querySelectorAll(".filter-weekly").forEach(function (el) {
    el.hidden = periodType !== "weekly";
  });
  form.querySelectorAll(".filter-monthly").forEach(function (el) {
    el.hidden = periodType !== "monthly";
  });

  updateIncentiveExportLinks(form);
}

function buildIncentiveExportHref(form, exportType) {
  const periodType = form.querySelector("#incentive-period-type")?.value || "daily";
  const staff = form.querySelector('[name="staff"]')?.value || "";
  const reportDate = form.querySelector('[name="report_date"]')?.value || "";
  const weekStart = form.querySelector('[name="week_start"]')?.value || "";
  const year = form.querySelector('[name="report_year"]')?.value || "";
  const monthNum = form.querySelector('[name="report_month_num"]')?.value || "";

  let href =
    "?period_type=" +
    encodeURIComponent(periodType) +
    "&staff=" +
    encodeURIComponent(staff) +
    "&run=1&export=" +
    encodeURIComponent(exportType);

  if (periodType === "daily") {
    href += "&report_date=" + encodeURIComponent(reportDate);
  } else if (periodType === "weekly") {
    href += "&week_start=" + encodeURIComponent(weekStart);
  } else if (periodType === "monthly") {
    href += "&report_year=" + encodeURIComponent(year);
    href += "&report_month_num=" + encodeURIComponent(monthNum);
  }
  return href;
}

function updateIncentiveExportLinks(form) {
  const exportXlsx = document.getElementById("incentive-export-xlsx");
  const exportPdf = document.getElementById("incentive-export-pdf");
  if (exportXlsx) exportXlsx.href = buildIncentiveExportHref(form, "xlsx");
  if (exportPdf) exportPdf.href = buildIncentiveExportHref(form, "pdf");
}

document.addEventListener("DOMContentLoaded", function () {
  const typeSelect = document.getElementById("incentive-period-type");
  const form = document.getElementById("incentive-filters");
  if (!form) return;

  if (typeSelect) {
    typeSelect.addEventListener("change", syncIncentiveFilters);
  }
  form.addEventListener("change", function () {
    updateIncentiveExportLinks(form);
  });
  syncIncentiveFilters();
});
