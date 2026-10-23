// Draws the chart on the charts page from the JSON the server embeds (#chart-data)
const SERIES_COLORS = ["#2b5eb0", "#9e2a47", "#067647", "#b54708"];

function drawChart() {
    const chart = document.getElementById("chart");
    const dataElement = document.getElementById("chart-data");
    if (!chart || !dataElement || !window.Plotly) return;
    const { series } = JSON.parse(dataElement.textContent);

    const traces = series.map((s, i) => ({
        x: s.dates,
        y: s.values,
        name: s.unit || "no unit",
        type: "scatter",
        mode: "lines+markers",
        line: { color: SERIES_COLORS[i % SERIES_COLORS.length], width: 2 },
        marker: { size: 8 },
        hovertemplate: "%{x|%Y-%m-%d}<br><b>%{y}</b> " + (s.unit || "") + "<extra></extra>",
        // Units have different scales (e.g. FT4: ~15 pmol/l vs ~1.3 ng/dl). Sharing one axis would
        // squash the smaller one flat, so the first unit uses the left axis and the rest the right one.
        yaxis: i === 0 ? "y" : "y2",
    }));
    const axisTitle = (index) => ({
        text: series[index].unit || "no unit",
        font: { color: traces.length > 1 ? SERIES_COLORS[index] : undefined },
    });

    Plotly.newPlot(chart, traces, {
        margin: { t: 35, r: traces.length > 1 ? 60 : 20, b: 40, l: 60 }, // Top space keeps the toolbar off the axis labels
        showlegend: traces.length > 1,
        legend: { orientation: "h", y: -0.15 },
        xaxis: { type: "date" },
        yaxis: { title: axisTitle(0), zeroline: false },
        ...(traces.length > 1 && {
            yaxis2: { title: axisTitle(1), overlaying: "y", side: "right", showgrid: false, zeroline: false,
                      tickmode: "auto" }, // Its own round tick numbers, not lined up with the left axis
        }),
        hovermode: "closest",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { family: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" },
    }, {
        responsive: true,  // Resize with the window
        displaylogo: false,
        modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"],
    });
}

document.addEventListener("DOMContentLoaded", drawChart);     // Page opened directly, e.g. /charts?test=12
document.addEventListener("htmx:afterSettle", drawChart);     // A test was picked from the dropdown
document.addEventListener("htmx:historyRestore", drawChart);  // Back / forward
