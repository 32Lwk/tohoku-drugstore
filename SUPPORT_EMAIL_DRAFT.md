Subject: Case 73530481 — Preventive measures completed (Places API New migration)

Dear Google Maps Platform Support Team,

Thank you for your assistance with case 73530481 regarding unexpected Places API charges on project “medicine-recommend” (billing account 01FC55-8ED67F-9817DC) on July 21, 2026.

As requested by Ian, I have implemented the recommended preventive measures. Below is a summary for your validation.

## Code changes (completed)

1. Migrated from legacy Places Text Search to Places API (New)
   - Endpoint: POST https://places.googleapis.com/v1/places:searchText
   - Removed use of the legacy googlemaps Text Search client

2. Applied an explicit minimal field mask (Text Search Pro only; no Enterprise / Atmosphere fields):
   - places.id
   - places.displayName
   - places.formattedAddress
   - places.location
   - places.types
   - places.businessStatus
   - nextPageToken
   - Wildcard field mask (*) is explicitly forbidden in code

3. Removed Place Details calls; store records are built from Text Search (New) results only

4. Added hard request budgets per run (defaults):
   - Max 60 Places requests per prefecture run
   - Max 2 pages per query
   - Max 8 municipality searches
   - Max 15 chain searches
   - Kill switch: PLACES_ENABLED=0
   - Optional reuse of existing CSV without API calls

5. Added Geocoding request cap (default 200/run) with GSI fallback

Repository documentation: BILLING_PREVENTION.md

## Console-side measures (please confirm / I am applying)

- API key application + API restrictions (Places API New + Geocoding only)
- Disable legacy Places API
- Daily quotas (target: Text Search ≤ 100/day, Geocoding ≤ 200/day)
- Budget alert at approximately JPY 3,000/month (50% / 90% / 100%)

I will continue using Google Maps Platform responsibly for personal learning and development as a university student in Japan. I would be deeply grateful if you could proceed with monitoring and the one-time courtesy billing adjustment request after validating these measures.

Please let me know if you need any additional details (project ID, API key suffix, screenshots of quotas/alerts, or code references).

Thank you very much for your support.

Best regards,
Yuto Kawashima
