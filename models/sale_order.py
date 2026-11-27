# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    legal_blocked = fields.Boolean(
        string='Legal Blocked',
        compute='_compute_legal_blocked',
    )
    legal_block_message = fields.Text(
        string='Legal Block Message',
        compute='_compute_legal_blocked',
    )
    legal_override_reason = fields.Text(
        string='Legal Override Reason',
        copy=False,
        tracking=True,
    )
    legal_override_user_id = fields.Many2one(
        'res.users',
        string='Legal Override By',
        copy=False,
        readonly=True,
        tracking=True,
    )
    legal_override_date = fields.Datetime(
        string='Legal Override On',
        copy=False,
        readonly=True,
        tracking=True,
    )

    @api.depends(
        'partner_id',
        'partner_id.commercial_partner_id',
        'partner_id.commercial_partner_id.is_wholesale_customer',
        'partner_id.commercial_partner_id.legal_document_ids',
        'partner_id.commercial_partner_id.legal_document_ids.state',
        'partner_id.commercial_partner_id.legal_document_ids.verified',
        'partner_id.commercial_partner_id.legal_document_ids.attachment_ids',
        'partner_id.commercial_partner_id.legal_document_ids.expiry_date',
        'legal_override_reason',
        'state',
    )
    def _compute_legal_blocked(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if (
                order.state in ('sale', 'cancel', 'done')
                or not partner
                or not partner.is_wholesale_customer
            ):
                order.legal_blocked = False
                order.legal_block_message = False
                continue
            blockers = partner._get_legal_blockers()
            if blockers and not order._has_valid_legal_override():
                order.legal_blocked = True
                order.legal_block_message = _(
                    'Cannot confirm: wholesale customer is missing valid legal documents:\n%s'
                ) % '\n'.join(f'- {b}' for b in blockers)
            else:
                order.legal_blocked = False
                order.legal_block_message = False

    def _has_valid_legal_override(self):
        self.ensure_one()
        return bool(self.legal_override_reason and self.legal_override_user_id)

    def _check_wholesale_legal_documents(self):
        """Raise if wholesale legal documents block confirmation (unless overridden)."""
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if not partner.is_wholesale_customer:
                continue
            blockers = partner._get_legal_blockers()
            if not blockers:
                continue
            if order._has_valid_legal_override():
                continue
            raise UserError(
                _(
                    'Sales Order %(order)s cannot be confirmed for wholesale customer '
                    '%(partner)s. Required legal documents are missing, unverified or expired:\n%(docs)s\n\n'
                    'A Legal Compliance Manager may use Legal Override to proceed.'
                )
                % {
                    'order': order.display_name,
                    'partner': partner.display_name,
                    'docs': '\n'.join(f'- {b}' for b in blockers),
                }
            )

    def action_confirm(self):
        # Legal check first; then super() so C-03 credit-limit (and other)
        # confirmation checks still run via inheritance chaining.
        self._check_wholesale_legal_documents()
        return super().action_confirm()

    def action_open_legal_override_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Legal Override'),
            'res_model': 'ethelco.legal.override.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }
