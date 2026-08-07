let currentAsset;
let currentAnalysis;
let currentChange;

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");
const escapeHtml = (value) => String(value).replace(
  /[&<>"']/g,
  (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character],
);

async function json(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

async function loadAssets() {
  const [assets, health] = await Promise.all([json("/api/assets"), json("/api/health")]);
  $("runtime-status").lastChild.textContent = health.catalog_mode === "mcp" ? " DataHub MCP connected" : " Deterministic demo ready";
  const sourceAssets = assets.filter((asset) => asset.columns.length);
  $("asset-select").innerHTML = sourceAssets.map((asset) => `<option value="${escapeHtml(asset.id)}">${escapeHtml(asset.name)}</option>`).join("");
}

async function discover() {
  currentAsset = $("asset-select").value;
  const [convergence, contract] = await Promise.all([
    json(`/api/assets/${currentAsset}/convergence`),
    json(`/api/assets/${currentAsset}/contract`),
  ]);
  $("score").textContent = convergence.score;
  $("risk").textContent = `${convergence.risk} convergence`;
  $("metrics").innerHTML = Object.entries(convergence.summary).map(([key, value]) => `<div class="metric"><b>${escapeHtml(value)}</b><span>${escapeHtml(key.replaceAll("_", " "))}</span></div>`).join("");
  $("consumer-count").textContent = `${convergence.consumers.length} connected consumers`;
  $("consumers").innerHTML = convergence.consumers.map((item) => `<div class="consumer"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.type.replaceAll("_", " "))} | ${escapeHtml(item.owner)}<br>${escapeHtml(item.domain)} | ${escapeHtml(item.hops)} hop${item.hops === 1 ? "" : "s"}</span></div>`).join("");
  $("contract").innerHTML = contract.dependencies.map((item) => `<div class="contract-row"><code>${escapeHtml(item.column)}</code><span>${escapeHtml(item.roles.join(", ") || "No observed role")}</span><span>${escapeHtml(item.consumer_count)} consumers</span><span class="confidence">${escapeHtml(item.confidence)}</span></div>`).join("");
  $("column-select").innerHTML = contract.dependencies.map((item) => `<option value="${escapeHtml(item.column)}">${escapeHtml(item.column)}</option>`).join("");
  ["overview", "consumer-section", "contract-section", "change-section"].forEach(show);
  $("analysis").classList.add("hidden");
}

$("change-kind").addEventListener("change", () => {
  const kind = $("change-kind").value;
  const input = $("new-value");
  const label = $("new-value-label");
  label.firstChild.textContent = kind === "rename" ? "New name" : kind === "type_change" ? "New type" : "Confirmation";
  input.disabled = kind === "remove";
  input.required = kind !== "remove";
  input.value = kind === "rename" ? "buyer_id" : kind === "type_change" ? "BIGINT" : "";
});

$("change-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const kind = $("change-kind").value;
  const payload = { asset_id: currentAsset, kind, column: $("column-select").value };
  if (kind === "rename") payload.new_name = $("new-value").value;
  if (kind === "type_change") payload.new_type = $("new-value").value;
  try {
    currentChange = payload;
    currentAnalysis = await json("/api/change/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const affected = currentAnalysis.known_affected_consumers;
    $("analysis").innerHTML = `<div class="analysis-grid"><div class="result"><p class="eyebrow">${escapeHtml(currentAnalysis.severity.toUpperCase())} RISK</p><h3>${escapeHtml(affected.length)} known consumers affected</h3><ul>${affected.map((item) => `<li>${escapeHtml(item.name)} - ${escapeHtml(item.owner)}</li>`).join("")}</ul><p class="notice">${escapeHtml(currentAnalysis.unknown_coverage)}</p></div><div class="result"><p class="eyebrow">GENERATED MIGRATION</p><h3>Compatibility SQL</h3><pre>${escapeHtml(currentAnalysis.generated.compatibility_sql)}</pre><h3>Regression test</h3><pre>${escapeHtml(currentAnalysis.generated.regression_tests)}</pre><div class="result-actions"><button id="package-button" class="primary writeback">Generate review package</button><button id="writeback-button" class="writeback">Approve & record</button></div><p id="package-result"></p><p id="writeback-result"></p></div></div>`;
    show("analysis");
    $("package-button").addEventListener("click", generatePackage);
    $("writeback-button").addEventListener("click", writeback);
  } catch (error) { alert(error.message); }
});

async function generatePackage() {
  const result = await json("/api/change/package", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(currentChange) });
  $("package-result").textContent = `Review package ready: ${result.package_id} (${result.files.length} files)`;
}

async function writeback() {
  const result = await json("/api/change/writeback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis: currentAnalysis }) });
  $("writeback-result").textContent = result.mode === "datahub" ? `Published to DataHub: ${result.urn}` : result.mode === "mcp" ? `Recorded through DataHub MCP: ${result.document_id}` : `Demo decision saved: ${result.document_id}`;
}

$("discover-button").addEventListener("click", discover);
loadAssets().then(discover);
