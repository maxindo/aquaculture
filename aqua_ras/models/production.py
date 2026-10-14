from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AquaFeeding(models.Model):
    _name = 'aqua.feeding'
    _description = 'Log Pemberian Pakan'
    _order = 'datetime desc'

    batch_id = fields.Many2one('aqua.batch', required=True, ondelete='cascade', domain="[('state','=','running')]")
    tank_id = fields.Many2one(related='batch_id.tank_id', store=True)
    company_id = fields.Many2one(related='batch_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    qty_kg = fields.Float(string='Pakan (kg)', required=True)
    product_id = fields.Many2one('product.product', string='Produk pakan')
    source = fields.Selection([('manual', 'Manual'), ('auto', 'Auto feeder')], default='manual')
    consume_stock = fields.Boolean(default=True, help='Buat pergerakan stok otomatis')
    move_id = fields.Many2one('stock.move', readonly=True, copy=False)
    feed_cost = fields.Monetary(compute='_compute_cost', store=True)
    note = fields.Char()

    @api.depends('qty_kg', 'product_id')
    def _compute_cost(self):
        for rec in self:
            rec.feed_cost = rec.qty_kg * rec.product_id.standard_price if rec.product_id else 0.0

    @api.constrains('qty_kg')
    def _check_qty(self):
        if any(r.qty_kg <= 0 for r in self):
            raise ValidationError(_('Jumlah pakan harus > 0.'))

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            rec._create_stock_move()
        return recs

    def _create_stock_move(self):
        self.ensure_one()
        if not self.product_id or not self.consume_stock or self.move_id:
            return
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        dest = self.product_id.with_company(self.company_id).property_stock_inventory
        move = self.env['stock.move'].create({
            'name': _('Pakan %s', self.batch_id.name),
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty_kg,
            'product_uom': self.product_id.uom_id.id,
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': dest.id,
            'company_id': self.company_id.id,
            'origin': self.batch_id.name,
        })
        move._action_confirm()
        move.quantity = self.qty_kg
        move.picked = True
        move._action_done()
        self.move_id = move


class AquaSampling(models.Model):
    _name = 'aqua.sampling'
    _description = 'Sampling Bobot'
    _order = 'date desc, id desc'

    batch_id = fields.Many2one('aqua.batch', required=True, ondelete='cascade')
    tank_id = fields.Many2one(related='batch_id.tank_id', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    sample_count = fields.Integer(string='Jumlah sampel (ekor)', required=True)
    total_weight_g = fields.Float(string='Total bobot sampel (g)', required=True)
    abw_g = fields.Float(string='ABW (g)', compute='_compute_abw', store=True)
    avg_length_cm = fields.Float()

    @api.depends('sample_count', 'total_weight_g')
    def _compute_abw(self):
        for rec in self:
            rec.abw_g = rec.total_weight_g / rec.sample_count if rec.sample_count else 0.0


class AquaMortality(models.Model):
    _name = 'aqua.mortality'
    _description = 'Kematian Harian'
    _order = 'date desc, id desc'

    batch_id = fields.Many2one('aqua.batch', required=True, ondelete='cascade')
    tank_id = fields.Many2one(related='batch_id.tank_id', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    qty = fields.Integer(string='Jumlah (ekor)', required=True)
    cause = fields.Selection([
        ('disease', 'Penyakit'), ('do', 'Stres oksigen'), ('temp', 'Stres suhu'),
        ('water', 'Kualitas air (amonia/nitrit)'), ('cannibal', 'Kanibal'),
        ('handling', 'Handling'), ('unknown', 'Tidak diketahui')], default='unknown')
    note = fields.Char()


class AquaWaterTest(models.Model):
    _name = 'aqua.water.test'
    _description = 'Uji Air Manual'
    _order = 'datetime desc'

    tank_id = fields.Many2one('aqua.tank', required=True, ondelete='cascade')
    datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    temp_c = fields.Float(string='Suhu (°C)')
    ph = fields.Float()
    tan_mgl = fields.Float(string='TAN (mg/L)')
    nh3_mgl = fields.Float(string='NH3 (mg/L)', compute='_compute_nh3', store=True, digits=(8, 4))
    no2_mgl = fields.Float(string='Nitrit (mg/L)')
    no3_mgl = fields.Float(string='Nitrat (mg/L)')
    alkalinity = fields.Float(string='Alkalinitas (mg/L CaCO3)')
    note = fields.Char()

    @api.depends('tan_mgl', 'ph', 'temp_c')
    def _compute_nh3(self):
        for rec in self:
            if rec.tan_mgl and rec.ph and rec.temp_c:
                pka = 0.09018 + 2729.92 / (rec.temp_c + 273.15)
                rec.nh3_mgl = rec.tan_mgl / (1 + 10 ** (pka - rec.ph))
            else:
                rec.nh3_mgl = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        Rule = self.env['aqua.alert.rule']
        for rec in recs:
            for param, val in (('nh3', rec.nh3_mgl), ('no2', rec.no2_mgl), ('no3', rec.no3_mgl)):
                if val:
                    Rule.evaluate_instant(rec.tank_id, param, val)
            if rec.ph:
                Rule.evaluate_instant(rec.tank_id, 'ph', rec.ph)
        return recs


class AquaHarvest(models.Model):
    _name = 'aqua.harvest'
    _description = 'Panen'
    _order = 'date desc, id desc'

    batch_id = fields.Many2one('aqua.batch', required=True, ondelete='cascade')
    tank_id = fields.Many2one(related='batch_id.tank_id', store=True)
    company_id = fields.Many2one(related='batch_id.company_id', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    partial = fields.Boolean(string='Panen parsial', default=True)
    qty = fields.Integer(string='Jumlah (ekor)', required=True)
    weight_kg = fields.Float(string='Berat total (kg)', required=True)
    abw_g = fields.Float(compute='_compute_abw', string='ABW panen (g)')
    product_id = fields.Many2one('product.product', string='Produk hasil panen')
    move_id = fields.Many2one('stock.move', readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Pembeli')

    @api.depends('qty', 'weight_kg')
    def _compute_abw(self):
        for rec in self:
            rec.abw_g = rec.weight_kg * 1000 / rec.qty if rec.qty else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            rec._create_stock_move()
        return recs

    def _create_stock_move(self):
        self.ensure_one()
        if not self.product_id or self.move_id:
            return
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        src = self.product_id.with_company(self.company_id).property_stock_production
        move = self.env['stock.move'].create({
            'name': _('Panen %s', self.batch_id.name),
            'product_id': self.product_id.id,
            'product_uom_qty': self.weight_kg,
            'product_uom': self.product_id.uom_id.id,
            'location_id': src.id,
            'location_dest_id': wh.lot_stock_id.id,
            'company_id': self.company_id.id,
            'origin': self.batch_id.name,
        })
        move._action_confirm()
        move.quantity = self.weight_kg
        move.picked = True
        move._action_done()
        self.move_id = move
