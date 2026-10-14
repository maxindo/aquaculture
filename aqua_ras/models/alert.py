import logging

import requests

from odoo import _, api, fields, models

from .constants import PARAMETERS

_logger = logging.getLogger(__name__)


class AquaAlert(models.Model):
    _name = 'aqua.alert'
    _description = 'Kejadian Alarm'
    _inherit = ['mail.thread']
    _order = 'date_start desc'

    name = fields.Char(readonly=True, default='New')
    alert_type = fields.Selection([('threshold', 'Ambang batas'), ('offline', 'Sensor offline')],
                                  default='threshold', required=True)
    rule_id = fields.Many2one('aqua.alert.rule', ondelete='set null')
    device_id = fields.Many2one('aqua.device', ondelete='set null')
    tank_id = fields.Many2one('aqua.tank', required=True, ondelete='cascade', index=True)
    farm_id = fields.Many2one(related='tank_id.farm_id', store=True)
    severity = fields.Selection([('warning', 'Warning'), ('critical', 'Critical')], default='warning')
    parameter = fields.Selection(PARAMETERS)
    value = fields.Float()
    threshold = fields.Float()
    date_start = fields.Datetime(default=fields.Datetime.now)
    date_end = fields.Datetime()
    state = fields.Selection([('open', 'Terbuka'), ('ack', 'Ditangani'), ('closed', 'Selesai')],
                             default='open', tracking=True)
    ack_user_id = fields.Many2one('res.users', readonly=True)
    ack_date = fields.Datetime(readonly=True)
    escalated = fields.Boolean(readonly=True)
    maintenance_id = fields.Many2one('maintenance.request', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('aqua.alert') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    @api.model
    def _open_from_rule(self, rule, tank, value, device):
        alert = self.create({
            'alert_type': 'threshold', 'rule_id': rule.id, 'tank_id': tank.id,
            'device_id': device.id if device else False, 'severity': rule.severity,
            'parameter': rule.parameter, 'value': value, 'threshold': rule.threshold,
        })
        op = '<' if rule.operator == 'lt' else '>'
        body = _('%(sev)s: %(param)s di %(tank)s = %(val).2f (batas %(op)s %(thr).2f)',
                 sev=rule.severity.upper(), param=rule.parameter, tank=tank.name,
                 val=value, op=op, thr=rule.threshold)
        alert._notify(rule.notify_user_ids, body)
        if rule.create_maintenance and device and device.equipment_id:
            alert.maintenance_id = self.env['maintenance.request'].create({
                'name': _('[%s] %s', alert.name, rule.name),
                'equipment_id': device.equipment_id.id,
                'maintenance_type': 'corrective',
            })
        return alert

    @api.model
    def _open_offline(self, device):
        if not device.tank_id:
            return False
        alert = self.create({
            'alert_type': 'offline', 'device_id': device.id, 'tank_id': device.tank_id.id,
            'severity': 'warning', 'parameter': device.parameter,
        })
        alert._notify(self.env['res.users'], _('Sensor %s tidak mengirim data sejak %s', device.name, device.last_seen))
        return alert

    def _notify(self, users, body):
        self.ensure_one()
        partners = users.partner_id
        if partners:
            self.message_subscribe(partner_ids=partners.ids)
        self.message_post(body=body, partner_ids=partners.ids,
                          subtype_xmlid='mail.mt_comment', message_type='comment')
        self._notify_telegram(body)

    def _notify_telegram(self, text):
        icp = self.env['ir.config_parameter'].sudo()
        token = icp.get_param('aqua_ras.telegram_bot_token')
        chat_id = icp.get_param('aqua_ras.telegram_chat_id')
        if not (token and chat_id):
            return
        try:
            requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                          json={'chat_id': chat_id, 'text': f'[AQUA RAS] {text}'}, timeout=5)
        except requests.RequestException:
            _logger.warning('Gagal mengirim notifikasi Telegram', exc_info=True)

    # ------------------------------------------------------------------
    def action_ack(self):
        self.write({'state': 'ack', 'ack_user_id': self.env.uid, 'ack_date': fields.Datetime.now()})

    def action_close(self):
        self._close()

    def _close(self):
        for alert in self.filtered(lambda a: a.state != 'closed'):
            alert.write({'state': 'closed', 'date_end': fields.Datetime.now()})
            alert.message_post(body=_('Alarm selesai / parameter kembali normal.'))

    @api.model
    def _cron_escalate(self):
        now = fields.Datetime.now()
        alerts = self.search([('state', '=', 'open'), ('severity', '=', 'critical'),
                              ('escalated', '=', False), ('rule_id', '!=', False)])
        for alert in alerts:
            rule = alert.rule_id
            if (now - alert.date_start).total_seconds() >= rule.escalate_min * 60:
                alert._notify(rule.escalate_user_ids,
                              _('ESKALASI: %s belum ditangani > %s menit', alert.name, rule.escalate_min))
                alert.escalated = True
