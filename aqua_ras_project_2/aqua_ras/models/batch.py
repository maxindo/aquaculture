import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AquaBatch(models.Model):
    _name = 'aqua.batch'
    _description = 'Batch / Siklus Budidaya'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    tank_id = fields.Many2one('aqua.tank', required=True, tracking=True)
    farm_id = fields.Many2one(related='tank_id.farm_id', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    species = fields.Selection([
        ('nila', 'Nila'), ('lele', 'Lele'), ('patin', 'Patin'),
        ('gurame', 'Gurame'), ('mas', 'Ikan Mas'), ('other', 'Lainnya')], required=True, default='nila')
    state = fields.Selection([
        ('draft', 'Draft'), ('running', 'Berjalan'),
        ('harvested', 'Selesai Panen'), ('cancel', 'Batal')], default='draft', tracking=True)
    start_date = fields.Date(default=fields.Date.context_today, required=True)
    end_date = fields.Date()
    initial_qty = fields.Integer(string='Jumlah tebar (ekor)', required=True)
    initial_abw_g = fields.Float(string='ABW awal (g)', required=True)
    seed_cost = fields.Monetary(string='Biaya benih')
    analytic_account_id = fields.Many2one('account.analytic.account', readonly=True, copy=False)

    feeding_ids = fields.One2many('aqua.feeding', 'batch_id')
    sampling_ids = fields.One2many('aqua.sampling', 'batch_id')
    mortality_ids = fields.One2many('aqua.mortality', 'batch_id')
    harvest_ids = fields.One2many('aqua.harvest', 'batch_id')

    # KPI (tidak disimpan, dihitung dari log)
    age_days = fields.Integer(compute='_compute_kpi')
    mortality_qty = fields.Integer(compute='_compute_kpi')
    harvest_qty = fields.Integer(compute='_compute_kpi')
    harvest_kg = fields.Float(compute='_compute_kpi')
    current_qty = fields.Integer(compute='_compute_kpi')
    last_abw_g = fields.Float(compute='_compute_kpi', string='ABW terakhir (g)')
    biomass_kg = fields.Float(compute='_compute_kpi')
    total_feed_kg = fields.Float(compute='_compute_kpi')
    fcr = fields.Float(compute='_compute_kpi', digits=(6, 2))
    sr = fields.Float(compute='_compute_kpi', string='SR (%)', digits=(6, 1))
    adg = fields.Float(compute='_compute_kpi', string='ADG (g/hari)', digits=(6, 2))
    sgr = fields.Float(compute='_compute_kpi', string='SGR (%/hari)', digits=(6, 2))
    ration_pct = fields.Float(compute='_compute_kpi', string='Ration (% biomassa)', digits=(6, 2))
    ration_kg_day = fields.Float(compute='_compute_kpi', string='Ration (kg/hari)', digits=(8, 2))
    ration_note = fields.Char(compute='_compute_kpi')
    feed_cost = fields.Monetary(compute='_compute_kpi')
    other_cost = fields.Monetary(compute='_compute_kpi', string='Biaya lain (analytic)')
    total_cost = fields.Monetary(compute='_compute_kpi')
    hpp_per_kg = fields.Monetary(compute='_compute_kpi', string='HPP/kg')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('aqua.batch') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    def _avg_tank_param(self, parameter, hours=24):
        self.ensure_one()
        since = fields.Datetime.subtract(fields.Datetime.now(), hours=hours)
        aggs = self.env['aqua.reading.agg'].search([
            ('tank_id', '=', self.tank_id.id), ('parameter', '=', parameter), ('timestamp', '>=', since)])
        return sum(aggs.mapped('avg')) / len(aggs) if aggs else 0.0

    @api.depends('feeding_ids.qty_kg', 'feeding_ids.feed_cost', 'sampling_ids.abw_g', 'sampling_ids.date',
                 'mortality_ids.qty', 'harvest_ids.qty', 'harvest_ids.weight_kg',
                 'initial_qty', 'initial_abw_g', 'seed_cost', 'state', 'start_date', 'end_date',
                 'analytic_account_id')
    def _compute_kpi(self):
        today = fields.Date.context_today(self)
        for b in self:
            end = b.end_date or today
            b.age_days = max((end - b.start_date).days, 0) if b.start_date else 0
            b.mortality_qty = sum(b.mortality_ids.mapped('qty'))
            b.harvest_qty = sum(b.harvest_ids.mapped('qty'))
            b.harvest_kg = sum(b.harvest_ids.mapped('weight_kg'))
            b.current_qty = max(b.initial_qty - b.mortality_qty - b.harvest_qty, 0)
            last_sampling = b.sampling_ids.sorted(lambda s: (s.date, s.id))[-1:]
            b.last_abw_g = last_sampling.abw_g if last_sampling else b.initial_abw_g
            b.biomass_kg = b.current_qty * b.last_abw_g / 1000.0
            b.total_feed_kg = sum(b.feeding_ids.mapped('qty_kg'))

            initial_biomass = b.initial_qty * b.initial_abw_g / 1000.0
            gain = b.biomass_kg + b.harvest_kg - initial_biomass     # bobot ikan mati diabaikan
            b.fcr = b.total_feed_kg / gain if gain > 0 else 0.0
            b.sr = (b.current_qty + b.harvest_qty) / b.initial_qty * 100 if b.initial_qty else 0.0
            b.adg = (b.last_abw_g - b.initial_abw_g) / b.age_days if b.age_days else 0.0
            if b.age_days and b.initial_abw_g > 0 and b.last_abw_g > 0:
                b.sgr = (math.log(b.last_abw_g) - math.log(b.initial_abw_g)) / b.age_days * 100
            else:
                b.sgr = 0.0

            # rekomendasi ration
            Rule = self.env['aqua.ration.rule']
            temp = b._avg_tank_param('temp') if b.state == 'running' else 0.0
            b.ration_pct = Rule._pct_for(b.last_abw_g) * Rule._temp_factor(temp)
            b.ration_kg_day = b.biomass_kg * b.ration_pct / 100.0
            note = ''
            if b.state == 'running':
                do_val = b._avg_tank_param('do', hours=1)
                if do_val and do_val < 4.0:
                    note = _('DO rendah (%.1f mg/L): tunda/kurangi pakan', do_val)
                    b.ration_kg_day = 0.0
            b.ration_note = note

            # biaya & HPP
            b.feed_cost = sum(b.feeding_ids.mapped('feed_cost'))
            other = 0.0
            if b.analytic_account_id:
                lines = self.env['account.analytic.line'].search([('account_id', '=', b.analytic_account_id.id)])
                other = -sum(lines.mapped('amount'))
            b.other_cost = other
            b.total_cost = b.seed_cost + b.feed_cost + other
            b.hpp_per_kg = b.total_cost / b.harvest_kg if b.harvest_kg else 0.0

    # ------------------------------------------------------------------
    def action_start(self):
        for b in self:
            if b.initial_qty <= 0 or b.initial_abw_g <= 0:
                raise UserError(_('Isi jumlah tebar dan ABW awal terlebih dahulu.'))
            busy = self.search([('tank_id', '=', b.tank_id.id), ('state', '=', 'running'), ('id', '!=', b.id)], limit=1)
            if busy:
                raise UserError(_('Tangki %s masih memiliki batch berjalan: %s', b.tank_id.name, busy.name))
            if not b.analytic_account_id:
                plan = self.env.ref('aqua_ras.analytic_plan_aqua')
                b.analytic_account_id = self.env['account.analytic.account'].create({
                    'name': b.name, 'plan_id': plan.id, 'company_id': b.company_id.id})
            b.state = 'running'

    def action_finish(self):
        self.write({'state': 'harvested', 'end_date': fields.Date.context_today(self)})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})
