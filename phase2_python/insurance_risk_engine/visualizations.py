#insurance_risk_engine/visualizations.py

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import os
from scipy.stats import gaussian_kde
from scipy import stats
from phase2_python.insurance_risk_engine.inputs import PORTFOLIO


sns.set_theme(style="whitegrid", palette="muted")
os.makedirs("outputs", exist_ok=True)

def _crore_fmt(x, pos):
    return f"Rs{x/1e7:.1f}Cr"

#─────────────────────────────────────────────────────────────────────────────
#Chart 1
#─────────────────────────────────────────────────────────────────────────────

def plot_loss_distribution(losses, metrics, save=True):
    fig, ax = plt.subplots(figsize=(13, 6))

    ax.hist(losses, bins=120, density=True, alpha=0.55,
            color="#4C72B0", label="Simulated Loss Distribution")

    kde = gaussian_kde(losses, bw_method="silverman")
    x   = np.linspace(losses.min(), losses.max(), 600)
    ax.plot(x, kde(x), color="#2E5C9E", linewidth=2.5,
            label="_nolegend_")

    # Shade tail beyond VaR 99%
    ax.axvspan(
        metrics["var_99"],
        losses.max(),
        alpha=0.12,
        color="red",
        label="Tail (>VaR 99%)"
    )

    vlines = [
        (metrics["mean_loss"],     "green",   "--", 1.8,
         f'E[Loss] = Rs{metrics["mean_loss"]/1e7:.2f}Cr'),
        (metrics["net_available"], "black",   ":",  1.8,
         f'Net Available = Rs{metrics["net_available"]/1e7:.2f}Cr'),
        (metrics["var_95"],        "orange",  "--", 1.8,
         f'VaR 95% = Rs{metrics["var_95"]/1e7:.2f}Cr'),
        (metrics["var_99"],        "red",     "--", 2.0,
         f'VaR 99% = Rs{metrics["var_99"]/1e7:.2f}Cr'),
        (metrics["var_99_5"],      "darkred", "-",  2.5,
         f'VaR 99.5% (Underwriting SCR basis) = Rs{metrics["var_99_5"]/1e7:.2f}Cr'),
    ]
    for value, color, ls, lw, label in vlines:
        ax.axvline(value, color=color, linestyle=ls,
                   linewidth=lw, label=label)

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_crore_fmt))
    ax.set_xlabel("Aggregate Annual Loss (Rs)", fontsize=12)
    ax.set_ylabel("Probability Density", fontsize=12)
    ax.set_title(
        "Insurance Portfolio \u2014 Aggregate Loss Distribution\n"
        "Poisson Frequency \u00d7 Lognormal Severity  |  "
        "100,000 Monte Carlo Simulations",
        fontsize=13,
    )
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    plt.tight_layout()

    if save:
        plt.savefig("outputs/loss_distribution.png",
                    dpi=150, bbox_inches="tight")
    plt.show()
    plt.close(fig)

#─────────────────────────────────────────────────────────────────────────────
#Chart 2
#─────────────────────────────────────────────────────────────────────────────

