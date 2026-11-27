# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class EthelcoLegalOverrideWizard(models.TransientModel):
    _name = 'ethelco.legal.override.wizard'
    _description = 'Legal Document Confirmation Override'

    order_id = fields.Many2one('sale.order', string='Sales Order', required=True)
    partner_id = fields.Many2one(
        related='order_id.partner_id',
        string='Customer',
    )
    blocker_info = fields.Text(
        string='Blocking Documents',
        compute='_compute_blocker_info',
    )
    reason = fields.Text(
        string='Override Reason',
        required=True,
        help='Mandatory justification logged in the order chatter.',
    )

    @api.depends('order_id', 'order_id.partner_id')
    def _compute_blocker_info(self):
        for wizard in self:
            partner = wizard.order_id.partner_id.commercial_partner_id
            if partner and partner.is_wholesale_customer:
                blockers = partner._get_legal_blockers()
                wizard.blocker_info = '\n'.join(f'- {b}' for b in blockers) if blockers else False
            else:
                wizard.blocker_info = False

    def action_confirm_with_override(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'ethelco_wholesale_legal_docs.group_legal_compliance_manager'
        ):
            raise AccessError(
                _('Only Legal Compliance Managers can override legal document checks.')
            )
        if not (self.reason or '').strip():
            raise UserError(_('An override reason is required.'))

        order = self.order_id
        order.write({
            'legal_override_reason': self.reason.strip(),
            'legal_override_user_id': self.env.user.id,
            'legal_override_date': fields.Datetime.now(),
        })
        order.message_post(
            body=_(
                'Legal document check overridden by %(user)s.<br/>'
                '<b>Reason:</b> %(reason)s<br/>'
                '<b>Blocking issues:</b><br/>%(blockers)s'
            ) % {
                'user': self.env.user.display_name,
                'reason': self.reason.strip(),
                'blockers': (self.blocker_info or _('None')).replace('\n', '<br/>'),
            },
            subtype_xmlid='mail.mt_note',
        )
        return order.action_confirm()
