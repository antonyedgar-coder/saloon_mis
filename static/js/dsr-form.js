var DSR_FORM_FIELDS = [
  "net_service_income",
  "membership_card",
  "ear_piercing",
  "other_income",
  "product_sale_18",
  "product_sale_5",
  "gst",
  "bridal_advance",
  "male_walkins",
  "male_income",
  "female_walkins",
  "female_income",
  "kids_walkins",
  "kids_income",
  "card_payment",
  "upi_payment",
  "cash_payment",
  "calls_done",
  "zooty_appointment",
  "google_appointment",
  "just_dial",
  "status_story",
  "broadcast",
  "google_reviews_request",
  "new_clients",
];

var DSR_EMPTY_VALUES = {
  net_service_income: "0",
  membership_card: "0",
  ear_piercing: "0",
  other_income: "0",
  product_sale_18: "0",
  product_sale_5: "0",
  gst: "0",
  bridal_advance: "0",
  male_walkins: "0",
  male_income: "0",
  female_walkins: "0",
  female_income: "0",
  kids_walkins: "0",
  kids_income: "0",
  card_payment: "0",
  upi_payment: "0",
  cash_payment: "0",
  calls_done: "0",
  zooty_appointment: "0",
  google_appointment: "0",
  just_dial: "0",
  status_story: "",
  broadcast: "0",
  google_reviews_request: "",
  new_clients: "0",
};

function parseFieldAmount(form, name) {
  const el = form.querySelector('[name="' + name + '"]');
  if (!el) return 0;
  return parseFloat(el.value) || 0;
}

function formatAmount(value) {
  return value.toFixed(2);
}

function calcAvb(income, walkins) {
  if (!walkins || walkins <= 0) return "—";
  return formatAmount(income / walkins);
}

function sumSelectorValues(form, selector) {
  let total = 0;
  form.querySelectorAll(selector).forEach(function (el) {
    total += parseFloat(el.value) || 0;
  });
  return total;
}

function applyFormValues(form, values) {
  DSR_FORM_FIELDS.forEach(function (name) {
    const el = form.querySelector('[name="' + name + '"]');
    if (!el) return;
    const value = values[name];
    el.value = value === undefined || value === null ? "" : value;
  });
}

function createDsrStaffRow(staffItems, preset) {
  const row = document.createElement("div");
  row.className = "line-row line-row-staff dsr-staff-row";
  row.innerHTML =
    '<div class="combobox" data-source="staff-data">' +
    '<input type="text" class="combobox-input" placeholder="Search staff..." autocomplete="off">' +
    '<input type="hidden" class="combobox-id" name="staff_id">' +
    '<ul class="combobox-list" hidden></ul></div>' +
    '<input name="staff_amount" type="number" step="0.01" min="0.01" class="dsr-staff-amount" placeholder="Amount">' +
    '<input name="staff_mem_card" type="number" step="1" min="0" class="dsr-staff-extra" placeholder="0" title="Mem Card">' +
    '<input name="staff_makeup" type="number" step="0.01" min="0" class="dsr-staff-extra" placeholder="0" title="Make-Up">' +
    '<input name="staff_google_review_with_photo" type="number" step="1" min="0" class="dsr-staff-extra" placeholder="0" title="GR with Photo">' +
    '<input name="staff_google_review_without_photo" type="number" step="1" min="0" class="dsr-staff-extra" placeholder="0" title="GR without Photo">' +
    '<input name="staff_ear_piercing" type="number" step="1" min="0" class="dsr-staff-extra" placeholder="0" title="Ear Piercing">' +
    '<input name="staff_watts" type="number" step="1" min="0" class="dsr-staff-extra" placeholder="0" title="Watts">' +
    '<input name="staff_ot" type="number" step="0.01" min="0" class="dsr-staff-extra" placeholder="0" title="OT">' +
    '<button type="button" class="btn btn-secondary btn-sm line-remove" title="Remove">×</button>';

  const combobox = row.querySelector(".combobox");
  initCombobox(combobox, staffItems);

  if (preset) {
    const input = row.querySelector(".combobox-input");
    const hidden = row.querySelector(".combobox-id");
    const amount = row.querySelector('input[name="staff_amount"]');
    if (input && preset.staff_name) input.value = preset.staff_name;
    if (hidden && preset.staff_id) hidden.value = preset.staff_id;
    if (amount && preset.amount) amount.value = preset.amount;
    const fieldMap = [
      ["staff_mem_card", "mem_card"],
      ["staff_makeup", "makeup"],
      ["staff_google_review_with_photo", "google_review_with_photo"],
      ["staff_google_review_without_photo", "google_review_without_photo"],
      ["staff_ear_piercing", "ear_piercing"],
      ["staff_watts", "watts"],
      ["staff_ot", "ot"],
    ];
    fieldMap.forEach(function (pair) {
      const el = row.querySelector('input[name="' + pair[0] + '"]');
      const value = preset[pair[1]];
      if (el && value !== undefined && value !== null && value !== "") {
        el.value = value;
      }
    });
  }

  return row;
}

