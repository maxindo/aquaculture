from odoo import api, fields, models


class AquaFarm(models.Model):
    _name = 'aqua.farm'
    _description = 'Unit Usaha / Lokasi Budidaya'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    address = fields.Text()
    tank_ids = fields.One2many('aqua.tank', 'farm_id')
    system_ids = fields.One2many('aqua.system', 'farm_id')
    tank_count = fields.Integer(compute='_compute_tank_count')

    @api.depends('tank_ids')
    def _compute_tank_count(self):
        for rec in self:
            rec.tank_count = len(rec.tank_ids)


class AquaSystem(models.Model):
    _name = 'aqua.system'
    _description = 'Loop Sistem RAS'

    name = fields.Char(required=True)
    farm_id = fields.Many2one('aqua.farm', required=True, ondelete='cascade')
    tank_ids = fields.One2many('aqua.tank', 'system_id')
    components = fields.Text(help='Drum filter, biofilter, sump, UV, protein skimmer, dll.')
    total_volume_m3 = fields.Float()
