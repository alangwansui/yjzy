odoo.define('mail_base.base', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var utils = require('mail.utils');
var config = require('web.config');
var Bus = require('web.Bus');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var web_client = require('web.web_client');
var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var _t = core._t;
var _lt = core._lt;
var LIMIT = 25;
var preview_msg_max_size = 350;  // optimal for native english speakers
var ODOOBOT_ID = "ODOOBOT";
var chat_manager = require('mail.chat_manager');
// Private model
//----------------------------------------------------------------------------------
var messages = [];
var channels = [];
var channels_preview_def;
var channel_defs = {};
var chat_unread_counter = 0;
var unread_conversation_counter = 0;
var emojis = [];
var emoji_substitutions = {};
var emoji_unicodes = {};
var needaction_counter = 0;
var starred_counter = 0;
var mention_partner_suggestions = [];
var canned_responses = [];
var commands = [];
var discuss_menu_id;
var global_unread_counter = 0;
var pinned_dm_partners = [];  // partner_ids we have a pinned DM with
var client_action_open = false;

// Global unread counter and notifications
//----------------------------------------------------------------------------------
bus.on("window_focus", null, function() {
    global_unread_counter = 0;
    web_client.set_title_part("_chat");
});

var ChatAction = core.action_registry.get('mail.chat.instant_messaging');
ChatAction.include({
    init: function (parent, action, options) {
        this._super.apply(this, arguments);
        this.channels_show_send_button = ['channel_inbox'];
        this.channels_display_subject = [];
    },
    start: function () {
        var result = this._super.apply(this, arguments);

        var search_defaults = {};
        var context = this.action ? this.action.context : [];
        _.each(context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });
        this.searchview.defaults = search_defaults;

        var self = this;
        return $.when(result).done(function () {
            $('.oe_leftbar').toggle(false);
            self.searchview.do_search();
        });
    },
    destroy: function() {
        var result = this._super.apply(this, arguments);
        $('.oe_leftbar .oe_secondary_menu').each(function () {
            if ($(this).css('display') == 'block'){
                if ($(this).children().length > 0) {
                    $('.oe_leftbar').toggle(true);
                }
                return false;
            }
        });
        return result;
    },
    set_channel: function (channel) {
        var result = this._super.apply(this, arguments);
        var self = this;
        return $.when(result).done(function() {
            self.$buttons
                .find('.o_mail_chat_button_new_message')
                .toggle(self.channels_show_send_button.indexOf(channel.id) != -1);
        });
    },
    get_thread_rendering_options: function (messages) {
        var options = this._super.apply(this, arguments);
        options.display_subject = options.display_subject || this.channels_display_subject.indexOf(this.channel.id) != -1;
        return options;
    },
    update_message_on_current_channel: function (current_channel_id, message) {
        var starred = current_channel_id === "channel_starred" && !message.is_starred;
        var inbox = current_channel_id === "channel_inbox" && !message.is_needaction;
        return starred || inbox;
    },
    on_update_message: function (message) {
        var self = this;
        var current_channel_id = this.channel.id;
        if (this.update_message_on_current_channel(current_channel_id, message)) {
            chat_manager.get_messages({channel_id: this.channel.id, domain: this.domain}).then(function (messages) {
                var options = self.get_thread_rendering_options(messages);
                self.thread.remove_message_and_render(message.id, messages, options).then(function () {
                    self.update_button_status(messages.length === 0);
                });
            });
        } else if (_.contains(message.channel_ids, current_channel_id)) {
            this.fetch_and_render_thread();
        }
    }
});

chat_manager.notify_incoming_message = function (msg, options) {
    if (bus.is_odoo_focused() && options.is_displayed) {
        // no need to notify
        return;
    }
    var title = _t('New message');
    if (msg.author_id[1]) {
        title = _.escape(msg.author_id[1]);
    }
    var content = utils.parse_and_transform(msg.body, utils.strip_html).substr(0, preview_msg_max_size);

    if (!bus.is_odoo_focused()) {
        global_unread_counter++;
        var tab_title = _.str.sprintf(_t("%d Messages"), global_unread_counter);
        web_client.set_title_part("_chat", tab_title);
    }

    utils.send_notification(web_client, title, content);
}

// Message and channel manipulation helpers
//----------------------------------------------------------------------------------

// options: channel_id, silent
chat_manager.add_message = function (data, options) {
    options = options || {};
    var msg = _.findWhere(messages, { id: data.id });

    if (!msg) {
        msg = chat_manager.make_message(data);
        // Keep the array ordered by id when inserting the new message
        messages.splice(_.sortedIndex(messages, msg, 'id'), 0, msg);
        _.each(msg.channel_ids, function (channel_id) {
            var channel = chat_manager.get_channel(channel_id);
            if (channel) {
                // update the channel's last message (displayed in the channel
                // preview, in mobile)
                if (!channel.last_message || msg.id > channel.last_message.id) {
                    channel.last_message = msg;
                }
                chat_manager.add_to_cache(msg, []);
                if (options.domain && options.domain !== []) {
                    chat_manager.add_to_cache(msg, options.domain);
                }
                if (channel.hidden) {
                    channel.hidden = false;
                    chat_manager.bus.trigger('new_channel', channel);
                }
                if (channel.type !== 'static' && !msg.is_author && !msg.is_system_notification) {
                    if (options.increment_unread) {
                        chat_manager.update_channel_unread_counter(channel, channel.unread_counter+1);
                    }
                    if (channel.is_chat && options.show_notification) {
                        if (!client_action_open && !config.device.isMobile) {
                            // automatically open chat window
                            chat_manager.bus.trigger('open_chat', channel, { passively: true });
                        }
                        var query = {is_displayed: false};
                        chat_manager.bus.trigger('anyone_listening', channel, query);
                        chat_manager.notify_incoming_message(msg, query);
                    }
                }
            }
        });
        if (!options.silent) {
            chat_manager.bus.trigger('new_message', msg);
        }
    } else if (options.domain && options.domain !== []) {
        chat_manager.add_to_cache(msg, options.domain);
    }
    return msg;
}

