# Teacher paid tests

Approved tutors and lecture houses can publish tests assembled from published questions in selected curriculum topics. Each paid test has a shareable link, a teacher-set price with a ₦200 minimum, question count, time limit, and one of two question-selection modes:

- **Shared set:** KalmiPrep selects the test questions when it is published. Every buyer gets that question set in a shuffled order.
- **Unique draw:** each buyer gets a new random draw from the chosen topics.

## Revenue and payment handling

For each server-verified sale, 80% of the test price is recorded in the teacher wallet and 20% is recorded as platform revenue. Amounts are stored in kobo. Gateway fees returned by Paystack are stored separately and do not change the recorded 80/20 split. Refunds debit the teacher wallet's proportional share, with cumulative rounding so a full refund reverses the full teacher credit.

Paystack is used for checkout. The backend verifies successful transactions with Paystack's transaction verification endpoint before it creates wallet credit or issues a PIN. The callback and webhook can both process the same sale safely. Webhook signatures are checked against the raw request body using the configured secret key. Duplicate webhook payloads, transaction references, and refund references do not create duplicate wallet entries.

Successful purchases receive a 10-character access PIN. Students can use it to start or resume their single test attempt without creating an account. The PIN is derived from `PAID_TEST_PIN_SECRET`; keep that value stable so buyers can recover the same PIN from the verified payment callback.

## Development and operations

1. Set `PAYSTACK_TEST_MODE=True`, `PAYSTACK_SECRET_KEY` to a Paystack test secret, `PAID_TEST_PIN_SECRET` to a long random value, and `SITE_URL` to the canonical KalmiPrep origin in the local environment.
2. Run migrations, create a teacher account, and approve its `TeacherProfile` in Django admin.
3. Set a webhook URL in the Paystack test dashboard to `https://<host>/monetization/paystack/webhook/`. Subscribe to successful charge and refund events.
4. Test checkout with Paystack's test environment. No real transfer or payout is made by the application.

Teachers can submit withdrawal requests against their available wallet balance. Requests appear in Django admin for review. Marking a request paid records a wallet debit only; it does not call Paystack Transfers or otherwise send money. Bank details and actual payouts remain an operations process.

The split and ₦200 floor come from the recommended terms supplied for this feature. Changing these terms requires a code and product decision; they are not currently editable by teachers.
