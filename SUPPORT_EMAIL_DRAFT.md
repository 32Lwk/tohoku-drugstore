Subject: Re: Case 73530481 — Implementation fix and preventive measures completed; ready for monitoring

Hi Ian,

Thank you for your follow-up.

I am writing to confirm that the **implementation remediation and preventive measures are now in place**, so you may **start monitoring** my usage for the next 24–48 hours.

## 1. Implementation / Places API (New)

For project **medicine-recommend** (Project ID: **340042923793**):

- I have **stopped** the unintended Places usage that caused the July 21 spike.
- I have reviewed the application design. This project is a personal student learning app (OTC medicine recommendation chat UI). Places was only being considered for limited nearby-pharmacy lookups, and I am **re-evaluating whether Places should be used at all**.
- **Current state:** Places API calls from this project are **disabled / not in active use**.
- **If Maps usage is ever resumed**, it will use **Places API (New) Text Search only**, with an explicit **minimal field mask** (no wildcard `*`), and with hard request limits in code. Legacy Text Search will not be used.

## 2. Preventive measures (project + API key)

Completed:

- **API key:** The Places API key involved in the spike has been **disabled (invalidated)**. It can no longer generate traffic.
- **Budget alerts:** Billing budget alerts have been configured on my Google Cloud account.
- **Quotas / future key controls:** Daily quotas and API key restrictions will be applied **before any new key is enabled**. Until then, Places traffic remains stopped via the disabled key.
- **Application safeguard:** Development will not call Places unintentionally; any future integration will be narrowly scoped and rate-limited.

## 3. Request

Please proceed with **usage monitoring** and, after validation, with the **one-time courtesy billing adjustment** review discussed earlier.

I will keep Places usage stopped during your monitoring window. If you need screenshots (disabled key, budget alert, quota settings) or any additional details, I will provide them immediately.

Thank you again for your support.

Best regards,
Yuto Kawashima
University student (Japan)
Case: 73530481
Billing account: 01FC55-8ED67F-9817DC
Project: medicine-recommend (Project ID: 340042923793)
