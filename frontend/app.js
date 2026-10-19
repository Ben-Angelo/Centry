const form = document.querySelector("#transaction-form");
const exampleSelect = document.querySelector("#example-select");
const simulateButton = document.querySelector("#simulate-button");
const resultSection = document.querySelector("#result-section");
const formError = document.querySelector("#form-error");
const historyError = document.querySelector("#history-error");
const historyBody = document.querySelector("#history-body");
const backendStatus = document.querySelector("#backend-status");
let historyRecords = [];

const examples = {
  normal: {
    amount: 18000,
    history_avg_amount: 20000,
    device_trusted: "true",
    recent_transaction_count: 1,
    new_payee: "false",
    failed_attempt_count: 0,
    latitude: 6.5244,
    longitude: 3.3792,
    usual_latitude: 6.5244,
    usual_longitude: 3.3792,
  },
  anomalies: {
    amount: 70000,
    history_avg_amount: 50000,
    device_trusted: "false",
    recent_transaction_count: 4,
    new_payee: "true",
    failed_attempt_count: 1,
    latitude: 6.5244,
    longitude: 3.3792,
    usual_latitude: 6.5244,
    usual_longitude: 3.3792,
  },
  high: {
    amount: 500000,
    history_avg_amount: 50000,
    device_trusted: "false",
    recent_transaction_count: 6,
    new_payee: "true",
    failed_attempt_count: 3,
    latitude: 6.5244,
    longitude: 3.3792,
    usual_latitude: 9.0765,
    usual_longitude: 7.3986,
  },
};

function readOptionalNumber(value) {
  return value === "" ? null : Number(value);
}

function readOptionalBoolean(value) {
  if (value === "") return null;
  return value === "true";
}

async function apiRequest(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(
      "Cannot reach the Sentry API. Start it with `python -m uvicorn backend.main:app --reload`.",
      { cause: error },
    );
  }
  const body = await response.json();
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
  }
  return body;
}

function setBackendStatus(status, message) {
  backendStatus.dataset.status = status;
  backendStatus.textContent = message;
}

async function checkBackend() {
  try {
    const health = await apiRequest("/health");
    setBackendStatus("connected", `Backend connected · ${health.database}`);
    return true;
  } catch {
    setBackendStatus("offline", "Backend unavailable");
    return false;
  }
}

function populateExample() {
  const values = examples[exampleSelect.value];
  for (const [name, value] of Object.entries(values)) {
    form.elements.namedItem(name).value = value;
  }
}

function renderAssessment(result) {
  resultSection.classList.remove("hidden");
  document.querySelector("#risk-score").textContent = result.risk_score;
  const riskBadge = document.querySelector("#risk-level");
  riskBadge.textContent = `${result.risk_level} risk`;
  riskBadge.className = `risk-badge ${result.risk_level}`;

  const action = result.suggested_action;
  const actionElement = document.querySelector("#suggested-action");
  actionElement.replaceChildren();
  const title = document.createElement("strong");
  title.textContent = action.label;
  const description = document.createElement("span");
  description.textContent = ` — ${action.description}`;
  actionElement.append(title, description);

  const signalList = document.querySelector("#signals");
  signalList.replaceChildren();
  for (const signal of result.detected_signals) {
    const item = document.createElement("li");
    item.className = "signal";
    const name = document.createElement("strong");
    name.textContent = signal.name;
    const points = document.createElement("span");
    points.className = "signal-points";
    points.textContent = `+${signal.points}`;
    const reason = document.createElement("p");
    reason.textContent = signal.reason;
    item.append(name, points, reason);
    signalList.append(item);
  }
  document.querySelector("#assessment-notice").textContent = result.notice;
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatMoney(transaction) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: transaction.currency,
    maximumFractionDigits: 0,
  }).format(transaction.amount);
}

function renderHistory(records) {
  historyRecords = records;
  historyBody.replaceChildren();
  if (records.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.textContent = "No assessments have been saved yet.";
    row.append(cell);
    historyBody.append(row);
    return;
  }
  records.forEach((record, index) => {
    const row = document.createElement("tr");
    row.className = "log-row";
    const values = [
      new Date(record.created_at).toLocaleString(),
      record.transaction_id,
      formatMoney(record.transaction),
      `${record.risk_score}/100`,
      record.risk_level,
      record.suggested_action.label,
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    const detailsCell = document.createElement("td");
    const viewButton = document.createElement("button");
    viewButton.type = "button";
    viewButton.className = "view-log-entry";
    viewButton.dataset.recordIndex = index;
    viewButton.textContent = "View";
    viewButton.setAttribute("aria-label", `View assessment ${record.transaction_id}`);
    detailsCell.append(viewButton);
    row.append(detailsCell);
    historyBody.append(row);
  });
}

async function loadHistory() {
  historyError.textContent = "";
  try {
    const connected = await checkBackend();
    if (!connected) {
      throw new Error("The backend is offline. Start it using the command shown above.");
    }
    renderHistory(await apiRequest("/transactions?limit=50"));
    setBackendStatus("connected", "Backend connected");
  } catch (error) {
    historyError.textContent = `Could not load history: ${error.message}`;
    if (error.cause) {
      setBackendStatus("offline", "Backend unavailable");
    }
  }
}

exampleSelect.addEventListener("change", populateExample);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";
  simulateButton.disabled = true;
  setBackendStatus("checking", "Sending assessment…");

  const values = new FormData(form);
  const transaction = {
    amount: Number(values.get("amount")),
    currency: "NGN",
    merchant: "Synthetic transfer recipient",
    history_avg_amount: readOptionalNumber(values.get("history_avg_amount")),
    device_trusted: readOptionalBoolean(values.get("device_trusted")),
    recent_transaction_count: readOptionalNumber(values.get("recent_transaction_count")),
    new_payee: readOptionalBoolean(values.get("new_payee")),
    failed_attempt_count: readOptionalNumber(values.get("failed_attempt_count")),
  };
  const latitude = readOptionalNumber(values.get("latitude"));
  const longitude = readOptionalNumber(values.get("longitude"));
  const usualLatitude = readOptionalNumber(values.get("usual_latitude"));
  const usualLongitude = readOptionalNumber(values.get("usual_longitude"));
  if (latitude !== null && longitude !== null) {
    transaction.location = { latitude, longitude };
  }
  if (usualLatitude !== null && usualLongitude !== null) {
    transaction.usual_location = {
      latitude: usualLatitude,
      longitude: usualLongitude,
    };
  }

  try {
    const result = await apiRequest("/transactions/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(transaction),
    });
    setBackendStatus("connected", "Backend connected");
    renderAssessment(result);
    await loadHistory();
  } catch (error) {
    if (error.cause) {
      setBackendStatus("offline", "Backend unavailable");
    }
    formError.textContent = `Assessment failed: ${error.message}`;
  } finally {
    simulateButton.disabled = false;
  }
});

document.querySelector("#refresh-button").addEventListener("click", loadHistory);
historyBody.addEventListener("click", (event) => {
  const button = event.target.closest(".view-log-entry");
  if (!button) return;
  const record = historyRecords[Number(button.dataset.recordIndex)];
  if (record) renderAssessment(record);
});
populateExample();
loadHistory();
