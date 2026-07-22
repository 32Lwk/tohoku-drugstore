Subject: Re: Case 73530481 — Confirmation of preventive measures and answers to your questions

Hi Ian,

Thank you for your follow-up email and for monitoring my usage over the next 24–48 hours.

Please find my confirmation and answers below.

## Confirmation: quota / API key / budget controls

- **API key:** I have **disabled (invalidated) the Places API key** that was associated with this spike, so it can no longer generate traffic.
- **Budget alerts:** I have configured **billing budget alerts** on my Google Cloud account so I am notified early if costs rise again.
- **Quotas:** I am setting / confirming **daily quotas** for Places / Maps usage before any key is re-enabled. Until then, Places API usage from this project remains stopped because the key is disabled.
- **Application review:** I am also reviewing whether this application should use Places API at all, and I will not re-enable Maps access until that review and the safeguards below are complete.

## 1. What is this specific project used for, and how does your application use Google Maps Platform data?

This Google Cloud project **medicine-recommend** (Project ID: **340042923793**) is a **personal learning and development project** operated by me, a university student in Japan.

The application is an **AI-assisted tool with a chat UI** that recommends **over-the-counter (OTC) medicines** for personal study and development. It is **not a commercial service** and is used only by me for learning and development.

Regarding Google Maps Platform:
- I had been **considering** using Places data only for **limited store-location lookups** (for example, nearby pharmacies).
- It was **not** intended as a core, high-volume feature of the product.
- I am currently **re-evaluating whether this application should use Places API at all**.
- As part of that review, I have already disabled the Places API key, configured budget alerts, and begun revising the related code and the overall application design so that any future Maps usage (if resumed) would be strictly limited and controlled.

## 2. What caused this sudden spike in usage?

Based on my investigation so far, the spike on **July 21, 2026** was caused by **unintended API requests during development / testing**, not by production user traffic or public end users.

More specifically:
- Usage came from **Places API – Text Search (legacy)** under project **medicine-recommend**
- During development/testing related to the limited “nearby pharmacy / store location” idea, requests appear to have been generated far beyond what I expected
- Legacy Text Search can trigger billing for **multiple Data SKUs** per request, which amplified the cost
- My normal monthly Google Cloud spend had been around **JPY 2,000**, so this was completely unexpected

I did **not** intend to generate this volume of requests. As soon as I received the Cost Anomaly alert, I stopped the affected usage and began remediation.

## 3. Has the underlying issue been corrected? Will quotas control traffic going forward?

Yes. Traffic is now controlled, and the underlying approach is being corrected:

**Immediate stop**
- The affected **Places API key has been disabled**
- Places API usage from this project has been stopped

**Application / design correction (in progress)**
- I am reviewing **whether medicine-recommend should use Places API at all**
- I am revising the related code and the application design so Places is not called unintentionally during development
- If Maps usage is ever resumed, it will be only for narrowly scoped lookups, using **Places API (New)** with an explicit **minimal field mask**, and with hard request limits in code

**Ongoing controls**
- **Budget alerts** are already configured
- **Daily quotas** will gate any future usage after a new restricted key is created
- Any future key will be issued only with proper **API restrictions**, and will remain unused until those safeguards are confirmed

Therefore, the disabled key, budget alerts, quotas, and the application redesign will prevent a similar uncontrolled spike going forward.

I would be grateful if you could continue monitoring and proceed with the **one-time courtesy billing adjustment** review after validation. As a university student in Japan supported by a scholarship, this unexpected charge remains far beyond what I can afford.

Please let me know if you need screenshots of the disabled key, budget alert configuration, quota settings, or additional project details.

Thank you again for your help.

Best regards,
Yuto Kawashima
University student (Japan)
Case: 73530481
Billing account: 01FC55-8ED67F-9817DC
Project: medicine-recommend (Project ID: 340042923793)
