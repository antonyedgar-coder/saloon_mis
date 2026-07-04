function parseJsonData(id) {
  const el = document.getElementById(id);
  if (!el) return [];
  try {
    const data = JSON.parse(el.textContent);
    return Array.isArray(data) ? data : [];
  } catch (e) {
    return [];
  }
}

function initCombobox(wrapper, itemsOverride) {
  if (!wrapper) return;
  if (wrapper.dataset.comboboxInit === "1") return;
  wrapper.dataset.comboboxInit = "1";

  const input = wrapper.querySelector(".combobox-input");
  const hidden = wrapper.querySelector(".combobox-id");
  const list = wrapper.querySelector(".combobox-list");
  if (!input || !hidden || !list) return;

  const sourceId = wrapper.dataset.source;
  const items = itemsOverride || (sourceId ? parseJsonData(sourceId) : []);

  function openList() {
    wrapper.classList.add("is-open");
    list.removeAttribute("hidden");
  }

  function closeList() {
    wrapper.classList.remove("is-open");
    list.setAttribute("hidden", "hidden");
  }

  function render(filter) {
    const q = (filter || "").trim().toLowerCase();
    list.innerHTML = "";

    const matches = items.filter(function (item) {
      if (!q) return true;
      return String(item.name).toLowerCase().includes(q);
    });

    if (matches.length === 0) {
      const empty = document.createElement("li");
      empty.className = "combobox-empty";
      empty.textContent = q ? "No matches for \"" + filter.trim() + "\"" : "No options available";
      list.appendChild(empty);
      openList();
      return;
    }

    matches.forEach(function (item) {
      const li = document.createElement("li");
      li.dataset.id = item.id;
      li.dataset.name = item.name;
      li.textContent = item.name;
      list.appendChild(li);
    });
    openList();
  }

  function pick(item) {
    if (!item || item.classList.contains("combobox-empty")) return;
    input.value = item.dataset.name;
    hidden.value = item.dataset.id;
    closeList();
  }

  input.addEventListener("focus", function () {
    render(input.value);
  });

  input.addEventListener("input", function () {
    hidden.value = "";
    render(input.value);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeList();
    if (e.key === "ArrowDown" && list.hasAttribute("hidden")) render(input.value);
  });

  list.addEventListener("mousedown", function (e) {
    const item = e.target.closest("li");
    if (item) {
      e.preventDefault();
      pick(item);
    }
  });

  document.addEventListener("click", function (e) {
    if (!wrapper.contains(e.target)) closeList();
  });
}

function initAllComboboxes(root) {
  (root || document).querySelectorAll(".combobox[data-source]").forEach(function (el) {
    initCombobox(el);
  });
}

function createProductLineRow(productItems, preset) {
  const row = document.createElement("div");
  row.className = "line-row line-row-product";
  row.innerHTML =
    '<div class="combobox" data-source="products-data">' +
    '<input type="text" class="combobox-input" placeholder="Type to search product..." autocomplete="off" required>' +
    '<input type="hidden" class="combobox-id" name="product_id">' +
    '<ul class="combobox-list" hidden></ul>' +
    "</div>" +
    '<input name="quantity" type="number" step="0.01" min="0.01" placeholder="Qty" required>' +
    '<button type="button" class="btn btn-secondary btn-sm line-remove" title="Remove">×</button>';

  const combobox = row.querySelector(".combobox");
  initCombobox(combobox, productItems);

  if (preset) {
    const input = row.querySelector(".combobox-input");
    const hidden = row.querySelector(".combobox-id");
    const qty = row.querySelector('input[name="quantity"]');
    if (input) input.value = preset.product_name || "";
    if (hidden) hidden.value = preset.product_id || "";
    if (qty && preset.quantity) qty.value = preset.quantity;
  }

  return row;
}

function initLineRows(options) {
  const container = document.getElementById(options.containerId);
  const addBtn = document.getElementById(options.addButtonId);
  if (!container || !addBtn) return;

  const productItems = parseJsonData(options.productsDataId);

  function addRow(preset) {
    const row = createProductLineRow(productItems, preset);
    container.appendChild(row);
    row.querySelector(".line-remove").addEventListener("click", function () {
      if (container.children.length > 1) row.remove();
    });
  }

  addBtn.addEventListener("click", function () {
    addRow();
  });

  const editLines = options.editLinesId ? parseJsonData(options.editLinesId) : [];
  if (editLines.length) {
    editLines.forEach(function (line) {
      addRow(line);
    });
  } else {
    addRow();
  }
}

