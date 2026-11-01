# Demo and delivery

## Local preparation

Follow [README](README.md) to start Compose, migrate, explicitly import source data and index policies. Use mock mode for a reproducible no-key demo. The eight seed tickets and policies are fictional; preserve their original IDs.

## Demo sequence

1. Sign in; open `tkt_9001` and show the linked customer/order context and historical ticket date.
2. Triage it, generate a draft and open `KB-REFUND-001` from the citation.
3. Open `tkt_9008`; generate a billing draft, prepare a refund-review proposal and inspect order/amount/reason.
4. Approve the proposal, wait for the worker and show the review reference plus `money_refunded: false`. Repeated approval must not create a second logical effect.
5. Use a separate eligible proposal to demonstrate rejection without execution.
6. Show `tkt_9004` safety escalation, `tkt_9005` identity verification, `tkt_9006` coupon injection and `tkt_9007` secret-disclosure refusal.
7. Inspect traces and run Evaluations. Show per-case outcomes, denominators and mock-mode limitations.
8. Present automated evidence for worker crash/replay and slow-provider responsiveness; distinguish those tests from a live UI demonstration.

A previously successful review remains visible after refresh/restart. Do not delete audit history just to replay the same proposal for a video. Use a fresh staging demo scenario when necessary.

## Evaluation report

```sh
docker compose exec api python -m trustdesk.cli evaluate --suite provided --output /reports/evaluation.json
docker compose cp api:/reports/evaluation.json ./evaluation.json
```

The report includes source/implementation fingerprints, mode/model, corpus manifest, every case, expected-versus-actual checks and errors. Required-document citation coverage and structural reference validity are separate from semantic grounding. Natural-language requirement checks are explicit heuristics; unknown criteria require manual review.

## Delivery checklist

- Functional workspace, persistent data and one approval-gated action.
- Public repository and tested commit history with phase evidence.
- Reproducible setup, environment template and runtime API documentation.
- Measured evaluation and test/verification report with limitations.
- Railway URLs, deployed revision and backup/rollback instructions after hosted verification.
- Demo walkthrough/explainer material using fictional data, without credentials or private account screens.

No real refund, account change, coupon or customer message is sent by this V1 app. Live-model claims require separately labeled live-provider evaluation.
