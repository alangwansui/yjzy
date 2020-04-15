odoo.define('web_widget_colored_field', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var basic_fields = require('web.basic_fields');
    var relational_fields = require('web.relational_fields');

    var FieldChar = basic_fields.FieldChar;
    var FieldFloat = basic_fields.FieldFloat;
    var FieldInteger = basic_fields.FieldInteger;
    var FieldSelection = relational_fields.FieldSelection;
    var FieldMany2One = relational_fields.FieldMany2One;


    AbstractField.include({
        _getColorNode: function (record, options) {
            var fieldColor = options.color;
            var fieldTitle = options.title;
            var fieldExpr = options.expr;

             var fd = options.fd;
             var op = options.op;
             var v = options.v;















            //var expr = py.parse(py.tokenize(fieldExpr));
            //console.info('>>1>>',fieldExpr)
            //console.info('>>2>>',  py.evaluate(fieldExpr));

            //var res = true; //py.PY_isTrue(py.evaluate(expr, record.evalContext));

            var eval_str = "record.data['" + fd +  "']" + op    + "'"  +  v + "'"
            var res  = eval(eval_str);


            console.info('>>>>>>>ww>>', res,  eval_str);
            if (res) {
                // Make sure that multiple whitespace don't be escape
                var $color = $('<pre/>', {
                    css: {
                        "color": fieldColor,
                        "padding": "inherit",
                        "background": "none",
                        "border": "none",
                        "border-radius": "unset",
                        "font-size": "inherit",
                        "margin": 0
                    },
                    html: this._formatValue(this.value)
                });
                if (fieldTitle) {
                    return $color.tooltip({html: true}).attr('data-original-title', '<p>' + fieldTitle + '</p>');
                }
                return $color;
            } else {
                return false;
            }
        }
    });

    FieldChar.include({
        _renderReadonly: function () {
            var options = this.nodeOptions;
            if (this.value && 'color' in options) {
                var $colorNode = this._getColorNode(this.record, options);
                if ($colorNode) {
                    this.$el.html($colorNode)
                } else {
                    this._super()
                }
            } else {
                this._super()
            }
        }
    });

    FieldFloat.include({
        _renderReadonly: function () {
            var options = this.nodeOptions;
            if (this.value && 'color' in options) {
                var $colorNode = this._getColorNode(this.record, options);
                if ($colorNode) {
                    this.$el.html($colorNode)
                } else {
                    this._super()
                }
            } else {
                this._super()
            }
        }
    });

    FieldInteger.include({
        _renderReadonly: function () {
            var options = this.nodeOptions;
            if (this.value && 'color' in options) {
                var $colorNode = this._getColorNode(this.record, options);
                if ($colorNode) {
                    this.$el.html($colorNode)
                } else {
                    this._super()
                }
            } else {
                this._super()
            }
        }
    });

    FieldSelection.include({
        _renderReadonly: function () {
            var options = this.nodeOptions;
            if (this.value && 'color' in options) {
                var $colorNode = this._getColorNode(this.record, options);
                if ($colorNode) {
                    this.$el.html($colorNode)
                } else {
                    this._super()
                }
            } else {
                this._super()
            }
        }
    });

    FieldMany2One.include({
        _renderReadonly: function () {
            var options = this.nodeOptions;
            if (this.value && 'color' in options) {
                var $colorNode = this._getColorNode(this.record, options);
                if ($colorNode) {
                    this.$el.html($colorNode)
                } else {
                    this._super()
                }
            } else {
                this._super()
            }
        }
    });


});