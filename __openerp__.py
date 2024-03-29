# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Impact Assessment',
    'version': '0.1',
    'category': 'Internal',
    'description': """
Create beautiful web ias and visualize answers
==================================================

It depends on the answers or reviews of some questions by different users. A
ia may have multiple pages. Each page may contain multiple questions and
each question may have multiple answers. Different users may give different
answers of question and according to that ia is done. Partners are also
sent mails with personal token for the invitation of the ia.
    """,
    'summary': 'Create Impact Assessment forms, collect answers and print statistics',
    'author': 'Sarath M S',
    'website': 'http://reapbenefit.org',
    'depends': ['email_template', 'mail', 'website'],
    'data': [
        'security/ia_security.xml',
        'security/ir.model.access.csv',
        'views/ia_views.xml',
        'views/ia_templates.xml',
        'views/ia_result.xml',
        'wizard/ia_email_compose_message.xml',
        'data/ia_stages.xml',
        'data/ia_cron.xml',
        'report/ia_report_view.xml'
    ],
    # 'demo': ['data/ia_demo_user.xml',
    #          'data/ia_demo_feedback.xml',
    #          'data/ia.user_input.csv',
    #          'data/ia.user_input_line.csv'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
    'images': [],
}
