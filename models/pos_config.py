from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = "pos.config"

    enable_approval = fields.Boolean('Enable Approval for Cash Difference')
    approval_level = fields.Selection([('one_way', 'One Way Approval'), ('two_way', 'Two-Way Approval')],
                                      string="Approval Level")
    roles = fields.Many2many('res.groups', string='Approval Roles')
