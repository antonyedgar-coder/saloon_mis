function syncInventoryReportFilters() {
  const typeSelect = document.getElementById("inventory-report-type");
  const form = document.getElementById("inventory-report-filters");
  const productSelect = document.getElementById("inventory-product");
  if (!typeSelect || !form) return;

  const reportType = typeSelect.value;
  const showBranch = reportType !== "grn" && reportType !== "outward";
  const isStockBalance = reportType === "stock-balance";

  form.querySelectorAll(".filter-branch").forEach(function (el) {
    el.hidden = !showBranch;
  });
  form.querySelectorAll(".filter-range").forEach(function (el) {
    el.hidden = isStockBalance;
  });
  form.querySelectorAll(".filter-asof").forEach(function (el) {
    el.hidden = !isStockBalance;
  });

  if (productSelect) {
    const blankOption = productSelect.querySelector('option[value=""]');
    if (blankOption) {
      blankOption.textContent = isStockBalance ? "All stock" : "— Select —";
    }
    productSelect.required = !isStockBalance;
  }
}

function buildInventoryExportHref(form) {
  const params = new URLSearchParams(new FormData(form));
  params.set("export", "xlsx");
  params.set("run", "1");
  return "?" + params.toString();
}

document.addEventListener("DOMContentLoaded", function () {
  const typeSelect = document.getElementById("inventory-report-type");
  const form = document.getElementById("inventory-report-filters");
  const exportLink = document.getElementById("inventory-export-xlsx");

  if (typeSelect) {
    typeSelect.addEventListener("change", syncInventoryReportFilters);
    syncInventoryReportFilters();
  }

  if (exportLink && form) {
    exportLink.addEventListener("click", function (event) {
      event.preventDefault();
      window.location.href = buildInventoryExportHref(form);
    });
  }
});
