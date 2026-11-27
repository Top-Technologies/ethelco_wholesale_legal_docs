# Ethelco Wholesale Legal Documents

Odoo **18.0** module that blocks Sales Order confirmation for wholesale
customers until all required legal documents are present, verified and not
expired.

## Business rule

ETHELCO PLC sells to wholesale customers on credit. A Sales Order whose
commercial partner is marked **Wholesale Customer** cannot be confirmed if any
required legal document is:

- missing (no record or no attachment)
- unverified
- expired

Quotation creation and sending remain allowed. A **Legal Compliance Manager**
may override the block with a mandatory reason (logged in chatter).

## Dependencies

- `base`, `mail`, `contacts`, `sale`, `sale_management`

## Installation

1. Copy this folder into your Odoo addons path (e.g. `custom_addons/`).
2. Update the apps list and install **Ethelco Wholesale Legal Documents**.
3. Assign users to:
   - **Legal Documents / User** — upload and maintain documents
   - **Legal Documents / Manager** — verify, configure types, override SO blocks

## Configuration

1. Open **Sales → Configuration → Legal Document Types**.
2. Review seed types (Trade License, TIN Certificate, VAT Certificate, Signed
   Wholesale Agreement, Tax Clearance) or add your own.
3. Mark partners as **Wholesale Customer** and maintain documents on the
   **Legal Documents** tab.
4. Only Managers can set **Verified**.

## Daily automation

Cron **Legal Documents: recompute states & expiry activities** runs daily to:

- recompute document and partner compliance states
- create To-Do activities for the salesperson and Compliance Managers at
  `warning_days`, **15 days** and on **expiry**

## Sales flow

1. Create / send quotation — always allowed.
2. Confirm SO — blocked with a clear list of document issues when non-compliant.
3. Manager uses **Legal Override** on the order, enters a reason, confirms.
4. `action_confirm` calls `super()` so other confirmation checks (e.g. C-03
   credit limit) still run.

## Reports & filters

- Partner search: **Non-compliant**, **Expiring in 30 days**, group by compliance
- Menu **Sales → Wholesale Legal Compliance** — list of wholesale customers by status

## Technical notes (Odoo 18)

- List views (`<list>`), no `attrs` / `states`
- SQL rules via `_sql_constraints`
- Groups via `category_id` on `res.groups`
- OWL-safe view expressions (`invisible="..."`)
