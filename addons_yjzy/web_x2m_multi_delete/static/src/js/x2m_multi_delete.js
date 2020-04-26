odoo.define('web_x2m_multi_delete.ListRenderer', function(require) {
    "use strict";
    
    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    var Dialog = require('web.Dialog');
    var Qweb = core.qweb;
    var _t = core._t;

    ListRenderer.include({
        events: _.extend({}, ListRenderer.prototype.events, {
            'click tr th.o_list_x2m_remove': '_onRemoveSelectedRecords',
        }),
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.hasSelectors = params.hasSelectors || this.addTrashIcon;
        },
        _renderHeader: function (isGrouped) {
            var $tbody = this._super.apply(this, arguments);
            if (this.addTrashIcon && this.state.data.length) {
                var $icon = $('<button>', {class: 'fa fa-trash-o o_list_record_delete_btn', name: 'delete',
                    'aria-label': _t('Delete selected rows ')});
                var $th = $('<th>', {class: 'o_list_x2m_remove'}).append($icon);
                $tbody.find('tr').append($th);
            }
            return $tbody;
        },
        _onRemoveSelectedRecords: function(event) {
            var self = this;
            event.stopPropagation();
            var $selectedRows = this.$('tbody .o_list_record_selector input:checked').closest('tr');
            if(self.state.data.length){
                if(!$selectedRows.length){
                    self.do_warn(_t("Please select at least one record."));
                    return;
                }
                Dialog.confirm(this, (_t("Do you really want to remove these records?")), {
                    confirm_callback: function () {
                        _.each(_.map($selectedRows, function (row) {
                            return $(row).data('id');
                        }), function(resID){
                            self.unselectRow().then(function () {
                                self.trigger_up('list_record_delete', {id: resID});
                            })
                        })
                    },
                });
            }
        },
    });
});