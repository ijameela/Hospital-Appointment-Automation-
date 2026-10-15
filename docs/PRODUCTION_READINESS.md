# Real-System Integration Checklist

**Current status: NOT READY for production use.**

- [ ] Written authorization from the healthcare system owner and security/privacy teams
- [ ] Approved staging/test environment and synthetic patient accounts
- [ ] Review institutional policy for browser automation and auditability
- [ ] Map actual UI controls, field names, login redirects, and validation messages
- [ ] Verify patient identity and prevent wrong-patient bookings
- [ ] Confirm allowed visit types, clinic codes, clinician selection and time-zone behavior
- [ ] Define whether overbooking is permitted and who must approve it
- [ ] Implement and test explicit post-save verification and duplicate/idempotency checks
- [ ] Handle network failures, ambiguous saves, manual review and crash recovery
- [ ] Run controlled end-to-end tests and obtain operational sign-off
- [ ] Store credentials only via approved login/secret-management workflow

The included `staging_preview.py` deliberately performs **no booking or Save operation**. A booking-capable adapter must be implemented and validated after the checklist is satisfied.
