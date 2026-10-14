import hashlib
import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AquaGateway(models.Model):
    _name = 'aqua.gateway'
    _description = 'Edge Gateway (Node-RED / Mini PC)'

    name = fields.Char(required=True)
    farm_id = fields.Many2one('aqua.farm', required=True)
    active = fields.Boolean(default=True)
    key_hash = fields.Char(readonly=True, copy=False)
    last_seen = fields.Datetime(readonly=True)
    device_ids = fields.One2many('aqua.device', 'gateway_id')

    def action_generate_key(self):
        self.ensure_one()
        key = secrets.token_urlsafe(32)
        self.key_hash = hashlib.sha256(key.encode()).hexdigest()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('API key gateway'),
                'message': _('Simpan sekarang, tidak akan ditampilkan lagi: %s', key),
                'sticky': True, 'type': 'warning',
            },
        }

    @api.model
    def _authenticate(self, key):
        if not key:
            return self.browse()
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self.search([('key_hash', '=', digest), ('active', '=', True)], limit=1)

    # ------------------------------------------------------------------
    def ingest(self, readings):
        """Terima agregat dari gateway.

        readings: [{topic, ts('YYYY-MM-DD HH:MM:SS' UTC), avg, min, max, n}, ...]
        """
        self.ensure_one()
        Device = self.env['aqua.device']
        Agg = self.env['aqua.reading.agg']
        server_now = fields.Datetime.now()
        created, duplicates, unknown = 0, 0, set()
        touched = {}   # (tank, parameter) -> [device, latest_ts]

        for r in readings or []:
            topic = r.get('topic')
            device = Device.search([('mqtt_topic', '=', topic), ('gateway_id', 'in', (self.id, False))], limit=1)
            if not device:
                unknown.add(topic)
                continue
            try:
                ts = fields.Datetime.to_datetime(r.get('ts')) or server_now
                avg = float(r['avg'])
            except (KeyError, TypeError, ValueError):
                continue
            if Agg.search_count([('device_id', '=', device.id), ('timestamp', '=', ts)]):
                duplicates += 1
                continue
            Agg.create({
                'device_id': device.id,
                'timestamp': ts,
                'avg': avg,
                'min': float(r.get('min', avg)),
                'max': float(r.get('max', avg)),
                'sample_count': int(r.get('n', 1)),
                'flag': 'calibration_expired' if device.calibration_due else 'ok',
            })
            created += 1
            if not device.last_seen or ts >= device.last_seen:
                device.write({'last_value': avg, 'last_seen': ts})
            if device.tank_id:
                key = (device.tank_id.id, device.parameter)
                if key not in touched or ts > touched[key][1]:
                    touched[key] = [device, ts]

        self.last_seen = server_now
        Rule = self.env['aqua.alert.rule']
        for (tank_id, parameter), (device, ts) in touched.items():
            # data buffer lama (replay) tidak memicu alarm baru
            if server_now - ts > timedelta(minutes=15):
                continue
            Rule.evaluate_for_tank(device.tank_id, parameter, ts, device)
        return {'created': created, 'duplicates': duplicates, 'unknown_topics': sorted(t for t in unknown if t)}
