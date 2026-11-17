"""Run from the repository root: streamlit run frontend/app.py."""

from pathlib import Path
import math

import pycountry
import streamlit as st

from frontend import client
from frontend.presentation import description_html, locations, safe_url, salary, text, timestamp_label, timezones

st.set_page_config(page_title="JobCompass · Find your next role", page_icon=":material/explore:", layout="wide")
st.html(Path(__file__).with_name("styles.css"))

DEFAULTS = {"q": "", "role": "", "country": "", "remote_only": True,
            "min_salary": None, "currency": "", "salary_period": "", "mode": "Keyword match"}
for key, value in {**DEFAULTS, "offset": 0, "page_size": 10, "selected_id": None,
                   "mobile_view": "Results", "form_error": None, "applied": DEFAULTS.copy()}.items():
    st.session_state.setdefault(key, value)


def reset():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state.applied = DEFAULTS.copy()
    st.session_state.offset = 0
    st.session_state.selected_id = None
    st.session_state.form_error = None
    st.session_state.mobile_view = "Results"


def apply_filters():
    values = {key: st.session_state[key] for key in DEFAULTS}
    try:
        client.search_params(values)
    except ValueError as error:
        st.session_state.form_error = str(error)
        return
    st.session_state.applied = values
    st.session_state.offset = 0
    st.session_state.selected_id = None
    st.session_state.form_error = None
    st.session_state.mobile_view = "Results"


def select_job(source_id):
    st.session_state.selected_id = source_id
    st.session_state.mobile_view = "Job details"


def change_page(delta=0):
    st.session_state.offset = max(0, st.session_state.offset + delta * st.session_state.page_size) if delta else 0
    st.session_state.selected_id = None
    st.session_state.mobile_view = "Results"


def paragraph(value, css="muted"):
    st.html(f'<p class="{css}">{text(value)}</p>')


def tags(values):
    st.html('<div class="tags">' + ''.join(f'<span>{text(v)}</span>' for v in values if v) + '</div>')


countries = {country.alpha_2: country.name for country in pycountry.countries}
with st.sidebar:
    st.html('<div class="brand"><span class="brand-mark" aria-hidden="true">◈</span> JobCompass</div>')
    paragraph("A clearer path to your next role.", "brand-caption")
    st.html('<h2 class="filter-heading">Search & filters</h2>')
    with st.form("search_filters", border=False):
        st.text_input("Keywords or skills", placeholder="e.g. frontend web developer", key="q", max_chars=300)
        st.text_input("Role in job title", placeholder="e.g. engineer", key="role", max_chars=120,
                      help="Every word must appear in the job title. Use Keywords or skills to search descriptions too.")
        st.selectbox("Country eligibility", [""] + sorted(countries, key=countries.get), key="country",
                     format_func=lambda value: countries.get(value, "Any country"),
                     help="Only jobs whose stated country restrictions allow this country. This does not confirm work authorization.")
        st.checkbox("Remote jobs only", key="remote_only")
        with st.expander("Salary constraints"):
            st.number_input("Minimum advertised salary", min_value=0.0, max_value=1e12, value=None,
                            step=1000.0, key="min_salary", placeholder="No minimum")
            st.selectbox("Currency", [""] + sorted(c.alpha_3 for c in pycountry.currencies), key="currency",
                         format_func=lambda value: value or "Any currency")
            st.selectbox("Pay period", ["", "annual", "monthly", "fortnightly", "weekly", "hourly"],
                         key="salary_period", format_func=lambda value: value.capitalize() if value else "Any period")
            st.caption("A minimum needs both currency and period. Unreported salaries are excluded when a minimum is set.")
        st.radio("Search mode", list(client.ENDPOINTS), key="mode",
                 help="Keyword match ranks shared words. Semantic match finds similar meaning. Browse jobs requires every keyword.")
        st.form_submit_button("Search jobs", type="primary", icon=":material/search:", width="stretch", on_click=apply_filters)
    st.button("Clear filters", key="clear_filters", width="stretch", on_click=reset)
    if st.session_state.form_error:
        st.error(st.session_state.form_error + " Your previous search is still shown.")
    st.html('<div class="sidebar-note">Real listings. Original application links.<br>Jobs sourced from <a href="https://himalayas.app" target="_blank" rel="noopener noreferrer">Himalayas</a>.</div>')

applied = st.session_state.applied
with st.container(key="topbar"):
    st.html('<div class="page-heading"><div><h1>Find your next role</h1><p>Explore real opportunities. Understand every match.</p></div></div>')

