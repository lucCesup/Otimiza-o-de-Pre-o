const BACKEND_BASE = "http://127.0.0.1:5000";

function $(id) {
  return document.getElementById(id);
}

async function postJSON(path, body) {
  try {
    const res = await fetch(BACKEND_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => null);
    return { ok: res.ok, data };
  } catch (err) {
    return { ok: false, data: { error: err.message || String(err) } };
  }
}

// ----------------------
// Helpers
// ----------------------
function parsePairs(text) {
  return text
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const [pStr, qStr] = l.split(/[;,]/).map((x) => x.trim());
      return { price: +pStr, quantity: +qStr };
    });
}

// ----------------------
// Otimização direta
// ----------------------
async function onOptimize() {
  const alpha = +$("alpha").value;
  const beta = +$("beta").value;
  const c = +$("c").value;
  const F = +$("F").value;
  const pMin = +$("pMin").value;
  const pMax = +$("pMax").value;

  const payload = { alpha, beta, c, F, pMin, pMax };
  const { ok, data } = await postJSON("/optimize", payload);

  $("optOut").innerHTML = ok
    ? renderOptimize(data)
    : `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

// ----------------------
// Fit + Otimização
// ----------------------
async function onFitAndOptimize() {
  const points = parsePairs($("data").value);

  // 1) Ajusta a demanda
  const fitRes = await postJSON("/fit", { data: points });
  if (!fitRes.ok) {
    $("fitOut").innerHTML = `<pre>${JSON.stringify(
      fitRes.data,
      null,
      2
    )}</pre>`;
    return;
  }

  const fit = fitRes.data;
  const alpha = fit.alpha;
  const beta = fit.beta;

  // 2) Otimiza usando alpha/beta estimados
  const c = +$("fit_c").value;
  const F = +$("fit_F").value;
  const pMin = +$("fit_pMin").value;
  const pMax = +$("fit_pMax").value;

  const payload = { alpha, beta, c, F, pMin, pMax };
  const optRes = await postJSON("/optimize", payload);

  $("fitOut").innerHTML = optRes.ok
    ? renderFit(fit) + renderOptimize(optRes.data)
    : `<pre>${JSON.stringify(optRes.data, null, 2)}</pre>`;
}

// ----------------------
// Render dos resultados
// ----------------------
function renderOptimize(j) {
  const badge = j.usedBoundary
    ? '<span class="badge">ótimo na borda</span>'
    : "";

  return `
    <p><strong>Preço ótimo:</strong> R$ ${j.pOpt.toFixed(2)} ${badge}</p>
    <ul>
      <li>Quantidade ótima: ${j.qOpt.toFixed(2)} consultas/mês</li>
      <li>Receita: R$ ${j.revenue.toFixed(2)}</li>
      <li>Lucro: R$ ${j.profitOpt.toFixed(2)}</li>
      <li>Margem média: ${(j.margin * 100).toFixed(1)}%</li>
      <li>Elasticidade no ponto ótimo: ${j.elasticity.toFixed(3)}</li>
    </ul>
    <details>
      <summary>Ver derivação simbólica</summary>
      <pre>
π(p)   = ${j.derivation?.objective ?? "—"}
π'(p)  = ${j.derivation?.d1 ?? "—"}
π''(p) = ${j.derivation?.d2 ?? "—"}
p*     = ${j.derivation?.pStarFormula ?? "—"}</pre>
    </details>
    <details>
      <summary>JSON bruto</summary>
      <pre>${JSON.stringify(j, null, 2)}</pre>
    </details>
  `;
}

function renderFit(j) {
  const sinal = j.slope >= 0 ? "+" : "-";
  const absSlope = Math.abs(j.slope);

  return `
    <p><strong>Demanda estimada (OLS):</strong>
       q = ${j.intercept.toFixed(3)} ${sinal} ${absSlope.toFixed(3)}·p
       (R² = ${j.r2.toFixed(3)})</p>
    <p><em>Forma usada no modelo:</em>
       q(p) = α − β·p, com α = ${j.alpha.toFixed(
         3
       )}, β = ${j.beta.toFixed(3)}</p>
  `;
}

// ----------------------
// Listeners
// ----------------------
window.addEventListener("DOMContentLoaded", () => {
  $("btnOptimize").addEventListener("click", onOptimize);
  $("btnFit").addEventListener("click", onFitAndOptimize);
});
