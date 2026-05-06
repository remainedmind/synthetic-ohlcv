const DOM = {
  form: document.getElementById("configForm"),
  status: document.getElementById("status"),
  previewButton: document.getElementById("previewButton"),
  saveButton: document.getElementById("saveButton"),
  metrics: document.getElementById("metrics"),
  priceChart: document.getElementById("priceChart"),
  volumeChart: document.getElementById("volumeChart"),
};

const State = {
  controlGroups: [],
  defaultConfig: null,
  inputByPath: new Map(),
  cycleControls: [],
  cycleList: null,
  datasetNameInput: null,
  previewTimer: null,
};

async function jsonRequest(url, body = null) {
  const response = await fetch(url, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : null,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

function setStatus(message, isError = false) {
  DOM.status.textContent = message;
  DOM.status.classList.toggle("error", isError);
}

function buildControls(groups) {
  DOM.form.replaceChildren(...groups.map((group, index) => groupElement(group, index)));
}

function groupElement(group, index) {
  const details = document.createElement("details");
  details.className = "control-group";
  details.open = index < 4;
  const summary = document.createElement("summary");
  summary.textContent = group.label;
  const body = document.createElement("div");
  body.className = "group-body";

  const cycleControls = group.controls.filter((control) => control.path.startsWith("cycles[]"));
  const controls = group.controls.filter((control) => !control.path.startsWith("cycles[]"));
  body.replaceChildren(...controls.map((control) => controlElement(control)));

  if (cycleControls.length > 0) {
    State.cycleControls = cycleControls;
    const actions = document.createElement("div");
    actions.className = "actions";
    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.textContent = "Add Cycle";
    addButton.addEventListener("click", () => {
      State.cycleList.appendChild(cycleElement({}));
      schedulePreview();
    });
    State.cycleList = document.createElement("div");
    State.cycleList.className = "cycle-list";
    actions.replaceChildren(addButton);
    body.append(actions, State.cycleList);
  }

  details.append(summary, body);
  return details;
}

function controlElement(control, value = control.default) {
  const wrapper = document.createElement("div");
  wrapper.className = control.input === "checkbox" ? "toggle-row" : "field";
  const fieldId = `field-${control.path.replace(/[^A-Za-z0-9_-]/g, "-")}-${Math.random()
    .toString(36)
    .slice(2)}`;
  const label = document.createElement("label");
  label.htmlFor = fieldId;
  label.textContent = control.label;
  const hint = hintElement(control, fieldId);
  const head = document.createElement("div");
  head.className = "field-head";
  head.replaceChildren(label, hint);
  const input = inputElement(control, fieldId, value);

  if (control.input === "checkbox") {
    wrapper.replaceChildren(head, input);
  } else if (control.input === "slider") {
    const valueLabel = document.createElement("span");
    valueLabel.textContent = String(value);
    valueLabel.dataset.sliderValue = fieldId;
    input.addEventListener("input", () => {
      valueLabel.textContent = input.value;
    });
    const meta = document.createElement("div");
    meta.className = "slider-meta";
    meta.replaceChildren(
      textNode(String(control.min)),
      valueLabel,
      textNode(String(control.max)),
    );
    wrapper.replaceChildren(head, input, meta);
  } else {
    wrapper.replaceChildren(head, input);
  }

  if (control.path === "export.dataset_name") {
    State.datasetNameInput = input;
  } else if (!control.path.startsWith("cycles[]")) {
    State.inputByPath.set(control.path, { control, input });
  }
  return wrapper;
}

function hintElement(control, fieldId) {
  const wrap = document.createElement("span");
  wrap.className = "field-hint-wrap";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "hint";
  button.textContent = "?";
  button.setAttribute("aria-label", `${control.label} help`);
  button.setAttribute("aria-expanded", "false");
  const tooltip = document.createElement("span");
  tooltip.id = `${fieldId}-hint`;
  tooltip.className = "tooltip";
  tooltip.role = "tooltip";
  tooltip.hidden = true;
  tooltip.textContent = control.hint;
  button.setAttribute("aria-describedby", tooltip.id);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleHint(button, tooltip);
  });
  button.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeHint(button, tooltip);
  });
  wrap.replaceChildren(button, tooltip);
  return wrap;
}

