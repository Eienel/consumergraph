let currentAsset;
let currentAnalysis;

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");

async function json(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

async function loadAssets() {
  const assets = await json("/api/assets");
  const sourceAssets = assets.filter((asset) => asset.columns.length);
  $("asset-select").innerHTML = sourceAssets.map((asset) => `<option value="${asset.id}">${asset.name}</option>`).join("");
}

async function discover() {
  currentAsset = $("asset-select").value;
  const [convergence, contract] = await Promise.all([
    json(`/api/assets/${currentAsset}/convergence`),
    json(`/api/assets/${currentAsset}/contract`),
  ]);
  $("score").textContent = convergence.score;
  $("risk").textContent = `${convergence.risk} convergence`;
  $("metrics").innerHTML = Object.entries(convergence.summary).map(([key, value]) => `<div class="metric"><b>${value}</b><span>${key.replaceAll("_", " ")}</span></div>`).join("");
  $("consumer-count").textContent = `${convergence.consumers.length} connected consumers`;
  $("consumers").innerHTML = convergence.consumers.map((item) => `<div class="consumer"><strong>${item.name}</strong><span>${item.type.replaceAll("_", " ")} · ${item.owner}<br>${item.domain} · ${item.hops} hop${item.hops === 1 ? "" : "s"}</span></div>`).join("");
  $("contract").innerHTML = contract.dependencies.map((item) => `<div class="contract-row"><code>${item.column}</code><span>${item.roles.join(", ") || "No observed role"}</span><span>${item.consumer_count} consumers</span><span class="confidence">${item.confidence}</span></div>`).join("");
  $("column-select").innerHTML = contract.dependencies.map((item) => `<option value="${item.column}">${item.column}</option>`).join("");
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
    currentAnalysis = await json("/api/change/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const affected = currentAnalysis.known_affected_consumers;
    $("analysis").innerHTML = `<div class="analysis-grid"><div class="result"><p class="eyebrow">${currentAnalysis.severity.toUpperCase()} RISK</p><h3>${affected.length} known consumers affected</h3><ul>${affected.map((item) => `<li>${item.name} — ${item.owner}</li>`).join("")}</ul><p class="notice">${currentAnalysis.unknown_coverage}</p></div><div class="result"><p class="eyebrow">GENERATED MIGRATION</p><h3>Compatibility SQL</h3><pre>${currentAnalysis.generated.compatibility_sql}</pre><h3>Regression test</h3><pre>${currentAnalysis.generated.regression_tests}</pre><button id="writeback-button" class="primary writeback">Approve & write back</button><p id="writeback-result"></p></div></div>`;
    show("analysis");
    $("writeback-button").addEventListener("click", writeback);
  } catch (error) { alert(error.message); }
});

async function writeback() {
  const result = await json("/api/change/writeback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis: currentAnalysis }) });
  $("writeback-result").textContent = result.mode === "datahub" ? `Published to DataHub: ${result.urn}` : `Demo decision saved: ${result.document_id}`;
}

$("discover-button").addEventListener("click", discover);
loadAssets().then(discover);