def plot_severity_comparison(params=None, save=True):
    if params is None:
        params = PORTFOLIO

    from phase2_python.insurance_risk_engine.stochastic_model import get_lognormal_params

    mean      = params["mean_severity"]
    cv        = params["severity_cv"]
    mu, sigma = get_lognormal_params(mean, cv)

    rng     = np.random.default_rng(42)
    samples = rng.lognormal(mu, sigma, size=50_000)
    p99     = float(np.percentile(samples, 99))
    p95     = float(np.percentile(samples, 95))

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # ── Left Panel — Excel Model ─────────────────────────────
    # Filled rectangle to show constant severity
    axes[0].axvspan(
        mean * 0.98, mean * 1.02,
        alpha=0.85, color="#C44E52",
        label=f"All claims = Rs{mean/1e3:.0f}K"
    )

    # Arrow pointing to the spike
    axes[0].annotate(
        f"Every claim\nexactly Rs{mean/1e3:.0f}K",
        xy=(mean, 0.5),
        xytext=(mean * 2.5, 0.65),
        fontsize=10,
        color="#C00000",
        fontweight="bold",
        arrowprops=dict(
            arrowstyle="->",
            color="#C00000",
            lw=2.0
        )
    )

    axes[0].set_xlim(0, mean * 6)
    axes[0].set_ylim(0, 1)
    axes[0].set_title(
        "Excel Model — Constant Severity",
        fontsize=13, color="#C00000",
        fontweight="bold", pad=12
    )
    axes[0].set_xlabel(
        "Individual Claim Amount (Rs)",
        fontsize=11
    )
    axes[0].set_ylabel("Probability Density", fontsize=11)
    axes[0].xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"Rs{x/1e3:.0f}K")
    )
    axes[0].legend(fontsize=10, loc="upper right")

    # ── Right Panel — Python Model ────────────────────────────
    # Main histogram
    n, bins, patches = axes[1].hist(
        samples, bins=120, density=True,
        alpha=0.0, color="#4C72B0"
    )

    # Color the bars by severity zone
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    for patch, center in zip(patches, bin_centers):
        if center < mean * 0.5:
            patch.set_facecolor("#9DC3E6")
            patch.set_alpha(0.8)
        elif center < mean:
            patch.set_facecolor("#4C72B0")
            patch.set_alpha(0.8)
        elif center < p95:
            patch.set_facecolor("#2E75B6")
            patch.set_alpha(0.85)
        elif center < p99:
            patch.set_facecolor("#FF8C00")
            patch.set_alpha(0.85)
        else:
            patch.set_facecolor("#C44E52")
            patch.set_alpha(0.90)

    # Shade extreme tail (>99th percentile)
    axes[1].axvspan(
        p99, samples.max(),
        alpha=0.12,
        color="#C44E52",
        label="_nolegend_"
    )

    # Vertical lines
    axes[1].axvline(
        mean, color="#375623",
        linestyle="--", linewidth=2.2,
        label=f"Mean = Rs{mean/1e3:.0f}K"
    )
    axes[1].axvline(
        p95, color="#FF8C00",
        linestyle="--", linewidth=2.0,
        label=f"95th pctile = Rs{p95/1e3:.0f}K"
    )
    axes[1].axvline(
        p99, color="#C44E52",
        linestyle="-", linewidth=2.5,
        label=f"99th pctile = Rs{p99/1e3:.0f}K"
    )

    # Annotations
    axes[1].annotate(
        f"Most claims\nbelow Rs{mean/1e3:.0f}K",
        xy=(mean * 0.4, max(n) * 0.6),
        xytext=(mean * 1.8, max(n) * 0.75),
        fontsize=9, color="#375623",
        fontweight="bold",
        arrowprops=dict(
            arrowstyle="->",
            color="#375623",
            lw=1.5
        )
    )

    axes[1].annotate(
        f"Rare but severe\nclaims up to\nRs{samples.max()/1e3:.0f}K",
        xy=(p99 * 1.05, max(n) * 0.05),
        xytext=(p99 * 0.65, max(n) * 0.35),
        fontsize=9, color="#C44E52",
        fontweight="bold",
        arrowprops=dict(
            arrowstyle="->",
            color="#C44E52",
            lw=1.5
        )
    )

    axes[1].set_title(
        "Python Model — Lognormal Severity",
        fontsize=13, color="#375623",
        fontweight="bold", pad=12
    )
    axes[1].set_xlabel(
        "Individual Claim Amount (Rs)",
        fontsize=11
    )
    axes[1].set_ylabel("Probability Density", fontsize=11)
    axes[1].xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"Rs{x/1e3:.0f}K")
    )

    # ── Legend boxes at bottom ────────────────────────────────
    legend_items = [
        (plt.Rectangle((0, 0), 1, 1,
         fc="#9DC3E6"), "Small claims < 50% mean"),
        (plt.Rectangle((0, 0), 1, 1,
         fc="#4C72B0"), "Typical claims"),
        (plt.Rectangle((0, 0), 1, 1,
         fc="#FF8C00"), "Large claims 95-99th pctile"),
        (plt.Rectangle((0, 0), 1, 1,
         fc="#C44E52"), "Extreme claims > 99th pctile"),
    ]
    axes[1].legend(
        [item[0] for item in legend_items],
        [item[1] for item in legend_items],
        loc="upper right",
        fontsize=8,
        framealpha=0.9
    )

    # ── Main title ────────────────────────────────────────────
    fig.suptitle(
        "What Python Adds Over Excel\n"
        "Realistic Claim Severity Distribution "
        "(Lognormal vs Constant)",
        fontsize=14,
        fontweight="bold",
        color="#1F4E79",
        y=1.02
    )

    # ── Bottom caption ────────────────────────────────────────
    fig.text(
        0.5, -0.02,
        f"Lognormal parameters: "
        f"μ = {mu:.3f}, σ = {sigma:.3f}  |  "
        f"Mean = Rs{mean/1e3:.0f}K, CV = {cv:.1f}  |  "
        f"n = 50,000 simulated claims",
        ha="center", fontsize=9,
        color="#595959", style="italic"
    )

    plt.tight_layout(pad=2.0)

    if save:
        plt.savefig(
            "outputs/severity_comparison.png",
            dpi=150,
            bbox_inches="tight"
        )
    plt.show()
    plt.close(fig)

