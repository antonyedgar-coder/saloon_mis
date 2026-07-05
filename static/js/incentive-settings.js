document.addEventListener("DOMContentLoaded", function () {
  const tabs = document.querySelectorAll(".incentive-period-tab");
  const panels = document.querySelectorAll(".incentive-period-panel");

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      const period = tab.dataset.period;
      tabs.forEach(function (item) {
        item.classList.toggle("is-active", item === tab);
      });
      panels.forEach(function (panel) {
        panel.classList.toggle("is-hidden", panel.dataset.period !== period);
      });
    });
  });

  function bindRemove(row) {
    const btn = row.querySelector(".incentive-slab-remove");
    if (!btn) return;
    btn.addEventListener("click", function () {
      const tbody = row.closest("tbody");
      if (tbody && tbody.querySelectorAll(".incentive-slab-row").length > 1) {
        row.remove();
      }
    });
  }

  function addSlabRow(periodType) {
    const tbody = document.getElementById("incentive-slab-rows-" + periodType);
    if (!tbody) return;
    const row = document.createElement("tr");
    row.className = "incentive-slab-row";
    row.innerHTML =
      '<td><input name="' + periodType + '_slab_sale_from" type="number" step="0.01" min="0" value="0" class="input"></td>' +
      '<td><input name="' + periodType + '_slab_sale_to" type="number" step="0.01" min="0" value="" class="input" placeholder="No limit"></td>' +
      '<td><input name="' + periodType + '_slab_incentive_value" type="number" step="0.01" min="0" value="0" class="input"></td>' +
      '<td><button type="button" class="btn btn-secondary btn-sm incentive-slab-remove" title="Remove">×</button></td>';
    tbody.appendChild(row);
    bindRemove(row);
  }

  document.querySelectorAll(".incentive-slab-row").forEach(bindRemove);
  document.querySelectorAll(".incentive-add-slab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      addSlabRow(btn.dataset.period);
    });
  });
});
