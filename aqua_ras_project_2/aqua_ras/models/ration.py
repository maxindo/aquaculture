from odoo import api, fields, models


class AquaRationRule(models.Model):
    _name = 'aqua.ration.rule'
    _description = 'Tabel Ration Pakan (% biomassa per hari)'
    _order = 'abw_min'

    name = fields.Char(compute='_compute_name', store=True)
    abw_min = fields.Float(string='ABW min (g)', required=True)
    abw_max = fields.Float(string='ABW maks (g)', required=True)
    pct = fields.Float(string='% biomassa/hari', required=True)
    pellet_size = fields.Char()
    note = fields.Char()

    @api.depends('abw_min', 'abw_max')
    def _compute_name(self):
        for rec in self:
            rec.name = f'{rec.abw_min:g} - {rec.abw_max:g} g'

    @api.model
    def _pct_for(self, abw_g):
        rule = self.search([('abw_min', '<=', abw_g), ('abw_max', '>', abw_g)], limit=1)
        return rule.pct if rule else 2.0

    @api.model
    def _temp_factor(self, temp):
        """Faktor koreksi suhu (contoh nila). Sesuaikan dengan spesies."""
        if not temp:
            return 1.0
        if temp < 20:
            return 0.3
        if temp < 24:
            return 0.6
        if temp < 26:
            return 0.85
        if temp <= 31:
            return 1.0
        if temp <= 33:
            return 0.8
        return 0.5
