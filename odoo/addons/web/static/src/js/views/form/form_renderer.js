odoo.define('web.FormRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var config = require('web.config');
var core = require('web.core');
var dom = require('web.dom');

var _t = core._t;
var qweb = core.qweb;

var FormRenderer = BasicRenderer.extend({
    className: "o_form_view",
    events: _.extend({}, BasicRenderer.prototype.events, {
        'click .o_notification_box .oe_field_translate': '_onTranslate',
        'click .oe_title, .o_inner_group': '_onClick',
    }),
    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.idsForLabels = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Focuses the field having attribute 'default_focus' set, if any, or the
     * first focusable field otherwise.
     */
    autofocus: function () {
        if (this.mode === 'readonly') {
            return;
        }
        var focusWidget = this.defaultFocusField;
        if (!focusWidget || !focusWidget.isFocusable()) {
            var widgets = this.allFieldWidgets[this.state.id];
            for (var i = 0; i < (widgets ? widgets.length : 0); i++) {
                var widget = widgets[i];
                if (widget.isFocusable()) {
                    focusWidget = widget;
                    break;
                }
            }
        }
        if (focusWidget) {
            focusWidget.activate({noselect: true});
        }
    },
    /**
     * Extend the method so that labels also receive the 'o_field_invalid' class
     * if necessary.
     *
     * @override
     * @see BasicRenderer.canBeSaved
     * @param {string} recordID
     * @returns {string[]}
     */
    canBeSaved: function (recordID) {
        var self = this;
        var fieldNames = this._super.apply(this, arguments);

        var $labels = this.$('label');
        $labels.removeClass('o_field_invalid');

        _.each(fieldNames, function (fieldName) {
            var idForLabel = self.idsForLabels[fieldName];
            if (idForLabel) {
                $labels
                    .filter('[for=' + idForLabel + ']')
                    .addClass('o_field_invalid');
            }
        });
        return fieldNames;
    },
    /**
     * Show a warning message if the user modified a translated field.  For each
     * field, the notification provides a link to edit the field's translations.
     *
     * @param {Object[]} alertFields field list
     */
    displayTranslationAlert: function (alertFields) {
        this.$('.o_notification_box').remove();
        var $notification = $(qweb.render('notification-box', {type: 'info'}))
            .append(qweb.render('translation-alert', {
                fields: alertFields,
                lang: _t.database.parameters.name
            }));
        if (this.$('.o_form_statusbar').length) {
            this.$('.o_form_statusbar').after($notification);
        } else {
            this.$el.prepend($notification);
        }
    },
    /**
     * @see BasicRenderer.confirmChange
     *
     * We need to reapply the idForLabel postprocessing since some widgets may
     * have recomputed their dom entirely.
     *
     * @override
     */
    confirmChange: function (state, id, fields, e) {
        var self = this;
        return this._super.apply(this, arguments).then(function (resetWidgets) {
            _.each(resetWidgets, function (widget) {
                self._setIDForLabel(widget, self.idsForLabels[widget.name]);
            });
            if (self.$('.o_field_invalid').length) {
                self.canBeSaved(self.state.id);
            }
            return resetWidgets;
        });
    },
    /**
     * Disable statusbar buttons and stat buttons so that they can't be clicked anymore
     *
     */
    disableButtons: function () {
        this.$('.o_statusbar_buttons button, .oe_button_box button')
            .attr('disabled', true);
    },
    /**
     * Enable statusbar buttons and stat buttons so they can be clicked again
     *
     */
    enableButtons: function () {
        this.$('.o_statusbar_buttons button, .oe_button_box button')
            .removeAttr('disabled');
    },
    /**
     * returns the active tab pages for each notebook
     *
     * @todo currently, this method is unused...
     *
     * @see setLocalState
     * @returns {Object} a map from notebook name to the active tab index
     */
    getLocalState: function () {
        var state = {};
        this.$('div.o_notebook').each(function () {
            var $notebook = $(this);
            var name = $notebook.data('name');
            var index = -1;
            $notebook.find('li').each(function (i) {
                if ($(this).hasClass('active')) {
                    index = i;
                }
            });
            state[name] = index;
        });
        return state;
    },
    /**
     * restore active tab pages for each notebook
     *
     * @todo make sure this method is called
     *
     * @param {Object} state the result from a getLocalState call
     */
    setLocalState: function (state) {
        this.$('div.o_notebook').each(function () {
            var $notebook = $(this);
            var name = $notebook.data('name');
            if (name in state) {
                var $page = $notebook.find('> ul > li').eq(state[name]);
                if (!$page.hasClass('o_invisible_modifier')) {
                    $page.find('a[data-toggle="tab"]').click();
                }
            }
        });
    },
    /**
     * @override method from AbstractRenderer
     * @param {Object} state a valid state given by the model
     * @param {Object} params
     * @param {string} [params.mode] new mode, either 'edit' or 'readonly'
     * @param {string[]} [params.fieldNames] if given, the renderer will only
     *   update the fields in this list
     * @returns {Deferred}
     */
    updateState: function (state, params) {
        this.mode = (params && 'mode' in params) ? params.mode : this.mode;

        // if fieldNames are given, we update the corresponding field widget.
        // I think this is wrong, and the caller could directly call the
        // confirmChange method
        if (params.fieldNames) {
            // only update the given fields
            return this.confirmChange(state, state.id, params.fieldNames);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a tooltip on a button
     *
     * @private
     * @param {Object} node
     * @param {jQuery} $button
     */
    _addButtonTooltip: function (node, $button) {
        var self = this;
        $button.tooltip({
            delay: { show: 1000, hide: 0 },
            title: function () {
                return qweb.render('WidgetButton.tooltip', {
                    debug: config.debug,
                    state: self.state,
                    node: node,
                });
            },
        });
    },
    /**
     * @private
     * @param {jQueryElement} $el
     * @param {Object} node
     */
    _addOnClickAction: function ($el, node) {
        var self = this;
        $el.click(function () {
            self.trigger_up('button_clicked', {
                attrs: node.attrs,
                record: self.state,
            });
        });
    },
    /**
     * @private
     * @param {string} name
     * @returns {string}
     */
    _getIDForLabel: function (name) {
        var idForLabel = this.idsForLabels[name];
        if (!idForLabel) {
            idForLabel = _.uniqueId('o_field_input_');
            this.idsForLabels[name] = idForLabel;
        }
        return idForLabel;
    },
    /**
     * @override
     * @private
     */
    _postProcessField: function (widget, node) {
        this._setIDForLabel(widget, this._getIDForLabel(node.attrs.name));
        this._handleAttributes(widget.$el, node);
        if (JSON.parse(node.attrs.default_focus || "0")) {
            this.defaultFocusField = widget;
        }
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderButtonBox: function (node) {
        var self = this;
        var $result = $('<' + node.tag + '>', { 'class': 'o_not_full' });
        var buttons = _.map(node.children, function (child) {
            if (child.tag === 'button') {
                return self._renderStatButton(child);
            } else {
                return self._renderNode(child);
            }
        });
        var buttons_partition = _.partition(buttons, function ($button) {
            return $button.is('.o_invisible_modifier');
        });
        var invisible_buttons = buttons_partition[0];
        var visible_buttons = buttons_partition[1];

        // Get the unfolded buttons according to window size
        var nb_buttons = [2, 4, 6, 7][config.device.size_class];
        var unfolded_buttons = visible_buttons.slice(0, nb_buttons).concat(invisible_buttons);

        // Get the folded buttons
        var folded_buttons = visible_buttons.slice(nb_buttons);
        if (folded_buttons.length === 1) {
            unfolded_buttons = buttons;
            folded_buttons = [];
        }

        // Toggle class to tell if the button box is full (LESS requirement)
        var full = (visible_buttons.length > nb_buttons);
        $result.toggleClass('o_full', full).toggleClass('o_not_full', !full);

        // Add the unfolded buttons
        _.each(unfolded_buttons, function ($button) {
            $button.appendTo($result);
        });

        // Add the dropdown with folded buttons if any
        if (folded_buttons.length) {
            $result.append($("<button>", {
                type: 'button',
                'class': "btn btn-sm oe_stat_button o_button_more dropdown-toggle",
                'data-toggle': "dropdown",
                text: _t("More"),
            }));

            var $ul = $("<ul>", {'class': "dropdown-menu o_dropdown_more", role: "menu"});
            _.each(folded_buttons, function ($button) {
                $('<li>').appendTo($ul).append($button);
            });
            $ul.appendTo($result);
        }

        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderGenericTag: function (node) {
        var $result = $('<' + node.tag + '>', _.omit(node.attrs, 'modifiers'));
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        $result.append(_.map(node.children, this._renderNode.bind(this)));
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderHeaderButton: function (node) {
        var $button = $('<button>')
                        .text(node.attrs.string)
                        .addClass('btn btn-sm btn-default');
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);

        // Display tooltip
        if (config.debug || node.attrs.help) {
            this._addButtonTooltip(node, $button);
        }
        return $button;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderHeaderButtons: function (node) {
        var self = this;
        var $buttons = $('<div>', {class: 'o_statusbar_buttons'});
        _.each(node.children, function (child) {
            if (child.tag === 'button') {
                $buttons.append(self._renderHeaderButton(child));
            }
        });
        return $buttons;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroup: function (node) {
        var self = this;
        var $result = $('<table/>', {class: 'o_group o_inner_group'});
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);

        var col = parseInt(node.attrs.col, 10) || 2;

        if (node.attrs.string) {
            var $sep = $('<tr><td colspan="' + col + '" style="width: 100%;"><div class="o_horizontal_separator">' + node.attrs.string + '</div></td></tr>');
            $result.append($sep);
        }

        var rows = [];
        var $currentRow = $('<tr/>');
        var currentColspan = 0;
        _.each(node.children, function (child) {
            if (child.tag === 'newline') {
                rows.push($currentRow);
                $currentRow = $('<tr/>');
                currentColspan = 0;
                return;
            }

            var colspan = parseInt(child.attrs.colspan, 10);
            var isLabeledField = (child.tag === 'field' && child.attrs.nolabel !== '1');
            if (!colspan) {
                if (isLabeledField) {
                    colspan = 2;
                } else {
                    colspan = 1;
                }
            }
            var finalColspan = colspan - (isLabeledField ? 1 : 0);
            currentColspan += colspan;

            if (currentColspan > col) {
                rows.push($currentRow);
                $currentRow = $('<tr/>');
                currentColspan = colspan;
            }

            var $tds;
            if (child.tag === 'field') {
                $tds = self._renderInnerGroupField(child);
            } else if (child.tag === 'label') {
                $tds = self._renderInnerGroupLabel(child);
            } else {
                $tds = $('<td/>').append(self._renderNode(child));
            }
            if (finalColspan > 1) {
                $tds.last().attr('colspan', finalColspan);
            }
            $currentRow.append($tds);
        });
        rows.push($currentRow);

        _.each(rows, function ($tr) {
            var nonLabelColSize = 100 / (col - $tr.children('.o_td_label').length);
            _.each($tr.children(':not(.o_td_label)'), function (el) {
                var $el = $(el);
                $el.css('width', ((parseInt($el.attr('colspan'), 10) || 1) * nonLabelColSize) + '%');
            });
            $result.append($tr);
        });

        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroupField: function (node) {
        var widget = this._renderFieldWidget(node, this.state);
        var $tds = $('<td/>').append(widget.$el);

        if (node.attrs.nolabel !== '1') {
            var $labelTd = this._renderInnerGroupLabel(node);
            $tds = $labelTd.add($tds);
        }

        return $tds;
    },
    /**
     * @private
     * @param {string} label
     * @returns {jQueryElement}
     */
    _renderInnerGroupLabel: function (label) {
        return $('<td/>', {class: 'o_td_label'})
            .append(this._renderTagLabel(label));
    },
    /**
     * Render a node, from the arch of the view. It is a generic method, that
     * will dispatch on specific other methods.  The rendering of a node is a
     * jQuery element (or a string), with the correct classes, attrs, and
     * content.
     *
     * For fields, it will return the $el of the field widget. Note that this
     * method is synchronous, field widgets are instantiated and appended, but
     * if they are asynchronous, they register their deferred in this.defs, and
     * the _renderView method will properly wait.
     *
     * @private
     * @param {Object} node
     * @returns {jQueryElement | string}
     */
    _renderNode: function (node) {
        var renderer = this['_renderTag' + _.str.capitalize(node.tag)];
        if (renderer) {
            return renderer.call(this, node);
        }
        if (node.tag === 'div' && node.attrs.name === 'button_box') {
            return this._renderButtonBox(node);
        }
        if (_.isString(node)) {
            return node;
        }
        return this._renderGenericTag(node);
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderStatButton: function (node) {
        var $button = $('<button>').addClass('btn btn-sm oe_stat_button');
        if (node.attrs.icon) {
            $('<div>')
                .addClass('fa fa-fw o_button_icon')
                .addClass(node.attrs.icon)
                .appendTo($button);
        }
        if (node.attrs.string) {
            $('<span>')
                .text(node.attrs.string)
                .appendTo($button);
        }
        $button.append(_.map(node.children, this._renderNode.bind(this)));
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);
        return $button;
    },
    /**
     * @private
     * @param {Object} page
     * @param {string} page_id
     * @returns {jQueryElement}
     */
    _renderTabHeader: function (page, page_id) {
        var $a = $('<a>', {
            'data-toggle': 'tab',
            disable_anchor: 'true',
            href: '#' + page_id,
            role: 'tab',
            text: page.attrs.string,
        });
        return $('<li>').append($a);
    },
    /**
     * @private
     * @param {Object} page
     * @param {string} page_id
     * @returns {jQueryElement}
     */
    _renderTabPage: function (page, page_id) {
        var $result = $('<div class="tab-pane" id="' + page_id + '">');
        $result.append(_.map(page.children, this._renderNode.bind(this)));
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagButton: function (node) {
        var $button = dom.renderButton({
            attrs: _.omit(node.attrs, 'icon', 'string'),
            icon: node.attrs.icon,
            text: (node.attrs.string || '').replace(/_/g, ''),
        });
        $button.append(_.map(node.children, this._renderNode.bind(this)));
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);

        // Display tooltip
        if (config.debug || node.attrs.help) {
            this._addButtonTooltip(node, $button);
        }

        return $button;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagField: function (node) {
        return this._renderFieldWidget(node, this.state).$el;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagForm: function (node) {
        var $result = $('<div/>');
        if (node.attrs.class) {
            $result.addClass(node.attrs.class);
        }
        $result.append(_.map(node.children, this._renderNode.bind(this)));
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagGroup: function (node) {
        var self = this;
        var isOuterGroup = _.some(node.children, function (child) {
            return child.tag === 'group';
        });
        if (!isOuterGroup) {
            return this._renderInnerGroup(node);
        }

        var $result = $('<div/>', {class: 'o_group'});
        var colSize = Math.max(1, Math.round(12 / (parseInt(node.attrs.col, 10) || 2)));
        if (node.attrs.string) {
            var $sep = $('<div/>', {class: 'o_horizontal_separator'}).text(node.attrs.string);
            $result.append($sep);
        }
        $result.append(_.map(node.children, function (child) {
            if (child.tag === 'newline') {
                return $('<br/>');
            }
            var $child = self._renderNode(child);
            $child.addClass('o_group_col_' + (colSize * (parseInt(child.attrs.colspan, 10) || 1)));
            return $child;
        }));
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagHeader: function (node) {
        var self = this;
        var $statusbar = $('<div>', {class: 'o_form_statusbar'});
        $statusbar.append(this._renderHeaderButtons(node));
        _.each(node.children, function (child) {
            if (child.tag === 'field') {
                var widget = self._renderFieldWidget(child, self.state);
                $statusbar.append(widget.$el);
            }
        });
        this._handleAttributes($statusbar, node);
        this._registerModifiers(node, this.state, $statusbar);
        return $statusbar;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagLabel: function (node) {
        var self = this;
        var text;
        var fieldName = node.tag === 'label' ? node.attrs.for : node.attrs.name;
        if ('string' in node.attrs) { // allow empty string
            text = node.attrs.string;
        } else if (fieldName) {
            text = this.state.fields[fieldName].string;
        } else  {
            return this._renderGenericTag(node);
        }
        var $result = $('<label>', {
            class: 'o_form_label',
            for: this._getIDForLabel(fieldName),
            text: text,
        });
        if (node.tag === 'label') {
            this._handleAttributes($result, node);
        }

        //<jon> 设置标题颜色
        if (node.attrs.color_options &&   node.attrs.color_options.includes('color')){

            var color_options =  eval("(" + node.attrs.color_options + ")");
            var fd = color_options.fd;
            var op = color_options.op;
            var v = color_options.v;
            var color = color_options.color;

            var eval_str = "self.state.data['" + fd +  "']" + op    + "'"  +  v + "'" ;
            var res  = eval(eval_str);
            if (res===true){
                $result.css("color", color);
            };

        };

        var modifiersOptions;
        if (fieldName) {
            modifiersOptions = {
                callback: function (element, modifiers, record) {
                    var widgets = self.allFieldWidgets[record.id];
                    var widget = _.findWhere(widgets, {name: fieldName});
                    if (!widget) {
                        return; // FIXME this occurs if the widget is created
                                // after the label (explicit <label/> tag in the
                                // arch), so this won't work on first rendering
                                // only on reevaluation
                    }
                    element.$el.toggleClass('o_form_label_empty', !!( // FIXME condition is evaluated twice (label AND widget...)
                        record.data.id
                        && (modifiers.readonly || self.mode === 'readonly')
                        && !widget.isSet()
                    ));
                },
            };
        }
        // FIXME if the function is called with a <label/> node, the registered
        // modifiers will be those on this node. Maybe the desired behavior
        // would be to merge them with associated field node if any... note:
        // this worked in 10.0 for "o_form_label_empty" reevaluation but not for
        // "o_invisible_modifier" reevaluation on labels...
        this._registerModifiers(node, this.state, $result, modifiersOptions);
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagNotebook: function (node) {
        var self = this;
        var $headers = $('<ul class="nav nav-tabs">');
        var $pages = $('<div class="tab-content nav nav-tabs">');
        var autofocusTab = -1;
        // renderedTabs is used to aggregate the generated $headers and $pages
        // alongside their node, so that their modifiers can be registered once
        // all tabs have been rendered, to ensure that the first visible tab
        // is correctly activated
        var renderedTabs = _.map(node.children, function (child, index) {
            var pageID = _.uniqueId('notebook_page_');
            var $header = self._renderTabHeader(child, pageID);
            var $page = self._renderTabPage(child, pageID);
            if (autofocusTab === -1 && child.attrs.autofocus === 'autofocus') {
                autofocusTab = index;
            }
            self._handleAttributes($header, child);
            $headers.append($header);
            $pages.append($page);
            return {
                $header: $header,
                $page: $page,
                node: child,
            };
        });
        if (renderedTabs.length) {
            var tabToFocus = renderedTabs[Math.max(0, autofocusTab)];
            tabToFocus.$header.addClass('active');
            tabToFocus.$page.addClass('active');
        }
        // register the modifiers for each tab
        _.each(renderedTabs, function (tab) {
            self._registerModifiers(tab.node, self.state, tab.$header, {
                callback: function (element, modifiers) {
                    // if the active tab is invisible, activate the first visible tab instead
                    if (modifiers.invisible && element.$el.hasClass('active')) {
                        element.$el.removeClass('active');
                        tab.$page.removeClass('active');
                        var $firstVisibleTab = $headers.find('li:not(.o_invisible_modifier):first()');
                        $firstVisibleTab.addClass('active');
                        $pages.find($firstVisibleTab.find('a').attr('href')).addClass('active');
                    }
                },
            });
        });
        var $notebook = $('<div class="o_notebook">')
                .data('name', node.attrs.name || '_default_')
                .append($headers, $pages);
        this._registerModifiers(node, this.state, $notebook);
        this._handleAttributes($notebook, node);
        return $notebook;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagSeparator: function (node) {
        var $separator = $('<div/>').addClass('o_horizontal_separator').text(node.attrs.string);
        this._handleAttributes($separator, node);
        this._registerModifiers(node, this.state, $separator);
        return $separator;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagSheet: function (node) {
        this.has_sheet = true;
        var $sheet = $('<div>').addClass('o_form_sheet');
        $sheet.append(_.map(node.children, this._renderNode.bind(this)));
        return $sheet;
    },
    /**
     * Instantiate custom widgets
     *
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagWidget: function (node) {
        return this._renderWidget(this.state, node);
    },
    /**
     * Main entry point for the rendering.  From here, we call _renderNode on
     * the root of the arch, then, when every deferred (from the field widgets)
     * are done, it will resolves itself.
     *
     * @private
     * @override method from BasicRenderer
     * @returns {Deferred}
     */
    _renderView: function () {
        var self = this;

        // render the form and evaluate the modifiers
        var defs = [];
        this.defs = defs;
        var $form = this._renderNode(this.arch).addClass(this.className);
        delete this.defs;

        return $.when.apply($, defs).then(function () {
            self._updateView($form.contents());
        }, function () {
            $form.remove();
        });
    },
    /**
     * Updates the form's $el with new content.
     *
     * @private
     * @see _renderView
     * @param {JQuery} $newContent
     */
    _updateView: function ($newContent) {
        var self = this;

        // Set the new content of the form view, and toggle classnames
        this.$el.html($newContent);
        this.$el.toggleClass('o_form_nosheet', !this.has_sheet);
        if (this.has_sheet) {
            this.$el.children().not('.oe_chatter')
                .wrapAll($('<div/>', {class: 'o_form_sheet_bg'}));
        }
        this.$el.toggleClass('o_form_editable', this.mode === 'edit');
        this.$el.toggleClass('o_form_readonly', this.mode === 'readonly');

        // Attach the tooltips on the fields' label
        _.each(this.allFieldWidgets[this.state.id], function (widget) {
            var idForLabel = self.idsForLabels[widget.name];
            // We usually don't support multiple widgets for the same field on the
            // same view but it is the case with the new settings view on V11.0.
            // Therefore, we need to retrieve the correct label since it could be
            // displayed multiple times on the view, otherwise, for example the
            // enterprise label will be displayed as many times as the field
            // exists on settings.
            var $widgets = self.$('.o_field_widget[name=' + widget.name + ']');
            var $label = idForLabel ? self.$('label[for=' + idForLabel + ']') : $();
            $label = $label.eq($widgets.index(widget.$el));
            if (config.debug || widget.attrs.help || widget.field.help) {
                self._addFieldTooltip(widget, $label);
            }
            if (widget.attrs.widget === 'upgrade_boolean') {
                // this widget needs a reference to its $label to be correctly
                // rendered
                widget.renderWithLabel($label);
            }
        });
    },
    /**
     * Sets id attribute of given widget to idForLabel
     *
     * @private
     * @param {AbstractField} widget
     * @param {idForLabel} string
     */
    _setIDForLabel: function (widget, idForLabel) {
        widget.getFocusableElement().attr('id', idForLabel);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Makes the Edit button bounce in readonly
     *
     * @private
     */
    _onClick: function () {
        if (this.mode === 'readonly') {
            this.trigger_up('bounce_edit');
        }
    },
    /**
     * @override
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        ev.stopPropagation();

        var index;
        if (ev.data.direction === "next") {
            index = this.allFieldWidgets[this.state.id].indexOf(ev.data.target);
            this._activateNextFieldWidget(this.state, index);
        } else if (ev.data.direction === "previous") {
            index = this.allFieldWidgets[this.state.id].indexOf(ev.data.target);
            this._activatePreviousFieldWidget(this.state, index);
        }
    },
    /**
     * open the translation view for the current field
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onTranslate: function (event) {
        event.preventDefault();
        this.trigger_up('translate', {fieldName: event.target.name, id: this.state.id});
    },
});

return FormRenderer;
});