function toggleHint(button, tooltip) {
  const shouldOpen = tooltip.hidden;
  closeAllHints();
  if (shouldOpen) {
    tooltip.hidden = false;
    button.setAttribute("aria-expanded", "true");
  }
}

function closeHint(button, tooltip) {
  tooltip.hidden = true;
  button.setAttribute("aria-expanded", "false");
}

function closeAllHints() {
  for (const tooltip of document.querySelectorAll(".tooltip")) {
    tooltip.hidden = true;
  }
  for (const button of document.querySelectorAll(".hint")) {
    button.setAttribute("aria-expanded", "false");
  }
}

function inputElement(control, id, value) {
  if (control.input === "select") {
    const select = document.createElement("select");
    select.id = id;
    select.replaceChildren(
      ...control.options.map((option) => {
        const element = document.createElement("option");
        element.value = option.value;
        element.textContent = option.label;
        return element;
      }),
    );
    select.value = value;
    return select;
  }

  const input = document.createElement("input");
  input.id = id;
  input.type = control.input === "slider" ? "range" : control.input;
  input.value = value;
  if (control.input === "checkbox") {
    input.checked = Boolean(value);
  }
  for (const key of ["min", "max", "step"]) {
    if (control[key] !== null && control[key] !== undefined) {
      input[key] = control[key];
    }
  }
  return input;
}

function textNode(value) {
  return document.createTextNode(value);
}

function applyConfig(config) {
  for (const [path, entry] of State.inputByPath.entries()) {
    setControlValue(entry.input, getPath(config, path));
  }
  State.cycleList.replaceChildren(...config.cycles.map((cycle) => cycleElement(cycle)));
}

function cycleElement(cycle) {
  const element = document.createElement("div");
  element.className = "cycle";
  const head = document.createElement("div");
  head.className = "cycle-head";
  const title = document.createElement("strong");
  title.textContent = "Cycle";
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "danger";
  remove.textContent = "Remove";
  remove.addEventListener("click", () => {
    element.remove();
    schedulePreview();
  });
  head.replaceChildren(title, remove);

  const grid = document.createElement("div");
  grid.className = "cycle-grid";
  grid.replaceChildren(
    ...State.cycleControls.map((control) => {
      const key = control.path.replace("cycles[].", "");
      const field = controlElement(control, cycle[key] ?? control.default);
      field.dataset.cyclePath = key;
      return field;
    }),
  );
  element.addEventListener("input", schedulePreview);
  element.addEventListener("change", schedulePreview);
  element.append(head, grid);
  return element;
}

function setControlValue(input, value) {
  if (input.type === "checkbox") {
    input.checked = Boolean(value);
  } else {
    input.value = value;
    const valueLabel = document.querySelector(`[data-slider-value="${input.id}"]`);
    if (valueLabel) valueLabel.textContent = String(value);
  }
}

function readConfig() {
  const config = structuredClone(State.defaultConfig);
  for (const [path, entry] of State.inputByPath.entries()) {
    setPath(config, path, readControlValue(entry.control, entry.input));
  }
  config.cycles = [...State.cycleList.querySelectorAll(".cycle")].map((cycleElement) => {
    const cycle = {};
    for (const field of cycleElement.querySelectorAll("[data-cycle-path]")) {
      const path = `cycles[].${field.dataset.cyclePath}`;
      const control = State.cycleControls.find((candidate) => candidate.path === path);
      const input = field.querySelector("input, select");
      cycle[field.dataset.cyclePath] = readControlValue(control, input);
    }
    return cycle;
  });
  return config;
}

function readControlValue(control, input) {
  if (control.input === "checkbox") return input.checked;
  if (control.input === "text" || control.input === "select") return input.value;
  const number = Number(input.value);
  return Number.isInteger(control.default) ? Math.round(number) : number;
}

function getPath(object, path) {
  return path.split(".").reduce((value, part) => value[part], object);
}

function setPath(object, path, value) {
  const parts = path.split(".");
  const key = parts.pop();
  const target = parts.reduce((current, part) => current[part], object);
  target[key] = value;
}

