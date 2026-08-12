# Infor product lines - object and screen map

Infor ERP is a family. A task's objects and screen addressing depend on which line is connected. Read when
you need the per-line object names, how screens are addressed, or which line a CloudSuite edition sits on.

## Contents
- The three lines at a glance
- M3 (ex-Movex) - programs and objects
- LN (ex-Baan) - sessions and objects
- SyteLine / CloudSuite Industrial (CSI) - forms and objects
- CloudSuite editions - which line underneath
- Where the same task diverges

## The three lines at a glance
| | M3 | LN | SyteLine / CSI |
|---|---|---|---|
| Heritage | Movex / Intentia | Baan | Mapics / Symix |
| Best fit | process, distribution, F&B, fashion, chemicals | discrete, project, aerospace & defense, industrial machinery | mid-market discrete manufacturing |
| Screen addressing | **program codes** (letters + number, e.g. PPS200) | **session codes** (`<pkg><module><nnnn>m<vvv>`, e.g. tdpur4100m000) | **named forms** + IDOs (Mongoose framework) |
| Extensibility | H5 client, Enterprise Search, ION | Tools / extensions, ION | Mongoose (IDOs, events, custom forms), ION |

## M3 (ex-Movex) - programs and objects
Program prefixes signal the module:
- **PPS** - Purchasing. PPS200 Purchase Order. Open Lines (PO entry/maintain); PPS300 Purchase Order. Receive
  Goods (goods receipt). PPS001 is purchasing settings.
- **MMS** - Material/inventory. MMS001 Item. Open (item master); MMS200 Item. Connect Warehouse; MMS060
  Balance Identity (stock on hand by warehouse/location/lot/status).
- **OIS** - Sales (Customer Order). OIS100/OIS300 customer order entry.
- **APS** - Accounts Payable. APS100 Supplier Invoice. Record (record the invoice batch); APS360 Supplier
  Invoice. Match GR Lines (three-way match to goods received); payment proposal for the pay run.
- **GLS** - General Ledger. GLS100 Journal Voucher. Open (GL voucher entry).
- **CRS** - Common. CRS610 Supplier. Open (supplier master); accounting-rule and control-object configuration.
- Stock is tracked by **balance identity** (warehouse, location, lot, container, status). Finance postings are
  derived by **accounting rules** configuration; a mis-set rule posts to the wrong account silently.
- M3 leans heavily on **lot control** for traceable industries (food, pharma) - lot and shelf-life data drive
  FEFO picking and quality.

## LN (ex-Baan) - sessions and objects
Session code = `<package><module><program>m<version>`. Package prefixes:
- **tdpur** - Purchase (Procurement). tdpur4100m000 Purchase Orders (maintain); purchase order lines and the
  approve-PO step live in the same package.
- **tdsls** - Sales.
- **whinh** - Warehouse inbound (receipts); **whwmd/whinr** - warehouse master data / inventory reconciliation.
- **tfacp** - Accounts Payable (purchase invoice registration and matching to receipt).
- **tfgld** - General Ledger (journal / financial transactions, period status).
- **tfcmg** - Cash Management (payments); **tccom** - Common (business partners, buy-from BP).
- **Integration transactions + mapping scheme** - LN decouples logistics from finance. A logistic event
  (receipt, issue) creates an integration transaction that is **mapped** to GL accounts and **posted**
  separately. Until posted, logistics and the ledger disagree. This is the single biggest LN-specific hazard.
- LN keeps **separate fiscal, tax, and reporting period statuses**, each with Open / Closed / **Finally
  Closed** (terminal, cannot reopen).
- Valuation methods per item: **FTP** (Fixed Transfer Price), standard cost, **MAUC** (Moving Average Unit
  Cost), FIFO, LIFO, Lot. The method decides what a receipt posts.

## SyteLine / CloudSuite Industrial (CSI) - forms and objects
- Screens are **named forms**; the data/API layer is **IDOs** (Intelligent Data Objects) on the **Mongoose**
  framework. Customization is via Mongoose (custom forms, IDO extensions, events), not core-code edits.
- Purchasing: "Purchase Orders", "Purchase Order Receiving".
- Payables: the AP invoice is a **Voucher**. "Voucher Builder" builds vouchers from receipts; "A/P Vouchers"
  maintains them; "A/P Payments" runs payments. An **unvouchered receipt** is an accrued liability until a
  voucher is built and matched three-way.
- GL: "Journal Entries" (Unposted, editable) -> "Post Transactions" (updates the ledger); "Accounting
  Periods" holds the period status.
- Costing per item: standard, average, actual (FIFO/LIFO).

## CloudSuite editions - which line underneath
The CloudSuite name is the **industry edition**, not the mechanics. Look under it for the line and apply that
line's object model:
- CloudSuite **Industrial** = SyteLine (CSI).
- CloudSuite **Distribution**, CloudSuite **Food & Beverage**, CloudSuite **Fashion**, CloudSuite
  **Chemicals** = typically **M3**.
- CloudSuite **Aerospace & Defense**, CloudSuite **Industrial Enterprise** (large discrete/project) =
  typically **LN**.
If unsure, confirm from the addressing style you see (program code vs session code vs named form) before
acting.

## Where the same task diverges
| Task | M3 | LN | SyteLine / CSI |
|---|---|---|---|
| Receive a PO | PPS300 goods receipt | whinh warehouse receipt session | "Purchase Order Receiving" form |
| Record AP invoice | APS100 | tfacp purchase invoice | Voucher (Voucher Builder) |
| Three-way match | APS360 | tfacp match to receipt | voucher match |
| GL entry | GLS100 journal voucher | tfgld journal | "Journal Entries" -> Post |
| Post logistics to finance | accounting rules (interactive or batch) | **process integration transactions** | Post Transactions |
| Period status | GL period status | fiscal/tax/reporting period status | "Accounting Periods" |
