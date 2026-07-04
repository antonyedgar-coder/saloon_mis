function syncStaffPerfFilters() {
  const typeSelect = document.getElementById("staff-perf-period-type");
  const form = document.getElementById("staff-perf-filters");
  if (!typeSelect || !form) return;

  const periodType = typeSelect.value;
  form.querySelectorAll(".filter-range").forEach(function (el) {
    el.hidden = periodType !== "range";
  });
  form.querySelectorAll(".filter-monthly").forEach(function (el) {
    el.hidden = periodType !== "monthly";
  });
  form.querySelectorAll(".filter-yearly").forEach(function (el) {
    el.hidden = periodType !== "yearly";
  });
}

function buildStaffPerfExportHref(form) {
  const params = new URLSearchParams(new FormData(form));
  params.set("export", "xlsx");
  params.set("run", "1");
  return "?" + params.toString();
}

document.addEventListener("DOMContentLoaded", function () {
  const typeSelect = document.getElementById("staff-perf-period-type");
  const form = document.getElementById("staff-perf-filters");
  const exportLink = document.getElementById("staff-perf-export-xlsx");

  if (typeSelect) {
    typeSelect.addEventListener("change", syncStaffPerfFilters);
    syncStaffPerfFilters();
  }

  if (exportLink && form) {
    exportLink.addEventListener("click", function (event) {
      event.preventDefault();
      window.location.href = buildStaffPerfExportHref(form);
    });
  }
});
