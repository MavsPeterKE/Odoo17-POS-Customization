from odoo import fields, models, api
from odoo.tools import formatLang
from markupsafe import Markup
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    POS_SESSION_APPROVAL_STATE = [
        ('pending_approval_1', 'To Approve'),
        ('pending_approval_2', 'To Approve'),
    ]

    approval_data = fields.Json(string='Approval Data')
    state = fields.Selection(selection_add=POS_SESSION_APPROVAL_STATE,
                             ondelete={'pending_approval_1': 'set default', 'pending_approval_2': 'set default'}
                             )

    @api.model
    def post_close_session_approval(self, vals):
        session = self.env['pos.session'].browse(vals.get('pos_session_id'))
        if vals.get('approval_level') == 'one_way':
            role_id = vals.get('roles')[0] if vals.get('roles') else None

            if role_id:
                role = self.env['res.groups'].browse(role_id)
                approving_user = role.users[0] if role.users else None
                self.update_pos_session('pending_approval_1', approving_user, session, vals)

        elif vals.get('approval_level') == 'two_way':
            role_ids = vals.get('roles') if vals.get('roles') else []
            if role_ids:
                roles = self.env['res.groups'].browse(role_ids)

                first_level_user = None
                if roles:
                    first_role = roles[0]
                    if first_role.users:
                        first_level_user = first_role.users[0]

                # Update Approval for first level
                self.update_pos_session('pending_approval_1', first_level_user, session, vals)
        return {
            'request_type': 'close_session_approval',
            'action': 'done'
        }

    def update_pos_session(self, state, user, session, vals):
        session.write(
            {'state': state,
             'approval_data': vals
             })
        _logger.info("post_close_session_approval called")
        self.send_approval_notifications(session, user, vals.get('cash_difference'))
        self.post_message_note(session, vals.get('cash_difference'), user)

    def post_message_note(self, session, cash_diff, user):
        message_body = Markup("""
            <h4>POS Close Session Approval Requested</h4>
            <ul>
                <li><strong>Session:</strong> %(session_name)s</li>
                <li><strong>Cash Difference:</strong> %(cash_difference)s</li>
                <li><strong>Approval Request to:</strong> %(approval_users)s</li>
                <li><strong>User:</strong> %(user_name)s</li>
            </ul>
        """) % {
            'session_name': session.name,
            'cash_difference': formatLang(self.env, cash_diff, digits=2),
            'approval_users': user.complete_name,
            'user_name': self.env.user.name,
        }
        session.message_post(body=message_body)

    def send_approval_notifications(self, session, user, cash_diff):
        self.env['mail.message'].create({
            'body': f'Session {session.name} is pending your approval. Session has a Cash Difference of ',
            'subject': 'POS Session Approval Required',
            'message_type': 'notification',
            'model': 'pos.session',
            'res_id': self.env.context.get('active_id'),
            'partner_ids': [(4, user.partner_id.id)],
        })
        _logger.info(f"Notification sent to {user.name} for session {session.id}")

        template = self.env.ref('custom_pos_approval.email_template_pos_session_approval')

        values = {
            'session_name': session.name,
            'cash_difference': formatLang(self.env, cash_diff, digits=2),
            'receipt_mails': user.email,
            'pos_user': self.env.user.name,
            'email_from': self._get_default_email_from
        }

        template.with_context(values).send_mail(session.id, force_send=False)

    def _get_default_email_from(self):
        smtp_server = self.env['ir.mail_server'].search([('sequence', '=', 1)], limit=1)
        return smtp_server.smtp_user if smtp_server else 'devodootest54@gmail.com'

    def action_approve_session_close(self):
        # Retrieve approval and current user
        vals = self.approval_data
        approval_level = vals.get('approval_level', False)

        if not self.is_valid_approving_user(vals.get('roles')):
            raise ValidationError('The User is not authorized to perform this operation')

        # If approval_level is 'one_way', complete the POS close session immediately
        if approval_level == 'one_way':
            roles = self.env['res.groups'].browse(vals.get('roles')[0])
            user_ids = [user.id for user in roles.users]

            if self.env.user.id not in user_ids:
                raise ValidationError("You do not have permission to approve this request")

            self.complete_pos_close_session(vals)
            return

        # For 'two_way' approval, check the current state
        if approval_level == 'two_way':
            if self.state == 'pending_approval_2':
                # If already pending second approval, complete the session
                second_role = self.env['res.groups'].browse(vals.get('roles')[1])
                user_ids = [user.id for user in second_role.users]

                if self.env.user.id not in user_ids:
                    raise ValidationError("You do not have permission to approve this request")

                self.complete_pos_close_session(vals)
            else:
                # Otherwise, move to the second approval stage
                role_ids = vals.get('roles') if vals.get('roles') else []

                if role_ids:
                    roles = self.env['res.groups'].browse(role_ids)

                    second_level_user = None
                    if roles:
                        second_role = roles[1]
                        user_ids = [user.id for user in second_role.users]

                        if self.env.user.id not in user_ids:
                            raise ValidationError("You do not have permission to approve this request")

                        if second_role.users:
                            second_level_user = second_role.users[1]
                    self.update_pos_session('pending_approval_2', second_level_user, self, vals)
        return True

    def complete_pos_close_session(self, vals):
        super(PosSession, self).post_closing_cash_details(vals.get('cash_difference'))
        super(PosSession, self).update_closing_control_state_session(vals.get('notes'))
        super(PosSession, self).close_session_from_ui(vals.get('payment_methods'))
        return True

    def is_valid_approving_user(self, role_ids):
        if not role_ids:
            return False

        current_user_id = self.env.user.id
        roles = self.env['res.groups'].browse(role_ids)
        user_ids = list(set(user.id for role in roles for user in role.users))
        return current_user_id in user_ids
