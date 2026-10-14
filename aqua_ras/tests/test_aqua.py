from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestAquaRas(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.farm = cls.env['aqua.farm'].create({'name': 'Farm Test'})
        cls.tank = cls.env['aqua.tank'].create({'name': 'T1', 'farm_id': cls.farm.id, 'volume_m3': 10})
        cls.gw = cls.env['aqua.gateway'].create({'name': 'GW', 'farm_id': cls.farm.id})
        cls.dev = cls.env['aqua.device'].create({
            'name': 'DO T1', 'code': 'DO-T1', 'tank_id': cls.tank.id, 'gateway_id': cls.gw.id,
            'parameter': 'do', 'kind': 'sensor', 'mqtt_topic': 'farm1/t1/do'})
        cls.env['aqua.alert.rule'].create({
            'name': 'DO kritis', 'parameter': 'do', 'operator': 'lt', 'threshold': 4.0,
            'duration_min': 3, 'severity': 'critical'})

    def test_kpi(self):
        batch = self.env['aqua.batch'].create({
            'tank_id': self.tank.id, 'initial_qty': 1000, 'initial_abw_g': 5.0})
        batch.action_start()
        self.env['aqua.sampling'].create({'batch_id': batch.id, 'sample_count': 10, 'total_weight_g': 500})
        self.env['aqua.mortality'].create({'batch_id': batch.id, 'qty': 50})
        self.env['aqua.feeding'].create({'batch_id': batch.id, 'qty_kg': 100})
        self.assertEqual(batch.current_qty, 950)
        self.assertAlmostEqual(batch.biomass_kg, 47.5)
        self.assertAlmostEqual(batch.sr, 95.0)
        self.assertAlmostEqual(batch.fcr, 100 / 42.5, places=3)

    def test_ingest_alert_and_recovery(self):
        now = fields.Datetime.now()
        readings = [{'topic': 'farm1/t1/do', 'ts': fields.Datetime.to_string(now - timedelta(minutes=i)),
                     'avg': 3.0, 'min': 2.9, 'max': 3.1, 'n': 6} for i in range(4, -1, -1)]
        res = self.gw.ingest(readings)
        self.assertEqual(res['created'], 5)
        alert = self.env['aqua.alert'].search([('tank_id', '=', self.tank.id)])
        self.assertEqual(len(alert), 1)
        self.assertEqual(alert.severity, 'critical')
        # pulih
        self.gw.ingest([{'topic': 'farm1/t1/do', 'ts': fields.Datetime.to_string(now + timedelta(minutes=1)),
                         'avg': 6.0, 'min': 6.0, 'max': 6.0, 'n': 6}])
        self.assertEqual(alert.state, 'closed')

    def test_nh3_calc(self):
        wt = self.env['aqua.water.test'].create({
            'tank_id': self.tank.id, 'temp_c': 28, 'ph': 8.0, 'tan_mgl': 1.0})
        self.assertAlmostEqual(wt.nh3_mgl, 0.0654, places=3)