function updateWalkinAvb(form) {
  form.querySelectorAll(".dsr-walkin-row").forEach(function (row) {
    const count = parseFloat(row.querySelector(".walkin-count")?.value) || 0;
    const income = parseFloat(row.querySelector(".walkin-income")?.value) || 0;
    const avbEl = row.querySelector(".walkin-avb");
    if (avbEl) avbEl.textContent = calcAvb(income, count);
  });

  const totalCount = sumSelectorValues(form, ".walkin-count");
  const totalIncome = sumSelectorValues(form, ".walkin-income");
  const totalAvb = document.getElementById("walkin-total-avb");
  if (totalAvb) totalAvb.textContent = calcAvb(totalIncome, totalCount);
}

function validateDsrTotals(form) {
  const netService = parseFieldAmount(form, "net_service_income");
  const incomeTotal = sumSelectorValues(form, ".dsr-income-field");
  const walkinIncome = sumSelectorValues(form, ".walkin-income");
  const paymentTotal = sumSelectorValues(form, ".dsr-payment-field");
  const staffTotal = sumSelectorValues(form, ".dsr-staff-amount");

  const errors = [];
  if (walkinIncome > netService + 0.004) {
    errors.push(
      "Walk Ins income total (₹" + formatAmount(walkinIncome) + ") cannot be greater than Net Service income (₹" + formatAmount(netService) + ")."
    );
  }
  if (staffTotal > netService + 0.004) {
    errors.push(
      "Staff Performance total (₹" + formatAmount(staffTotal) + ") cannot be greater than Net Service income (₹" + formatAmount(netService) + ")."
    );
  }
  if (incomeTotal > paymentTotal + 0.004) {
    errors.push(
      "Total Income (₹" + formatAmount(incomeTotal) + ") cannot be greater than Mode of Payment total (₹" + formatAmount(paymentTotal) + ")."
    );
  }
  return errors;
}