chat_manager.get_channel_array = function(msg){
    return [ msg.channel_ids, 'channel_inbox', 'channel_starred' ];
}

chat_manager.get_properties = function(msg){
    return {
        is_starred: chat_manager.property_descr("channel_starred", msg, chat_manager),
        is_needaction: chat_manager.property_descr("channel_inbox", msg, chat_manager)
    };
}

chat_manager.property_descr = function (channel, msg, self) {
    return {
        enumerable: true,
        get: function () {
            return _.contains(msg.channel_ids, channel);
        },
        set: function (bool) {
            if (bool) {
                chat_manager.add_channel_to_message(msg, channel);
            } else {
                msg.channel_ids = _.without(msg.channel_ids, channel);
            }
        }
    };
}

chat_manager.set_channel_flags = function (data, msg) {
    if (_.contains(data.needaction_partner_ids, session.partner_id)) {
        msg.is_needaction = true;
    }
    if (_.contains(data.starred_partner_ids, session.partner_id)) {
        msg.is_starred = true;
    }
    return msg;
}

chat_manager.make_message = function (data) {
    var msg = {
        id: data.id,
        author_id: data.author_id,
        body: data.body || "",
        date: moment(time.str_to_datetime(data.date)),
        message_type: data.message_type,
        subtype_description: data.subtype_description,
        is_author: data.author_id && data.author_id[0] === session.partner_id,
        is_note: data.is_note,
        is_system_notification: (data.message_type === 'notification' && data.model === 'mail.channel')
            || data.info === 'transient_message',
        attachment_ids: data.attachment_ids || [],
        subject: data.subject,
        email_from: data.email_from,
        customer_email_status: data.customer_email_status,
        customer_email_data: data.customer_email_data,
        record_name: data.record_name,
        tracking_value_ids: data.tracking_value_ids,
        channel_ids: data.channel_ids,
        model: data.model,
        res_id: data.res_id,
        url: session.url("/mail/view?message_id=" + data.id),
        module_icon:data.module_icon,
    };

    _.each(_.keys(emoji_substitutions), function (key) {
        var escaped_key = String(key).replace(/([.*+?=^!:${}()|[\]\/\\])/g, '\\$1');
        var regexp = new RegExp("(?:^|\\s|<[a-z]*>)(" + escaped_key + ")(?=\\s|$|</[a-z]*>)", "g");
        msg.body = msg.body.replace(regexp, ' <span class="o_mail_emoji">'+emoji_substitutions[key]+'</span> ');
    });

    Object.defineProperties(msg, chat_manager.get_properties(msg));

    msg = chat_manager.set_channel_flags(data, msg);
    if (msg.model === 'mail.channel') {
        var real_channels = _.without(chat_manager.get_channel_array(msg));
        var origin = real_channels.length === 1 ? real_channels[0] : undefined;
        var channel = origin && chat_manager.get_channel(origin);
        if (channel) {
            msg.origin_id = origin;
            msg.origin_name = channel.name;
        }
    }

    // Compute displayed author name or email
    if ((!msg.author_id || !msg.author_id[0]) && msg.email_from) {
        msg.mailto = msg.email_from;
    } else {
        msg.displayed_author = (msg.author_id === ODOOBOT_ID) && "OdooBot" ||
                               msg.author_id && msg.author_id[1] ||
                               msg.email_from || _t('Anonymous');
    }

    // Don't redirect on author clicked of self-posted or OdooBot messages
    msg.author_redirect = !msg.is_author && msg.author_id !== ODOOBOT_ID;

    // Compute the avatar_url
    if (msg.author_id === ODOOBOT_ID) {
        msg.avatar_src = "/mail/static/src/img/odoo_o.png";
    } else if (msg.author_id && msg.author_id[0]) {
        msg.avatar_src = "/web/image/res.partner/" + msg.author_id[0] + "/image_small";
    } else if (msg.message_type === 'email') {
        msg.avatar_src = "/mail/static/src/img/email_icon.png";
    } else {
        msg.avatar_src = "/mail/static/src/img/smiley/avatar.jpg";
    }

    // add anchor tags to urls
    msg.body = utils.parse_and_transform(msg.body, utils.add_link);

    // Compute url of attachments
    _.each(msg.attachment_ids, function(a) {
        a.url = '/web/content/' + a.id + '?download=true';
    });

    // format date to the local only once by message
    // can not be done in preprocess, since it alter the original value
    if (msg.tracking_value_ids && msg.tracking_value_ids.length) {
        _.each(msg.tracking_value_ids, function(f) {
            if (f.field_type === 'datetime') {
                var format = 'LLL';
                if (f.old_value) {
                    f.old_value = moment.utc(f.old_value).local().format(format);
                }
                if (f.new_value) {
                    f.new_value = moment.utc(f.new_value).local().format(format);
                }
            } else if (f.field_type === 'date') {
                var format = 'LL';
                if (f.old_value) {
                    f.old_value = moment(f.old_value).local().format(format);
                }
                if (f.new_value) {
                    f.new_value = moment(f.new_value).local().format(format);
                }
            }
        });
    }

    return msg;
}

chat_manager.add_channel_to_message = function (message, channel_id) {
    message.channel_ids.push(channel_id);
    message.channel_ids = _.uniq(message.channel_ids);
}

