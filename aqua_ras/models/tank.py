from odoo import api, fields, models


class AquaTank(models.Model):
    _name = 'aqua.tank'
    _description = 'Kolam / Tangki'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    farm_id = fields.Many2one('aqua.farm', required=True, ondelete='cascade')
    system_id = fields.Many2one('aqua.system', domain="[('farm_id', '=', farm_id)]")
    volume_m3 = fields.Float(string='Volume (m³)')
    device_ids = fields.One2many('aqua.device', 'tank_id')
    batch_ids = fields.One2many('aqua.batch', 'tank_id')
    alert_ids = fields.One2many('aqua.alert', 'tank_id')

    current_batch_id = fields.Many2one('aqua.batch', compute='_compute_live')
    open_alert_count = fields.Integer(compute='_compute_live')
    last_do = fields.Float(compute='_compute_live')
    last_temp = fields.Float(compute='_compute_live')
    last_ph = fields.Float(compute='_compute_live')
    color = fields.Integer(compute='_compute_live')

    @api.depends('batch_ids.state', 'alert_ids.state', 'device_ids.last_value')
    def _compute_live(self):
        for tank in self:
            tank.current_batch_id = tank.batch_ids.filtered(lambda b: b.state == 'running')[:1]
            open_alerts = tank.alert_ids.filtered(lambda a: a.state in ('open', 'ack'))
            tank.open_alert_count = len(open_alerts)
            vals = {d.parameter: d.last_value for d in tank.device_ids if d.kind == 'sensor'}
            tank.last_do = vals.get('do', 0.0)
            tank.last_temp = vals.get('temp', 0.0)
            tank.last_ph = vals.get('ph', 0.0)
            if any(a.severity == 'critical' for a in open_alerts):
                tank.color = 1       # merah
            elif open_alerts:
                tank.color = 2       # oranye
            else:
                tank.color = 10      # hijau

    def action_view_alerts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Alert', 'res_model': 'aqua.alert',
            'view_mode': 'list,form', 'domain': [('tank_id', '=', self.id)],
        }

    def action_view_readings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'Pembacaan Sensor', 'res_model': 'aqua.reading.agg',
            'view_mode': 'graph,pivot,list', 'domain': [('tank_id', '=', self.id)],
        }
