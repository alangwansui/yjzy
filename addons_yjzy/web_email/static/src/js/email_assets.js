odoo.define('web_email.web_email1', function (require) {
"use strict";
    var core = require('web.core');
    core.form_widget_registry.get('email').include({
        render_value: function() {
            if (!this.get("effective_readonly")) {
                this._super();
            }else{
                if(this.view.dataset._model.name == 'res.partner'){
                    this.$el.find('a').text(this.get('value') || '')
                    this.$el.find('a').attr('href', '/web_emails/compose_mail?partner_id=' + this.view.datarecord.id || '');
                }else{
                    this._super.apply(this);
                }
            }
        },
    });
});
