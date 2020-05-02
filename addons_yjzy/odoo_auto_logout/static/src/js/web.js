odoo.define('odoo_auto_logout', function(require) {
    "use strict";

    var rpc = require('web.rpc');
    var session = require('web.session');

    rpc.query({
        model: 'res.company',
        method: 'read',
        args: [[session.company_id],['logout_time']],
    }).then(function(result) {
        if (result) {
            // console.log("Tsting result>>>>>>>>>>>",session.company_id);
            var timeout = setTimeout(function() {
                    window.location.href = "/web/session/logout?redirect=/"; 
                }, result[0]['logout_time'] *1000);
            $(document).on('mousemove', function() {
                if (timeout !== null) {
                    clearTimeout(timeout);
                }
                timeout = setTimeout(function() {
                    window.location.href = "/web/session/logout?redirect=/"; 
                }, result[0]['logout_time'] *1000);
            });
        }
    });
});
