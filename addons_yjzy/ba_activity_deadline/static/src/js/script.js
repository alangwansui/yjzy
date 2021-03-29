odoo.define('ba_activity_deadline.alert', function (require) {
    "use strict";

    let Notification = require('web.notification').Notification;
    let session = require('web.session');
    let WebClient = require('web.WebClient');
    let core = require('web.core');
    let date_util = require('web.time');
    let bus = require('bus.bus').bus;

    let channel = 'ba_activity_deadline.alarm';
    let _t = core._t;

    let ActivityNotification = Notification.extend({
        template: "ba_activity_deadline.notification",

        init: function (parent, title, text, eid, resModelName, resModel, resID, icon) {
            this._super(parent, title, text, eid);
            this.aid = eid;
            this.sticky = true;
            this.resModelName = resModelName;
            this.resModel = resModel;
            this.resID = resID;
            this.icon = icon;

            this.events = _.extend(this.events || {}, {
                'click .ba_activity_deadline_activity': function () {
                    let self = this;

                    this._rpc({
                        route: '/web/action/load',
                        params: {
                            action_id: 'ba_activity_deadline.action_open_activity',
                        },
                    })
                        .then(function (r) {
                            r.res_id = self.aid;
                            return self.do_action(r);
                        });
                },
                'click .ba_activity_deadline_record': function () {
                    let self = this;

                    this.do_action({
                        type: 'ir.actions.act_window',
                        view_type: 'form',
                        view_mode: 'form',
                        res_model: self.resModel,
                        views: [[false, 'form']],
                        res_id: self.resID,
                        target: 'current',

                    });
                },
                'click .ba_activity_deadline_showed': function () {
                    this.destroy(true);
                },
            });
        },
    });

    WebClient.include({
        start: function () {
            this._super.apply(this, arguments);
            bus.add_channel(channel);
            bus.on("notification", this, this.onActivityNotif);
        },
        onActivityNotif: function (notifications) {
            let self = this;
            _.each(notifications, function (notification) {
                let ch = notification[0];
                let msg = notification[1];
                if (ch === channel) {
                    self.handlerMsg(msg);
                }
            });
        },

        handlerMsg: function (msg) {
            let self = this;
            if (msg.user_id === session.uid) {
                this._rpc({
                    model: 'mail.activity',
                    method: 'search_read',
                    domain: [['id', '=', msg.id]],
                }).then(function (result) {
                    let title = _t('Activity: ') + result[0].activity_type_id[1];
                    let message = result[0].res_name;
                    let resModel = result[0].res_model;
                    let resModelName = result[0].model_name;
                    let resID = result[0].res_id;
                    let DueDate = date_util.str_to_datetime(result[0].dd);
                    let actCategory = result[0].activity_type_id[0];
                    self._rpc({
                        model: 'mail.activity.type',
                        method: 'search_read',
                        domain: [['id', '=', actCategory]],
                    }).then(function (categ) {
                        let icon = categ[0].icon || 'fa-lightbulb-o';

                        message = '<b>' + resModelName + ': </b>' + message + '<br/>';
                        message += _t('<b>到期时间: </b>') + DueDate;

                        let notification = new ActivityNotification(
                            self.notification_manager,
                            title,
                            message,
                            msg.id,
                            resModelName,
                            resModel,
                            resID,
                            icon,
                        );
                        self.notification_manager.display(notification);
                    });
                });
            }
        },
    });

});