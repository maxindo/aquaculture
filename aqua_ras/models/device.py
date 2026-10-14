from datetime import timedelta

from odoo import api, fields, models

from .constants import PARAMETERS


class AquaDevice(models.Model):
    _name = 'aqua.device'
    _description = 'Sensor / Aktuator'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    kind = fields.Selection([('sensor', 'Sensor'), ('actuator', 'Aktuator')], default='sensor', required=True)
    parameter = fields.Selection(PARAMETERS, required=True)
    unit = fields.Char()
    tank_id = fields.Many2one('aqua.tank', ondelete='set null')
    gateway_id = fields.Many2one('aqua.gateway')
    mqtt_topic = fields.Char(help='Contoh: farm1/tank3/do')
    equipment_id = fields.Many2one('maintenance.equipment', help='Untuk membuat maintenance request otomatis')
    last_value = fields.Float(readonly=True)
    last_seen = fields.Datetime(readonly=True)
    offline_after_min = fields.Integer(default=15)
    state = fields.Selection([('never', 'Belum ada data'), ('online', 'Online'), ('offline', 'Offline')],
                             compute='_compute_state')
    calibration_date = fields.Date()
    calibration_interval_days = fields.Integer(default=30)
    calibration_due = fields.Boolean(compute='_compute_calibration_due')

    _code_uniq = models.Constraint('UNIQUE(code)', 'Kode perangkat harus unik.')
    _topic_uniq = models.Constraint('UNIQUE(mqtt_topic)', 'Topic MQTT harus unik.')

    @api.depends('last_seen', 'offline_after_min')
    def _compute_state(self):
        now = fields.Datetime.now()
        for dev in self:
            if not dev.last_seen:
                dev.state = 'never'
            elif (now - dev.last_seen).total_seconds() > dev.offline_after_min * 60:
                dev.state = 'offline'
            else:
                dev.state = 'online'

    @api.depends('calibration_date', 'calibration_interval_days', 'kind', 'parameter')
    def _compute_calibration_due(self):
        today = fields.Date.context_today(self)
        for dev in self:
            if dev.kind == 'sensor' and dev.parameter in ('ph', 'do', 'orp', 'tds', 'turbidity'):
                due = (not dev.calibration_date) or \
                    dev.calibration_date + timedelta(days=dev.calibration_interval_days) < today
                dev.calibration_due = due
            else:
                dev.calibration_due = False

    @api.model
    def _cron_check_offline(self):
        """Watchdog: sensor berhenti mengirim data -> alert 'offline'."""
        Alert = self.env['aqua.alert']
        for dev in self.search([('kind', '=', 'sensor'), ('last_seen', '!=', False)]):
            open_alert = Alert.search([('device_id', '=', dev.id), ('alert_type', '=', 'offline'),
                                       ('state', 'in', ('open', 'ack'))], limit=1)
            if dev.state == 'offline' and not open_alert:
                Alert._open_offline(dev)
            elif dev.state == 'online' and open_alert:
                open_alert._close()
