odoo.define('web_listview_multiselect.ListRenderer', function (require) {
    "use strict";
    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        events: _.extend({}, ListRenderer.prototype.events, {
            'click tbody .o_list_record_selector input': '_onSelectCheckbox',
        }),
        _onSelectCheckbox: function (event) {
            var $chkboxes = this.$('tbody .o_list_record_selector input');
            if(!this.lastChecked) {
                this.lastChecked = event.target;
                return;
            }

            if(event.shiftKey) {
                var start = $chkboxes.index(event.target);
                var end = $chkboxes.index(this.lastChecked);
                $chkboxes.slice(Math.min(start,end), Math.max(start,end)+ 1).prop('checked', this.lastChecked.checked);
            }

            this.lastChecked = event.target;
        },
    });
});