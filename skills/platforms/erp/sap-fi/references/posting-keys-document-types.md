# SAP FI - posting keys, document types, number ranges

The three controls that decide what a line does, what a document may contain, and how it is numbered. Read
when building or classifying a posting, or reasoning about which account type a line hits.

## Contents
- Posting keys (the debit/credit + account-type control)
- Document types (number range + allowed accounts + reversal)
- Number ranges
- Field status (which fields are required/suppressed)
- Reconciliation accounts

## Posting keys - what each one means
A posting key is 2 digits on every line item. It fixes **both** the posting side (debit/credit) **and** the
account type. Same amount, different key = different account and different sign.

| Key | Side | Account type | Typical use |
|---|---|---|---|
| 40 | Debit | G/L | expense, asset, clearing debit |
| 50 | Credit | G/L | revenue, liability, clearing credit |
| 01 | Debit | Customer (AR) | customer invoice |
| 11 | Credit | Customer (AR) | customer credit memo |
| 15 | Credit | Customer (AR) | incoming payment (credit to the customer, reduces AR) |
| 09 / 19 | Dr / Cr | Customer special G/L | down payment received, etc. |
| 31 | Credit | Vendor (AP) | vendor invoice |
| 21 | Debit | Vendor (AP) | vendor credit memo |
| 25 | Debit | Vendor (AP) | outgoing payment (reduces the vendor/AP balance) |
| 29 / 39 | Dr / Cr | Vendor special G/L | down payment made, etc. |

The special-G/L keys (09/19/29/39) route to an **alternative reconciliation account**, not the normal AP/AR
recon account. In S/4HANA Fiori "enjoy" screens the key is often set behind the debit/credit toggle, but the
underlying key still governs the posting.

## Document types - what a document may contain
The document type is 2 characters in the header. It controls the **number range**, the **account types
allowed**, whether posting is net or gross, and the **reversal document type**.

| Type | Use |
|---|---|
| SA | G/L account document |
| AB | General document (all account types) |
| KR | Vendor invoice (AP) |
| KG | Vendor credit memo |
| KZ | Vendor payment |
| DR | Customer invoice (AR) |
| DG | Customer credit memo |
| DZ | Customer payment |
| RE | Gross invoice receipt (MM/MIRO logistics invoice) |
| RV | Billing document transfer from SD |
| WE / WA | Goods receipt / goods issue (from MM movements) |

Picking the wrong type can block the accounts you need (e.g. a G/L-only type refuses a vendor line) or number
the document in the wrong range.

## Number ranges
- A document number comes from the range tied to the **document type**, and it is assigned **per company code,
  per fiscal year**. So a number is **not globally unique** - the same number can exist in another year or
  company code. Always qualify a document by company code + fiscal year + number.
- Ranges can be internal (system-assigned) or external (user-entered). External ranges are used for legacy or
  interfaced documents.

## Field status (why a field is required or greyed out)
Two controls jointly decide whether a field on a line is required, optional, or suppressed:
- the **field status group** on the G/L account (FS00), and
- the field status linked to the **posting key**.
The stricter of the two wins. A conflict (one requires, the other suppresses) throws an error at posting. This
is why a field you expect is missing or a field you left blank is demanded.

## Reconciliation accounts
- A **reconciliation account** is a G/L account marked as the control account for a sub-ledger (AP, AR, assets).
- You **cannot post to it directly** - it updates only when the sub-ledger posts. A direct G/L line to a recon
  account is rejected.
- **Special G/L** transactions post to an **alternative** reconciliation account (set in config), keeping down
  payments, bills of exchange, and guarantees separate from normal payables/receivables on the balance sheet.
- Changing the recon account on a vendor/customer master re-routes **future** postings only; historical items
  stay on the old account until cleared.
