# -*- coding: utf-8 -*-
{
    'name': 'Ethelco Wholesale Legal Documents',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Block wholesale SO confirmation when required legal documents are missing, unverified or expired',
    'description': """
Ethelco Wholesale Legal Documents
=================================

Enforces legal-document compliance for wholesale customers before Sales Order
confirmation. Quotation creation and sending remain allowed.

Features
--------
* Configurable legal document types (Trade License, TIN, VAT, etc.)
* Partner document register with verification and expiry tracking
* Wholesale SO confirmation blocked until documents are valid
* Manager override wizard with chatter audit trail
* Daily cron for state recompute and expiry activities
    """,
    'author': 'Top System Solutions Technologies',
    'website': 'https://www.topsystechnologies.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
        'sale',
        'sale_management',
    ],
    'data': [
        'security/legal_docs_security.xml',
        'security/ir.model.access.csv',
        'security/legal_docs_record_rules.xml',
        'data/legal_document_type_data.xml',
        'data/ir_cron_data.xml',
        'views/legal_document_type_views.xml',
        'views/partner_legal_document_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/menus.xml',
        'report/wholesale_compliance_report_views.xml',
        'wizard/legal_override_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