#─────────────────────────────────────────────────────────────────────────────
#Chart 3
#─────────────────────────────────────────────────────────────────────────────

def plot_stress_scenarios(results_dict, save=True):
    scenarios = list(results_dict.keys())
    colors    = ["#4C72B0", "#55A868", "#C44E52"]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    def _bar_labels(ax, bars, values, fmt):
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + height * 0.01,
                fmt.format(val),
                ha="center", va="bottom",
                fontsize=9, fontweight="bold",
            )

    values = [results_dict[s]["var_99"] / 1e7 for s in scenarios]
    bars   = axes[0, 0].bar(scenarios, values, color=colors, alpha=0.85)
    _bar_labels(axes[0, 0], bars, values, "Rs{:.2f}Cr")
    axes[0, 0].set_title("VaR 99% (1-in-100 Year Loss)", fontsize=11)
    axes[0, 0].set_ylabel("Rs Crore", fontsize=10)

    values = [results_dict[s]["es_99"] / 1e7 for s in scenarios]
    bars   = axes[0, 1].bar(scenarios, values, color=colors, alpha=0.85)
    _bar_labels(axes[0, 1], bars, values, "Rs{:.2f}Cr")
    axes[0, 1].set_title("Expected Shortfall 99%", fontsize=11)
    axes[0, 1].set_ylabel("Rs Crore", fontsize=10)

    values = [results_dict[s]["ruin_probability"] * 100 for s in scenarios]
    bars   = axes[1, 0].bar(scenarios, values, color=colors, alpha=0.85)
    _bar_labels(axes[1, 0], bars, values, "{:.2f}%")
    axes[1, 0].axhline(5, color="red", linestyle="--",
                       linewidth=1.5, label="5% threshold")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].set_title("Ruin Probability (%)", fontsize=11)
    axes[1, 0].set_ylabel("Probability (%)", fontsize=10)

    values = [results_dict[s]["solvency_ratio"] for s in scenarios]
    bars   = axes[1, 1].bar(scenarios, values, color=colors, alpha=0.85)
    _bar_labels(axes[1, 1], bars, values, "{:.2f}x")
    axes[1, 1].axhline(1.0, color="red", linestyle="--",
                       linewidth=1.5, label="Min = 1.0x")
    axes[1, 1].axhline(1.5, color="orange", linestyle="--",
                       linewidth=1.2, label="Comfortable = 1.5x")
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].set_title("Solvency Ratio", fontsize=11)
    axes[1, 1].set_ylabel("Ratio (x)", fontsize=10)

    fig.suptitle(
        "Stress Scenario Analysis \u2014 Base vs Optimistic vs Stress",
        fontsize=13, fontweight="bold")
    plt.tight_layout()

    if save:
        plt.savefig("outputs/stress_scenarios.png",
                    dpi=150, bbox_inches="tight")
    plt.show()
    plt.close(fig)

