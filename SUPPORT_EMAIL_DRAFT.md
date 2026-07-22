Subject: Re: Case 73530481 — Implementation review and preventive measures completed

Hi Ian,

Thank you for your follow-up.

I am writing to confirm that I have completed the required remediation and preventive measures, so you may begin monitoring my usage.

## Implementation / migration status

- I have **stopped all Places API usage** on project **medicine-recommend** (Project ID: **340042923793**).
- I have reviewed the application’s Places-related implementation.
- I am **not currently using legacy Text Search**.
- I am also **re-evaluating whether this application should use Places API at all**.
- If Maps usage is resumed in the future, I will use **Places API (New) / Text Search (New)** only, with an explicit **minimal field mask**, and only for narrowly scoped lookups (e.g. nearby pharmacy). Until that decision is made, Places remains disabled.

## Preventive measures applied

1. **Places API key disabled (invalidated)** — the key involved in the July 21 spike can no longer generate traffic.
2. **Budget alerts configured** on my Google Cloud billing account.
3. **Daily quotas / API controls** — I am applying quota limits and will only issue a new key (if ever needed) with proper **API key restrictions**.
4. **Application redesign** — I am revising the medicine-recommend app so Places is not called unintentionally during development/testing.

Because the API key is disabled, current Places usage is effectively **zero**, and a similar spike cannot recur under the current setup.

Please proceed with your **24–48 hour usage monitoring**. After validation, I would be deeply grateful if you could continue with the **one-time courtesy billing adjustment** review.

As a university student in Japan using this project only for personal learning and development, the unexpected charge remains far beyond what I can afford. Thank you again for your support.

Please let me know if you need screenshots of the disabled key, budget alert settings, quota configuration, or any other details.

Best regards,
Yuto Kawashima
University student (Japan)
Case: 73530481
Billing account: 01FC55-8ED67F-9817DC
Project: medicine-recommend (Project ID: 340042923793)
