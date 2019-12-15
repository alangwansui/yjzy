odoo.define('mail_all.all', function (require) {
"use strict";

var chat_manager = require('mail_base.base').chat_manager;
var core = require('web.core');
var session = require('web.session');

var _lt = core._lt;

var ChatAction = core.action_registry.get('mail.chat.instant_messaging');
ChatAction.include({
    get_thread_rendering_options: function (messages) {
        var options = this._super.apply(this, arguments);
        options.display_subject = options.display_subject || this.channel.id === "channel_all";
        return options;
    }
});

// override methods
var chat_manager_super = _.clone(chat_manager);

chat_manager.get_properties = function (msg) {
    var properties = chat_manager_super.get_properties.apply(this, arguments);
    properties.is_all = this.property_descr("channel_all", msg, this);
    return properties;
};

chat_manager.set_channel_flags = function (data, msg) {
    chat_manager_super.set_channel_flags.apply(this, arguments);
    msg.is_all = data.author_id !== 'ODOOBOT';
    return msg;
};

chat_manager.get_channel_array = function (msg) {
    var arr = chat_manager_super.get_channel_array.apply(this, arguments);
    arr.concat('channel_all');
    arr.concat('email_income');
    arr.concat('email_outer');

    return arr;
};

chat_manager.get_domain = function (channel) {
    console.info('------===-----', session.user_context);
    var dm =  (channel.id === "channel_all") ? [] :
            (channel.id === "email_income") ? [['message_type', '=', 'email'],['partner_ids.user_ids','=',session.user_context.uid]] :
            (channel.id === "email_outer") ? [['message_type', '=', 'email'],['author_id.user_ids','=', session.user_context.uid]] :
            chat_manager_super.get_domain.apply(this, arguments);
    console.info('11111111', channel, dm, session.user_context);
    return dm;
};


chat_manager.is_ready.then(function () {
        // Add all channel
        chat_manager.add_channel({
            id: "channel_all",
            name: _lt("All messages"),
            type: "static"
        });
        chat_manager.add_channel({
            id: "email_income",
            name: _lt("收件箱"),
            type: "static"
        });
        chat_manager.add_channel({
            id: "email_outer",
            name: _lt("发件箱"),
            type: "static"
        });

        return $.when();
    });

return chat_manager;

});
