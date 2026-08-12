# SAP QM - notifications, quality info records, certificates, batch linkage

The QM objects around the inspection lot: how a defect or complaint is tracked, how a source is released or
blocked, how quality is certified to a customer, and how the usage decision touches the batch. Read when a
task raises or closes a quality notification, releases/blocks a procurement or sales source, handles a
certificate of analysis, or reasons about batch status.

## Contents
- Quality notifications (defects and complaints)
- Quality info records (procurement and SD)
- Certificates of analysis (inbound and outbound)
- Source inspection and certificate requirement
- Batch status and classification linkage

## Quality notifications (defects and complaints)
The record of a quality problem and its resolution (QM01 create, QM02 change, QM03 display). Notification
**types**:
- **Q1** - customer complaint (a customer reported a defect against something you shipped).
- **Q2** - complaint against a vendor (a problem with received material; often follows a UD reject or return).
- **Q3** - internal problem / defect (found in-house).

Structure: a notification header, one or more **defect items** (coded against defect-type catalogs), **causes**,
**tasks** (corrective / preventive actions to do), and **activities** (what was done). This is the container
for an **8D / CAPA** investigation.

Status flow: **OSNO** outstanding -> **NOPR** in process -> **NOCO** completed. Tasks have their own
outstanding / released / completed states.

Gating: creating and editing a notification and its items/tasks is reversible (a working record).
**Completing it (NOCO)** is committing: it closes the disposition and can release any holds the notification
drove, so outstanding tasks/activities should be done first. Completing early to clear a queue loses the open
corrective actions.

## Quality info records (procurement and SD)
A quality info record is a **source-of-supply control** keyed on material + partner.
- **Procurement** (QI01 create, QI02 change, QI03 display) - per material + vendor. It carries a **release /
  block status** that governs whether that source may be **ordered from and received**, a release quantity and
  date, technical delivery terms, and a **certificate requirement**. When **QM in procurement** is active for a
  material, a PO or goods receipt for that material + vendor is **blocked without a released info record**.
  - Releasing an info record opens a source: it is committing (it permits spend and receipt).
  - Blocking one halts all procurement for that material + vendor; **lifting a block** to push a receipt
    through is a compliance action that belongs to whoever set it - asymmetric, like an MM vendor block.
- **Sales / SD** - per material + customer. It can impose a **delivery block** on quality grounds, so an
  outbound delivery is held until quality clears. Same asymmetry: setting the hold is reversible, releasing it
  is the committing direction.

## Certificates of analysis (inbound and outbound)
- A **certificate profile** (QC01) defines which characteristics appear on a certificate and how they are
  formatted, and is assigned by material / customer / certificate type.
- **Outbound** - a certificate of analysis (CoA) is generated for a delivery or batch and sent to the
  customer. Issuing it is a **certification**: you are asserting the batch meets the stated characteristics. If
  a characteristic failed, or the wrong profile omitted a failing characteristic, or the batch classification
  is wrong, the CoA is a false claim. There is no clean "unsend"; a wrong certificate is corrected by issuing a
  new one and notifying (a recall, not an edit).
- **Inbound** - a certificate from the vendor can be a **receipt control**: if the info record requires a
  certificate, the goods receipt / usage decision can be held until the certificate is recorded as received.

## Source inspection and certificate requirement
When QM in procurement is set up for source inspection, an inspection lot can be created **before or at the
vendor** rather than only at goods receipt. A receipt is then allowed once the source lot passes and (if
required) the certificate is present. This shifts the quality gate upstream: the block is on the source /
certificate, not just on the received stock. Treat releasing a source or waiving a required certificate as a
committing control decision.

## Batch status and classification linkage
For batch-managed materials the usage decision reaches into the batch:
- **Batch status** - the UD can set the batch to **unrestricted-use** (accept) or leave it **restricted /
  blocked** (reject or pending). A **restricted batch is excluded from unrestricted ATP** even though the
  quantity exists on hand - a different lever from the QI stock state, and both must be right for stock to be
  freely usable.
- **Batch classification (batch valuation)** - inspection results can be **copied into the batch's
  classification characteristics** (potency, grade, shelf-life, origin). Downstream **FEFO / shelf-life
  picking and customer-spec selection read those class values**, so a wrong measured value written to the batch
  class mis-grades the batch and causes the wrong stock to be picked or promised later.
- Consequence for reasoning: a batch can be physically present, in unrestricted QI-cleared stock, and still be
  **restricted** or **mis-classified** - check batch status and class values, not just the inspection lot's UD,
  before treating a batch as good and available.
