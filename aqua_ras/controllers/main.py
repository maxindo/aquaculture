import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AquaGatewayController(http.Controller):

    def _gateway(self):
        key = request.httprequest.headers.get('X-Gateway-Key')
        return request.env['aqua.gateway'].sudo()._authenticate(key)

    @http.route('/aqua/ingest', type='http', auth='public', methods=['POST'], csrf=False)
    def ingest(self, **kw):
        gateway = self._gateway()
        if not gateway:
            return request.make_json_response({'status': 'unauthorized'}, status=401)
        try:
            payload = request.get_json_data()
        except Exception:
            return request.make_json_response({'status': 'bad_json'}, status=400)
        result = gateway.ingest(payload.get('readings', []))
        return request.make_json_response({'status': 'ok', **result})

    @http.route('/aqua/config', type='http', auth='public', methods=['GET'], csrf=False)
    def config(self, **kw):
        """Edge mengambil aturan alert untuk dipakai sebagai kontrol lokal (fail-safe)."""
        gateway = self._gateway()
        if not gateway:
            return request.make_json_response({'status': 'unauthorized'}, status=401)
        rules = request.env['aqua.alert.rule'].sudo().search([])
        data = [{
            'id': r.id, 'parameter': r.parameter, 'operator': r.operator, 'threshold': r.threshold,
            'duration_min': r.duration_min, 'severity': r.severity,
            'tanks': r.tank_ids.mapped('code') or [],
        } for r in rules]
        devices = [{'topic': d.mqtt_topic, 'parameter': d.parameter, 'kind': d.kind}
                   for d in gateway.device_ids]
        return request.make_json_response({'status': 'ok', 'rules': data, 'devices': devices})
