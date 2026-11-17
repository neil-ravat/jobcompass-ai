# Frontend design — F1

The user's frontend directive explicitly authorizes this additional milestone.
Use Streamlit and HTTP to the existing FastAPI app; preserve backend behavior.

## Plan and review

Palette: canvas `#f7f8fa`, surface `#ffffff`, text `#252c32`, muted text `#637078`,
border `#dfe5e7`, accent `#286351`. Typography: Avenir Next when installed, then
Segoe UI/system sans. Use 14–16px body text and 20–26px headings. Left alignment,
8px spacing units, 6px controls and borders rather than shadows.

```text
Desktop
┌──────────────────┬─────────────────────┬────────────────────────────┐
│ JobCompass       │ Jobs / query summary                             │
│ Search & filters ├─────────────────────┬────────────────────────────┤
│                  │ Compact results     │ Selected job + Apply       │
│ Salary (expand)  │ Selected row        │ Overview / Match / Details │
│ Search / Reset   │ Previous / Next     │ Source and freshness       │
└──────────────────┴─────────────────────┴────────────────────────────┘
Narrow: collapsible filters; Results / Job details switch; one content panel.
```

Reference review: [Linear](https://linear.app) informs restrained typography,
spacing and low-noise surfaces. [LinkedIn Jobs](https://www.linkedin.com/jobs/)
informs the search, list, selected-detail and external-application workflow.
Only public reference pages are inspected; no job records or proprietary assets
are taken from either service. Application listings come only from FastAPI.

The initial idea of separate large job cards was rejected in favor of compact
rows: job titles are long, the corpus is small, and selection needs more emphasis
than decoration. No statistics dashboard, pretend profiles, logos, fit percentages
or AI chat surface. The real ranking score appears only for a submitted query,
with the backend's exact component values and a note that it is not a probability.

The backend gains only an additive plain-text description field. No source HTML
is executed. Streamlit renders escaped source text; HTTP errors clear the result
view. Form submission applies filters together; reset restores a known state.
Country filtering does not promise work authorization. Unknown salaries and
restrictions remain explicitly unknown.

Visual review must include desktop and narrow screenshots, real search/filter
interactions, keyboard controls, selection and external application URLs.
Synthetic responses may be used only in tests; screenshots of the real demo must
use actual backend responses. Streamlit's optional frontend dependency is pinned
to its tested minor series because scoped CSS depends on its rendered structure.