try:
    with st.spinner("Connecting to the job service…"):
        health = client.get_json("/health")
    if health.get("ready") is not True:
        raise client.APIError("Job data needs refreshing. Let the refresh worker finish, then retry.")
    with st.spinner("Finding jobs…"):
        params = client.search_params(applied, st.session_state.offset, st.session_state.page_size)
        page = client.search(applied["mode"], params)
        # A refresh can shrink the result set while the user is on a later page.
        if st.session_state.offset and st.session_state.offset >= page["total"]:
            st.session_state.offset = 0
            st.session_state.selected_id = None
            page = client.search(applied["mode"], client.search_params(applied, 0, st.session_state.page_size))
except client.APIError as error:
    with st.container(key="unavailable"):
        st.html('<h2>Job search is temporarily unavailable</h2>')
        st.error(str(error))
        st.button("Retry connection", icon=":material/refresh:", key="retry_unavailable")
    st.stop()

source_url = safe_url(page["attribution"].get("url"))
source_label = page["attribution"].get("label", "Job source")
st.html(f'<div class="source-strip"><span class="feed-timestamp">Source feed fetched: {text(timestamp_label(page.get("feed_fetched_at")))}</span>'
        + (f'<a href="{text(source_url)}" target="_blank" rel="noopener noreferrer">{text(source_label)}</a>' if source_url else text(source_label)) + '</div>')

summary = []
if applied["q"].strip(): summary.append('Keywords: “' + applied["q"].strip() + '”')
if applied["role"].strip(): summary.append("Title: " + applied["role"].strip())
if applied["country"]: summary.append("Country: " + countries[applied["country"]])
if applied["remote_only"]: summary.append("Remote only")
if applied["min_salary"] is not None:
    summary.append("Minimum salary: " + salary({"salary_min": applied["min_salary"], "salary_max": applied["min_salary"],
                                               "currency": applied["currency"], "salary_period": applied["salary_period"]}))
else:
    if applied["currency"]: summary.append("Currency: " + applied["currency"])
    if applied["salary_period"]: summary.append("Pay period: " + applied["salary_period"].capitalize())
with st.container(key="applied_filters"):
    st.html(f'<div class="search-mode-summary"><span>Search mode</span><strong>{text(applied["mode"])}</strong></div>'
            '<div class="applied-summary"><span class="summary-label">Applied filters</span><div class="tags">'
            + (''.join(f'<span>{text(value)}</span>' for value in summary) if summary else '<span>No filters applied</span>')
            + '</div></div>')

with st.container(key="mobile_nav"):
    st.segmented_control("Workspace", ["Results", "Job details"], key="mobile_view", selection_mode="single", width="stretch")
hidden = "detail" if st.session_state.mobile_view != "Job details" else "results"
st.html(f'<style>@media(max-width:1000px){{.st-key-workspace [data-testid="stColumn"]:has(.st-key-{hidden}){{display:none;}}}}</style>')

