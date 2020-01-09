odoo.define('web_tree_image_tooltip.web_tree_image_tooltip',
        function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    ListRenderer.include({
        events: _.extend({}, ListRenderer.prototype.events, {
            'mouseover tbody tr td .tip_button': '_onHoverRecord_img',
        }),
        _onHoverRecord_img: function (event) {
            // var img_src =
            //     $(event.currentTarget).children('.img-fluid').attr('src')

            console.info('>>>>', event.currentTarget, event);

            //如何查询消息下简单信息

            $(event.currentTarget).tooltip({
                title: "<h1>xxxx</h1>",
                delay: 3,
            }).tooltip('show');
        }
    });
})
