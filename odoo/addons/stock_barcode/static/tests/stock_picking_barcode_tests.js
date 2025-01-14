odoo.define('stock_barcode.stock_picking_barcode_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var FormView = require('web.FormView');

var createView = testUtils.createView;
var triggerKeypressEvent = testUtils.triggerKeypressEvent;

QUnit.module('stock_barcode', {}, function () {

QUnit.module('Barcode', {
    beforeEach: function () {
        this.data = {
            product: {
                fields: {
                    name: {string : "Product name", type: "char"},
                },
                records: [{
                    id: 1,
                    name: "iPad Mini",
                }, {
                    id: 4,
                    name: "Mouse, Optical",
                }],
            },
            'stock.move.line': {
                fields: {
                    product_id: {string: "Product", type: 'many2one', relation: 'product'},
                    product_qty: {string: "To Do", type: 'float', digits: [16,1]},
                    qty_done: {string: "Done", type: 'float', digits: [16,1]},
                    product_barcode: {string: "Product Barcode", type: 'char'},
                    lots_visible: {string: "Product tracked by lots", type: 'boolean'},
                },
                records: [{
                    id: 3,
                    product_id: 1,
                    product_qty: 2.0,
                    qty_done: 0.0,
                    product_barcode: "543982671252",
                }, {
                    id: 5,
                    product_id: 4,
                    product_qty: 2.0,
                    qty_done: 0.0,
                    product_barcode: "678582670967",
                }],
            },
            stock_picking: {
                fields: {
                    _barcode_scanned: {string: "Barcode Scanned", type: 'char'},
                    move_line_ids: {
                        string: "one2many field",
                        relation: 'stock.move.line',
                        type: 'one2many',
                    },
                },
                records: [{
                    id: 2,
                    move_line_ids: [3],
                }, {
                    id: 5,
                    move_line_ids: [5],
                }],
            },
        };
    }
});

QUnit.test('scan a product (no tracking)', function (assert) {
    assert.expect(5);

    var form = createView({
        View: FormView,
        model: 'stock_picking',
        data: this.data,
        arch: '<form string="Products">' +
                '<field name="_barcode_scanned" widget="picking_barcode_handler"/>' +
                '<sheet>' +
                    '<notebook>' +
                        '<page string="Operations">' +
                            '<field name="move_line_ids">' +
                                '<tree>' +
                                    '<field name="product_id"/>' +
                                    '<field name="product_qty"/>' +
                                    '<field name="qty_done"/>' +
                                    '<field name="product_barcode"/>' +
                                    '<field name="lots_visible" invisible="1"/>' +
                                '</tree>' +
                            '</field>' +
                        '</page>' +
                    '</notebook>' +
                '</sheet>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            assert.step(args.method);
            return this._super.apply(this, arguments);
        },
        viewOptions: {
            mode: 'edit',
        },
    });

    assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(2)').text(), '0.0',
        "quantity done should be 0");

    _.each(['5','4','3','9','8','2','6','7','1','2','5','2','Enter'], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(2)').text(), '1.0',
        "quantity done should be 1");
    assert.verifySteps(['read', 'read'], "no RPC should have been done for the barcode scanned");

    form.destroy();
});

QUnit.test('scan a product tracked by lot', function (assert) {
    assert.expect(8);

    // simulate a PO for a tracked by lot product
    this.data['stock.move.line'].records[0].lots_visible = true;

    var form = createView({
        View: FormView,
        model: 'stock_picking',
        data: this.data,
        arch: '<form string="Products">' +
                '<field name="_barcode_scanned" widget="picking_barcode_handler"/>' +
                '<sheet>' +
                    '<notebook>' +
                        '<page string="Operations">' +
                            '<field name="display_name"/>' +
                            '<field name="move_line_ids">' +
                                '<tree>' +
                                    '<field name="product_id"/>' +
                                    '<field name="product_qty"/>' +
                                    '<field name="qty_done"/>' +
                                    '<field name="product_barcode"/>' +
                                    '<field name="lots_visible" invisible="1"/>' +
                                '</tree>' +
                            '</field>' +
                        '</page>' +
                    '</notebook>' +
                '</sheet>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            assert.step(args.method);
            if (args.method === 'get_po_to_split_from_barcode') {
                return $.when({action_id: 1});
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            do_action: function (event) {
                assert.deepEqual(event.data.action, {action_id: 1}, "should trigger a do_action");
            },
        },
        viewOptions: {
            mode: 'edit',
        },
    });

    assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(2)').text(), '0.0',
        "quantity done should be 0");

    // trigger a change on a field to be able to check that the record is correctly
    // saved before calling get_po_to_split_from_barcode
    form.$('.o_field_widget[name="display_name"]').val('new value').trigger('input');
    _.each(['5','4','3','9','8','2','6','7','1','2','5','2','Enter'], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(2)').text(), '0.0',
        "quantity done should still be 0");
    assert.verifySteps(['read', 'read', 'write', 'get_po_to_split_from_barcode'],
        "get_po_to_split_from_barcode method call verified");

    form.destroy();
});

});
});
