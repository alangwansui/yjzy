odoo.define('web_grid.GridController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var core = require('web.core');
var dialogs = require('web.view_dialogs');
var utils = require('web.utils');

var qweb = core.qweb;
var _t = core._t;

var GridController = AbstractController.extend({
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        'cell_edited': '_onCellEdited',
    }),
    events: {
        'click .o_grid_cell_information': '_onClickCellInformation',
        'focus .o_grid_input': '_onGridInputFocus',
    },

    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.set('title', params.title);
        this.context = params.context;
        this.navigationButtons = params.navigationButtons;
        this.ranges = params.ranges;
        this.currentRange = params.currentRange;
        this.formViewID = params.formViewID;
        this.listViewID = params.listViewID;
        this.adjustment = params.adjustment;
        this.adjustName = params.adjustName;
        this.canCreate = params.activeActions.create;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('grid.GridArrows', { widget: {
            _ranges: this.ranges,
            _buttons: this.navigationButtons,
            allowCreate: this.canCreate,
        }}));
        this.$buttons.appendTo($node);
        this._updateButtons();
        this.$buttons.on('click', '.o_grid_button_add', this._onAddLine.bind(this));
        this.$buttons.on('click', '.grid_arrow_previous', this._onPaginationChange.bind(this, 'prev'));
        this.$buttons.on('click', '.grid_button_initial', this._onPaginationChange.bind(this, 'initial'));
        this.$buttons.on('click', '.grid_arrow_next', this._onPaginationChange.bind(this, 'next'));
        this.$buttons.on('click', '.grid_arrow_range', this._onRangeChange.bind(this));
        this.$buttons.on('click', '.grid_arrow_button', this._onButtonClicked.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} cell
     * @param {number} newValue
     */
    _adjust: function (cell, newValue) {
        var difference = newValue - cell.value;
        // 1e-6 is probably an overkill, but that way milli-values are usable
        if (Math.abs(difference) < 1e-6) {
            // cell value was set to itself, don't hit the server
            return;
        }
        // convert row values to a domain, concat to action domain
        var state = this.model.get();
        var domain = this.model.domain.concat(cell.row.domain);

        var actionData = {
            type: this.adjustment,
            name: this.adjustName,
            args: JSON.stringify([ // args for type=object
                domain,
                state.colField,
                cell.col.values[state.colField][0],
                state.cellField,
                difference
            ]),
            context: this.model.getContext({
                grid_adjust: { // context for type=action
                    row_domain: domain,
                    column_field: state.colField,
                    column_value: cell.col.values[state.colField][0],
                    cell_field: state.cellField,
                    change: difference,
                },
            }),
        };
        this.trigger_up('execute_action', {
            action_data: actionData,
            env: {
                context: this.model.getContext(),
                model: this.modelName
            },
            on_success: this.reload.bind(this),
        });
    },
    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _update: function () {
        return this._super.apply(this, arguments)
            .then(this._updateButtons.bind(this));
    },
    /**
     * @private
     */
    _updateButtons: function () {
        if (this.$buttons) {
            var state = this.model.get();
            this.$buttons.find('.grid_arrow_previous').toggleClass('hidden', !state.prev);
            this.$buttons.find('.grid_arrow_next').toggleClass('hidden', !state.next);
            this.$buttons.find('.grid_button_initial').toggleClass('hidden', !state.initial);
            this.$buttons.find('.grid_arrow_range[data-name=' + this.currentRange + ']')
                    .addClass('active')
                    .siblings().removeClass('active');
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAddLine: function (event) {
        event.preventDefault();

        var context = this.model.getContext();
        var formContext = _.extend({}, context, {view_grid_add_line: true});
        // TODO: document quick_create_view (?) context key
        var formViewID = context.quick_create_view || this.formViewID || false;
        new dialogs.FormViewDialog(this, {
            res_model: this.modelName,
            res_id: false,
            context: formContext,
            view_id: formViewID,
            title: _t("Add a Line"),
            disable_multiple_selection: true,
            on_saved: this.reload.bind(this, {}),
        }).open();
    },
    /**
     * @private
     * @param {OdooEvent} e
     */
    _onCellEdited: function (event) {
        var state = this.model.get();
        this._adjust({
            row: utils.into(state, event.data.row_path),
            col: utils.into(state, event.data.col_path),
            value: utils.into(state, event.data.cell_path).value,
        }, event.data.value);
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onButtonClicked: function (e) {
        var self = this;
        e.stopPropagation();
        // TODO: maybe allow opting out of getting ids?
        var button = this.navigationButtons[$(e.target).attr('data-index')];
        var actionData = _.extend(button, {
            context: this.model.getContext(button.context),
        });
        this.model.getIds().then(function (ids) {
            self.trigger_up('execute_action', {
                action_data: actionData,
                env: {
                    context: self.model.getContext(),
                    model: self.modelName,
                    resIDs: ids,
                },
                on_closed: self.reload.bind(self),
            });
        });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onClickCellInformation: function (e) {
        var $target = $(e.target);
        var cell_path = $target.parent().attr('data-path').split('.');
        var row_path = cell_path.slice(0, -3).concat(['rows'], cell_path.slice(-2, -1));
        var state = this.model.get();
        var cell = utils.into(state, cell_path);
        var row = utils.into(state, row_path);

        var groupFields = state.groupBy.slice(_.isArray(state) ? 1 : 0);
        var label = _.map(groupFields, function (g) {
            return row.values[g][1] || _t('Undefined');
        }).join(': ');

        this.do_action({
            type: 'ir.actions.act_window',
            name: label,
            res_model: this.modelName,
            views: [
                [this.listViewID, 'list'],
                [this.formViewID, 'form']
            ],
            domain: cell.domain,
            context: this.context,
        });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onGridInputFocus: function (e) {
        var selection = window.getSelection();
        var range = document.createRange();
        range.selectNodeContents(e.target);
        selection.removeAllRanges();
        selection.addRange(range);
    },
    /**
     * @private
     * @param {string} dir either 'prev', 'initial' or 'next
     */
    _onPaginationChange: function (dir) {
        var state = this.model.get();
        this.update({pagination: state[dir]});
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onRangeChange: function (e) {
        e.stopPropagation();
        var $target = $(e.target);
        if ($target.hasClass('active')) {
            return;
        }
        this.currentRange = $target.attr('data-name');
        this.update({range: this.currentRange});
    },
});

return GridController;

});