chat_manager.add_channel = function (data, options) {
    options = typeof options === "object" ? options : {};
    var channel = chat_manager.get_channel(data.id);
    if (channel) {
        if (channel.is_folded !== (data.state === "folded")) {
            channel.is_folded = (data.state === "folded");
            chat_manager.bus.trigger("channel_toggle_fold", channel);
        }
    } else {
        channel = chat_manager.make_channel(data, options);
        channels.push(channel);
        if (data.last_message) {
            channel.last_message = chat_manager.add_message(data.last_message);
        }
        // In case of a static channel (Inbox, Starred), the name is translated thanks to _lt
        // (lazy translate). In this case, channel.name is an object, not a string.
        channels = _.sortBy(channels, function (channel) { return _.isString(channel.name) ? channel.name.toLowerCase() : '' });
        if (!options.silent) {
            chat_manager.bus.trigger("new_channel", channel);
        }
        if (channel.is_detached) {
            chat_manager.bus.trigger("open_chat", channel);
        }
    }
    return channel;
}

chat_manager.make_channel = function (data, options) {
    var channel = {
        id: data.id,
        name: data.name,
        server_type: data.channel_type,
        type: data.type || data.channel_type,
        all_history_loaded: false,
        uuid: data.uuid,
        is_detached: data.is_minimized,
        is_folded: data.state === "folded",
        autoswitch: 'autoswitch' in options ? options.autoswitch : true,
        hidden: options.hidden,
        display_needactions: options.display_needactions,
        mass_mailing: data.mass_mailing,
        group_based_subscription: data.group_based_subscription,
        needaction_counter: data.message_needaction_counter || 0,
        unread_counter: 0,
        last_seen_message_id: data.seen_message_id,
        cache: {'[]': {
            all_history_loaded: false,
            loaded: false,
            messages: [],
        }},
    };
    if (channel.type === "channel") {
        channel.type = data.public !== "private" ? "public" : "private";
    }
    if (_.size(data.direct_partner) > 0) {
        channel.type = "dm";
        channel.name = data.direct_partner[0].name;
        channel.direct_partner_id = data.direct_partner[0].id;
        channel.status = data.direct_partner[0].im_status;
        pinned_dm_partners.push(channel.direct_partner_id);
        bus.update_option('bus_presence_partner_ids', pinned_dm_partners);
    } else if ('anonymous_name' in data) {
        channel.name = data.anonymous_name;
    }
    if (data.last_message_date) {
        channel.last_message_date = moment(time.str_to_datetime(data.last_message_date));
    }
    channel.is_chat = !channel.type.match(/^(public|private|static)$/);
    if (data.message_unread_counter) {
        chat_manager.update_channel_unread_counter(channel, data.message_unread_counter);
    }
    return channel;
}

chat_manager.remove_channel = function (channel) {
    if (!channel) { return; }
    if (channel.type === 'dm') {
        var index = pinned_dm_partners.indexOf(channel.direct_partner_id);
        if (index > -1) {
            pinned_dm_partners.splice(index, 1);
            bus.update_option('bus_presence_partner_ids', pinned_dm_partners);
        }
    }
    channels = _.without(channels, channel);
    delete channel_defs[channel.id];
}

chat_manager.get_channel_cache = function (channel, domain) {
    var stringified_domain = JSON.stringify(domain || []);
    if (!channel.cache[stringified_domain]) {
        channel.cache[stringified_domain] = {
            all_history_loaded: false,
            loaded: false,
            messages: [],
        };
    }
    return channel.cache[stringified_domain];
}

chat_manager.invalidate_caches = function (channel_ids) {
    _.each(channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.cache = { '[]': channel.cache['[]']};
        }
    });
}

chat_manager.add_to_cache = function (message, domain) {
    _.each(message.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            var channel_cache = chat_manager.get_channel_cache(channel, domain);
            var index = _.sortedIndex(channel_cache.messages, message, 'id');
            if (channel_cache.messages[index] !== message) {
                channel_cache.messages.splice(index, 0, message);
            }
        }
    });
}

chat_manager.remove_message_from_channel = function (channel_id, message) {
    message.channel_ids = _.without(message.channel_ids, channel_id);
    var channel = _.findWhere(channels, { id: channel_id });
    _.each(channel.cache, function (cache) {
        cache.messages = _.without(cache.messages, message);
    });
}

chat_manager.update_channel_unread_counter = function (channel, counter) {
    if (channel.unread_counter > 0 && counter === 0) {
        unread_conversation_counter = Math.max(0, unread_conversation_counter-1);
    } else if (channel.unread_counter === 0 && counter > 0) {
        unread_conversation_counter++;
    }
    if (channel.is_chat) {
        chat_unread_counter = Math.max(0, chat_unread_counter - channel.unread_counter + counter);
    }
    channel.unread_counter = counter;
    chat_manager.bus.trigger("update_channel_unread_counter", channel);
}

// Notification handlers
// ---------------------------------------------------------------------------------
chat_manager.on_notification = function (notifications) {
    // sometimes, the web client receives unsubscribe notification and an extra
    // notification on that channel.  This is then followed by an attempt to
    // rejoin the channel that we just left.  The next few lines remove the
    // extra notification to prevent that situation to occur.
    var unsubscribed_notif = _.find(notifications, function (notif) {
        return notif[1].info === "unsubscribe";
    });
    if (unsubscribed_notif) {
        notifications = _.reject(notifications, function (notif) {
            return notif[0][1] === "mail.channel" && notif[0][2] === unsubscribed_notif[1].id;
        });
    }
    _.each(notifications, function (notification) {
        var model = notification[0][1];
        if (model === 'ir.needaction') {
            // new message in the inbox
            chat_manager.on_needaction_notification(notification[1]);
        } else if (model === 'mail.channel') {
            // new message in a channel
            chat_manager.on_channel_notification(notification[1]);
        } else if (model === 'res.partner') {
            // channel joined/left, message marked as read/(un)starred, chat open/closed
            chat_manager.on_partner_notification(notification[1]);
        } else if (model === 'bus.presence') {
            // update presence of users
            chat_manager.on_presence_notification(notification[1]);
        }
    });
}

