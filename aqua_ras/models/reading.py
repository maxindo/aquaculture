from datetime import timedelta

from odoo import api, fields, models

from .constants import PARAMETERS


class AquaReadingAgg(models.Model):
    _name = 'aqua.reading.agg'
    _description = 'Agregat Pembacaan Sensor'
    _order = 'timestamp desc'

    device_id = fields.Many2one('aqua.device', required=True, ondelete='cascade', index=True)
    tank_id = fields.Many2one(related='device_id.tank_id', store=True, index=True)
    farm_id = fields.Many2one(related='tank_id.farm_id', store=True)
    parameter = fields.Selection(PARAMETERS, related='device_id.parameter', store=True, index=True)
    timestamp = fields.Datetime(required=True, index=True)
    avg = fields.Float(string='Rata-rata')
    min = fields.Float()
    max = fields.Float()
    sample_count = fields.Integer()
    flag = fields.Selection([('ok', 'OK'), ('calibration_expired', 'Kalibrasi kedaluwarsa')], default='ok')

    _dev_ts_uniq = models.Constraint('UNIQUE(device_id, timestamp)', 'Data duplikat.')

    @api.model
    def _cron_purge(self):
        months = int(self.env['ir.config_parameter'].sudo().get_param('aqua_ras.retention_months', 12))
        limit = fields.Datetime.now() - timedelta(days=30 * months)
        self.search([('timestamp', '<', limit)]).unlink()
