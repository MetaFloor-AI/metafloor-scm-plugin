# Recall classification, depth, clocks, and effectiveness

The operator's map of what governs recall scope, urgency, and closure. **The recall class, the notification
clock, the recall depth, and the effectiveness-check level are the quality / regulatory head's determination,
not the agent's.** This file is the frame so the agent surfaces the right facts and tracks the right clock; the
exact obligation depends on jurisdiction, product type, and the org's controlled recall SOP. Cited frameworks
are US FDA examples - other regulators (EMA, MHRA, TGA, Health Canada) and other domains (auto/NHTSA, food)
have their own equivalents.

## Contents
- Recall class (urgency)
- Recall depth (how far down the chain)
- Notification-clock frameworks (examples)
- Effectiveness-check levels

## Recall class (drives urgency and depth)
| Class | Meaning | Typical response |
|---|---|---|
| **Class I** | reasonable probability that use will cause serious adverse health consequences or death | fastest; consumer/patient-level depth; Level A effectiveness; public notice likely |
| **Class II** | use may cause temporary or medically reversible harm, or the probability of serious harm is remote | prompt; often retail level; partial effectiveness checks |
| **Class III** | use is not likely to cause adverse health consequences | least urgent; often wholesale level; audit-level checks |

The class is a health-hazard evaluation the regulator/quality head makes. The agent surfaces the **likely**
class and its consequences so the gate is informed - it does not assign the class.

## Recall depth (how far down the distribution chain)
- **Wholesale/consumer level** - the depth is chosen with the class. Higher harm -> deeper pull.
  - **Wholesale**: recover from distributors / DCs only.
  - **Retail**: recover from retail/dispensing points too.
  - **Consumer / user level**: recover from the end consumer or patient (hospital, pharmacy, home) - the deepest
    and most expensive, typical for Class I.
The where-distributed map and the pull-vs-hold options are built to the chosen depth; a depth set too shallow
leaves affected product in the field.

## Notification-clock frameworks (examples - confirm the actual obligation in the org SOP)
The clock generally starts at the moment the reportable event is known or the decision to recall is made, and
runs in **hours to a few working days**. Real US FDA examples:
- **Food (Reportable Food Registry)** - the responsible party submits within **24 hours** of determining an
  article of food is a reportable food (adulterated, serious-harm probability).
- **Medical device (corrections & removals, 21 CFR Part 806)** - report a reportable correction/removal within
  **10 working days**.
- **Drug (NDA/ANDA Field Alert Report, 21 CFR 314.81)** - a distribution/quality problem is reported within
  **3 working days**.
Different products, jurisdictions, and severities carry different clocks; a firm may also owe both an initial
report on the known scope and supplements as the trace completes. **Multi-jurisdiction**: when affected product
crosses jurisdictions, each regulator's clock applies independently and some are shorter than the US examples
above - for instance EU MDR device vigilance runs serious-incident reporting in calendar days (commonly within
15, tighter for a serious public-health threat; confirm the exact obligation in the SOP). Surface and track the
**tightest** applicable clock across all jurisdictions in scope, not just the home one. The rule the agent
enforces: **notify on the known scope on time rather than run the clock out chasing a complete trace** -
on-time-partial beats late-complete, and a late regulator notification is itself a violation.

## Effectiveness-check levels (drives closure)
A recall is closed only when it is provably complete to the level the regulator sets. Effectiveness checks
verify consignees received the notice and acted:
- **Level A** - contact **100%** of consignees. Typical for Class I.
- **Lower levels** - progressively fewer consignees contacted (a set percentage, down to none / audit-only),
  used as the hazard drops.
Reconcile `accounted / distributed` per node against the level's bar. `accounted = returned + quarantined-in-
place + destroyed-on-site (with proof) + documented-consumed-before-recall`. Non-responding consignees are
escalated (re-contact, second notice, on-site verification); the recall stays **open** while affected nodes are
unaccounted above the threshold. Document units that cannot be physically recovered (already consumed /
administered) with evidence - they count as accounted, they are not ignored.