chat_manager.on_needaction_notification = function (message) {
    message = chat_manager.add_message(message, {
        channel_id: 'channel_inbox',
        show_notification: true,
        increment_unread: true,
    });
    chat_manager.invalidate_caches(message.channel_ids);
    if (message.channel_ids.length !== 0) {
        needaction_counter++;
    }
    _.each(message.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.needaction_counter++;
        }
    });
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

chat_manager.on_channel_notification = function (message) {
    var def;
    var channel_already_in_cache = true;
    if (message.channel_ids.length === 1) {
        channel_already_in_cache = !!chat_manager.get_channel(message.channel_ids[0]);
        def = chat_manager.join_channel(message.channel_ids[0], {autoswitch: false});
    } else {
        def = $.when();
    }
    def.then(function () {
        // don't increment unread if channel wasn't in cache yet as its unread counter has just been fetched
        chat_manager.add_message(message, { show_notification: true, increment_unread: channel_already_in_cache });
        chat_manager.invalidate_caches(message.channel_ids);
    });
}

chat_manager.on_partner_notification = function (data) {
    if (data.info === "unsubscribe") {
        var channel = chat_manager.get_channel(data.id);
        if (channel) {
            var msg;
            if (_.contains(['public', 'private'], channel.type)) {
                msg = _.str.sprintf(_t('You unsubscribed from <b>%s</b>.'), channel.name);
            } else {
                msg = _.str.sprintf(_t('You unpinned your conversation with <b>%s</b>.'), channel.name);
            }
            chat_manager.remove_channel(channel);
            chat_manager.bus.trigger("unsubscribe_from_channel", data.id);
            web_client.do_notify(_("Unsubscribed"), msg);
        }
    } else if (data.type === 'toggle_star') {
        chat_manager.on_toggle_star_notification(data);
    } else if (data.type === 'mark_as_read') {
        chat_manager.on_mark_as_read_notification(data);
    } else if (data.type === 'mark_as_unread') {
        chat_manager.on_mark_as_unread_notification(data);
    } else if (data.info === 'channel_seen') {
        chat_manager.on_channel_seen_notification(data);
    } else if (data.info === 'transient_message') {
        chat_manager.on_transient_message_notification(data);
    } else if (data.type === 'activity_updated') {
        chat_manager.onActivityUpdateNodification(data);
    } else {
        chat_manager.on_chat_session_notification(data);
    }
}

chat_manager.on_toggle_star_notification = function (data) {
    _.each(data.message_ids, function (msg_id) {
        var message = _.findWhere(messages, { id: msg_id });
        if (message) {
            chat_manager.invalidate_caches(message.channel_ids);
            message.is_starred = data.starred;
            if (!message.is_starred) {
                chat_manager.remove_message_from_channel("channel_starred", message);
                starred_counter--;
            } else {
                chat_manager.add_to_cache(message, []);
                var channel_starred = chat_manager.get_channel('channel_starred');
                channel_starred.cache = _.pick(channel_starred.cache, "[]");
                starred_counter++;
            }
            chat_manager.bus.trigger('update_message', message);
        }
    });
    chat_manager.bus.trigger('update_starred', starred_counter);
}

