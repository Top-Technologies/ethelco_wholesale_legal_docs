# -*- coding: utf-8 -*-
from odoo import fields, models


class EthelcoLegalDocumentType(models.Model):
    _name = 'ethelco.legal.document.type'
    _description = 'Legal Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    required_for_wholesale = fields.Boolean(
        string='Required for Wholesale',
        default=True,
        help='When enabled, wholesale customers must have a valid document of this type.',
    )
    has_expiry = fields.Boolean(
        string='Has Expiry Date',
        help='When enabled, documents of this type must have an expiry date.',
    )
    warning_days = fields.Integer(
        string='Warning Days',
        default=30,
        help='Days before expiry to mark the document as expiring and schedule activities.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The document type code must be unique.'),
    ]
