---
id: accounting-events
title: Accounting events catalogue
version: "1.3"
status: current
effective_from: 2026-02-15
owner: Financial Controller
---

# Accounting events catalogue

## 1. Scope

**1.1** Every money movement on Wandrel is recorded through one of the events in this catalogue.

## 2. Rules

**2.1** Every money flow must map to an event in this catalogue before launch.

**2.2** A new event type requires approval by the Financial Controller and at least six weeks of lead time before launch.

## 3. Events

**3.1** BOOKING_CREATED: a traveller pays for a booking.

**3.2** ACTIVITY_COMPLETED: the activity date has passed and the booking was not cancelled.

**3.3** COMMISSION_EARNED: Wandrel's commission on a commission-model booking.

**3.4** MARKUP_EARNED: Wandrel's markup on a net-rate or reseller channel booking.

**3.5** SERVICE_FEE_EARNED: a traveller service fee becomes revenue.

**3.6** REFUND_ISSUED: money returned to a traveller.

**3.7** SUPPLIER_PAYOUT: money paid to a supplier.

**3.8** PENALTY_APPLIED: a supplier penalty deducted from a payout.

**3.9** VOUCHER_ISSUED, VOUCHER_REDEEMED and VOUCHER_EXPIRED: the life of a gift card or compensation voucher.

**3.10** FX_GAIN_LOSS: the difference between traveller currency and supplier contract currency.
