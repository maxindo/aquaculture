from datetime import timedelta

from odoo import fields, models

from .constants import PARAMETERS


class AquaAlertRule(models.Model):
    _name = 'aqua.alert.rule'
    _description = 'Aturan Alert Kualitas Air'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    parameter = fields.Selection(PARAMETERS, required=True)
    operator = fields.Selection([('lt', '<'), ('gt', '>')], required=True)
    threshold = fields.Float(required=True)
    hysteresis = fields.Float(default=0.3, help='Selisih agar alarm dianggap pulih (mencegah flapping)')
    duration_min = fields.Integer(default=5, help='Kondisi harus berlangsung N menit. 0 = langsung.')
    severity = fields.Selection([('warning', 'Warning'), ('critical', 'Critical')], default='warning', required=True)
    tank_ids = fields.Many2many('aqua.tank', help='Kosong = berlaku untuk semua tangki')
    notify_user_ids = fields.Many2many('res.users', 'aqua_rule_notify_rel', string='Notifikasi ke')
    escalate_min = fields.Integer(default=10, help='Naik level jika belum di-acknowledge')
    escalate_user_ids = fields.Many2many('res.users', 'aqua_rule_escalate_rel', string='Eskalasi ke')
    create_maintenance = fields.Boolean(help='Buat maintenance request pada equipment sensor terkait')

    # ------------------------------------------------------------------
    def _violates(self, value):
        self.ensure_one()
        return value < self.threshold if self.operator == 'lt' else value > self.threshold

    def _recovered(self, value):
        self.ensure_one()
        if self.operator == 'lt':
            return value >= self.threshold + self.hysteresis
        return value <= self.threshold - self.hysteresis

    def _open_alert(self, tank):
        return self.env['aqua.alert'].search([
            ('rule_id', '=', self.id), ('tank_id', '=', tank.id), ('state', 'in', ('open', 'ack'))], limit=1)

    def _rules_for(self, tank, parameter):
        return self.search([
            ('parameter', '=', parameter), '|', ('tank_ids', '=', False), ('tank_ids', 'in', tank.id)])

    # ------------------------------------------------------------------
    def evaluate_for_tank(self, tank, parameter, latest_ts, device=None):
        for rule in self._rules_for(tank, parameter):
            rule._evaluate(tank, latest_ts, device)

    def _evaluate(self, tank, latest_ts, device=None):
        self.ensure_one()
        since = latest_ts - timedelta(minutes=self.duration_min)
        aggs = self.env['aqua.reading.agg'].search([
            ('tank_id', '=', tank.id), ('parameter', '=', self.parameter),
            ('timestamp', '>=', since), ('timestamp', '<=', latest_ts)], order='timestamp')
        if not aggs:
            return
        last = aggs[-1]
        span = (aggs[-1].timestamp - aggs[0].timestamp).total_seconds()
        span_ok = self.duration_min == 0 or span >= self.duration_min * 60 * 0.8
        open_alert = self._open_alert(tank)
        if span_ok and all(self._violates(a.avg) for a in aggs):
            if open_alert:
                open_alert.value = last.avg
            else:
                self.env['aqua.alert']._open_from_rule(self, tank, last.avg, device)
        elif open_alert and self._recovered(last.avg):
            open_alert._close()

    def evaluate_instant(self, tank, parameter, value):
        """Untuk input manual (uji air): tanpa durasi."""
        for rule in self._rules_for(tank, parameter):
            open_alert = rule._open_alert(tank)
            if rule._violates(value):
                if not open_alert:
                    self.env['aqua.alert']._open_from_rule(rule, tank, value, None)
            elif open_alert and rule._recovered(value):
                open_alert._close()
