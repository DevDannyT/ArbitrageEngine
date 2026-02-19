const resultsDiv = document.getElementById("results");
const btn = document.getElementById("btnSearch");

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

async function doSearch() {
  const game = document.getElementById("game").value;
  const q = document.getElementById("q").value.trim();
  if (!q) return;

  resultsDiv.innerHTML = `<div class="muted">Searching…</div>`;
  const res = await fetch(`/api/search?game=${encodeURIComponent(game)}&q=${encodeURIComponent(q)}`);
  const data = await res.json();

  if (!Array.isArray(data) || data.length === 0) {
    resultsDiv.innerHTML = `<div class="muted">No results.</div>`;
    return;
  }

  const rows = data.map(card => {
    const setLine = [card.set, card.number].filter(Boolean).join(" • ");
    return `
      <div class="resultRow">
        <div>
          <div class="rTitle">${escapeHtml(card.name)}</div>
          <div class="rSub">${escapeHtml(setLine || "")}</div>
        </div>
        <div>
          <a class="primaryLink" href="/results?game=${encodeURIComponent(game)}&product_id=${encodeURIComponent(card.productId)}">
            Flip Radar →
          </a>
        </div>
      </div>
    `;
  }).join("");

  resultsDiv.innerHTML = rows;
}

btn.addEventListener("click", doSearch);
document.getElementById("q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doSearch();
});
