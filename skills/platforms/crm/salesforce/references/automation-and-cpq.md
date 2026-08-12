# Salesforce - automation order of execution, CPQ, and pricing

Why a single save can do far more than change one field, and how CPQ turns a quote into committed spend. Read
when an edit may fire automation, or a workflow touches CPQ quotes, orders-from-quotes, or price books.

## Contents
- Order of execution (what runs on a save)
- Kinds of automation and their side effects
- Time-based and scheduled paths
- CPQ: configuration, pricing, discounting
- Quote sync and generating orders/contracts
- Price books and pricing mechanics
- Approval processes

## Order of execution (what runs on a save)
A record save runs a fixed sequence server-side, and the ordering matters for reasoning about what can block
or fire what. Simplified but order-accurate:
1. System validation, then **before-save** record-triggered **Flows**.
2. **before-save Apex triggers** (so a before-save Flow sees field values before a before-save Apex trigger does).
3. Custom **validation rules** and **duplicate rules** (either can reject the save).
4. Record saved to the database but **not yet committed**.
5. **after-save Apex triggers**.
6. Assignment rules, then auto-response rules (lead/case).
7. **Workflow rules** and their field updates; a workflow field update re-saves the record and re-fires
   before/after triggers **once** - and that re-save **re-runs validation rules**, so a save that passed the
   first validation can still fail on the workflow-triggered pass (the write then does not land).
8. **Escalation rules** (case), then **after-save** record-triggered **Flows**, then **entitlement / SLA
   milestone** processing.
9. Roll-up summary recalculation on the parent (which can fire the parent's own triggers); sharing recalculation.
10. **Commit**, then post-commit actions: outbound email, and async/scheduled paths (future/queueable, scheduled
    Flow paths, time-based workflow).
The takeaways: before-save Flows run before before-save Apex triggers, and after-save Flows run after after-save
triggers, so *which* automation sees a value first depends on this order; a validation or duplicate rule can
silently block the whole thing; a workflow field update causes a re-entrant pass; and roll-ups recompute the
parent from the child you just changed. Case work additionally fires escalation and SLA-milestone logic here.

## Kinds of automation and their side effects
| Mechanism | Fires on | Typical side effects |
|---|---|---|
| **Validation rule** | any save | blocks the save if a condition fails (silent to a caller who does not check) |
| **Record-triggered Flow** | create/update/delete | field updates, create/update related records, send email, external callout, scheduled path |
| **Apex trigger** | create/update/delete | arbitrary code: cascading DML, callouts, custom validation |
| **Workflow rule** (legacy) | create/update | field update, email alert, task, outbound message |
| **Process Builder** | create/update | similar to record-triggered flow; superseded by record-triggered Flow (prefer Flow for new automation) |
| **Assignment / auto-response** | lead/case create | reassign owner (to a queue/user), send templated email |

The practical rule: **you cannot tell from the field alone whether an edit is inert.** A cosmetic-looking
change may be the trigger a Flow is watching. Read the object's wired automation before classifying an edit as
a reversible write, and re-read state after saving because later-firing paths change it again.

## Time-based and scheduled paths
- A record-triggered Flow can have a **scheduled path** (e.g. act 2 days after close), and legacy workflow has
  **time-based actions**. These fire *after* the save, sometimes days later.
- Consequence: the side effect is not visible at save time. A record can email a customer or create a task well
  after the edit that armed it, so "nothing happened on save" does not mean nothing will happen.

## CPQ: configuration, pricing, discounting
- **Configuration** - a product can be a **bundle** with features and options; a quote line may belong to a
  bundle, so editing one line can require reconfiguring the bundle. Configuration attributes constrain valid options.
- **Pricing** - CPQ prices a line from list price, then applies discount schedules (volume/term), contracted
  prices, and manual discounts. The final price is computed, not typed; overriding it can break the pricing waterfall.
- **Discounting and approvals** - discounts past a threshold route through **approval** (native or Advanced
  Approvals). Editing a discount can re-trigger approval; do not treat a discount change on an approved quote as inert.

## Quote sync and generating orders/contracts
- **Primary quote** - one quote per opportunity can be primary. **Quote Sync** pushes the primary quote's lines
  onto the Opportunity, overwriting its Amount and Opportunity Products. Turning sync on/off or re-syncing can
  clobber existing opportunity line items - treat a sync as a committing rewrite of the opportunity.
- **Order from quote** - generating an Order (and Order Products) from a quote is committing; activating that
  Order signals fulfillment. Post-activation changes go through a reduction/amendment order.
- **Contract from quote/order** - creates the agreement record and can start entitlements and auto-renewal.
- **Amendment / renewal quotes** - CPQ amendments and renewals are *new* quotes against an existing contract,
  not edits of the original; they re-price and re-approve.

## Price books and pricing mechanics
- **Standard Price Book** plus custom price books; a **PricebookEntry** is a product's price in one book.
- An opportunity/quote line references a specific book, so **the price is per book**. Changing a PricebookEntry
  re-prices every future line that uses it (existing lines keep their captured price unless re-priced).
- Deactivating a price book, a product, or a PricebookEntry breaks quotes/opportunities that reference it and
  removes the product from new quotes.
- Multi-currency: a price book can carry per-currency entries; the line's currency selects the entry.

## Approval processes
- Submitting a record for approval **locks it** (read-only) until it is approved, rejected, or recalled; related
  records can lock too. Initial submission actions and final approval/rejection actions can update fields, send
  email, and create records.
- **Recall** (by the submitter) and **admin unlock** both remove the lock and bypass the intended review - an
  authority action, not a routine edit. A rejected record returns editable; an approved record can fire
  post-approval automation (e.g. activate an order, set a stage).

Gating note: because any save can cascade, classify a write by the *most committing* thing its automation does,
not by the field you touched. A discount edit that re-triggers approval, a stage change that fires order
creation, or a quote sync that rewrites the opportunity are committing, not reversible edits.
