# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class EthelcoPartnerLegalDocument(models.Model):
    _name = 'ethelco.partner.legal.document'
    _description = 'Partner Legal Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, type_id'
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    type_id = fields.Many2one(
        'ethelco.legal.document.type',
        string='Document Type',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    document_number = fields.Char(tracking=True)
    issue_date = fields.Date(tracking=True)
    expiry_date = fields.Date(tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ethelco_partner_legal_document_attachment_rel',
        'document_id',
        'attachment_id',
        string='Attachments',
    )
    # Readable by sales (needed for blockers/state); writable only by Compliance Managers
    # (enforced in create/write + form groups).
    verified = fields.Boolean(default=False, tracking=True)
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True, tracking=True)
    verified_date = fields.Datetime(string='Verified On', readonly=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        related='partner_id.company_id',
        store=True,
        index=True,
    )
    has_expiry = fields.Boolean(related='type_id.has_expiry', store=True)
    warning_days = fields.Integer(related='type_id.warning_days')
    state = fields.Selection(
        [
            ('missing', 'Missing'),
            ('valid', 'Valid'),
            ('expiring', 'Expiring'),
            ('expired', 'Expired'),
        ],
        string='Status',
        compute='_compute_state',
        store=True,
        index=True,
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry')

    @api.depends('partner_id', 'partner_id.name', 'type_id', 'type_id.name', 'document_number')
    def _compute_display_name(self):
        for doc in self:
            parts = [
                doc.partner_id.name or '',
                doc.type_id.name or '',
            ]
            if doc.document_number:
                parts.append(doc.document_number)
            doc.display_name = ' / '.join(p for p in parts if p) or _('Legal Document')

    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for doc in self:
            if doc.expiry_date:
                doc.days_to_expiry = (doc.expiry_date - today).days
            else:
                doc.days_to_expiry = 0

    @api.depends(
        'expiry_date',
        'verified',
        'attachment_ids',
        'type_id',
        'type_id.has_expiry',
        'type_id.warning_days',
    )
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for doc in self:
            if not doc.attachment_ids or not doc.verified:
                doc.state = 'missing'
                continue
            if doc.type_id.has_expiry and doc.expiry_date:
                if doc.expiry_date < today:
                    doc.state = 'expired'
                elif doc.expiry_date <= today + relativedelta(days=doc.type_id.warning_days or 0):
                    doc.state = 'expiring'
                else:
                    doc.state = 'valid'
            elif doc.type_id.has_expiry and not doc.expiry_date:
                doc.state = 'missing'
            else:
                doc.state = 'valid'

    @api.constrains('expiry_date', 'issue_date', 'type_id')
    def _check_expiry_date(self):
        for doc in self:
            if doc.type_id.has_expiry and not doc.expiry_date:
                raise ValidationError(
                    _('Expiry date is required for document type "%s".') % doc.type_id.display_name
                )
            if doc.issue_date and doc.expiry_date and doc.expiry_date < doc.issue_date:
                raise ValidationError(
                    _('Expiry date must be on or after the issue date for "%s".')
                    % doc.display_name
                )

    @api.constrains('partner_id', 'type_id', 'active')
    def _check_one_active_per_partner_type(self):
        for doc in self.filtered('active'):
            domain = [
                ('id', '!=', doc.id),
                ('partner_id', '=', doc.partner_id.id),
                ('type_id', '=', doc.type_id.id),
                ('active', '=', True),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _('Partner "%(partner)s" already has an active "%(type)s" document.')
                    % {
                        'partner': doc.partner_id.display_name,
                        'type': doc.type_id.display_name,
                    }
                )

    def write(self, vals):
        restricted = {'verified', 'verified_by', 'verified_date'}
        if restricted & set(vals):
            if not self.env.user.has_group(
                'ethelco_wholesale_legal_docs.group_legal_compliance_manager'
            ):
                raise AccessError(
                    _('Only Legal Compliance Managers can verify legal documents.')
                )
        if 'verified' in vals:
            if vals['verified']:
                vals.setdefault('verified_by', self.env.user.id)
                vals.setdefault('verified_date', fields.Datetime.now())
            else:
                vals.setdefault('verified_by', False)
                vals.setdefault('verified_date', False)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('verified'):
                if not self.env.user.has_group(
                    'ethelco_wholesale_legal_docs.group_legal_compliance_manager'
                ):
                    raise AccessError(
                        _('Only Legal Compliance Managers can verify legal documents.')
                    )
                vals.setdefault('verified_by', self.env.user.id)
                vals.setdefault('verified_date', fields.Datetime.now())
        return super().create(vals_list)

    def action_mark_verified(self):
        self.ensure_one()
        if not self.env.user.has_group(
            'ethelco_wholesale_legal_docs.group_legal_compliance_manager'
        ):
            raise UserError(_('Only Legal Compliance Managers can verify legal documents.'))
        if not self.attachment_ids:
            raise UserError(_('Attach the document file before verifying.'))
        self.write({'verified': True})
        return True

    @api.model
    def _cron_recompute_legal_documents(self):
        """Recompute stored states and schedule expiry reminder activities."""
        docs = self.search([('active', '=', True)])
        docs._compute_state()
        docs.mapped('partner_id')._compute_legal_compliance()
        self._cron_create_expiry_activities(docs)

    @api.model
    def _cron_create_expiry_activities(self, docs=None):
        today = fields.Date.context_today(self)
        docs = docs if docs is not None else self.search([
            ('active', '=', True),
            ('type_id.has_expiry', '=', True),
            ('expiry_date', '!=', False),
        ])
        Activity = self.env['mail.activity']
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return

        manager_group = self.env.ref(
            'ethelco_wholesale_legal_docs.group_legal_compliance_manager',
            raise_if_not_found=False,
        )
        manager_users = manager_group.user_ids if manager_group else self.env['res.users']

        for doc in docs.filtered(lambda d: d.expiry_date and d.type_id.has_expiry):
            days_left = (doc.expiry_date - today).days
            milestones = {doc.type_id.warning_days or 30, 15, 0}
            if days_left not in milestones:
                continue

            if days_left > 0:
                summary = _('Legal document expiring in %s day(s)') % days_left
                note = _(
                    'Document "%(type)s" for %(partner)s expires on %(date)s.'
                ) % {
                    'type': doc.type_id.display_name,
                    'partner': doc.partner_id.display_name,
                    'date': doc.expiry_date,
                }
            else:
                summary = _('Legal document expired')
                note = _(
                    'Document "%(type)s" for %(partner)s expired on %(date)s.'
                ) % {
                    'type': doc.type_id.display_name,
                    'partner': doc.partner_id.display_name,
                    'date': doc.expiry_date,
                }

            user_ids = set()
            salesperson = doc.partner_id.user_id
            if salesperson:
                user_ids.add(salesperson.id)
            user_ids.update(manager_users.ids)
            if not user_ids:
                user_ids.add(self.env.user.id)

            for user_id in user_ids:
                existing = Activity.search([
                    ('res_model', '=', self._name),
                    ('res_id', '=', doc.id),
                    ('user_id', '=', user_id),
                    ('summary', '=', summary),
                    ('activity_type_id', '=', activity_type.id),
                ], limit=1)
                if existing:
                    continue
                doc.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=summary,
                    note=note,
                    user_id=user_id,
                    date_deadline=doc.expiry_date if days_left >= 0 else today,
                )
