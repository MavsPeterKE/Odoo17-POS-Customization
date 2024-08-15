{
    'name': 'Custom POS Approval',
    "author": "Peter",
    'version': '17.0.1.0',
    'category': 'Point of Sale',
    'summary':'Custom POS Session Approval',
    'description': """
        Module that adds approval to POS session
    """,
    "data": [
            "views/res_config_settings_views.xml",
            "views/pos_session_view_inherit.xml",
            "views/email_template.xml",
            "views/pos_config_kanban_view_inherit.xml",
            "security/groups.xml",
    ],
    'assets': {
            'point_of_sale._assets_pos': [
                'custom_pos_approval/static/src/js/custom_close_popup.js',
            ],
        },
    'depends': ['point_of_sale'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}