// The little JavaScript the app needs. Everything that talks to the server is HTMX.

// Picking a test fills in its usual unit (stored on each <option> as data-unit)
document.addEventListener("change", (event) => {
    const select = event.target.closest("select[name=test_id]");
    if (!select) return;
    const unit = select.selectedOptions[0]?.dataset.unit;
    const unitInput = select.closest("form, tr")?.querySelector("input[name=unit]");
    if (unit && unitInput) unitInput.value = unit;
});

// Filter box: hide table rows that don't contain the typed text
function applyFilter() {
    const filter = document.getElementById("filter");
    if (!filter) return;
    const words = filter.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    document.querySelectorAll("#results-body tr[data-search]").forEach((row) => {
        row.hidden = !words.every((word) => row.dataset.search.includes(word));
    });
}
document.addEventListener("input", (event) => {
    if (event.target.id === "filter") applyFilter();
});
document.addEventListener("htmx:afterSettle", applyFilter); // Keep the filter applied after the table refreshes
