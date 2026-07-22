Subject: Re: Case 73530481 — Understood: enabling Places API (New) with preventive measures

Hi Ian,

Thank you for the clarification. I understand your point.

Disabling the API key stops all traffic, so there is no usage for your team to monitor. I will therefore **enable Places API (New)** and apply the preventive measures first, then confirm back to you so monitoring can begin.

## Plan (before I ask you to start monitoring)

1. **Enable Places API (New)** on project medicine-recommend (Project ID: 340042923793)
2. **Create / configure an API key** with restrictions:
   - API restrictions: Places API (New) only (and Geocoding only if strictly needed)
   - Application restrictions as appropriate
3. **Set low daily quotas** so usage cannot spike again
4. Keep **budget alerts** enabled
5. Ensure the application uses **Text Search (New)** with an explicit **minimal field mask** only (no legacy Text Search, no wildcard `*`)
6. Generate only a **small, controlled amount of test usage** under those limits, so you can validate that the preventive measures are effective

I will complete these steps carefully and reply again once everything is in place and ready for your 24–48 hour monitoring.

Thank you for your guidance, and for continuing to assist with the one-time courtesy billing adjustment review afterward.

Best regards,
Yuto Kawashima
University student (Japan)
Case: 73530481
Billing account: 01FC55-8ED67F-9817DC
Project: medicine-recommend (Project ID: 340042923793)
