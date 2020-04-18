odoo.define('freeze_header.freeze', function (require) {
"use strict";

require('web.dom_ready');
var ListView = require('web.ListView');
var ListRenderer = require('web.ListRenderer');

ListRenderer.include({
    _renderView: function(){
        var self = this;
        return this._super.apply(this, arguments).done(function () {
            var form_field_length = self.viewType;
            var scrollArea = $(".o_content")[0];
            function do_freeze () {
                self.$el.find('table.o_list_view').each(function () {
                    $(this).stickyTableHeaders({scrollableArea: scrollArea, fixedOffset: 0.1, zIndex: 1});
                    $(this).closest('.table-responsive').scroll(function(){
                        $(this).trigger('resize.stickyTableHeaders');
                    });
                });

            }

            if (form_field_length == 'list') {
                do_freeze();
                $(window).unbind('resize', do_freeze).bind('resize', do_freeze);
            }
        });
    },
});

});