items = page["items"]
selected = next((row for row in items if row["source_id"] == st.session_state.selected_id), items[0] if items else None)
st.session_state.selected_id = selected["source_id"] if selected else None
has_query = bool(applied["q"].strip())
with st.container(key="workspace"):
    results_column, detail_column = st.columns([0.92, 1.35], gap="large")
    with results_column, st.container(key="results"):
        st.html(f'<div class="section-heading"><h2>{page["total"]} {"job" if page["total"] == 1 else "jobs"}</h2>'
                f'<span>{"Best matches first" if has_query else "By source update"}</span></div>')
        if not page.get("feed_complete"):
            paragraph("Partial source feed", "small-note")
        if not items:
            st.html('<div class="empty-state"><h3>No jobs match these filters</h3><p>Try a broader keyword, remove the title filter, or clear salary constraints.</p></div>')
            if applied["country"]:
                st.caption("Jobs with unknown country eligibility are excluded. Remote does not always mean worldwide.")
            st.button("Reset search", on_click=reset, key="reset_empty")
        for index, row in enumerate(items):
            is_selected = row["source_id"] == st.session_state.selected_id
            with st.container(key=f"job_{index}_{'selected' if is_selected else 'idle'}"):
                paragraph(row["company"], "company")
                st.button(row["title"], key=f"select_job_{index}", width="stretch", on_click=select_job,
                          args=(row["source_id"],))
                paragraph(locations(row) + (" · Remote" if row.get("remote") else ""), "job-meta")
                paragraph(salary(row), "job-meta")
                if has_query:
                    paragraph(f"Match score {row['score']:.2f}" + (" · Selected" if is_selected else ""), "match-line")
                elif is_selected:
                    paragraph("Selected", "match-line")
        if page["total"]:
            with st.container(key="pagination"):
                previous, count, following = st.columns([1, 1.4, 1])
                previous.button("Previous", disabled=st.session_state.offset == 0, on_click=change_page, args=(-1,), width="stretch")
                count.caption(f"Page {st.session_state.offset // st.session_state.page_size + 1} of {max(1, math.ceil(page['total'] / st.session_state.page_size))}")
                following.button("Next", disabled=st.session_state.offset + st.session_state.page_size >= page["total"], on_click=change_page, args=(1,), width="stretch")
                st.selectbox("Results per page", [5, 10, 20], key="page_size", on_change=change_page)
    with detail_column, st.container(key="detail"):
        if selected is None:
            st.html('<div class="empty-detail"><h2>Your next opportunity starts here</h2><p>Adjust your search to see available jobs and their details.</p></div>')
        else:
            row = selected
            paragraph(row["company"], "detail-company")
            st.html(f'<h2 class="detail-title">{text(row["title"])}</h2>')
            tags(["Remote" if row.get("remote") else None, row.get("employment_type"), *(row.get("seniority") or [])])
            paragraph(locations(row), "detail-location")
            paragraph(salary(row), "detail-salary")
            application = safe_url(row["application_url"])
            if application:
                st.link_button("Apply on Himalayas", application, type="primary", icon=":material/open_in_new:", width="stretch")
            else:
                st.warning("The application link is unavailable for this listing.")
            st.caption("Opens the original application page in a new tab.")
            overview, match, details = st.tabs(["Overview", "Why this match", "Eligibility & source"])
            with overview:
                st.html('<h3 class="subheading">About the role</h3>')
                description = row.get("description") or row.get("excerpt")
                if description and description.split("\n", 1)[0].strip().casefold() == "about the role":
                    description = description.partition("\n")[2].lstrip()
                if description:
                    st.html(f'<div class="description">{description_html(description)}</div>')
                else:
                    st.info("The source did not provide a description for this job.")
                if not row.get("description"):
                    st.caption("The service supplied a summary. See the original listing for full requirements.")
                if row.get("categories"):
                    st.html('<h3 class="subheading">Role categories</h3>')
                    tags(row["categories"])
            with match:
                if not has_query:
                    st.info("Add keywords or use semantic search to see a ranking explanation. Jobs are currently ordered by their source update time.")
                else:
                    st.html(f'<div class="score-summary"><span>Match score</span><strong>{row["score"]:.2f}</strong></div>')
                    st.caption("A ranking score, not a hiring probability or percentage fit.")
                    for component, value in row.get("score_components", {}).items():
                        st.html(f'<div class="score-row"><span>{text(component.capitalize())}</span><strong>{value:.6f}</strong></div>')
                    if row.get("semantic_similarity") is not None:
                        paragraph(f"Cosine similarity: {row['semantic_similarity']:.6f}")
                    st.caption(page.get("rules", {}).get("score", ""))
                    if row.get("matched_terms"):
                        st.html('<h3 class="subheading">Matching words</h3>')
                        tags(row["matched_terms"])
            with details:
                eligibility = {"eligible": "Matches your selected country", "unrestricted": "No country restriction stated",
                               "restricted": "Country restrictions apply", "unknown": "Country eligibility unknown",
                               "ineligible": "Outside the stated country restrictions"}.get(row.get("country_eligibility"), "Not assessed")
                st.html(f'<h3 class="subheading">Eligibility</h3><p>{text(eligibility)}</p>')
                paragraph("Countries: " + locations(row))
                paragraph("Timezones: " + timezones(row))
                st.caption("Country eligibility does not confirm work authorization. Check the description for residency, travel and other requirements.")
                st.html('<h3 class="subheading">Source information</h3>')
                paragraph("Source updated: " + timestamp_label(row.get("source_updated_at")))
                paragraph("Listed expiry: " + timestamp_label(row.get("expires_at")))
                paragraph("Status checked: " + timestamp_label(row.get("status_checked_at")))
                if row.get("validation_issues"):
                    st.warning("Some source fields could not be verified and are shown as unknown.")
                    for issue in row["validation_issues"]:
                        st.caption(issue)
                source_listing = safe_url(row["source_id"])
                if source_listing:
                    st.link_button("View source listing", source_listing, icon=":material/open_in_new:")
            st.html('<div class="detail-footer">Jobs sourced from <a href="https://himalayas.app" target="_blank" rel="noopener noreferrer">Himalayas</a>. Always review the original listing before applying.</div>')

if page.get("data_quality", {}).get("status_errors") or page.get("data_quality", {}).get("rejected_records"):
    st.warning("Some source records could not be verified. Only currently eligible, verified listings are shown.")