#─────────────────────────────────────────────────────────────────────────────
#Chart 4
#─────────────────────────────────────────────────────────────────────────────
def plot_summary_dashboard(metrics, det_results, save=True):
    m   = metrics
    det = det_results

    table_data = [
        ["DETERMINISTIC MODEL", "", ""],
        ["Expected Claim Count",
         f'{det["expected_claim_count"]:,.0f}', ""],
        ["Expected Gross Loss",
         f'Rs {det["expected_gross_loss"]/1e7:.2f} Cr', ""],
        ["Loss Ratio",
         f'{det["loss_ratio"]:.1%}',
         "GOOD" if det["loss_ratio"] < 0.60
         else "REVIEW"],
        ["Combined Ratio",
         f'{det["combined_ratio"]:.1%}',
         "PROFITABLE" if det["combined_ratio"] < 1.0
         else "LOSS-MAKING"],
        ["Net Profit",
         f'Rs {det["net_profit"]/1e7:.2f} Cr',
         "POSITIVE" if det["net_profit"] > 0
         else "NEGATIVE"],
        ["", "", ""],
        
        ["STOCHASTIC RISK METRICS", "", ""],
        ["Mean Loss",
         f'Rs {m["mean_loss"]/1e7:.3f} Cr',
         "Best estimate annual cost"],
        ["Std Deviation",
         f'Rs {m["std_dev"]/1e7:.3f} Cr',
         "Year-to-year variability"],
        ["VaR 95%",
         f'Rs {m["var_95"]/1e7:.3f} Cr',
         "1-in-20 year loss"],
        ["VaR 99%",
         f'Rs {m["var_99"]/1e7:.3f} Cr',
         "1-in-100 year loss"],
        ["VaR 99.5% (SCR basis)",
         f'Rs {m["var_99_5"]/1e7:.3f} Cr',
         "1-in-200 year loss"],
        ["Expected Shortfall 99%",
         f'Rs {m["es_99"]/1e7:.3f} Cr',
         "Average of worst 1% years"],
        ["Ruin Probability",
         f'{m["ruin_probability"]:.2%}',
         "LOW" if m["ruin_probability"] < 0.05
         else "HIGH"],
        ["", "", ""],

        ["UNDERWRITING CAPITAL ADEQUACY (SOLVENCY II STYLE)", "", ""],
        ["Underwriting SCR",
         f'Rs {m["scr"]/1e7:.3f} Cr',
         "Underwriting risk capital only"],
        ["Management Buffer (20%)",
         f'Rs {m["management_buffer"]/1e7:.3f} Cr',
         "Discretionary buffer"],
        ["Total Capital Required",
         f'Rs {m["total_capital_required"]/1e7:.3f} Cr',
         "SCR + buffer"],
        ["Available Capital",
         f'Rs {PORTFOLIO["available_capital"]/1e7:.2f} Cr',
         "Allocated surplus"],
        ["Solvency Ratio",
         f'{m["solvency_ratio"]:.2f}x',
         "SOLVENT" if m["solvency_ratio"] >= 1.0
         else "BREACH"],
        ["Return on Risk Capital",
         f'{m["rorc"]:.1%}',
         "STRONG" if m["rorc"] >= 0.10
         else "REVIEW"],
    ]

    # ── Figure ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.axis("off")
    fig.patch.set_facecolor("white")

    tbl = ax.table(
        cellText  = table_data,
        colLabels = ["Metric", "Value", "Status / Notes"],
        cellLoc   = "left",
        colWidths = [0.40, 0.25, 0.35],
        loc       = "center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.75)

    # ── Row index sets (now correct) ──────────────────────────
    section_rows = {0, 7, 16}
    spacer_rows  = {6, 15}

    good_status = {
        "GOOD", "PROFITABLE", "POSITIVE",
        "LOW", "SOLVENT", "STRONG",
    }
    warn_status = {"REVIEW", "HIGH"}
    bad_status  = {"LOSS-MAKING", "NEGATIVE", "BREACH"}

    cells  = tbl.get_celld()
    n_cols = 3

    for row in range(len(table_data) + 1):
        for col in range(n_cols):
            cell = cells.get((row, col))
            if cell is None:
                continue

            data_idx = row - 1
            cell.set_edgecolor("#CCCCCC")
            cell.set_linewidth(0.5)

            # Header row
            if row == 0:
                cell.set_facecolor("#1F4E79")
                cell.get_text().set_color("white")
                cell.get_text().set_fontweight("bold")
                cell.get_text().set_fontsize(10)

            # Section header rows
            elif data_idx in section_rows:
                cell.set_facecolor("#1F4E79")
                cell.get_text().set_color("white")
                cell.get_text().set_fontweight("bold")
                cell.get_text().set_fontsize(10)
                cell.set_edgecolor("#1F4E79")

            # Spacer rows
            elif data_idx in spacer_rows:
                cell.set_facecolor("white")
                cell.set_edgecolor("white")
                cell.set_linewidth(0)

            # Data rows
            else:
                bg = "white" if data_idx % 2 == 0 else "#F7FAFD"
                cell.set_facecolor(bg)

                if col == 0:
                    cell.get_text().set_color("#1F4E79")
                    cell.get_text().set_fontweight("bold")

                if col == 1:
                    cell.get_text().set_color("#1F4E79")
                    cell.get_text().set_fontweight("bold")

                if col == 2:
                    status_text = table_data[data_idx][2]
                    if status_text in good_status:
                        cell.set_facecolor("#E8F5E9")
                        cell.get_text().set_color("#375623")
                        cell.get_text().set_fontweight("bold")
                    elif status_text in warn_status:
                        cell.set_facecolor("#FFF8E1")
                        cell.get_text().set_color("#BF8F00")
                        cell.get_text().set_fontweight("bold")
                    elif status_text in bad_status:
                        cell.set_facecolor("#FFEBEE")
                        cell.get_text().set_color("#C00000")
                        cell.get_text().set_fontweight("bold")
                    else:
                        cell.get_text().set_color("#595959")

    # ── Title ─────────────────────────────────────────────────
    ax.set_title(
        "Insurance Risk Engine — Results Summary Dashboard",
        fontsize=14,
        fontweight="bold",
        color="#1F4E79",
        pad=20,
    )

    # ── Footer ────────────────────────────────────────────────
    fig.text(
        0.5, 0.01,
        "Collective Risk Model  |  "
        "Poisson x Lognormal  |  "
        "100,000 Monte Carlo Simulations  |  "
        "Solvency II-style underwriting framework",
        ha="center",
        fontsize=9,
        color="#595959",
        style="italic",
    )

    plt.tight_layout(pad=2.0)

    if save:
        plt.savefig(
            "outputs/summary_dashboard.png",
            dpi=150,
            bbox_inches="tight"
        )

    plt.show()
    plt.close(fig)

#─────────────────────────────────────────────────────────────────────────────
# Chart 5 — MLE Goodness of Fit (Lognormal vs Observed Claims)
#─────────────────────────────────────────────────────────────────────────────

def plot_mle_fit(params, save=True):

    losses = params["gross_losses"] / 1e5

    mu = params["mu"]
    sigma = params["sigma"]

    plt.style.use("seaborn-v0_8-whitegrid")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # ───────────────── LEFT: HISTOGRAM + FIT ─────────────────
    x = np.linspace(losses.min(), losses.max(), 500)

    pdf = stats.lognorm.pdf(
        x,
        sigma,
        scale=np.exp(mu) / 1e5
    )

    axes[0].hist(
        losses,
        bins=60,
        density=True,
        alpha=0.6,
        color="#4C72B0",
        label="Observed claims"
    )

    axes[0].plot(
        x,
        pdf,
        color="#C44E52",
        linewidth=2,
        label=f"Fitted Lognormal\n(μ={mu:.3f}, σ={sigma:.3f})"
    )

    # Mean lines
    fitted_mean = params["mean"] / 1e5
    model_mean = np.exp(
        params["mu_model"] + params["sigma_model"]**2 / 2
    ) / 1e5

    axes[0].axvline(
        fitted_mean,
        color="green",
        linestyle="--",
        linewidth=1.8,
        label=f"MLE mean: Rs {fitted_mean:.1f}L"
    )

    axes[0].axvline(
        model_mean,
        color="orange",
        linestyle="--",
        linewidth=1.8,
        label=f"Model mean: Rs {model_mean:.1f}L"
    )

    axes[0].set_xlim(left=0)
    axes[0].set_ylim(bottom=0)

    axes[0].set_title("Severity Distribution Fit", fontsize=11)
    axes[0].set_xlabel("Claim Severity (₹ Lakh)")
    axes[0].set_ylabel("Density")
    axes[0].legend()

    # ───────────────── RIGHT: QQ PLOT ─────────────────
    theoretical = stats.lognorm.ppf(
        np.linspace(0.01, 0.99, len(losses)),
        sigma,
        scale=np.exp(mu) / 1e5
    )

    empirical = np.sort(losses)

    axes[1].scatter(
        theoretical,
        empirical,
        s=12,
        color="#4C72B0",
        alpha=0.7
    )

    max_val = max(empirical)

    axes[1].set_xlim(left=0)
    axes[1].set_ylim(bottom=0)

    axes[1].plot(
        [0, max_val],
        [0, max_val],
        linestyle="--",
        color="#C44E52",
        linewidth=2,
        label="45° line (perfect fit)"
    )

    axes[1].fill_between(
        [0, max_val],
        [0, max_val],
        [0, max_val],
        color="#C44E52",
        alpha=0.05
    )

    axes[1].set_title("Q-Q Plot: Lognormal Fit", fontsize=11)
    axes[1].set_xlabel("Theoretical Quantiles (₹ Lakh)")
    axes[1].set_ylabel("Empirical Quantiles (₹ Lakh)")
    axes[1].legend()

    # ───────────────── TITLE ─────────────────
    fig.suptitle(
        "MLE Goodness of Fit: Lognormal vs Observed Claims",
        fontsize=13,
        fontweight="bold"
    )

    plt.tight_layout()

    if save:
        plt.savefig(
            "outputs/mle_goodness_of_fit.png",
            dpi=150,
            bbox_inches="tight"
        )
        
    plt.show()
    plt.close(fig)

#─────────────────────────────────────────────────────────────────────────────
# Chart 6 — IBNR Chain Ladder (PDF-STYLE EXACT)
#─────────────────────────────────────────────────────────────────────────────

def plot_ibnr_chain_ladder(uw_all, save=True):


    plt.style.use("seaborn-v0_8-whitegrid")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # ───────── GLOBAL TITLE (match PDF) ─────────
    fig.suptitle(
        "IBNR Reserving: Chain-Ladder Development Analysis",
        fontsize=13,
        fontweight="bold",
        color="#1F4E79"
    )

    #──────────────────────── LEFT CHART ────────────────────────
    x = uw_all["uw_year"].astype(str)
    positions = np.arange(len(x))
    w = 0.35

    axes[0].bar(
        positions - w/2,
        uw_all["paid_loss"] / 1e7,
        width=w,
        color="#4C72B0",
        label="Paid Loss"
    )

    axes[0].bar(
        positions + w/2,
        uw_all["ibnr_cl"] / 1e7,
        width=w,
        color="#C44E52",
        alpha=0.8,
        label="IBNR (Chain-Ladder)"
    )

    axes[0].set_xticks(positions)
    axes[0].set_xticklabels(x)

    axes[0].set_xlabel("Underwriting Year")
    axes[0].set_ylabel("₹ Crore")

    axes[0].set_title("Paid Loss vs IBNR by UW Year", fontsize=11)

    axes[0].legend()

    axes[0].set_ylim(bottom=0)

    # ───────── ANNOTATIONS (EXACT STYLE) ─────────
    axes[0].annotate(
        "Early stage\n(high IBNR)",
        xy=(positions[-1], uw_all["ibnr_cl"].iloc[-1] / 1e7),
        xytext=(positions[-1] - 0.8, uw_all["ibnr_cl"].iloc[-1] / 1e7 + 0.4),
        fontsize=8,
        color="#C44E52",
        arrowprops=dict(arrowstyle="->", color="#C44E52")
    )

    axes[0].annotate(
        "Mature\n(low IBNR)",
        xy=(positions[0], uw_all["ibnr_cl"].iloc[0] / 1e7),
        xytext=(positions[0] + 0.1, uw_all["ibnr_cl"].iloc[0] / 1e7 + 0.4),
        fontsize=8,
        color="#375623",
        arrowprops=dict(arrowstyle="->", color="#375623")
    )

    #──────────────────────── RIGHT CHART ────────────────────────
    axes[1].plot(
        uw_all["uw_year"],
        uw_all["ult_factor"],
        "o-",
        color="#4C72B0",
        lw=2,
        ms=7,
        label="Development Factor"
    )

    # Threshold lines
    axes[1].axhline(
        1.0,
        linestyle="--",
        color="#2E7D32",
        lw=1.5,
        label="Fully developed (~1.0)"
    )
    
    axes[1].axhline(
        1.5,
        linestyle=":",
        color="#F39C12",
        lw=1.5,
        label="Higher reserve need"
    )

    # ───────── LABEL EACH POINT ─────────
    for _, row in uw_all.iterrows():
        
        if row["ult_factor"] <= 1.1:
            label = "Mature"
            color = "#375623"
        elif row["ult_factor"] <= 1.5:
            label = "Developing"
            color = "#BF8F00"
        else:
            label = "Early"
            color = "#C44E52"
            
        axes[1].annotate(
            label,
            xy=(row["uw_year"], row["ult_factor"]),
            xytext=(row["uw_year"] + 0.1, row["ult_factor"] + 0.05),
            fontsize=7,
            color=color
        )
        
    axes[1].set_xlabel("Underwriting Year")
    axes[1].set_ylabel("Development Factor")
        
    axes[1].set_title(
        "Claims Development Pattern\n(Chain-Ladder)",
        fontsize=11
    )
        
    axes[1].set_ylim(1.0, 2.3)

    axes[1].legend(fontsize=8)
    axes[1].invert_xaxis()

    # ───────── FINAL LAYOUT ─────────
    plt.tight_layout()

    if save:
        plt.savefig(
            "outputs/ibnr_chain_ladder.png",
            dpi=150,
            bbox_inches="tight"
        )
        
    plt.show()
    plt.close(fig)