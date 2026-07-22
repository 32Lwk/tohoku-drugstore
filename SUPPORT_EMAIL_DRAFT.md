Subject: Re: Case 73530481 — Confirmation of preventive measures and answers to your questions

Hi Ian,

Thank you for your follow-up email and for monitoring my usage over the next 24–48 hours.

Please find my confirmation and answers below.

## Confirmation: quota / API key / budget controls

- **API key:** I have **disabled (invalidated) the Places API key** that was associated with this spike, so it can no longer generate traffic.
- **Budget alerts:** I have configured **billing budget alerts** on my Google Cloud account so I am notified early if costs rise again.
- **Quotas:** I am setting / confirming **daily quotas** for Places / Maps usage before any key is re-enabled. Until then, Places API usage from this project remains stopped because the key is disabled.
- **Code-side controls:** I have also updated the application to use Places API (New) with a minimal field mask, removed legacy Text Search, and added hard request budgets per run so usage cannot spike even after a new restricted key is issued.

## 1. What is this specific project used for, and how does your application use Google Maps Platform data?

This is a **personal student learning / development project** (Google Cloud project: **medicine-recommend**).

The application is a research-style tool that collects and maps **drugstore (ドラッグストア) store locations** in Japan (primarily the Tohoku region) for personal study and visualization. It is **not a commercial product** and is not serving public end-user traffic.

How Google Maps Platform was used:
- **Places Text Search** to look up store candidates by query (e.g. drugstore + prefecture / city / chain name)
- Optionally **Geocoding** as a fallback to resolve addresses to coordinates when needed
- Results were stored locally (CSV) and used only for offline analysis / map generation for my own learning

I am now reviewing the medicine-recommend project’s Places API usage more carefully, and I will continue improving both the code and the overall application design so Maps Platform is used only when necessary and within strict limits.

## 2. What caused this sudden spike in usage?

Based on my investigation so far, the spike on **July 21, 2026** was caused by **unintended API requests during development / testing**, not by production user traffic.

More specifically:
- The app used **legacy Places Text Search**, which can trigger billing for **multiple Data SKUs** per request
- During development I ran broad search loops (prefecture / municipality / chain queries, including pagination)
- Multiple development runs appear to have amplified the number of requests far beyond my normal personal usage (~JPY 2,000/month)

I did **not** intend to generate this volume of requests. As soon as I received the Cost Anomaly alert, I stopped the affected usage and began remediation.

## 3. Has the underlying issue been corrected? Will quotas control traffic going forward?

Yes. Both sides are now controlled:

**Immediate stop**
- The affected **Places API key has been disabled**
- Affected API usage has been stopped

**Correction in code / application**
- Migrated away from legacy Text Search to **Places API (New)** with an explicit **minimal field mask** (Pro-tier fields only; no wildcard `*`)
- Removed unnecessary Place Details calls
- Added hard per-run request limits and kill switches in code
- Reviewing the medicine-recommend application design so Places is not called aggressively during development

**Ongoing controls**
- **Budget alerts** are configured
- **Daily quotas** will gate any future usage after a new restricted key is created
- Any future key will be issued only with proper **API restrictions** and will remain unused until those safeguards are confirmed

Therefore, even if development resumes later, the disabled key, quotas, budget alerts, and code budgets will prevent a similar uncontrolled spike.

I would be grateful if you could continue monitoring and proceed with the **one-time courtesy billing adjustment** review after validation. As a university student in Japan supported by a scholarship, this unexpected charge remains far beyond what I can afford.

Please let me know if you need screenshots of the disabled key, budget alert configuration, quota settings, or additional project details.

Thank you again for your help.

Best regards,
Yuto Kawashima
University student (Japan)
Case: 73530481
Billing account: 01FC55-8ED67F-9817DC
Project: medicine-recommend