chat_manager.on_mark_as_read_notification = function (data) {
    _.each(data.message_ids, function (msg_id) {
        var message = _.findWhere(messages, { id: msg_id });
        if (message) {
            chat_manager.invalidate_caches(message.channel_ids);
            chat_manager.remove_message_from_channel("channel_inbox", message);
            chat_manager.bus.trigger('update_message', message, data.type);
        }
    });
    if (data.channel_ids) {
        _.each(data.channel_ids, function (channel_id) {
            var channel = chat_manager.get_channel(channel_id);
            if (channel) {
                channel.needaction_counter = Math.max(channel.needaction_counter - data.message_ids.length, 0);
            }
        });
    } else { // if no channel_ids specified, this is a 'mark all read' in the inbox
        _.each(channels, function (channel) {
            channel.needaction_counter = 0;
        });
    }
    needaction_counter = Math.max(needaction_counter - data.message_ids.length, 0);
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

chat_manager.on_mark_as_unread_notification = function (data) {
    _.each(data.message_ids, function (message_id) {
        var message = _.findWhere(messages, { id: message_id });
        if (message) {
            chat_manager.invalidate_caches(message.channel_ids);
            chat_manager.add_channel_to_message(message, 'channel_inbox');
            chat_manager.add_to_cache(message, []);
        }
    });
    var channel_inbox = chat_manager.get_channel('channel_inbox');
    channel_inbox.cache = _.pick(channel_inbox.cache, "[]");

    _.each(data.channel_ids, function (channel_id) {
        var channel = chat_manager.get_channel(channel_id);
        if (channel) {
            channel.needaction_counter += data.message_ids.length;
        }
    });
    needaction_counter += data.message_ids.length;
    chat_manager.bus.trigger('update_needaction', needaction_counter);
}

chat_manager.on_channel_seen_notification = function (data) {
    var channel = chat_manager.get_channel(data.id);
    if (channel) {
        channel.last_seen_message_id = data.last_message_id;
        if (channel.unread_counter) {
            chat_manager.update_channel_unread_counter(channel, 0);
        }
    }
}

chat_manager.on_chat_session_notification = function (chat_session) {
    var channel;
    if ((chat_session.channel_type === "channel") && (chat_session.state === "open")) {
        chat_manager.add_channel(chat_session, {autoswitch: false});
        if (!chat_session.is_minimized && chat_session.info !== 'creation') {
            web_client.do_notify(_t("Invitation"), _t("You have been invited to: ") + chat_session.name);
        }
    }
    // partner specific change (open a detached window for example)
    if ((chat_session.state === "open") || (chat_session.state === "folded")) {
        channel = chat_session.is_minimized && chat_manager.get_channel(chat_session.id);
        if (channel) {
            channel.is_detached = true;
            channel.is_folded = (chat_session.state === "folded");
            chat_manager.bus.trigger("open_chat", channel);
        }
    } else if (chat_session.state === "closed") {
        channel = chat_manager.get_channel(chat_session.id);
        if (channel) {
            channel.is_detached = false;
            chat_manager.bus.trigger("close_chat", channel, {keep_open_if_unread: true});
        }
    }
}

chat_manager.on_presence_notification = function (data) {
    var dm = chat_manager.get_dm_from_partner_id(data.id);
    if (dm) {
        dm.status = data.im_status;
        chat_manager.bus.trigger('update_dm_presence', dm);
    }
}

chat_manager.on_transient_message_notification = function(data) {
    var last_message = _.last(messages);
    data.id = (last_message ? last_message.id : 0) + 0.01;
    data.author_id = data.author_id || ODOOBOT_ID;
    chat_manager.add_message(data);
}

chat_manager.onActivityUpdateNodification = function (data) {
    chat_manager.bus.trigger('activity_updated', data);
}
// Public interface



//----------------------------------------------------------------------------------

// chat_manager.init = function (parent) {
//     var self = this;
//     Mixins.EventDispatcherMixin.init.call(this);
//     this.setParent(parent);

//     this.bus = new Bus();
//     this.bus.on('client_action_open', null, function (open) {
//         client_action_open = open;
//     });

//     bus.on('notification', null, chat_manager.on_notification);

//     this.channel_seen = _.throttle(function (channel) {
//         return self._rpc({
//                 model: 'mail.channel',
//                 method: 'channel_seen',
//                 args: [[channel.id]],
//             }, {
//                 shadow: true
//             });
//     }, 3000);
// }

chat_manager.start = function () {
    var self = this;
    this.bus.on('client_action_open', null, function (open) {
        client_action_open = open;
    });
    this.is_ready = session.is_bound.then(function(){
            var context = _.extend({isMobile: config.device.isMobile}, session.user_context);
            return session.rpc('/mail/client_action', {context: context});
        }).then(chat_manager._onMailClientAction.bind(this));

    this.channel_seen = _.throttle(function (channel) {
        return self._rpc({
                model: 'mail.channel',
                method: 'channel_seen',
                args: [[channel.id]],
            }, {
                shadow: true
            });
    }, 3000);

    chat_manager.add_channel({
        id: "channel_inbox",
        name: _lt("Inbox"),
        type: "static",
    }, { display_needactions: true });

    chat_manager.add_channel({
        id: "channel_starred",
        name: _lt("Starred"),
        type: "static"
    });
},

chat_manager._onMailClientAction = function (result) {
    _.each(result.channel_slots, function (channels) {
        _.each(channels, chat_manager.add_channel);
    });
    needaction_counter = result.needaction_inbox_counter;
    starred_counter = result.starred_counter;
    commands = _.map(result.commands, function (command) {
        return _.extend({ id: command.name }, command);
    });
    mention_partner_suggestions = result.mention_partner_suggestions;
    discuss_menu_id = result.menu_id;

    // Shortcodes: canned responses and emojis
    _.each(result.shortcodes, function (s) {
        if (s.shortcode_type === 'text') {
            canned_responses.push(_.pick(s, ['id', 'source', 'substitution']));
        } else {
            emojis.push(_.pick(s, ['id', 'source', 'unicode_source', 'substitution', 'description']));
            emoji_substitutions[_.escape(s.source)] = s.substitution;
            if (s.unicode_source) {
                emoji_substitutions[_.escape(s.unicode_source)] = s.substitution;
                emoji_unicodes[_.escape(s.source)] = s.unicode_source;
            }
        }
    });
    bus.start_polling();
}

chat_manager.get_domain = function (channel) {
    return (channel.id === "channel_inbox") ? [['needaction', '=', true]] :
        (channel.id === "channel_starred") ? [['starred', '=', true]] : false;

}

    // options: domain, load_more
chat_manager._fetchFromChannel = function (channel, options) {
    options = options || {};
    var domain = chat_manager.get_domain(channel) || [['channel_ids', 'in', channel.id]];

    console.info('==_fetchFromChannel===1', domain);
    var cache = chat_manager.get_channel_cache(channel, options.domain);

    if (options.domain) {
        domain = domain.concat(options.domain || []);
    }
    console.info('==_fetchFromChannel===2', domain);
    if (options.load_more) {
        var min_message_id = cache.messages[0].id;
        domain = [['id', '<', min_message_id]].concat(domain);
    }


    console.info('==_fetchFromChannel===3', channel, domain);

    return this._rpc({
            model: 'mail.message',
            method: 'message_fetch',
            args: [domain],
            kwargs: {limit: LIMIT, context: session.user_context},
        })
        .then(function (msgs) {
            if (!cache.all_history_loaded) {
                cache.all_history_loaded =  msgs.length < LIMIT;
            }
            cache.loaded = true;

            _.each(msgs, function (msg) {
                chat_manager.add_message(msg, {channel_id: channel.id, silent: true, domain: options.domain});
            });
            var channel_cache = chat_manager.get_channel_cache(channel, options.domain || []);
            return channel_cache.messages;
        });
}
    // options: force_fetch
chat_manager._fetchDocumentMessages = function (ids, options) {
    var loaded_msgs = _.filter(messages, function (message) {
        return _.contains(ids, message.id);
    });
    var loaded_msg_ids = _.pluck(loaded_msgs, 'id');

    options = options || {};
    if (options.force_fetch || _.difference(ids.slice(0, LIMIT), loaded_msg_ids).length) {
        var ids_to_load = _.difference(ids, loaded_msg_ids).slice(0, LIMIT);

        return this._rpc({
                model: 'mail.message',
                method: 'message_format',
                args: [ids_to_load],
                context: session.user_context,
            })
            .then(function (msgs) {
                var processed_msgs = [];
                _.each(msgs, function (msg) {
                    processed_msgs.push(chat_manager.add_message(msg, {silent: true}));
                });
                return _.sortBy(loaded_msgs.concat(processed_msgs), function (msg) {
                    return msg.id;
                });
            });
    } else {
        return $.when(loaded_msgs);
    }
},

chat_manager.post_message = function (data, options) {
    var self = this;
    options = options || {};

    // This message will be received from the mail composer as html content subtype
    // but the urls will not be linkified. If the mail composer takes the responsibility
    // to linkify the urls we end up with double linkification a bit everywhere.
    // Ideally we want to keep the content as text internally and only make html
    // enrichment at display time but the current design makes this quite hard to do.
    var body = utils.parse_and_transform(_.str.trim(data.content), utils.add_link);

    var msg = {
        partner_ids: data.partner_ids,
        body: body,
        attachment_ids: data.attachment_ids,
    };

    // for module mail_private
    if (data.is_private) {
        msg.is_private = data.is_private;
        msg.channel_ids = data.channel_ids;
    }

    // Replace emojis by their unicode character
    _.each(_.keys(emoji_unicodes), function (key) {
        var escaped_key = String(key).replace(/([.*+?=^!:${}()|[\]\/\\])/g, '\\$1');
        var regexp = new RegExp("(\\s|^)(" + escaped_key + ")(?=\\s|$)", "g");
        msg.body = msg.body.replace(regexp, "$1" + emoji_unicodes[key]);
    });

    if ('subject' in data) {
        msg.subject = data.subject;
    }
    if ('channel_id' in options) {
        // post a message in a channel or execute a command
        return this._rpc({
                model: 'mail.channel',
                method: data.command ? 'execute_command' : 'message_post',
                args: [options.channel_id],
                kwargs: _.extend(msg, {
                    message_type: 'comment',
                    content_subtype: 'html',
                    subtype: 'mail.mt_comment',
                    command: data.command,
                }),
            });
    }
    if ('model' in options && 'res_id' in options) {
        // post a message in a chatter
        _.extend(msg, {
            content_subtype: data.content_subtype,
            context: data.context,
            message_type: data.message_type,
            subtype: data.subtype,
            subtype_id: data.subtype_id,
        });

        if (options.model && options.res_id) {
            return this._rpc({
                model: options.model,
                method: 'message_post',
                args: [options.res_id],
                kwargs: msg,
            })
            .then(function (msg_id) {
                return self._rpc({
                        model: 'mail.message',
                        method: 'message_format',
                        args: [msg_id],
                    })
                    .then(function (msgs) {
                        msgs[0].model = options.model;
                        msgs[0].res_id = options.res_id;
                        chat_manager.add_message(msgs[0]);
                    });
            });
        } else {
            // This condition was added to avoid an error in the mail_reply module. 
            // If the options.channel_id or options.model variables are missing
            // the mail.compose.message model has to be used.
            // It happens when we send a message not attached to any record or channel
            // and hence we cannot call message_post method. */
            options.model = 'mail.compose.message';
            return this._rpc({
                model: options.model,
                method: 'create',
                args: [msg],
            }).then(function (id) {
                return self._rpc({
                    model: options.model,
                    method: 'send_mail_action',
                    args: [id]
                })
            });
        }
    }
}

chat_manager.get_message = function (id) {
    return _.findWhere(messages, {id: id});
}

chat_manager.get_messages = function (options) {
    var channel;

    console.info('==get_messages===', options);

    console.info('==get_messages===1', 'channel_id' in options && options.load_more);
    console.info('==get_messages===2', 'channel_id' in options);

    if ('channel_id' in options && options.load_more) {
        // get channel messages, force load_more
        channel = this.get_channel(options.channel_id);
        return this._fetchFromChannel(channel, {domain: options.domain || {}, load_more: true});
    }
    if ('channel_id' in options) {
        // channel message, check in cache first

        channel = this.get_channel(options.channel_id);
        var channel_cache = chat_manager.get_channel_cache(channel, options.domain);

        console.info('==get_messages===3', options.domain,  channel_cache.loaded);


        if (channel_cache.loaded) {
            return $.when(channel_cache.messages);
        } else {
            return this._fetchFromChannel(channel, {domain: options.domain});
        }
    }
    if ('ids' in options) {
        // get messages from their ids (chatter is the main use case)
        return this._fetchDocumentMessages(options.ids, options).then(function(result) {
            chat_manager.mark_as_read(options.ids);
            return result;
        });
    }
    if ('model' in options && 'res_id' in options) {
        // get messages for a chatter, when it doesn't know the ids (use
        // case is when using the full composer)
        var domain = [['model', '=', options.model], ['res_id', '=', options.res_id]];
        this._rpc({
                model: 'mail.message',
                method: 'message_fetch',
                args: [domain],
                kwargs: {limit: 30},
            })
            .then(function (msgs) {
                return _.map(msgs, chat_manager.add_message);
            });
    }
}

chat_manager.toggle_star_status = function (message_id) {
    return this._rpc({
            model: 'mail.message',
            method: 'toggle_message_starred',
            args: [[message_id]],
        });
}

chat_manager.unstar_all = function () {
    return this._rpc({
            model: 'mail.message',
            method: 'unstar_all',
            args: [[]]
        });
}

chat_manager.mark_as_read = function (message_ids) {
    var ids = _.filter(message_ids, function (id) {
        var message = _.findWhere(messages, {id: id});
        // If too many messages, not all are fetched, and some might not be found
        return !message || message.is_needaction;
    });
    if (ids.length) {
        return this._rpc({
                model: 'mail.message',
                method: 'set_message_done',
                args: [ids],
            });
    } else {
        return $.when();
    }
}

chat_manager.mark_all_as_read = function (channel, domain) {
    if ((channel.id === "channel_inbox" && needaction_counter) || (channel && channel.needaction_counter)) {
        return this._rpc({
                model: 'mail.message',
                method: 'mark_all_as_read',
                kwargs: {channel_ids: channel.id !== "channel_inbox" ? [channel.id] : [], domain: domain},
            });
    }
    return $.when();
}

chat_manager.undo_mark_as_read = function (message_ids, channel) {
    return this._rpc({
            model: 'mail.message',
            method: 'mark_as_unread',
            args: [message_ids, [channel.id]],
        });
}

chat_manager.mark_channel_as_seen = function (channel) {
    if (channel.unread_counter > 0 && channel.type !== 'static') {
        chat_manager.update_channel_unread_counter(channel, 0);
        this.channel_seen(channel);
    }
}

chat_manager.get_channels = function () {
    return _.clone(channels);
}

chat_manager.get_channel = function (id) {
    return _.findWhere(channels, {id: id});
}

chat_manager.get_dm_from_partner_id = function (partner_id) {
    return _.findWhere(channels, {direct_partner_id: partner_id});
}

chat_manager.all_history_loaded = function (channel, domain) {
    return chat_manager.get_channel_cache(channel, domain).all_history_loaded;
}

chat_manager.get_mention_partner_suggestions = function (channel) {
    if (!channel) {
        return mention_partner_suggestions;
    }
    if (!channel.members_deferred) {
        channel.members_deferred = this._rpc({
                model: 'mail.channel',
                method: 'channel_fetch_listeners',
                args: [channel.uuid],
            }, {
                shadow: true
            })
            .then(function (members) {
                var suggestions = [];
                _.each(mention_partner_suggestions, function (partners) {
                    suggestions.push(_.filter(partners, function (partner) {
                        return !_.findWhere(members, { id: partner.id });
                    }));
                });

                return [members];
            });
    }
    return channel.members_deferred;
}

chat_manager.get_commands = function (channel) {
    return _.filter(commands, function (command) {
        return !command.channel_types || _.contains(command.channel_types, channel.server_type);
    });
}

chat_manager.get_canned_responses = function () {
    return canned_responses;
}

chat_manager.get_emojis = function() {
    return emojis;
}

chat_manager.get_needaction_counter = function () {
    return needaction_counter;
}

chat_manager.get_starred_counter = function () {
    return starred_counter;
}

chat_manager.get_chat_unread_counter = function () {
    return chat_unread_counter;
}

chat_manager.get_unread_conversation_counter = function () {
    return unread_conversation_counter;
}

chat_manager.get_last_seen_message = function (channel) {
    if (channel.last_seen_message_id) {
        var messages = channel.cache['[]'].messages;
        var msg = _.findWhere(messages, {id: channel.last_seen_message_id});
        if (msg) {
            var i = _.sortedIndex(messages, msg, 'id') + 1;
            while (i < messages.length && (messages[i].is_author || messages[i].is_system_notification)) {
                msg = messages[i];
                i++;
            }
            return msg;
        }
    }
}

chat_manager.get_discuss_menu_id = function () {
    return discuss_menu_id;
}

chat_manager.detach_channel = function (channel) {
    return this._rpc({
            model: 'mail.channel',
            method: 'channel_minimize',
            args: [channel.uuid, true],
        }, {
            shadow: true,
        });
}

chat_manager.remove_chatter_messages = function (model) {
    messages = _.reject(messages, function (message) {
        return message.channel_ids.length === 0 && message.model === model;
    });
}

chat_manager.create_channel = function (name, type) {
    var method = type === "dm" ? "channel_get" : "channel_create";
    var args = type === "dm" ? [[name]] : [name, type];
    var context = _.extend({isMobile: config.device.isMobile}, session.user_context);
    return this._rpc({
            model: 'mail.channel',
            method: method,
            args: args,
            kwargs: {context: context},
        })
        .then(chat_manager.add_channel);
}

chat_manager.join_channel = function (channel_id, options) {
    if (channel_id in channel_defs) {
        // prevents concurrent calls to channel_join_and_get_info
        return channel_defs[channel_id];
    }
    var channel = this.get_channel(channel_id);
    if (channel) {
        // channel already joined
        channel_defs[channel_id] = $.when(channel);
    } else {
        channel_defs[channel_id] = this._rpc({
                model: 'mail.channel',
                method: 'channel_join_and_get_info',
                args: [[channel_id]],
            })
            .then(function (result) {
                return chat_manager.add_channel(result, options);
            });
    }
    return channel_defs[channel_id];
}

chat_manager.open_and_detach_dm = function (partner_id) {
    return this._rpc({
            model: 'mail.channel',
            method: 'channel_get_and_minimize',
            args: [[partner_id]],
        })
        .then(chat_manager.add_channel);
}

chat_manager.open_channel = function (channel) {
    chat_manager.bus.trigger(client_action_open ? 'open_channel' : 'detach_channel', channel);
}

chat_manager.unsubscribe = function (channel) {
    if (_.contains(['public', 'private'], channel.type)) {
        return this._rpc({
                model: 'mail.channel',
                method: 'action_unfollow',
                args: [[channel.id]],
            });
    } else {
        return this._rpc({
                model: 'mail.channel',
                method: 'channel_pin',
                args: [channel.uuid, false],
            });
    }
}

chat_manager.close_chat_session = function (channel_id) {
    var channel = this.get_channel(channel_id);
    this._rpc({
            model: 'mail.channel',
            method: 'channel_fold',
            kwargs: {uuid : channel.uuid, state : 'closed'},
        }, {shadow: true});
}

chat_manager.fold_channel = function (channel_id, folded) {
    var args = {
        uuid: this.get_channel(channel_id).uuid,
    };
    if (_.isBoolean(folded)) {
        args.state = folded ? 'folded' : 'open';
    }
    return this._rpc({
            model: 'mail.channel',
            method: 'channel_fold',
            kwargs: args,
        }, {shadow: true});
}
    /**
     * Special redirection handling for given model and id
     *
     * If the model is res.partner, and there is a user associated with this
     * partner which isn't the current user, open the DM with this user.
     * Otherwhise, open the record's form view, if this is not the current user's.
     */
chat_manager.redirect = function (res_model, res_id, dm_redirection_callback) {
    var self = this;
    var redirect_to_document = function (res_model, res_id, view_id) {
        web_client.do_action({
            type:'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: res_model,
            views: [[view_id || false, 'form']],
            res_id: res_id,
        });
    };
    if (res_model === "res.partner") {
        var domain = [["partner_id", "=", res_id]];
        this._rpc({
                model: 'res.users',
                method: 'search',
                args: [domain],
            })
            .then(function (user_ids) {
                if (user_ids.length && user_ids[0] !== session.uid && dm_redirection_callback) {
                    self.create_channel(res_id, 'dm').then(dm_redirection_callback);
                } else {
                    redirect_to_document(res_model, res_id);
                }
            });
    } else {
        this._rpc({
                model: res_model,
                method: 'get_formview_id',
                args: [[res_id], session.user_context],
            })
            .then(function (view_id) {
                redirect_to_document(res_model, res_id, view_id);
            });
    }
}

chat_manager.get_channels_preview = function (channels) {
    var channels_preview = _.map(channels, function (channel) {
        var info;
        if (channel.channel_ids && _.contains(channel.channel_ids,"channel_inbox")) {
            // map inbox(mail_message) data with existing channel/chat template
            info = _.pick(channel, 'id', 'body', 'avatar_src', 'res_id', 'model', 'module_icon', 'subject','date', 'record_name', 'status', 'displayed_author', 'email_from', 'unread_counter');
            info.last_message = {
                body: info.body,
                date: info.date,
                displayed_author: info.displayed_author || info.email_from,
            };
            info.name = info.record_name || info.subject || info.displayed_author;
            info.image_src = info.module_icon || info.avatar_src;
            info.message_id = info.id;
            info.id = 'channel_inbox';
            return info;
        }
        info = _.pick(channel, 'id', 'is_chat', 'name', 'status', 'unread_counter');
        info.last_message = channel.last_message || _.last(channel.cache['[]'].messages);
        if (!info.is_chat) {
            info.image_src = '/web/image/mail.channel/'+channel.id+'/image_small';
        } else if (channel.direct_partner_id) {
            info.image_src = '/web/image/res.partner/'+channel.direct_partner_id+'/image_small';
        } else {
            info.image_src = '/mail/static/src/img/smiley/avatar.jpg';
        }
        return info;
    });
    var missing_channels = _.where(channels_preview, {last_message: undefined});
    if (!channels_preview_def) {
        if (missing_channels.length) {
            var missing_channel_ids = _.pluck(missing_channels, 'id');
            channels_preview_def = this._rpc({
                    model: 'mail.channel',
                    method: 'channel_fetch_preview',
                    args: [missing_channel_ids],
                }, {
                    shadow: true,
                });
        } else {
            channels_preview_def = $.when();
        }
    }
    return channels_preview_def.then(function (channels) {
        _.each(missing_channels, function (channel_preview) {
            var channel = _.findWhere(channels, {id: channel_preview.id});
            if (channel) {
                channel_preview.last_message = chat_manager.add_message(channel.last_message);
            }
        });
        // sort channels: 1. unread, 2. chat, 3. date of last msg
        channels_preview.sort(function (c1, c2) {
            return Math.min(1, c2.unread_counter) - Math.min(1, c1.unread_counter) ||
                   c2.is_chat - c1.is_chat ||
                   !!c2.last_message - !!c1.last_message ||
                   (c2.last_message && c2.last_message.date.diff(c1.last_message.date));
        });

        // generate last message preview (inline message body and compute date to display)
        _.each(channels_preview, function (channel) {
            if (channel.last_message) {
                channel.last_message_preview = chat_manager.get_message_body_preview(channel.last_message.body);
                channel.last_message_date = channel.last_message.date.fromNow();
            }
        });
        return channels_preview;
    });
},
chat_manager.get_message_body_preview = function (message_body) {
    return utils.parse_and_transform(message_body, utils.inline);
}

chat_manager.search_partner = function (search_val, limit) {
    var def = $.Deferred();
    var values = [];
    // search among prefetched partners
    var search_regexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search_val)), 'i');
    _.each(mention_partner_suggestions, function (partners) {
        if (values.length < limit) {
            values = values.concat(_.filter(partners, function (partner) {
                return session.partner_id !== partner.id && search_regexp.test(partner.name);
            })).splice(0, limit);
        }
    });
    if (!values.length) {
        // extend the research to all users
        def = this._rpc({
                model: 'res.partner',
                method: 'im_search',
                args: [search_val, limit || 20],
            }, {
                shadow: true,
            });
    } else {
        def = $.when(values);
    }
    return def.then(function (values) {
        var autocomplete_data = _.map(values, function (value) {
            return { id: value.id, value: value.name, label: value.name };
        });
        return _.sortBy(autocomplete_data, 'label');
    });
}

chat_manager.start();
bus.off('notification');
bus.on('notification', null, function () {
    chat_manager.on_notification.apply(chat_manager, arguments);
});

return {
    ODOOBOT_ID: ODOOBOT_ID,
    chat_manager: chat_manager,
};

});