function formatNumber(value, digits = 2) {
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function renderMetrics(summary) {
  const cards = [
    ["Total Return", `${formatNumber(summary.total_return * 100, 2)}%`],
    ["Log Return Std", formatNumber(summary.log_return_std, 6)],
    ["Max Price Drawdown", `${formatNumber(summary.price_drawdown_max * 100, 2)}%`],
    ["Close Min", formatNumber(summary.close_min, 2)],
    ["Close Max", formatNumber(summary.close_max, 2)],
    [
      "Volume Range",
      `${formatNumber(summary.volume_min, 2)} - ${formatNumber(summary.volume_max, 2)}`,
    ],
  ].map(([label, value]) => {
    const element = document.createElement("div");
    element.className = "metric";
    element.innerHTML = `
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value}</div>
    `;
    return element;
  });
  DOM.metrics.replaceChildren(...cards);
}

async function renderPreview() {
  const config = readConfig();
  setStatus("Generating preview...");
  const payload = await jsonRequest("/api/preview", { config });
  const rows = payload.rows || [];
  const x = rows.map((row) => new Date(row.timestamp));
  await Promise.all([
    Plotly.react(
      DOM.priceChart,
      [
        {
          type: "candlestick",
          x,
          open: rows.map((row) => row.open),
          high: rows.map((row) => row.high),
          low: rows.map((row) => row.low),
          close: rows.map((row) => row.close),
          increasing: { line: { color: "#16a34a" } },
          decreasing: { line: { color: "#dc2626" } },
          name: "Price",
        },
      ],
      plotLayout("Synthetic Candles", "Price"),
      { responsive: true, displaylogo: false, scrollZoom: true },
    ),
    Plotly.react(
      DOM.volumeChart,
      [
        {
          type: "bar",
          x,
          y: rows.map((row) => row.volume),
          marker: { color: "#2563eb" },
          name: "Volume",
        },
      ],
      plotLayout("Volume", "Volume"),
      { responsive: true, displaylogo: false },
    ),
  ]);
  renderMetrics(payload.metadata.summary);
  setStatus(`Preview ready: ${rows.length} rows.`);
}

function plotLayout(title, yTitle) {
  return {
    title: { text: title, x: 0.01 },
    template: "plotly_dark",
    margin: { l: 50, r: 24, t: 48, b: 40 },
    paper_bgcolor: "#18181b",
    plot_bgcolor: "#18181b",
    font: { color: "#e4e4e7" },
    xaxis: { gridcolor: "#3f3f46" },
    yaxis: { title: yTitle, gridcolor: "#3f3f46" },
  };
}

function schedulePreview() {
  clearTimeout(State.previewTimer);
  State.previewTimer = setTimeout(() => {
    renderPreview().catch((error) => setStatus(error.message, true));
  }, 350);
}

async function saveDataset() {
  const config = readConfig();
  setStatus("Saving dataset...");
  const payload = await jsonRequest("/api/save", {
    config,
    dataset_name: State.datasetNameInput.value,
    overwrite: true,
  });
  setStatus(
    `Saved dataset:\n${payload.parquet_path}\n${payload.csv_path}\n${payload.metadata_path}`,
  );
}

async function boot() {
  const [configPayload, schemaPayload] = await Promise.all([
    jsonRequest("/api/default-config"),
    jsonRequest("/api/control-schema"),
  ]);
  State.defaultConfig = configPayload.config;
  State.controlGroups = schemaPayload.groups;
  buildControls(State.controlGroups);
  applyConfig(State.defaultConfig);
  DOM.form.addEventListener("input", schedulePreview);
  DOM.form.addEventListener("change", schedulePreview);
  DOM.previewButton.addEventListener("click", () => {
    renderPreview().catch((error) => setStatus(error.message, true));
  });
  DOM.saveButton.addEventListener("click", () => {
    saveDataset().catch((error) => setStatus(error.message, true));
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".field-hint-wrap")) closeAllHints();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAllHints();
  });
  await renderPreview();
}

boot().catch((error) => setStatus(error.message, true));
