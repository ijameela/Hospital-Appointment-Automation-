# Local Mock Test Evidence

The following results were observed in the local synthetic Flask/Selenium environment, not on a real hospital portal.

| Scenario | Observed behavior |
| --- | --- |
| Normal appointment | Saved and verified against mock schedule |
| Occupied slot | Mock overbooking path exercised |
| Duplicate booking | `Appointment Already Exists` reported at `POST_SAVE` |
| Delayed patient lookup | Artificial 15-second API delay caused a 12-second Selenium timeout, logged at `PATIENT_SEARCH` |
| Interrupted row | `In Progress - Review Before Retry` checkpoint was skipped on rerun |
| Restore after timeout experiment | Local API returned in about 0.096 seconds |

**Limits:** the interrupted-row checkpoint was simulated rather than caused by a real crash; the full end-to-end resume path was not established. No production portal, live patient data, or real booking has been tested. The actual local logs are intentionally excluded from the public repository.
