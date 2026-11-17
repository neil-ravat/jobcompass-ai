# JobCompass — Professional Frontend Design & Integration

## Role

Act as a Senior Frontend Engineer, Product Designer, and UI/UX Reviewer.

**Objective:** Build a polished, modern job-search and recommendation application that integrates with the existing JobCompass FastAPI backend.

This is an additional frontend milestone. Preserve all existing backend functionality, PostgreSQL integration, semantic retrieval, filtering, ranking, tests, and ingestion logic.

**The result must feel like a real software product, not an AI-generated portfolio dashboard.**

## 1. Design References

Study these real products for inspiration:

**Reference A — Linear**
https://linear.app

Study:
- Clean, minimal interface
- Typography and information hierarchy
- Sidebar navigation
- Precise spacing and alignment
- Subtle borders and interaction states
- Professional, restrained design language

**Reference B — LinkedIn Jobs**
https://www.linkedin.com/jobs/

Study:
- Job-search workflow
- Search and filter interactions
- Scannable job listings
- Selected-job detail panels
- Clear application actions

**Design instruction:** Combine Linear's visual refinement with LinkedIn Jobs' practical search experience. Do not copy either product's branding, exact layouts, or proprietary assets.

Use these products as references for interaction design and visual quality.

## 2. Visual Direction

Create a restrained, high-quality productivity application.

Preferred characteristics:
- Neutral light theme with an optional dark mode
- Off-white or white backgrounds
- Charcoal typography
- One restrained accent color
- Clear font hierarchy
- Compact spacing
- Subtle borders
- Minimal shadows
- Consistent spacing and component styles
- Responsive, purposeful layouts

Avoid:
- Excessive gradients
- Glassmorphism
- Oversized rounded cards
- Decorative KPI dashboards
- Fake analytics
- Emoji-heavy interfaces
- Giant AI-themed headings
- Unnecessary animations
- Generic chatbot layouts
- Random visual decorations

Use simple, functional components rather than adding elements purely to fill space.

## 3. Main Application Layout

Design a three-panel desktop workspace.

**Left panel — Search and filters**
- Job keyword search
- Role or skills input
- Country eligibility filter
- Remote-work filter
- Salary constraints with currency and pay-period validation
- Search-mode selection
- Clear/reset filters

**Center panel — Job results**
- Compact job listings
- Job title and company
- Location and remote status
- Salary when available
- Relevant matching information
- Clearly differentiated selected state
- Pagination
- Loading, empty and error states

**Right panel — Selected job**
- Full job information available from the backend
- Explainable match/ranking breakdown
- Eligibility and restrictions
- Relevant descriptions or requirements
- Source attribution
- Original job application link
- Clear external application action

For narrower screens, adapt the layout intelligently instead of simply shrinking three columns.

## 4. Backend Integration

Use the existing FastAPI backend.

Available endpoints include:
- GET /health
- GET /jobs
- GET /recommendations
- GET /search
- POST /agent/query (optional, credential-dependent)

Use the actual endpoint contracts from the repository.

Do not invent scores, job listings, salaries, eligibility decisions, companies, or application URLs.

The frontend must communicate with FastAPI over HTTP. Do not query PostgreSQL directly from the frontend.

Use Streamlit for the fastest reliable integration unless repository inspection identifies a concrete reason for a different approach. Avoid unnecessary new infrastructure.

The app must work without an OpenAI API key using deterministic and semantic search. Display AI-assisted functionality only when it is actually available.

## 5. UX Quality

Implement:
- Predictable navigation
- Clear search/filter state
- Useful empty-result messages
- Loading indicators
- Accessible controls
- Readable job descriptions
- Responsive layouts
- Clear API-unavailable messages
- Consistent typography
- Original source/application links

Do not display fabricated statistics, candidate profiles, or recommendations.

## 6. Implementation Process

1. Inspect the existing backend schemas and endpoints.
2. Implement the frontend using the actual API responses.
3. Start the frontend and backend locally.
4. Test real job searches and filters.
5. Inspect the interface in a browser.
6. Capture screenshots at desktop and narrow viewport sizes.
7. Identify and correct alignment, spacing, readability, interaction and responsiveness issues.
8. Repeat visual review until the major problems are resolved.
9. Run the existing backend regression tests and add suitable frontend/integration tests.
10. Document the exact startup commands.

Do not rewrite working backend components or add unrelated features.

## 7. Deliverables

- Fully integrated frontend
- Working job-search and recommendation experience
- Clean visual design
- Desktop and mobile/narrow-screen screenshots
- Successful frontend–backend tests
- Updated README
- Local Git checkpoint
- Concise implementation and testing report

## Acceptance Criteria

A user must be able to open JobCompass, search real jobs, apply filters, inspect ranking explanations, review a selected job and open its original application link.

All displayed data must come from the existing backend.

**Proceed with implementation immediately. Do not ask conceptual questions or pause for routine design approvals.**

Stop after delivering the tested integrated application.