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



            var rowIndex = event.fromElement.parentNode.rowIndex - 1;



            console.info('===tooltipp==', rowIndex)


            if(typeof rowIndex === 'number' && !isNaN(rowIndex)){
                var line_data = this.state.data[rowIndex];
                if (line_data){
                    var body = line_data.data.body;
                    console.info('===', body, line_data);
                    $(event.currentTarget).tooltip({
                        html: true,
                        title: body,
                        delay: 1,
                        template: '<div class="tooltip"  role="tooltip"><div class="tooltip-arrow"></div><div  style="max-width: 200px !important;max-height: 200px !important"  class="tooltip-inner"></div></div>'
                    }).tooltip('show');

                    console.info('==tooltip ok=');

                }


            }








        }
    });
})
