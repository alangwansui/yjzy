odoo.define('web_global_search.GlobalAutoComplete', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var core = require('web.core');

    return Widget.extend({
        template: "GlobalSearch.AutoComplete",
        init: function (parent, options) {
            this._super(parent);
            this.$input = parent.$el;
            this.current_result = null;
            this.searching = true;
            this.search_string = '';
            this.get_search_string = options.get_search_string;
            this.get_search_element = options.get_search_element;
            this.current_element = null;
            this.selected_data = '';
            this.focus_data = '';
        },
        start: function () {
            var self = this;
            self.$el.parents().find('.oe_application_menu_placeholder a').on('click', function () {
                self.$el.parents().find('.o_sub_menu').css('display', 'block');
            });
            this.$input.on('focusout', function () {
                self._onClose()
            });
            this.$input.on('keyup', function (ev) {
                if (ev.which === $.ui.keyCode.RIGHT) {
                    self.searching = true;
                    ev.preventDefault();
                    return;
                }
                var search_string = self.get_search_string();
                if (self.search_string !== search_string) {
                    if (search_string.length) {
                        self.search_string = search_string;
                    } else {
                        self._onClose();
                    }
                }
            });
            this.$input.on('keypress', function (ev) {
                self.search_string = self.search_string + String.fromCharCode(ev.which);
                if (self.search_string.length) {
                    self.searching = true;
                    var search_string = self.search_string;
                } else {
                    self._onClose();
                }
            });
            this.$input.on('keydown', function (ev) {
                switch (ev.which) {
                    case $.ui.keyCode.ENTER:
                    case $.ui.keyCode.TAB:
                        self.searching = false;
                        var current = self.current_result;
                        if (current && current.expand) {
                            ev.preventDefault();
                            ev.stopPropagation();
                            if (current.expanded) {
                                self.fold();
                            }
                            else {
                                self.expand();
                                self.searching = true;
                            }
                        }
                        else {
                            if (self.search_string.length) {
                                self._onSelectItem(ev);
                            }
                        }
                        ev.preventDefault();
                        break;
                    case $.ui.keyCode.DOWN:
                        if (self.search_string) {
                            self._onMove('down');
                            self.searching = false;
                            ev.preventDefault();
                        }
                        break;
                    case $.ui.keyCode.UP:
                        if (self.search_string) {
                            self._onMove('up');
                            self.searching = false;
                            ev.preventDefault();
                        }
                        break;
                    case $.ui.keyCode.RIGHT:
                        self.searching = false;
                        var current = self.current_result;
                        if (current && current.expand && !current.expanded) {
                            self.expand();
                            self.searching = true;
                        }
                        ev.preventDefault();
                        break;
                    case $.ui.keyCode.ESCAPE:
                        self._onClose();
                        self.searching = false;
                        break;
                }
            });
        },
        search: function (query, models) {
            var self = this;
            self.current_search = query;
            self._renderSearch(models);
        },
        _renderSearch: function (results) {
            var self = this;
            var $list = self.$('ul');
            $list.empty();
            var render_separator = false;
            var has_list = false
            $.each(results, function (key, val) {
                var result = {expand: true};
                result['model'] = [key, val];
                var $item = self._processListItem(result).appendTo($list);
            });
            this._onShow();
        },
        _processListItem: function (result) {
            var self = this;
            var $li = $('<li>')
                .hover(function () {
                    self._setfocus($li);
                })
                .mousedown(function (ev) {
                    self.searching = false;
                    var current = self.current_result;

                    if (current && current.expand) {
                        ev.preventDefault();
                        ev.stopPropagation();
                        if (current.expanded) {
                            self.fold();
                        }
                        else {
                            self.expand();
                        }
                    }
                    else {
                        if (self.search_string.length) {
                            self._onSelectItem(ev);
                        }
                    }
                    ev.preventDefault();
                })
                .data('result', result);
            if (result.expand) {
                var $expand = $('<span class="oe-expand">').addClass('fa fa-chevron-right').appendTo($li);
                result.expanded = false;
                $li.append($('<span>').html('Search <em>' + result.model[0] + '</em> for: <strong>' + self.search_string + '</strong>'));
            }
            if (result.indent) {
                if (result.label) {
                    $li.append($('<span>').html(' ' + result.label));
                }
                else {
                    var regex = RegExp(this.search_string, 'gi');
                    var replacement = '<strong>$&</strong>';
                    $li.append($('<strong>').html(' ' + result['display_name']));
                    for (var key in result) {
                        if ($.inArray(key, ['display_model', 'display_name', 'id', 'indent', 'model']) >= 0) {
                            continue;
                        }
                        $li.append($('<em>').html(' | ' + key));
                        $li.append($('<span>').html(': ' + String(result[key]).replace(regex, replacement)));
                    }
                }
                $li.addClass('oe-indent');
            }
            return $li;
        },
        expand: function () {
            var self = this;
            var current_result = this.current_result;
            return this._rpc({
                route: '/globalsearch/search_data',
                params: {
                    model: current_result['model'][1],
                    search_string: self.get_search_string()
                }
            }).then(function (results) {
                (results).reverse().forEach(function (result) {
                    if (Object.keys(result).length > 3 || result.label === '(no result)') {
                        result.display_model = current_result['model'][0];
                        result.indent = true;
                        var $li = self._processListItem(result);
                        self.current_element.after($li);
                    }
                });
                current_result.expanded = true;
                self.current_element.find('span.oe-expand').removeClass('fa-chevron-right');
                self.current_element.find('span.oe-expand').addClass('fa-chevron-down');
            });
        },
        fold: function () {
            var $next = this.current_element.next();
            while ($next.hasClass('oe-indent')) {
                $next.remove();
                $next = this.current_element.next();
            }
            this.current_result.expanded = false;
            this.current_element.find('span.oe-expand').removeClass('fa-chevron-down');
            this.current_element.find('span.oe-expand').addClass('fa-chevron-right');
        },
        _setfocus: function ($li) {
            this.$('li').removeClass('oe-selection-focus');
            $li.addClass('oe-selection-focus');
            this.current_result = $li.data('result');
            this.current_element = $li
            this.focus_data = $li.text();
        },
        removeFocus: function () {
            this.$('li').removeClass('oe-selection-focus');
            this.focus_data = ''
        },
        _onSelectItem: function (ev) {
            var self = this;
            if (this.current_result && this.current_result.label === '(no result)') {
                return true
            }
            if (this.current_result && this.current_result.expand) {
                this.expand()
            }
            if (this.current_result && this.current_result.indent) {
                var $li = self.$('li.oe-selection-focus')
                self.selected_data = $li.data('result')
                if (!_.isEmpty(self.selected_data)) {
                    var id = this.current_result['id'], model = this.current_result['model'];
                    self.$input.find('.o_search_input').val(self.selected_data['display_model'] + ':  ' + $.trim(this.focus_data.split('|')[0]))
                    ev.preventDefault();
                    self._onClose()
                    core.bus.trigger('toggle_switch');
                    self.do_action({
                        'type': 'ir.actions.act_window',
                        'res_id': id,
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': model,
                        'target': 'current',
                        'views': [[false, 'form']],
                    }).then(function (result) {
                        self.$el.parents().find('.o_sub_menu').css('display', 'none');
                        $('body').removeClass('o_open_gs');
                    });
                }
            }
        },
        _onShow: function () {
            this.$el.show();
        },
        _onClose: function () {
            this.current_search = null;
            this.search_string = '';
            this.searching = true;
            this.$el.hide();
        },
        _onMove: function (direction) {
            var $next;
            if (direction === 'down') {
                $next = this.$('li.oe-selection-focus').nextAll(':not(.oe-separator)').first();
                if (!$next.length) $next = this.$('li:first-child');
            } else {
                $next = this.$('li.oe-selection-focus').prevAll(':not(.oe-separator)').first();
                if (!$next.length) $next = this.$('li:not(.oe-separator)').last();
            }
            this._setfocus($next);
            $(".oe-global-autocomplete").scrollTop(0);//set to top
            if ($('li.oe-selection-focus').offset()) {
                $(".oe-global-autocomplete").scrollTop($('li.oe-selection-focus').offset().top - $(".oe-global-autocomplete").height());
            }
        },
        is_expandable: function () {
            return !!this.$('.oe-selection-focus .oe-expand').length;
        },
    });
});