function initGrnForm(options) {
  initAllComboboxes();
  initLineRows(options);
  const form = document.getElementById("grn-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      const rows = form.querySelectorAll(".line-row-product");
      let valid = 0;
      rows.forEach(function (row) {
        const pid = row.querySelector('.combobox-id[name="product_id"]');
        const qty = row.querySelector('input[name="quantity"]');
        if (pid && pid.value && qty && qty.value.trim()) valid++;
      });
      if (valid === 0) {
        e.preventDefault();
        alert("Select a product from the list and enter quantity for at least one line.");
      }
    });
  }
}

function createBranchOutwardLineRow(productItems, staffItems, isRetail) {
  const row = document.createElement("div");
  row.className = "line-row line-row-outward" + (isRetail ? " line-row-outward-retail" : "");
  row.innerHTML =
    '<div class="combobox" data-source="products-data">' +
    '<input type="text" class="combobox-input" placeholder="Search product..." autocomplete="off" required>' +
    '<input type="hidden" class="combobox-id" name="product_id">' +
    '<ul class="combobox-list" hidden></ul></div>' +
    '<input name="quantity" type="number" step="0.01" min="0.01" placeholder="Qty" required>' +
    (isRetail
      ? '<input name="line_amount" type="number" step="0.01" min="0.01" placeholder="Amount" class="retail-field" required>' +
        '<div class="combobox retail-field" data-source="staff-data">' +
        '<input type="text" class="combobox-input" placeholder="Search staff..." autocomplete="off" required>' +
        '<input type="hidden" class="combobox-id" name="staff_id">' +
        '<ul class="combobox-list" hidden></ul></div>'
      : "") +
    '<button type="button" class="btn btn-secondary btn-sm line-remove" title="Remove">×</button>';

  initCombobox(row.querySelector('.combobox[data-source="products-data"]'), productItems);
  if (isRetail) {
    initCombobox(row.querySelector('.combobox[data-source="staff-data"]'), staffItems);
  }
  return row;
}

function initBranchOutwardForm(options) {
  const container = document.getElementById(options.containerId);
  const addBtn = document.getElementById(options.addButtonId);
  const typeSelect = document.getElementById(options.typeSelectId);
  const header = document.getElementById(options.headerId);
  if (!container || !addBtn || !typeSelect) return;

  const productItems = parseJsonData(options.productsDataId);
  const staffItems = parseJsonData(options.staffDataId);

  function isRetail() {
    return typeSelect.value === "RETAIL_SALE";
  }

  function syncHeader() {
    if (header) header.classList.toggle("is-retail", isRetail());
  }

  function addRow() {
    const row = createBranchOutwardLineRow(productItems, staffItems, isRetail());
    container.appendChild(row);
    row.querySelector(".line-remove").addEventListener("click", function () {
      if (container.children.length > 1) row.remove();
    });
  }

  function rebuildRows() {
    container.innerHTML = "";
    addRow();
    syncHeader();
  }

  typeSelect.addEventListener("change", rebuildRows);
  addBtn.addEventListener("click", addRow);
  rebuildRows();

  const form = document.getElementById("branch-outward-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      const rows = form.querySelectorAll(".line-row-outward");
      let valid = 0;
      rows.forEach(function (row) {
        const pid = row.querySelector('input[name="product_id"]');
        const qty = row.querySelector('input[name="quantity"]');
        if (!pid || !pid.value || !qty || !qty.value.trim()) return;
        if (isRetail()) {
          const amount = row.querySelector('input[name="line_amount"]');
          const staff = row.querySelector('input[name="staff_id"]');
          if (amount && amount.value.trim() && staff && staff.value) valid++;
        } else {
          valid++;
        }
      });
      if (valid === 0) {
        e.preventDefault();
        alert(
          isRetail()
            ? "Each line needs product, quantity, amount, and staff from the lists."
            : "Add at least one product with quantity."
        );
      }
    });
  }
}
