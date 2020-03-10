odoo.define('web_global_search.GlobalSearch', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var SystrayMenu = require('web.SystrayMenu');
    var GlobalAutoComplete = require('web_global_search.GlobalAutoComplete');

    var GlobalSearchMenu = Widget.extend({
        template: 'GlobalSearchLi',
        events: {
            'click .o_search_icon': '_openGlobalSearch',
        },
        start: function(){
          this._super();
          this._onLoadGlobalSearch();
        },
        _onLoadGlobalSearch: function(){
            new GlobalSearch(this).appendTo($('body'));
        },
        _openGlobalSearch: function (ev) {
            ev.preventDefault();
            $('body').toggleClass('o_open_gs');
            $('.o_search_input').focus();
        },

    });
    var GlobalSearch = Widget.extend({
        template: 'GlobalSearch',
        events: {
            'input input.o_search_input': '_onChangeInput',
            'click input.o_search_input': '_onClickInput',
            'click .fa-times': '_onClearSearch',
            'click .o_search_close': '_closeGlobalSearch',
        },
        init: function (parent) {
            this._super(parent);
            this.models = null;
            this.autocomplete = null;
            this.timer = 0;
        },
        start: function () {
            var self = this;
            self._super.apply(this, arguments);
            self.values = [];
            self.autocomplete = new GlobalAutoComplete(this, {
                get_search_element: function () {
                    return self.$('input.o_search_input');
                },
                get_search_string: function () {
                    return self.$('input.o_search_input').val();
                },
            });
            self.autocomplete.appendTo(self.$('.o_global_search ul li'));
        },
        _onClickInput: function (e) {
            this.autocomplete.removeFocus()
        },
        _onChangeInput: function (e) {
            clearTimeout(this.timer);
            var self = this, $input_group = $('.user-dropdown.input-group');
            this.timer = setTimeout(this._getData.bind(this), 200);
            if (!this.$el.find('.o_search_input').val()) {
                $input_group.find('.cu_close').hide();
                $input_group.find('.cu_search').show();
            } else {
                if ($input_group.find('.cu_close').css('display') === 'none') {
                    $input_group.find('.cu_close').show();
                    $input_group.find('.cu_search').hide();
                }
            }
        },
        _onClearSearch: function (e) {
            var $input_group = $('.user-dropdown.input-group');
            $input_group.find('.cu_close').hide();
            $input_group.find('.cu_search').show();
            this.$el.find('.o_search_input').val('');
            this.$el.find('.o_search_input').focus();
        },
        _closeGlobalSearch: function (ev) {
            ev.preventDefault();
            $('body').removeClass('o_open_gs');
        },
        _getData: function () {
            var self = this;
            if (!self.$('input.o_search_input').val()) {
                self.autocomplete._onClose();
                return;
            }
            self.autocomplete.search_string = self.$('input.o_search_input').val();
            return self._rpc({
                route: '/globalsearch/model_fields',
                params: {}
            }).then(function (r) {
                return self.autocomplete.search(self.$('input.o_search_input').val(), r)
            });
        },

    });
    SystrayMenu.Items.push(GlobalSearchMenu)
});