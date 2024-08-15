from odoo import _, fields, models, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_approval = fields.Boolean(
        'Enable Approval for Cash Difference',
        readonly=False,
        related="pos_config_id.enable_approval",
    )
    approval_level = fields.Selection([
        ('one_way', 'One Way Approval'),
        ('two_way', 'Two-Way Approval')
    ], related="pos_config_id.approval_level",
        required=True,
        string="Approval Level", readonly=False, )

    approval_roles = fields.Many2many(
        'res.groups',
        related="pos_config_id.roles",
        string='Approval Roles',
        required=True,
        help='Select user roles for POS session approval',
        readonly=False
    )

    @api.onchange('approval_roles')
    def _check_approval_roles(self):
        if self.approval_level == 'one_way' and len(self.approval_roles) != 1:
            return {
                'warning': {
                    'title': "Validation Warning",
                    'message': "One-Way approval requires that one role to be selected."
                }
            }
        elif self.approval_level == 'two_way' and len(self.approval_roles) != 2:
            return {
                'warning': {
                    'title': "Validation Warning",
                    'message': "Two-Way approval requires two roles to be selected."
                }
            }
        elif not self.approval_level and self.approval_roles:
            self.approval_roles = [(5, 0, 0)]
            return {
                'warning': {
                    'title': "Validation Warning",
                    'message': "Approval roles cannot be set before setting a specific approval level. Please set Approval Level first."
                }
            }

    @api.constrains('approval_roles', 'approval_level')
    def _check_approval_roles(self):
        for record in self:
            if not record.approval_level and record.approval_roles:
                raise ValidationError(
                    "Approval roles cannot be set before setting a specific approval level. "
                    "Please set Approval Level first.")
            if record.approval_level == 'one_way' and len(record.approval_roles) != 1:
                raise ValidationError("One-Way approval requires that one role to be selected.")
            if record.approval_level == 'two_way' and len(record.approval_roles) != 2:
                raise ValidationError("Two-Way approval requires two roles to be selected.")
