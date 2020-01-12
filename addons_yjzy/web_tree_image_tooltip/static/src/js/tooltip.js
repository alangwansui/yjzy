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
            var rowIndex = event.fromElement.parentNode.rowIndex;
            if(rowIndex){
                var line_data = this.state.data[rowIndex];
                if (line_data){

                    var body_text = line_data.data.body_text;

                    console.info('===');

                    $(event.currentTarget).tooltip({
                        title: body_text,
                        delay: 1,
                        template: '<div class="tooltip"  role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>'
                    }).tooltip('show');

                }


            }








        }
    });
})
