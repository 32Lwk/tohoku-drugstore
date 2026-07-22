Subject: Re: Case 73530481 — Places API (New) enabled with preventive measures; ready for monitoring

Hi Ian,

Thank you again for your guidance.

I have now **enabled Places API (New)** on project **medicine-recommend** (Project ID: **340042923793**) and applied preventive measures so that your team can monitor usage.

## Completed actions

1. **Places API (New) enabled**
2. **API key controls**
   - The previous key involved in the July 21 spike remains disabled
   - A restricted key setup is in place for Places API (New) only
3. **Strict quotas applied** (examples):
   - SearchTextRequest per day: **5** (reduced from 75,000)
   - SearchTextRequest per minute: **5** (reduced from 600)
   - SearchNearby / GetPlace / Autocomplete and other Places (New) quotas also reduced to very low limits (around 5/day or 5/minute where applicable)
4. **Budget alerts** remain configured
5. **Usage policy**
   - No legacy Text Search
   - If any calls are made, they will use Text Search (New) with an explicit minimal field mask only
   - I will keep usage very small and controlled during your monitoring window

These preventive measures are now active. Please proceed with your **24–48 hour usage monitoring**.

After validation, I would be deeply grateful if you could continue with the **one-time courtesy billing adjustment** review. As a university student in Japan using this project only for personal learning and development, the unexpected charge remains far beyond what I can afford.

Please let me know if you need screenshots of the enabled API, quota overrides, key restrictions, or budget alert settings.

Thank you again for your support.

Best regards,
Yuto Kawashima
University student (Japan)
Case: 73530481
Billing account: 01FC55-8ED67F-9817DC
Project: medicine-recommend (Project ID: 340042923793)