function updateSummaryBar(form, errors) {
  const netService = parseFieldAmount(form, "net_service_income");
  const incomeTotal = sumSelectorValues(form, ".dsr-income-field");
  const walkinIncome = sumSelectorValues(form, ".walkin-income");
  const paymentTotal = sumSelectorValues(form, ".dsr-payment-field");
  const staffTotal = sumSelectorValues(form, ".dsr-staff-amount");

  const setText = function (id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setText("summary-net-service", "₹" + formatAmount(netService));
  setText("summary-walkins", "₹" + formatAmount(walkinIncome));
  setText("summary-staff", "₹" + formatAmount(staffTotal));
  setText("summary-income", "₹" + formatAmount(incomeTotal));
  setText("summary-payment", "₹" + formatAmount(paymentTotal));

  const statusEl = document.getElementById("summary-status");
  if (statusEl) {
    if (errors.length) {
      statusEl.textContent = errors.length + " issue(s) to fix";
      statusEl.className = "dsr-summary-status dsr-summary-bad";
    } else {
      statusEl.textContent = "Ready to save";
      statusEl.className = "dsr-summary-status dsr-summary-ok";
    }
  }
}

function updateDsrTotals(form) {
  const incomeTotal = sumSelectorValues(form, ".dsr-income-field");
  const walkinCount = sumSelectorValues(form, ".walkin-count");
  const walkinIncome = sumSelectorValues(form, ".walkin-income");
  const paymentTotal = sumSelectorValues(form, ".dsr-payment-field");
  const staffTotal = sumSelectorValues(form, ".dsr-staff-amount");
  const netService = parseFieldAmount(form, "net_service_income");

  const incomeEl = document.getElementById("income-total");
  const walkinCountEl = document.getElementById("walkin-total-count");
  const walkinIncomeEl = document.getElementById("walkin-total-income");
  const paymentEl = document.getElementById("payment-total");
  const staffEl = document.getElementById("staff-total");
  const liveErrors = document.getElementById("dsr-live-errors");

  if (incomeEl) incomeEl.textContent = formatAmount(incomeTotal);
  if (walkinCountEl) walkinCountEl.textContent = String(Math.round(walkinCount));
  const walkinIncomeText = formatAmount(walkinIncome);
  if (walkinIncomeEl) walkinIncomeEl.textContent = walkinIncomeText;
  form.querySelectorAll(".walkin-total-income-sync").forEach(function (el) {
    el.textContent = walkinIncomeText;
  });
  if (paymentEl) paymentEl.textContent = formatAmount(paymentTotal);
  if (staffEl) staffEl.textContent = formatAmount(staffTotal);
  updateWalkinAvb(form);

  const errors = validateDsrTotals(form);
  const incomePaymentMismatch = incomeTotal > paymentTotal + 0.004;
  const serviceWalkinMismatch = walkinIncome > netService + 0.004;
  const serviceStaffMismatch = staffTotal > netService + 0.004;

  const incomeElOut = document.getElementById("income-total");
  const paymentElOut = document.getElementById("payment-total");
  const staffElOut = document.getElementById("staff-total");
  const netServiceEl = form.querySelector(".dsr-net-service");

  if (incomeElOut) incomeElOut.classList.toggle("dsr-mismatch", incomePaymentMismatch);
  if (paymentElOut) paymentElOut.classList.toggle("dsr-mismatch", incomePaymentMismatch);
  form.querySelectorAll(".walkin-total-income-sync").forEach(function (el) {
    el.classList.toggle("dsr-mismatch", serviceWalkinMismatch);
  });
  if (staffElOut) staffElOut.classList.toggle("dsr-mismatch", serviceStaffMismatch);
  if (netServiceEl) {
    netServiceEl.classList.toggle("dsr-mismatch", serviceWalkinMismatch || serviceStaffMismatch);
  }

  updateSummaryBar(form, errors);

  if (liveErrors) {
    if (errors.length) {
      liveErrors.hidden = false;
      liveErrors.innerHTML =
        "<strong>Please correct totals before saving:</strong><ul>" +
        errors.map(function (e) { return "<li>" + e + "</li>"; }).join("") +
        "</ul>";
    } else {
      liveErrors.hidden = true;
      liveErrors.innerHTML = "";
    }
  }
}

function setSectionExpanded(section, expanded) {
  if (!section) return;
  section.classList.toggle("is-collapsed", !expanded);
  const head = section.querySelector(".master-section-head");
  if (head) head.setAttribute("aria-expanded", expanded ? "true" : "false");
}

function initMasterSectionToggles(form) {
  form.querySelectorAll(".master-section").forEach(function (section) {
    const head = section.querySelector(".master-section-head");
    if (!head) return;
    head.addEventListener("click", function () {
      setSectionExpanded(section, section.classList.contains("is-collapsed"));
    });
  });
}

function expandSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (!section) return;
  setSectionExpanded(section, true);
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function initDsrForm(options) {
  const container = document.getElementById(options.linesContainerId);
  const addBtn = document.getElementById(options.addButtonId);
  const form = document.getElementById("dsr-form");
  const loadStatus = document.getElementById("dsr-load-status");
  if (!container || !addBtn || !form) return;

  const staffItems = parseJsonData(options.staffDataId);
  const editLines = parseJsonData(options.editLinesId);
  const loadUrl = options.loadUrl || "/reports/dsr/load/";
  const loadBtn = document.getElementById("dsr-load-btn");
  const saveBtn = document.getElementById("dsr-save-btn");
  let loadTimer = null;
  let loadRequestId = 0;
  let isEditing = form.dataset.editing === "1";

  function refreshTotals() {
    updateDsrTotals(form);
  }

  function setEditingMode(editing) {
    isEditing = !!editing;
    form.dataset.editing = isEditing ? "1" : "0";
    if (saveBtn) saveBtn.textContent = isEditing ? "Update DSR" : "Save DSR";
  }

  function setLoadStatus(message, tone) {
    if (!loadStatus) return;
    loadStatus.hidden = !message;
    loadStatus.textContent = message || "";
    loadStatus.className = "dsr-load-status";
    if (tone) loadStatus.classList.add("dsr-load-status-" + tone);
  }

  function rebuildStaffLines(lines) {
    container.innerHTML = "";
    const rows = lines && lines.length ? lines : [null];
    rows.forEach(function (preset) {
      const row = createDsrStaffRow(staffItems, preset);
      container.appendChild(row);
      row.querySelector(".line-remove").addEventListener("click", function () {
        if (container.children.length > 1) {
          row.remove();
          refreshTotals();
        }
      });
      row.querySelector(".dsr-staff-amount").addEventListener("input", refreshTotals);
    });
    refreshTotals();
  }

  function addRow(preset) {
    const row = createDsrStaffRow(staffItems, preset);
    container.appendChild(row);
    row.querySelector(".line-remove").addEventListener("click", function () {
      if (container.children.length > 1) {
        row.remove();
        refreshTotals();
      }
    });
    row.querySelector(".dsr-staff-amount").addEventListener("input", refreshTotals);
    refreshTotals();
  }

  function loadReportForSelection() {
    const branchId = form.querySelector('[name="branch_id"]')?.value;
    const reportDate = form.querySelector('[name="report_date"]')?.value;
    if (!branchId || !reportDate) return;

    const requestId = ++loadRequestId;
    form.classList.add("dsr-form-loading");
    setLoadStatus("Loading report…", "loading");

    fetch(loadUrl + "?branch_id=" + encodeURIComponent(branchId) + "&report_date=" + encodeURIComponent(reportDate), {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (requestId !== loadRequestId) return;
        form.classList.remove("dsr-form-loading");
        if (data.error) {
          setLoadStatus(data.error, "error");
          return;
        }
        if (data.found) {
          applyFormValues(form, data.form);
          rebuildStaffLines(data.staff_lines);
          setEditingMode(true);
          setLoadStatus(
            "Editing saved report for this branch and date. Change values and click Update DSR.",
            "found"
          );
        } else {
          applyFormValues(form, DSR_EMPTY_VALUES);
          rebuildStaffLines([]);
          setEditingMode(false);
          setLoadStatus("No saved report for this date — enter a new one and click Save DSR.", "new");
        }
        refreshTotals();
      })
      .catch(function () {
        if (requestId !== loadRequestId) return;
        form.classList.remove("dsr-form-loading");
        setLoadStatus("Could not load report. Check your connection.", "error");
      });
  }

  function scheduleLoad() {
    clearTimeout(loadTimer);
    loadTimer = setTimeout(loadReportForSelection, 350);
  }

  if (editLines.length) {
    rebuildStaffLines(editLines);
  } else {
    rebuildStaffLines([]);
  }

  addBtn.addEventListener("click", function () {
    addRow();
  });

  form.querySelectorAll(
    ".dsr-income-field, .walkin-count, .walkin-income, .dsr-payment-field, .dsr-net-service"
  ).forEach(function (el) {
    el.addEventListener("input", refreshTotals);
  });

  const branchEl = form.querySelector('[name="branch_id"]');
  const dateEl = form.querySelector('[name="report_date"]');
  if (branchEl) branchEl.addEventListener("change", scheduleLoad);
  if (dateEl) dateEl.addEventListener("change", scheduleLoad);
  if (loadBtn) {
    loadBtn.addEventListener("click", function () {
      loadReportForSelection();
    });
  }

  if (!form.dataset.preserveValues) {
    scheduleLoad();
  } else if (editLines.length || isEditing) {
    setEditingMode(true);
    setLoadStatus(
      "Editing saved report for this branch and date. Change values and click Update DSR.",
      "found"
    );
  }

  initMasterSectionToggles(form);
  refreshTotals();

  form.addEventListener("submit", function (e) {
    let staffLineError = false;
    form.querySelectorAll(".dsr-staff-row").forEach(function (row) {
      const staff = row.querySelector('input[name="staff_id"]');
      const amount = row.querySelector('input[name="staff_amount"]');
      const hasStaff = staff && staff.value;
      const hasAmount = amount && amount.value.trim();
      if ((hasStaff && !hasAmount) || (!hasStaff && hasAmount)) {
        staffLineError = true;
      }
    });
    if (staffLineError) {
      e.preventDefault();
      expandSection("sec-staff");
      alert("Select a staff name from the list and enter an amount for each line.");
      return;
    }

    const errors = validateDsrTotals(form);
    if (errors.length) {
      e.preventDefault();
      const msg = errors.join("\n\n");
      if (msg.indexOf("Walk Ins") !== -1) expandSection("sec-walkins");
      else if (msg.indexOf("Staff Performance") !== -1) expandSection("sec-staff");
      else if (msg.indexOf("Mode of Payment") !== -1 || msg.indexOf("Total Income") !== -1) expandSection("sec-payment");
      else expandSection("sec-income");
      alert(msg);
    }
  });
}
