# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_wholesale_customer = fields.Boolean(
        string='Wholesale Customer',
        tracking=True,
        help='Wholesale customers on credit require valid legal documents before SO confirmation.',
    )
    legal_document_ids = fields.One2many(
        'ethelco.partner.legal.document',
        'partner_id',
        string='Legal Documents',
    )
    legal_compliance_status = fields.Selection(
        [
            ('compliant', 'Compliant'),
            ('expiring', 'Expiring'),
            ('non_compliant', 'Non-compliant'),
            ('not_applicable', 'N/A'),
        ],
        string='Legal Compliance',
        compute='_compute_legal_compliance',
        store=True,
        index=True,
    )
    legal_missing_info = fields.Text(
        string='Legal Issues',
        compute='_compute_legal_compliance',
        store=True,
    )

    @api.depends(
        'is_wholesale_customer',
        'legal_document_ids',
        'legal_document_ids.state',
        'legal_document_ids.active',
        'legal_document_ids.type_id',
        'legal_document_ids.type_id.required_for_wholesale',
        'legal_document_ids.type_id.active',
        'legal_document_ids.verified',
        'legal_document_ids.attachment_ids',
        'legal_document_ids.expiry_date',
    )
    def _compute_legal_compliance(self):
        required_types = self.env['ethelco.legal.document.type'].search([
            ('required_for_wholesale', '=', True),
            ('active', '=', True),
        ])
        for partner in self:
            if not partner.is_wholesale_customer:
                partner.legal_compliance_status = 'not_applicable'
                partner.legal_missing_info = False
                continue

            blockers = partner._get_legal_blockers(required_types=required_types)
            docs = partner.legal_document_ids.filtered(
                lambda d: d.active and d.type_id in required_types
            )
            if blockers:
                partner.legal_compliance_status = 'non_compliant'
                partner.legal_missing_info = '\n'.join(blockers)
            elif any(d.state == 'expiring' for d in docs):
                partner.legal_compliance_status = 'expiring'
                partner.legal_missing_info = _(
                    'Some required documents are approaching expiry.'
                )
            else:
                partner.legal_compliance_status = 'compliant'
                partner.legal_missing_info = False

    def _get_legal_blockers(self, required_types=None):
        """Return human-readable blockers for required wholesale document types.

        A type is a blocker when it is missing, unverified or expired.
        """
        self.ensure_one()
        if required_types is None:
            required_types = self.env['ethelco.legal.document.type'].search([
                ('required_for_wholesale', '=', True),
                ('active', '=', True),
            ])
        # Multi-company: limit to company-agnostic or matching company types
        company = self.company_id or self.env.company
        required_types = required_types.filtered(
            lambda t: not t.company_id or t.company_id == company
        )

        docs_by_type = {
            doc.type_id.id: doc
            for doc in self.legal_document_ids.filtered('active')
        }
        blockers = []
        for doc_type in required_types:
            doc = docs_by_type.get(doc_type.id)
            if not doc:
                blockers.append(_('%s: missing') % doc_type.display_name)
                continue
            if not doc.attachment_ids:
                blockers.append(_('%s: missing attachment') % doc_type.display_name)
            if not doc.verified:
                blockers.append(_('%s: unverified') % doc_type.display_name)
            if doc.state == 'expired' or (
                doc_type.has_expiry
                and doc.expiry_date
                and doc.expiry_date < fields.Date.context_today(self)
            ):
                blockers.append(
                    _('%(type)s: expired on %(date)s')
                    % {'type': doc_type.display_name, 'date': doc.expiry_date}
                )
        return blockers

    def action_view_legal_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Legal Documents'),
            'res_model': 'ethelco.partner.legal.document',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
