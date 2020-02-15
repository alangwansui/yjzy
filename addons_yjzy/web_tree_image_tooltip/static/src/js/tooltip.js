odoo.define('web_tree_image_tooltip.web_tree_image_tooltip',
        function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');


    var screenX = 0;
    var screenY = 0;


    ListRenderer.include({
        events: _.extend({}, ListRenderer.prototype.events, {
            'mouseover tbody tr td .tip_button': '_onHoverRecord_img',


        }),

        _onHoverRecord_img: function (event) {
            //console.info('===xxyy==', event.screenX, screenX, event.screenY, screenY);

            if (event.screenX != screenX || event.screenY != screenY){
            var rowIndex = event.fromElement.parentNode.rowIndex - 1;
            //console.info('===tooltipp==', rowIndex, event);
            if(typeof rowIndex === 'number' && !isNaN(rowIndex)){
                var line_data = this.state.data[rowIndex];
                if (line_data){
                    var body = line_data.data.body;
                    console.info('===', body, line_data);
                    var tip = $(event.currentTarget).tooltip({
                        html: true,
                        title: body,
                        delay: 20,
                        template: '<div class="tooltip" style="background:#CCC;border:4px solid #333 !important; width: 500px !important;height: 250px !important;display: -webkit-box;-webkit-box-orient: vertical;-webkit-line-clamp: 7; overflow: hidden;"  role="tooltip"><div class="tooltip-arrow"></div><div    class="tooltip-inner"></div></div>'
                    }).tooltip('show');
                    //console.info('==tooltip ok=');
                }
            }

            screenX = event.screenX;
            screenY = event.screenY;


            }








        }
    });
})
