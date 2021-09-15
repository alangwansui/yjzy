# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class Product_Product(models.Model):
    _inherit = 'product.product'

    def _default_packaging(self):
        res = []
        type_obj = self.env['packaging.type']
        min_type = type_obj.search([('min_default','=', True)], limit=True)
        max_type = type_obj.search([('max_default', '=', True)], limit=True)
        if min_type:
            res.append((0, 0, {
                'name': min_type.name,
                'qty': 1,
                'type_id': min_type.id,
                'size': min_type.size,

            }))
        if max_type:
            res.append((0, 0, {
                'name': max_type.name,
                'qty': 1,
                'type_id': max_type.id,
                'size': max_type.size,
            }))
        return res or None

    @api.depends('customer_id')
    def compute_jituan(self):
        for one in self:
            jituan = one.customer_id.jituan_id
            if jituan.is_product_share_group:
                one.jituan_id = jituan
            else:
                one.jituan_id = False
    @api.depends('so_line_ids')
    def compute_so_line_count(self):
        for one in self:
            one.so_line_count = len(one.so_line_ids)

    # @api.depends('so_line_ids')
    # def compute_tb_line_count(self):
    #     for one in self:
    #         one.so_line_count = len(one.so_line_ids)

    # tb_line_ids = fields.One2many('transport.bill_line','product_id', u'销售明细', domain=[('state','in',['approve','sale','done','abnormal','verifying','verification'])],)
    so_line_ids = fields.One2many('sale.order.line','product_id', u'销售明细', domain=[('state','in',['approve','sale','done','abnormal','verifying','verification'])],)
    so_line_count = fields.Integer('销售明细数量', compute=compute_so_line_count)
    # tb_line_count = fields.Integer('发货明细数量', compute=compute_tb_line_count)

    for_extra = fields.Boolean('可用于额外账单')
    for_other_po = fields.Boolean('可用于增加采购')

    jituan_id = fields.Many2one('ji.tuan','集团',compute=compute_jituan,store=True)

    en_name = fields.Char(u'英文名')
    hs_id = fields.Many2one('hs.hs', string='HS品名')
    back_tax = fields.Float(related='hs_id.back_tax', readonly=True)
    hs_en_name = fields.Char(related='hs_id.en_name', readonly=True)

    trademark = fields.Char(u'商标')
    lst_price = fields.Float(u'销售价格')
    bom_ids = fields.One2many('mrp.bom', 'product_id', u'BOM')
    mark_ids = fields.Many2many('transport.mark', 'ref_mark_product', 'pid', 'mid', u'唛头')
    tmpl_code = fields.Char(related='product_tmpl_id.tmpl_code')
    seq = fields.Char(u'规格流水号', readonly=False,  copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('product.product'))
    customer_id = fields.Many2one('res.partner', u'客户', domain=[('customer', '=', True)])
    customer_ref = fields.Char(u'客户型号')
    customer_ref2 = fields.Char(u'客户型号2')
    customer_description = fields.Text(u'客户产品描述', translate=False)
    other_description = fields.Text(u'其他描述')
    source_area = fields.Char(u'原产地') #13已经
    source_country_id = fields.Many2one('res.country', u'原产国') #13ok

    value_line_ids = fields.One2many('product.value.rel', 'product_product_id', u'产品属性明细')
    key_value_line_ids = fields.One2many('product.value.rel', compute='compute_key_value_line', string='关键属性')
    key_value_string = fields.Char(string='关键属性', compute='compute_key_value_line')

    pdt_image_ids = fields.One2many('product.image', 'product_id', string='图片')
    price_section_ids = fields.One2many('product.price.section', 'product_id', u'价格区间')

    default_code = fields.Char(u'内部编码', compute='compute_default_code', store=True, copy=False)

    s_uom_id = fields.Many2one('product.uom', u'销售打印单位')
    p_uom_id = fields.Many2one('product.uom', u'采购打印单位')

    function = fields.Text(u'功能描述', translate=False)
    meterial = fields.Text(u'主要材料', translate=False)
    purchase_discription = fields.Html(u'采购说明')

    packag_method = fields.Char(u'包装方式', translate=False)
    surface_treatment = fields.Char(u'表面处理', translate=False)

    packaging_ids = fields.One2many(
        'product.packaging', 'product_id', 'Product Packages', default=lambda self: self._default_packaging(), copy=True)

    customer_barcode = fields.Char(u'客户条码')
    pi_function = fields.Text(u'PI FUNCTION')
    pi_material = fields.Text(u'PI Materail')
    pi_package = fields.Char(u'PI Package')
    pi_surface = fields.Char(u'PI Surface')
    pi_description = fields.Text('PI_Description')
    pi_specification = fields.Text('PI_Specification')

    state = fields.Selection([('draft', u'草稿'),('submit',u'待业务责任人审批'),('first', '待产品合规审批'),('done', u'完成')], u'状态', default='draft')

    is_gold_sample = fields.Boolean('是否有金样')
    is_ps = fields.Boolean('是否有PS')




    def action_submit(self):
        if self.customer_id.user_id == self.env.user or self.customer_id.assistant_id == self.env.user:
            self.state = 'submit'
        else:
            raise Warning(u'您没有该产品的权限')


    def action_first(self):
        if self.customer_id.user_id == self.env.user:
            self.state = 'first'
        else:
            raise Warning(u'您不是该产品的责任人')
    def action_done(self):
            self.state = 'done'


    @api.depends('seq', 'categ_id')
    def compute_default_code(self):
        for one in self:
            one.default_code = '%s%s' % (one.categ_id.complete_code, one.seq)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        print('==name_search==',  self.env.context)
        res = super(Product_Product, self).name_search(name=name, args=args, operator=operator, limit=limit)
        #print('===', res)
        res_ids = [x[0] for x in res]
        products = self.search(['|', ('customer_ref',operator, name),('customer_ref2',operator, name)] + args, limit=limit)
        result = products.name_get()
        for r in result:
            if not (r[0] in res_ids):
                res.append(r)
        return res

    @api.multi
    def name_get(self):
        #多选：显示名称=（如果有客户编号显示客户编码，否则显示内部编码）+商品名称+关键属性，关键属性，供应商型号
        result = []
        only_name = self.env.context.get('only_name')
        only_code = self.env.context.get('only_code')
        def _get_name(one):
            ref = one.customer_ref and one.customer_ref or '无'
            variant_seller_ids = len(one.variant_seller_ids) >1 and one.variant_seller_ids[0] or  one.variant_seller_ids
            default_code = one.default_code
            can_be_expensed = one.can_be_expensed
            if variant_seller_ids:
                product_supplier_ref = variant_seller_ids.product_name
            else:
                product_supplier_ref = '无'
            if only_name:
                name = one.name
            elif only_code:
                name = one.default_code
            elif can_be_expensed:
                name = one.name
            elif ref and product_supplier_ref:
                name = '%s/%s/%s' % (ref,product_supplier_ref,default_code)
            else:
                name = '[%s]%s' % (one.default_code, one.name)
            return name
        for one in self:
            result.append((one.id, _get_name(one) ))
        return result


    #13no
    @api.depends('value_line_ids')
    def compute_key_value_line(self):
        for one in self:
            one.key_value_line_ids = one.value_line_ids.filtered(lambda x: x.is_key)
            key_values = one.key_value_line_ids.mapped('product_attribute_value_id')
            one.key_value_string = ','.join([x[1] for x in  key_values.name_get()])

    #13no
    def open_wizard_product_copy(self):
        wizard = self.env['wizard.product.copy'].create({'product_id': self.id})
        return {
            'name': u'复制产品',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.product.copy',
            'res_id': wizard.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
    #13yes
    def get_in_stock_quant(self):
        self.ensure_one()
        quants = self.env['stock.quant'].search([('product_id', '=', self.id), ('location_id.usage', '=', 'internal')])
        return {
            'name': u'库存批次',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.quant',
            'target': 'new',
            'domain': [('id', 'in', [x.id for x in quants])],
            'type': 'ir.actions.act_window',
        }
    #13no
    @api.multi
    def copy(self, default=None):

        _logger.info('====copy1 start')

        default = default or {}
        default['product_tmpl_id'] = self.product_tmpl_id.id
        pdt = super(Product_Product, self).copy(default=default)
        #pdt.onchange_category()

        _logger.info('====copy1 end')
        return pdt
    #13no
    @api.model
    def create(self, vales):
        pdt = super(Product_Product, self).create(vales)
        pdt.auto_rush_value_line()
        return pdt

    #def open_product(self):
    #   self.ensure_one()
    #    return {
    #        'name': u'成本单',
    #        'view_type': 'form',
    #       "view_mode": 'tree,form',
    #      'res_model': 'product.product',
    #      'type': 'ir.actions.act_window',
    #   }
    #13no
    def auto_rush_value_line(self):
        self.ensure_one()
        for line in self.value_line_ids:
            if line.product_attribute_value_id and not line.attribute_id:
                line.attribute_id = line.product_attribute_value_id.attribute_id


    @api.onchange('categ_id')
    def onchange_category(self):
        #print('====onchange product.product cateogry ==========')
        #self.hs_id = self.categ_id.hs_id
        self.default_code = '%s%s' % (self.categ_id.complete_code, self.seq)
    #13no 这里也没看到哪里有用到
    def wizard_product_lst_price(self):
        return {
            'name': u'属性设置向导',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.product.lst.price',
            # 'res_id': wizard.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
    #13no
    def open_wizard_attribute_configurator(self):
        wizard = self.env['wizard.attribute.configurator'].create({
            'product_id': self.id,
        })
        line_obj = self.env['wizard.attribute.configurator.line']

        #1：添加现有的值
        for v in self.attribute_value_ids:
            line_obj.create({
                'wizard_id': wizard.id,
                'attribute_id': v.attribute_id.id,
                'value_id': v.id,
            })
        #2：添加模板中的配置,的属性，剩余属性=模板配置属性 - 存在值的属性
        for remaind_attr in (self.attribute_line_ids.mapped('attribute_id') - self.attribute_value_ids.mapped('attribute_id')):
            line_obj.create({
                'wizard_id': wizard.id,
                'attribute_id': remaind_attr.id,
            })

        return {
            'name': u'属性设置向导',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.attribute.configurator',
            'res_id': wizard.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    #产品分类设置bom模板，可以直接创建引用。13no
    def open_bom_template(self):
        self.ensure_one()
        bom_template = self.categ_id.bom_template_id
        if not bom_template:
            raise Warning(u'请先在产品的分类上设置bom模板')

        wizard = self.env['wizard.bom.template'].with_context(bom_template=bom_template).create({
            'product_id': self.id,
        })
        return {
            'name': u'创建BOM',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.bom.template',
            'res_id': wizard.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


    def get_package_info(self, qty):
        """根据数量计算大包，中包，小包  净重，毛重，体积 数量"""

        def compute_gross_weight():
            res = 0
            return res

        self.ensure_one()
        max_qty =  mid_qty = min_qty = 0
        qty = int(qty)
        pdt = self

        max_package = pdt.packaging_ids.filtered(lambda x: x.size == 1)
        mid_package = pdt.packaging_ids.filtered(lambda x: x.size == 2)
        min_package = pdt.packaging_ids.filtered(lambda x: x.size == 3)

        if len(max_package) > 1  or  len(min_package) >1:
            raise Warning(u'产品 %s 大小包装重复定义' % pdt.name)


        max_package_qty = int(max_package.qty)
        mid_package_qty = int(mid_package.qty)
        min_package_qty = int(min_package.qty)

        if not max_package:
            raise Warning(u'产品 [%s]%s 找不到大包装设置，请检查产品上的包装配置' % (pdt.default_code, pdt.name))
        if not min_package:
            raise Warning(u'产品 [%s]%s 找不到小包装设置，请检查产品上的包装配置' % (pdt.default_code, pdt.name))

        # 大包
        #max_qty = math.ceil(qty / max_package_qty)   #qty % max_package_qty and (qty / max_package_qty + 1) or (qty / max_package_qty)
        max_qty = qty / max_package_qty
        max_qty2 = qty / max_package_qty
        max_qty_ng = qty % max_package_qty and True or False



        if mid_package:
            mid_qty = qty % mid_package_qty and (qty / mid_package_qty + 1) or (qty / mid_package_qty)
        min_qty = qty % min_package_qty and (qty / min_package_qty + 1) or (qty / min_package.qty)

        net_weight = max_package.net_weight * max_qty  ##出运的时候净重的公式做成：大包装的净重*大包装数量
        gross_weight = (max_qty * max_package.weight4product) ###中小包装不参与计算 + ( mid_qty * mid_package.weight4product) + (min_qty * min_package.weight4product)

        volume = max_qty * max_package.volume / 1000000

        return  {
            'max_package': max_package_qty,
            'mid_package': mid_package_qty,
            'min_package': min_package_qty,
            'max_qty': max_qty, #int(round(max_qty)),
            'mid_qty': mid_qty, #int(round(mid_qty)),
            'min_qty': min_qty, #int(round(min_qty)),
            'net_weight': net_weight,
            'gross_weight': gross_weight,
            'volume': volume,
            'min_record': min_package,
            'mid_record': mid_package,
            'max_record': max_package,
            'max_qty_ng': max_qty_ng,
            'max_qty2': max_qty2,
        }
    #13no
    def update_attribute_by_value(self):
        self.ensure_one()
        self.value_line_ids.update_attribute_by_value()

    #13no
    @api.model
    def cron_sync_sp_uom(self, overwrite=True):
        for p in self.search([]):
            if overwrite:
                p.s_uom_id = p.uom_id
                p.p_uom_id = p.uom_po_id
            else:
                if not p.s_uom_id:
                    p.s_uom_id = p.uom_id
                if not p.p_uom_id:
                    p.p_uom_id = p.uom_po_id






