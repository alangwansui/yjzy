odoo.define('popup_reminder.popup_reminder', function(require) {
    "use strict";

    var bus = require('bus.bus');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var Session = require('web.session')
    var SystrayMenu = require('web.SystrayMenu');
    var time = require('web.time');
    var Webclient = require('web.web_client');
    var Widget = require('web.Widget');

    var _t = core._t;
    var QWeb = core.qweb;

    var reminder_panel = null;

    var HeaderSelector = Widget.extend({
        template: "popup_reminder.record_header",
        events: {
            "change .select_record_header": "select_change"
        },
        init: function(parent, options) {
            this._super(parent);
            this.reminder_panel = parent;
            this.selected_header = false;
        },
        renderElement: function() {
            this._super();
            var self = this;
            if (self.reminder_panel.record_header) {
                for (var firstKey in self.reminder_panel.record_header) break;
                self.selected_header = firstKey;
                if (self.reminder_panel.offset + 100 > self.reminder_panel.model_count[self.selected_header]) {
                    self.reminder_panel.$el.find(".oe_next_button").hide();
                }
                self.render_panel();
            }
        },
        // Bind change event of header selector.
        select_change: function(e) {
            var self = this;
            self.reminder_panel.offset = 0;
            self.reminder_panel.$el.find(".oe_previous_button").hide();
            self.reminder_panel.$el.find(".oe_next_button").show();
            self.selected_header = e.target.value;
            if (self.reminder_panel.offset + 100 > self.reminder_panel.model_count[self.selected_header]) {
                self.reminder_panel.$el.find(".oe_next_button").hide();
            }
            self.reminder_panel.search_reminder();
        },
        // This method is used to set the data into the panel.
        render_panel: function() {
            var self = this;
            if (self.selected_header && self.reminder_panel.reminder_list[self.selected_header]) {
                self.reminder_panel.$el.find(".oe_popup_list").remove();
                self.reminder_panel.$el.find(".oe_popup_reminders")
                    .append(QWeb.render('popup_reminder.remider_widget_panel', {
                        widget: self,
                        reminder_list: self.reminder_panel.reminder_list[self.selected_header],
                        header_obj: self.reminder_panel.record_header[self.selected_header]
                    }));
            }
            self.row_click();
        },
        // Bind click event for each record row.
        row_click: function() {
            var self = this;
            var found = self.reminder_panel.model_data[self.selected_header]
            self.reminder_panel.$el.find(".oe_popup_list").find('.oe_popup_record_click').off('click').on('click', function(e) {
                var id = parseInt($(this).attr('recid'));
                if (found && id) {
                    Webclient.action_manager.do_action({
                        res_model: found,
                        type: 'ir.actions.act_window',
                        res_id: id,
                        view_type: 'form',
                        view_mode: 'form',
                        views: [
                            [false, 'form']
                        ],
                        target: 'current',
                        display_current_breadcrumb: true,
                    });
                }
            });
            self.reminder_panel.$el.find(".oe_popup_list").find('.oe_popup_record_read').off('click').on('click', function(e) {
                var id = parseInt($(this).attr('recid'));
                if (found && id) {
                    self._rpc({
                        model: found,
                        method: 'write',
                        args: [id, {
                            'active': false
                        }],
                    }).done(function(res) {
                        self.reminder_panel.search_reminder();
                    });
                }
            });
        }
    });


    // class to handle reminder panel functionality.
    var ReminderPanel = Widget.extend({
        template: "popup_reminder.ReminderPanel",
        events: {
            "click .oe_next_button": "next_reminder",
            "click .oe_previous_button": "prev_reminder"
        },
        init: function(parent, PopupTopButton) {
            if (reminder_panel) {
                return reminder_panel;
            }
            this._super(parent);
            this.shown = false;
            this.PopupTopButton = PopupTopButton;
            this.record_header = {};
            this.reminder_list = {};
            this.model_data = {};
            this.offset = 0;
            this.selected_model = false;
            this.model_count = {}
            reminder_panel = this;
            this.appendTo(Webclient.$el);
        },
        start: function() {
            var self = this;
            // Hide reminder panel if user click's outside reminder panel.
            $("body").click(function(e) {
                if (e.target.id == "popup_reminder_panel" || $(e.target).parents("#popup_reminder_panel").size()) {} else {
                    if (self.shown) {
                        self.toggle_display()
                    }
                }
            });
            this.$el.css("top", -this.$el.outerHeight());
            // If offset is 0 hide previous button.
            if (!this.offset) {
                this.$el.find(".oe_previous_button").hide()
            }
            // Used to get the total count and and configured model related count.
            self._rpc({
                model: 'popup.reminder',
                method: 'get_total_data',
                args: [],
            }).done(function(result) {
                self.set_count(result.tot_count)
                self.model_count = result.model_count;
            });
        },
        // Bind click event of previous button to show next button and hide button if offset is zero.
        // Call search_reminder in order to fetch new data.
        prev_reminder: function() {
            var self = this;
            self.$el.find(".oe_next_button").show()
            if (self.offset - 100 <= 0) {
                $(this).hide()
            }
            if (self.offset) {
                self.offset = self.offset - 100;
                self.search_reminder()
            } else {
                $(this).hide()
            }
        },

        // Bind click event of next button to show previous button and hide button if offset is zero.
        // Call search_reminder in order to fetch new data.
        next_reminder: function() {
            var self = this;
            if (self.header_selector) {
                self.selected_model = self.model_data[self.header_selector.selected_header]
            }
            self.offset = self.offset + 100;
            $(this).show();
            self.$el.find(".oe_previous_button").show()
            if (self.header_selector) {
                if (self.offset + 100 > self.model_count[self.header_selector.selected_header]) {
                    $(this).hide()
                }
            }
            self.search_reminder()
        },

        toggle_display: function() {
            var self = this;
            if (self.shown) {
                self.$el.hide()
            } else {
                // update the list of reminder and header panel.
                $.when(self.search_reminder()).done(function() {
                    if (self.header_selector) {
                        self.header_selector.destroy()
                    }
                    self.header_selector = new HeaderSelector(self);
                    self.header_selector.appendTo(self.$el.find(".oe_record_header_selector"));
                    self.$el.show()
                    self.$el.animate({
                        "top": 32,
                    });
                })
            }
            self.shown = !self.shown;
        },
        //Get the reminders records.
        search_reminder: function() {
            var self = this;
            //get the reminders's information and populate the queue
            return self._rpc({
                model: "popup.reminder",
                method: 'get_list',
                context: Session.user_context,
                args: [
                    self.offset
                ],
            }).done(_.bind(self.parse_reminder_record, self));
        },
        //Parse resulted reminder records and call reminder_panel() of header to render data according to selected header.
        parse_reminder_record: function(result) {
            var self = this;
            self.record_header = result.record_header;
            self.reminder_list = result.reminder_list;
            self.model_data = result.model_data;
            $.each(self.reminder_list, function(key, value) {
                for (var x = 0; x < value.length; x++) {
                    $.each(value[x], function(k, v) {
                        var date_val = false;
                        try {
                            time.auto_str_to_date(v);
                            date_val = true;
                        } catch (e) {
                            date_val = false;
                        }
                        if (date_val) {
                            if (v) {
                                var new_date_val = field_utils.format.datetime(moment(time.auto_str_to_date(v)));
                                value[x][k] = new_date_val;
                            }
                        }
                    });
                }
            });
            if (self.header_selector) {
                self.header_selector.render_panel()
            }
        },
        //Listen core bus notification and check channel
        //If channel is related to popup reminder display the message to top button using set_count method.
        on_notification: function(notification) {
            var self = this;
            var channel = notification[0];
            var message = notification[1];
            if ((Array.isArray(channel) && channel[0] && (channel[0][1] === 'popup.reminder'))) {
                var c_value = JSON.parse(JSON.stringify(channel[1]))
                if (channel[1]) {
                    if (!self.shown) {
                        self.start();
                        self.set_count(channel[1])
                        self.PopupTopButton.$el.find(".oe_popup_notification").addClass('oe_highlight_btn')
                    } else if (self.shown) {
                        self.set_count(channel[1])
                    }
                } else {
                    self.set_count(channel[1])
                }
            }
        },
        //Call set_count method to set count on the top button.
        set_count: function(count) {
            var self = this;
            self.PopupTopButton.$el.find(".oe_popup_notification").text(count)
        },
    });


    //Inherits widget class to display top button for notification.
    var PopupTopButton = Widget.extend({
        template: 'popup_reminder.switch_panel_popup_top_button',
        events: {
            "click": "toggle_display",
        },
        init: function(options) {
            options = options || {};
            this._super(options);
            this.title = _t('Display Reminder Panel');
        },
        start: function() {
            this._super()
            var self = this;
            self.init_bus();
        },
        //Initialize bus in order to listen to bus related notification.
        init_bus: function() {
            var self = this;
            self.bus = bus.bus;
            if (!self.ReminderPanel) {
                var self = this;
                self.ReminderPanel = new ReminderPanel(Webclient, self);
                self.bus.on("notification", self, self.ReminderPanel.on_notification);
            }
        },
        //Used to show/hide reminder panel in screen.
        toggle_display: function(ev) {
            var self = this;
            ev.preventDefault();

            if(this.ReminderPanel && this.ReminderPanel.model_count && _.isEmpty(this.ReminderPanel.model_count)) {
                this.do_warn( _t('Warning'), _t("Record not found."));
                return false;
            }
            
            if (!this.ReminderPanel) {
                var self = this;
                self.ReminderPanel = new ReminderPanel(Webclient, self);
                self.toggle_display(ev);
            } else {
                this.ReminderPanel.toggle_display();
            }
        }
    });

    // Put the reminder dialog widget in the systray menu if the user has access rights
    SystrayMenu.Items.push(PopupTopButton);

    return {
        popupTopButton: new PopupTopButton(),
    };
});