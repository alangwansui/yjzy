odoo.define('web_studio.KanbanRecordEditor', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var KanbanRecord = require('web.KanbanRecord');
var EditorMixin = require('web_studio.EditorMixin');

var _t = core._t;

var KanbanRecordEditor = KanbanRecord.extend(EditorMixin, {
    nearest_hook_tolerance: 50,
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} options
     * @param {Boolean} is_dashboard
     */
    init: function (parent, state, options, is_dashboard) {
        this._super.apply(this, arguments);
        this.node_id = 1;
        this.hook_nodes = [];
        this.is_dashboard = is_dashboard;
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        this._super.apply(this, arguments);

        // prevent the click on the record and remove the corresponding style
        this.$el.removeClass('oe_kanban_global_click oe_kanban_global_click_edit');

        // prevent the color dropdown to be displayed
        this.$('.o_dropdown_kanban > a')
            .removeAttr('data-toggle')
            .click(function (event) {
                event.preventDefault();
            });

        this.$el.droppable({
            accept: ".o_web_studio_component",
            drop: function (event, ui) {
                var $hook = self.$('.o_web_studio_nearest_hook');
                if ($hook.length) {
                    var hook_id = $hook.data('hook_id');
                    var hook = self.hook_nodes[hook_id];

                    var values = {
                        type: 'add',
                        structure: ui.draggable.data('structure'),
                        field_description: ui.draggable.data('field_description'),
                        node: hook.node,
                        new_attrs: _.defaults(ui.draggable.data('new_attrs'), {
                            display: 'full',
                        }),
                        position: hook.position,
                    };
                    ui.helper.removeClass('ui-draggable-helper-ready');
                    self.trigger_up('on_hook_selected');
                    self.trigger_up('view_change', values);
                }
            },
        });
    },
    /**
     * @override
     */
    start: function () {
        this.undelegateEvents();
        this.$el.click(function (e) {
            e.stopPropagation();
            e.preventDefault();
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    highlightNearestHook: function ($helper, position) {
        EditorMixin.highlightNearestHook.apply(this, arguments);

        var $nearest_form_hook = this.$('.o_web_studio_hook')
            .touching({
                x: position.pageX - this.nearest_hook_tolerance,
                y: position.pageY - this.nearest_hook_tolerance,
                w: this.nearest_hook_tolerance*2,
                h: this.nearest_hook_tolerance*2})
            .nearest({x: position.pageX, y: position.pageY}).eq(0);
        if ($nearest_form_hook.length) {
            $nearest_form_hook.addClass('o_web_studio_nearest_hook');
            return true;
        }
        return false;
    },
    /**
     * @override
     */
    setLocalState: function (state) {
        if (state.selected_node_id) {
            var $selected_node = this.$('[data-node-id="' + state.selected_node_id + '"]');
            if ($selected_node) {
                $selected_node.click();
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _addSpecialHooks: function () {
        var self = this;

        // add the tags hook
        if (!this.$('.o_kanban_tags').length) {
            var $kanban_tags_hook = $('<span>')
                .addClass('o_web_studio_add_kanban_tags')
                .append($('<span>', {
                    text: _t('Add tags'),
                }));
            $kanban_tags_hook.prependTo(this.$el);
            $kanban_tags_hook.click(function () {
                var compatible_fields = _.pick(self.state.fields, function (e) {
                    return e.type === 'many2many';
                });
                if (_.isEmpty(compatible_fields)) {
                    Dialog.alert(self, _t('You first need to create a many2many field in the form view.'));
                    return;
                }
                var dialog = new NewKanbanHelperDialog(self, compatible_fields, false);
                dialog.open();
                dialog.on('confirm', self, function (field_name) {
                    self.trigger_up('view_change', {
                        type: 'add',
                        structure: 'field',
                        new_attrs: { name: field_name },
                        node: {
                            tag: 'div/*[1]',
                        },
                        position: 'before',
                    });
                });
            });
        }

        // add the dropdown hook
        var $dropdown = this.$('.o_dropdown_kanban');
        if ($dropdown.length) {
            $dropdown.attr('data-node-id', this.node_id++);
            // bind handler on dropdown clicked to be able to remove it
            var node = {
                tag: 'div',
                attrs: {class: 'o_dropdown_kanban'},
            };
            this.setSelectable($dropdown);
            $dropdown.click(function () {
                self.selected_node_id = $dropdown.data('node-id');
                self.trigger_up('node_clicked', {node: node});
            });
        } else {
            var $top_left_hook = $('<div>')
                .addClass('o_web_studio_add_dropdown o_dropdown_kanban dropdown')
                .append($('<a>', {
                    class: 'dropdown-toggle btn',
                    'data-toggle': 'dropdown',
                    href: '#',
                }).append($('<span>', {
                    class: 'fa fa-bars fa-lg',
                })));
            $top_left_hook.prependTo(this.$el);
            $top_left_hook.click(function () {
                Dialog.confirm(self, _t("Do you want to add a dropdown with colors?"), {
                    size: 'small',
                    confirm_callback: function () {
                        self.trigger_up('view_change', {
                            structure: 'kanban_dropdown',
                        });
                    },
                });
            });
        }

        // add the priority hook
        if (!this.$('.o_priority').length) {
            var $priority_hook = $('<div>')
                .addClass('o_web_studio_add_priority oe_kanban_bottom_left')
                .append($('<span>', {
                    text: _t('Add a priority'),
                }));
            $priority_hook.appendTo(this.$el);
            $priority_hook.click(function () {
                var compatible_fields = _.pick(self.state.fields, function (e) {
                    return e.type === 'selection';
                });
                var dialog = new NewKanbanHelperDialog(self, compatible_fields, true).open();
                dialog.on('confirm', self, function (field) {
                    self.trigger_up('view_change', {
                        structure: 'kanban_priority',
                        field: field,
                    });
                });
            });
        }

        // add the image hook
        if (!this.$('.oe_kanban_bottom_right').length) {
            var $kanban_image_hook = $('<div>')
                .addClass('o_web_studio_add_kanban_image oe_kanban_bottom_right')
                .append($('<span>', {
                    text: _t('Add an image'),
                }));
            $kanban_image_hook.appendTo(this.$el);
            $kanban_image_hook.click(function () {
                var compatible_fields = _.pick(self.state.fields, function (e) {
                    return e.type === 'many2one' && (e.relation === 'res.partner' || e.relation === 'res.users');
                });
                if (_.isEmpty(compatible_fields)) {
                    Dialog.alert(self, _t('You first need to create a many2one field to Partner or User in the form view.'));
                    return;
                }
                var dialog = new NewKanbanHelperDialog(self, compatible_fields, false).open();
                dialog.on('confirm', self, function (field) {
                    self.trigger_up('view_change', {
                        structure: 'kanban_image',
                        field: field,
                    });
                });
            });
        }
    },
    /**
     * @private
     * @param {any} value
     * @returns {Boolean}
     */
    _isEmpty: function (value) {
        if (typeof(value) === 'object') {
            return _.isEmpty(value);
        } else {
            return !value && value !== 0;
        }
    },
    /**
     * @override
     */
    _processFields: function () {
        this._super.apply(this, arguments);

        // the layout of the special hooks are broken in the kanban dashboards
        if (!this.is_dashboard) {
            this._addSpecialHooks();
        }
    },
    /**
     * @override
     */
    _processField: function ($field, field_name) {
        var self = this;
        $field = this._super.apply(this, arguments);

        var field = this.record[field_name];
        // make empty widgets appear
        if (this._isEmpty(field.value)) {
            $field.text(field.string);
            $field.addClass('o_web_studio_widget_empty');
        }
        $field.attr('data-node-id', this.node_id++);

        // bind handler on field clicked to edit field's attributes
        var node = {
            tag: 'field',
            attrs: {name: field_name}
        };
        this.setSelectable($field);
        $field.click(function (event) {
            event.preventDefault();
            event.stopPropagation();
            self.selected_node_id = $field.data('node-id');
            self.trigger_up('node_clicked', {node: node});
        });

        // insert a hook to add new fields
        var $hook = this._renderHook(node);
        $hook.insertAfter($field);

        return $field;
    },
    /**
     * @override
     */
    _processWidget: function ($field, field_name) {
        var self = this;
        var widget = this._super.apply(this, arguments);
        widget.undelegateEvents();

        // make empty widgets appear
        if (this._isEmpty(widget.value)) {
            widget.$el.addClass('o_web_studio_widget_empty');
            widget.$el.text(widget.string);
        }
        widget.$el.attr('data-node-id', this.node_id++);

        // bind handler on field clicked to edit field's attributes
        var node = {
            tag: 'field',
            attrs: {name: field_name}
        };
        this.setSelectable(widget.$el);
        widget.$el.click(function (event) {
            event.preventDefault();
            event.stopPropagation();
            self.selected_node_id = widget.$el.data('node-id');
            self.trigger_up('node_clicked', {node: node});
        });

        // insert a hook to add new fields
        var $hook = this._renderHook(node);
        $hook.insertAfter(widget.$el);

        return widget;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {JQuery}
     */
    _renderHook: function (node) {
        var hook_id = _.uniqueId();
        this.hook_nodes[hook_id] = {
            node: node,
            position: 'after',
        };
        var $hook = $('<span>', {
            class: 'o_web_studio_hook',
            data: {
                hook_id: hook_id,
            }
        });
        return $hook;
    },
});

var NewKanbanHelperDialog = Dialog.extend({
    template: 'web_studio.NewKanbanHelperDialog',
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} fields
     * @param {Boolean} show_new
     */
    init: function (parent, fields, show_new) {

        this.fields = fields;
        this.orderered_fields = _.sortBy(this.fields, 'string');

        this.show_new = show_new;
        this.debug = core.debug;

        var options = {
            title: _t('Select a Field'),
            buttons: [{
                text: _t("Confirm"),
                classes: 'btn-primary',
                click: this._onConfirm.bind(this)
            }, {
                text: _t("Cancel"), close: true
            }],
        };
        this._super(parent, options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @
     * @returns {[type]} [description]
     */
    _onConfirm: function () {
        var selected_field = this.$('select[name="field"]').val();
        this.trigger('confirm', selected_field);
    },
});

return KanbanRecordEditor;

});
