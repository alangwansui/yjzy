odoo.define('sale_subscription_dashboard.dashboard', function (require) {
'use strict';

var ajax = require('web.ajax');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var datepicker = require('web.datepicker');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var session = require('web.session');
var utils = require('web.utils');
var web_client = require('web.web_client');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

/*

ABOUT

In this module, you'll find two main widgets : one that represents the Revenue KPIs dashboard
and one that represents the salesman dashboard.

In both of them, there are two steps of rendering : one that renders the main template that leaves
empty sections for the rendering of the second step. This second step can take some time to be rendered
because of the calculation and is then rendered separately.

*/

// Abstract widget with common methods
var sale_subscription_dashboard_abstract = Widget.extend(ControlPanelMixin, {
    cssLibs: [
        '/web/static/lib/nvd3/nv.d3.css'
    ],
    jsLibs: [
        '/web/static/lib/nvd3/d3.v3.js',
        '/web/static/lib/nvd3/nv.d3.js',
        '/web/static/src/js/libs/nvd3.js'
    ],

    /**
     * Loads the libraries listed in this.jsLibs and this.cssLibs
     *
     * @override
     */
    willStart: function () {
        return $.when(ajax.loadLibs(this), this._super.apply(this, arguments));
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            self.render_dashboard();
        });
    },

    on_reverse_breadcrumb: function() {
        this.update_cp();
        web_client.do_push_state({action: this.main_dashboard_action_id});
    },

    load_action: function(view_xmlid, options) {
        var self = this;
        options.on_reverse_breadcrumb = this.on_reverse_breadcrumb;
        return this.do_action(view_xmlid, options).then(function() {
            // This detailed dashboard can only be loaded from the main dashboard.
            // If the user refreshs the page or uses an URL and is direclty redirected to this page,
            // we redirect him to the main dashboard to avoid any error.
            if (options.push_main_state && self.main_dashboard_action_id){
                web_client.do_push_state({action: self.main_dashboard_action_id});
            }
        });
    },

    on_update_options: function() {
        this.start_date = this.start_picker.getValue() || '0001-02-01';
        this.end_date = this.end_picker.getValue()  || '9999-12-31';
        this.filters.template_ids = this.get_filtered_template_ids();
        this.filters.tag_ids = this.get_filtered_tag_ids();

        var company_ids = this.get_filtered_company_ids();

        if (!company_ids || !company_ids.length) {
            Dialog.alert(this, _t('Select at least one company.'), {
                title: _t('Warning'),
            });
            return;
        }

        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/companies_check', 'call', {
            'company_ids': company_ids,
        }).done(function (response) {
            if (response.result === true) {
                self.currency_id = response.currency_id;
                self.filters.company_ids = company_ids;
                self.$el.empty();
                self.render_dashboard();
            } else {
                Dialog.alert(self, response.error_message, {
                    title: _t('Warning'),
                });
            }
        });
    },

    get_filtered_template_ids: function() {
        var $contract_inputs = this.$searchview_buttons.find(".selected > .o_contract_template_filter");
        return _.map($contract_inputs, function(el) { return $(el).data('id'); });
    },

    get_filtered_tag_ids: function() {
        var $tag_inputs = this.$searchview_buttons.find(".selected > .o_tags_filter");
        return _.map($tag_inputs, function(el) { return $(el).data('id'); });
    },

    get_filtered_company_ids: function() {
        if (this.companies && this.companies.length === 1) {
            return [this.companies[0].id];
        } else {
            var $company_inputs = this.$searchview_buttons.find(".selected > .o_companies_filter");
            return _.map($company_inputs, function(el) { return $(el).data('id'); });
        }
    },

    render_filters: function() {
        this.$searchview_buttons = $();
        if(this.contract_templates.length || this.companies.length || this.tags.length) {
            this.$searchview_buttons = $(QWeb.render("sale_subscription_dashboard.dashboard_option_filters", {widget: this}));
        }
        this.$searchview_buttons.on('click', '.js_tag', function(e) {
            e.preventDefault();
            $(e.target).parent().toggleClass('selected');
        });

        // Check the boxes if it was already checked before the update
        var self = this;
        _.each(this.filters.template_ids, function(id) {
            self.$searchview_buttons.find('.o_contract_template_filter[data-id=' + id + ']').parent().addClass('selected');
        });
        _.each(this.filters.tag_ids, function(id) {
            self.$searchview_buttons.find('.o_tags_filter[data-id=' + id + ']').parent().addClass('selected');
        });
        _.each(this.filters.company_ids, function(id) {
            self.$searchview_buttons.find('.o_companies_filter[data-id=' + id + ']').parent().addClass('selected');
        });
    },

    update_cp: function() {
        var self = this;

        var def;
        if(!this.$searchview) {
            this.$searchview = $(QWeb.render("sale_subscription_dashboard.dashboard_option_pickers"));
            this.$searchview.on('click', '.o_update_options', this.on_update_options);
            def = this.set_up_datetimepickers();
            this.render_filters();
        }

        $.when(def).then(function() {
            self.update_control_panel({
                cp_content: {
                    $searchview: self.$searchview,
                    $searchview_buttons: self.$searchview_buttons,
                },
                breadcrumbs: self.getParent().get_breadcrumbs(),
            });
        });
    },

    set_up_datetimepickers: function() {
        var $sep = this.$searchview.find('.o_datepicker_separator');

        this.start_picker = new datepicker.DateWidget(this, {viewMode: 'years'});
        this.end_picker = new datepicker.DateWidget(this, {viewMode: 'years'});
        var def1 = this.start_picker.insertBefore($sep);
        var def2 = this.end_picker.insertAfter($sep);

        var self = this;
        return $.when(def1, def2).then(function() {
            self.start_picker.on('datetime_changed', self, function() {
                if (this.start_picker.getValue()) {
                    this.end_picker.picker.minDate(moment(this.start_picker.getValue()));
                }
            });
            self.end_picker.on('datetime_changed', self, function() {
                if (this.end_picker.getValue()) {
                    this.start_picker.picker.maxDate(moment(this.end_picker.getValue()));
                }
            });

            self.start_picker.setValue(moment(self.start_date));
            self.end_picker.setValue(moment(self.end_date));
        });
    },

    render_dashboard: function() {}, // Abstract

    format_number: function(value, symbol) {
        value = utils.human_number(value);
        if (symbol === 'currency') {
            return render_monetary_field(value, this.currency_id);
        } else {
            return value + symbol;
        }
    },
});

// 1. Main dashboard
var sale_subscription_dashboard_main = sale_subscription_dashboard_abstract.extend({
    events: {
        'click .on_stat_box': 'on_stat_box',
        'click .on_forecast_box': 'on_forecast_box',
        'click .on_demo_contracts': 'on_demo_contracts',
        'click .on_demo_templates': 'on_demo_templates',
    },

    init: function(parent, context) {
        this._super(parent);

        this.main_dashboard_action_id = context.id;
        this.start_date = moment().subtract(1, 'M');
        this.end_date = moment();

        this.filters = {
            template_ids: [],
            tag_ids: [],
            company_ids: [session.company_id],
        };

        this.defs = [];
        this.unresolved_defs_vals = [];
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return $.when(self.fetch_data());
        });
    },

    on_reverse_breadcrumb: function() {
        this._super();

        var self = this;
        if(this.$main_dashboard) {
            this.defs = [];

            // If there is unresolved defs, we need to replace the uncompleted boxes
            if (this.unresolved_defs_vals.length){
                var stat_boxes = this.$main_dashboard.find('.o_stat_box');
                _.each(this.unresolved_defs_vals, function(v){
                    self.defs.push(new SaleSubscriptionDashboardStatBox(
                        self,
                        self.start_date,
                        self.end_date,
                        self.filters,
                        self.currency_id,
                        self.stat_types,
                        stat_boxes[v].getAttribute("name"),
                        stat_boxes[v].getAttribute("code"),
                        self.has_mrr
                    ).replace($(stat_boxes[v])));
                });
            }
        } else {
            this.render_dashboard();
        }
    },

    fetch_data: function() {
        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/fetch_data', 'call', {
        }).done(function (result) {
            self.stat_types = result.stat_types;
            self.forecast_stat_types = result.forecast_stat_types;
            self.currency_id = result.currency_id;
            self.contract_templates = result.contract_templates;
            self.tags = result.tags;
            self.companies = result.companies;
            self.has_mrr = result.has_mrr;
            self.has_def_revenues = result.has_def_revenues;
            self.has_template = result.has_template;
        });
    },

    render_dashboard: function() {
        this.$main_dashboard = $(QWeb.render("sale_subscription_dashboard.dashboard", {
            has_mrr: this.has_mrr,
            has_template: this.has_template,
            has_def_revenues: this.has_def_revenues,
            stat_types: _.sortBy(_.values(this.stat_types), 'prior'),
            forecast_stat_types:  _.sortBy(_.values(this.forecast_stat_types), 'prior'),
            start_date: this.start_date,
            end_date: this.end_date,
        }));
        this.$el.append(this.$main_dashboard);

        var stat_boxes = this.$main_dashboard.find('.o_stat_box');
        var forecast_boxes = this.$main_dashboard.find('.o_forecast_box');

        for (var i=0; i < stat_boxes.length; i++) {
            this.defs.push(new SaleSubscriptionDashboardStatBox(
                this,
                this.start_date,
                this.end_date,
                this.filters,
                this.currency_id,
                this.stat_types,
                stat_boxes[i].getAttribute("name"),
                stat_boxes[i].getAttribute("code"),
                this.has_mrr
            ).replace($(stat_boxes[i])));
        }

        for (var j=0; j < forecast_boxes.length; j++) {
            new SaleSubscriptionDashboardForecastBox(
                this,
                this.end_date,
                this.filters,
                this.forecast_stat_types,
                forecast_boxes[j].getAttribute("name"),
                forecast_boxes[j].getAttribute("code"),
                this.currency_id,
                this.has_mrr
            ).replace($(forecast_boxes[j]));
        }

        this.update_cp();
    },

    store_unresolved_defs: function() {
        this.unresolved_defs_vals = [];
        var self = this;
        _.each(this.defs, function(v, k){
            if (v && v.state() !== "resolved"){
                self.unresolved_defs_vals.push(k);
            }
        });
    },

    on_stat_box: function(ev) {
        ev.preventDefault();
        this.selected_stat = $(ev.currentTarget).attr('data-stat');

        this.store_unresolved_defs();

        var options = {
            'stat_types': this.stat_types,
            'selected_stat': this.selected_stat,
            'start_date': this.start_date,
            'end_date': this.end_date,
            'contract_templates': this.contract_templates,
            'tags': this.tags,
            'companies': this.companies,
            'filters': this.filters,
            'currency_id': this.currency_id,
            'push_main_state': true,
        };
        this.load_action("sale_subscription_dashboard.action_subscription_dashboard_report_detailed", options);
    },

    on_forecast_box: function(ev) {
        ev.preventDefault();

        var options = {
            'forecast_types': this.forecast_types,
            'start_date': this.start_date,
            'end_date': this.end_date,
            'contract_templates': this.contract_templates,
            'tags': this.tags,
            'companies': this.companies,
            'filters': this.filters,
            'currency_id': this.currency_id,
            'push_main_state': true,
        };
        this.load_action("sale_subscription_dashboard.action_subscription_dashboard_report_forecast", options);
    },

    on_demo_contracts: function(ev) {
        ev.preventDefault();
        this.load_action("sale_subscription.sale_subscription_action", {});
    },

    on_demo_templates: function(ev) {
        ev.preventDefault();
        this.load_action("sale_subscription.sale_subscription_template_action", {});
    },
});


// 2. Detailed dashboard
var sale_subscription_dashboard_detailed = sale_subscription_dashboard_abstract.extend({
    events: {
        'click .o_detailed_analysis': 'on_detailed_analysis',
    },

    init: function(parent, context, options) {
        this._super(parent);

        this.main_dashboard_action_id = options.main_dashboard_action_id;
        this.stat_types = options.stat_types;
        this.start_date = options.start_date;
        this.end_date = options.end_date;
        this.selected_stat = options.selected_stat;
        this.contract_templates = options.contract_templates;
        this.tags = options.tags;
        this.companies = options.companies;
        this.filters = options.filters;
        this.currency_id = options.currency_id;

        this.display_stats_by_plan = !_.contains(['nrr', 'arpu', 'logo_churn'], this.selected_stat);
        this.report_name = this.stat_types[this.selected_stat].name;
    },

    fetch_computed_stat: function() {

        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/compute_stat', 'call', {
            'stat_type': this.selected_stat,
            'start_date': this.start_date.format('YYYY-MM-DD'),
            'end_date': this.end_date.format('YYYY-MM-DD'),
            'filters': this.filters,
        }).done(function (result) {
            self.value = result;
        });
    },

    render_dashboard: function() {

        var self = this;
        $.when(
            this.fetch_computed_stat()
        ).done(function(){

            self.$el.append(QWeb.render("sale_subscription_dashboard.detailed_dashboard", {
                selected_stat_values: _.findWhere(self.stat_types, {code: self.selected_stat}),
                start_date: self.start_date,
                end_date: self.end_date,
                stat_type: self.selected_stat,
                currency_id: self.currency_id,
                report_name: self.report_name,
                value: self.value,
                display_stats_by_plan: self.display_stats_by_plan,
                format_number: self.format_number,
            }));

            self.render_detailed_dashboard_stats_history();
            self.render_detailed_dashboard_graph();

            if (self.selected_stat === 'mrr') {
                self.render_detailed_dashboard_mrr_growth();
            }

            if (self.display_stats_by_plan){
                self.render_detailed_dashboard_stats_by_plan();
            }

            self.update_cp();
        });
    },

    render_detailed_dashboard_stats_history: function() {

        var self = this;
        ajax.jsonRpc('/sale_subscription_dashboard/get_stats_history', 'call', {
            'stat_type': this.selected_stat,
            'start_date': this.start_date.format('YYYY-MM-DD'),
            'end_date': this.end_date.format('YYYY-MM-DD'),
            'filters': this.filters,
        }).done(function (result) {
            // Rounding of result
            _.map(result, function(v, k, dict) {dict[k] = Math.round(v * 100) / 100;});
            var html = QWeb.render('sale_subscription_dashboard.stats_history', {
                stats_history: result,
                stat_type: self.selected_stat,
                stat_types: self.stat_types,
                currency_id: self.currency_id,
                rate: self.compute_rate,
                get_color_class: get_color_class,
                value: Math.round(self.value * 100) / 100,
                format_number: self.format_number,
            });
            self.$('#o-stat-history-box').empty();
            self.$('#o-stat-history-box').append(html);
        });
        addLoader(this.$('#o-stat-history-box'));
    },

    render_detailed_dashboard_stats_by_plan: function() {
        var self = this;
        ajax.jsonRpc('/sale_subscription_dashboard/get_stats_by_plan', 'call', {
            'stat_type': this.selected_stat,
            'start_date': this.start_date.format('YYYY-MM-DD'),
            'end_date': this.end_date.format('YYYY-MM-DD'),
            'filters': this.filters,
        }).done(function (result) {
            var html = QWeb.render('sale_subscription_dashboard.stats_by_plan', {
                stats_by_plan: result,
                stat_type: self.selected_stat,
                stat_types: self.stat_types,
                currency_id: self.currency_id,
                value: self.value,
                format_number: self.format_number,
            });
            self.$('.o_stats_by_plan').replaceWith(html);
        });
        addLoader(this.$('.o_stats_by_plan'));
    },

    compute_rate: function(old_value, new_value) {
        return old_value === 0 ? 0 : parseInt(100.0 * (new_value-old_value) / old_value);
    },

    render_detailed_dashboard_graph: function() {

        addLoader(this.$('#stat_chart_div'));

        var self = this;
        ajax.jsonRpc('/sale_subscription_dashboard/compute_graph', 'call', {
            'stat_type': this.selected_stat,
            'start_date': this.start_date.format('YYYY-MM-DD'),
            'end_date': this.end_date.format('YYYY-MM-DD'),
            'points_limit': 0,
            'filters': this.filters,
        }).done(function(result){
            load_chart('#stat_chart_div', self.stat_types[self.selected_stat].name, result, true);
            self.$('#stat_chart_div div.o_loader').hide();
        });
    },

    render_detailed_dashboard_mrr_growth: function() {

        addLoader(this.$('#mrr_growth_chart_div'));
        var self = this;

        ajax.jsonRpc('/sale_subscription_dashboard/compute_graph_mrr_growth', 'call', {
            'start_date' : this.start_date.format('YYYY-MM-DD'),
            'end_date': this.end_date.format('YYYY-MM-DD'),
	    'points_limit': 30,
            'filters': this.filters,
        }).done(function(result){
            self.load_chart_mrr_growth_stat('#mrr_growth_chart_div', result);
            self.$('#mrr_growth_chart_div div.o_loader').hide();
        });
    },

    on_detailed_analysis: function() {

        var additional_context = {};
        var view_xmlid = '';

        // To get the same numbers as in the dashboard, we need to give the filters to the backend
        if (this.selected_stat === 'mrr') {
            additional_context = {
                'search_default_asset_end_date': moment(this.end_date).toDate(),
                'search_default_asset_start_date': moment(this.end_date).toDate(),
                // TODO: add contract_ids as another filter
            };
            view_xmlid = "sale_subscription_dashboard.action_invoice_line_entries_report";
        }
        else if (this.selected_stat === 'nrr' || this.selected_stat  === 'net_revenue') {
            // TODO: add filters
            additional_context = {};
            view_xmlid = "account.action_account_invoice_report_all";
        }

        this.load_action(view_xmlid, {additional_context: additional_context});
    },

    load_chart_mrr_growth_stat: function(div_to_display, result) {
        var data_chart = [
            {
                values: result.new_mrr,
                key: _t('New MRR'),
                color: '#26b548',
            },
            {
                values: result.churned_mrr,
                key: _t('Churned MRR'),
                color: '#df2e28',
            },
            {
                values: result.expansion_mrr,
                key: _t('Expansion MRR'),
                color: '#fed049',
            },
            {
                values: result.down_mrr,
                key: _t('Down MRR'),
                color: '#ffa500',
            },
            {
                values: result.net_new_mrr,
                key: _t('Net New MRR'),
                color: '#2693d5',
            }
        ];

        nv.addGraph(function() {
            var chart = nv.models.lineChart()
                .interpolate("monotone")
                .x(function(d) { return getDate(d); })
                .y(function(d) { return getValue(d); })
                .margin({left: 100})
                .useInteractiveGuideline(true)
                .duration(350)
                .showLegend(true)
                .showYAxis(true)
                .showXAxis(true);

            var tick_values = getPrunedTickValues(data_chart[0].values, 10);

            chart.xAxis
                .tickFormat(function(d) { return d3.time.format("%m/%d/%y")(new Date(d)); })
                .tickValues(_.map(tick_values, function(d) {return getDate(d); }))
                .rotateLabels(-30);

            chart.yAxis
                .axisLabel('MRR')
                .tickFormat(function(d) { return field_utils.format.float(d);});

            var svg = d3.select(div_to_display)
                .append("svg")
                .attr("height", '20em');
            svg
                .datum(data_chart)
                .call(chart);
            nv.utils.windowResize(chart.update);
            return chart;

        });
    },
});

// 3. Forecast dashboard
var sale_subscription_dashboard_forecast = sale_subscription_dashboard_abstract.extend({
    events: {
        'change .o_forecast_input': 'on_forecast_input',
        'change input.growth_type': 'on_growth_type_change',
    },

    init: function(parent, context, options) {
        this._super(parent);

        this.main_dashboard_action_id = options.main_dashboard_action_id;
        this.start_date = options.start_date;
        this.end_date = options.end_date;
        this.contract_templates = options.contract_templates;
        this.tags = options.tags;
        this.companies = options.companies;
        this.filters = options.filters;
        this.currency_id = options.currency_id;

        this.values = {};
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return $.when(
                self.fetch_default_values_forecast('mrr'),
                self.fetch_default_values_forecast('contracts')
            );
        });
    },

    render_dashboard: function() {
        this.$el.append(QWeb.render("sale_subscription_dashboard.forecast", {
            start_date: this.start_date,
            end_date: this.end_date,
            values: this.values,
            currency_id: this.currency_id,
            get_currency: this.get_currency,
        }));

        this.values.mrr.growth_type = 'linear';
        this.values.contracts.growth_type = 'linear';
        this.reload_chart('mrr');
        this.reload_chart('contracts');

        this.update_cp();
    },

    on_forecast_input: function(ev) {
        var forecast_type = $(ev.target).data().forecast;
        var data_type = $(ev.target).data().type;
        this.values[forecast_type][data_type] = parseInt($(ev.target).val());
        this.reload_chart(forecast_type);
    },

    on_growth_type_change: function(ev) {
        var forecast_type = $(ev.target).data().type;

        this.values[forecast_type].growth_type = this.$("input:radio[name=growth_type_"+forecast_type+"]:checked").val();
        if (this.values[forecast_type].growth_type === 'linear') {
            this.$('#linear_growth_' + forecast_type).show();
            this.$('#expon_growth_' + forecast_type).hide();
        }
        else {
            this.$('#linear_growth_' + forecast_type).hide();
            this.$('#expon_growth_' + forecast_type).show();
        }
        this.reload_chart(forecast_type);
    },

    fetch_default_values_forecast: function(forecast_type) {
        addLoader(this.$('#forecast_chart_div_mrr, #forecast_chart_div_contracts'));

        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/get_default_values_forecast', 'call', {
            'forecast_type': forecast_type,
            'end_date': moment().format('YYYY-MM-DD'),
            'filters': this.filters,
        }).done(function(result){
            self.values[forecast_type] = result;
        });
    },

    reload_chart: function(chart_type) {
        var computed_values = compute_forecast_values(
            this.values[chart_type].starting_value,
            this.values[chart_type].projection_time,
            this.values[chart_type].growth_type,
            this.values[chart_type].churn,
            this.values[chart_type].linear_growth,
            this.values[chart_type].expon_growth
        );
        this.load_chart_forecast('#forecast_chart_div_' + chart_type, computed_values);

        var content = QWeb.render('sale_subscription_dashboard.forecast_summary_' + chart_type, {
            values: this.values[chart_type],
            computed_value: parseInt(computed_values[computed_values.length - 1][1]),
            currency_id: this.currency_id,
            format_number: this.format_number,
        });

        this.$('#forecast_summary_' + chart_type).replaceWith(content);
    },

    get_currency: function() {
        var currency = session.get_currency(this.currency_id);
        return currency.symbol;
    },

    format_number: function(value) {
        value = utils.human_number(value);
        return render_monetary_field(value, this.currency_id);
    },

    load_chart_forecast: function(div_to_display, values) {
        this.$(div_to_display).empty();

        var data_chart = [
        {
            values: values,
            color: '#2693d5',
            area: true
        },
        ];
        nv.addGraph(function() {
            var chart = nv.models.lineChart()
                .interpolate("monotone")
                .x(function(d) { return getDate(d); })
                .y(function(d) { return getValue(d); })
                .forceY([0]);
            chart
                .margin({left: 100})
                .useInteractiveGuideline(true)
                .duration(350)
                .showLegend(false)
                .showYAxis(true)
                .showXAxis(true);

            var tick_values = getPrunedTickValues(data_chart[0].values, 10);

            chart.xAxis
                .tickFormat(function(d) { return d3.time.format("%m/%d/%y")(new Date(d)); })
                .tickValues(_.map(tick_values, function(d) { return getDate(d); }))
                .rotateLabels(-30);

            chart.yAxis
                .tickFormat(function(d) { return field_utils.format.float(d);});

            var svg = d3.select(div_to_display)
                .append("svg");

            svg.attr("height", '20em');

            svg
                .datum(data_chart)
                .call(chart);
            nv.utils.windowResize(chart.update);
            return chart;
        });
    },

    update_cp: function() { // Redefinition to not show anything in controlpanel for forecast dashboard
        this.update_control_panel({
            breadcrumbs: this.getParent().get_breadcrumbs(),
        });
    },
});

// These are two smalls widgets to display all the stat boxes in the main dashboard
var SaleSubscriptionDashboardStatBox = Widget.extend({
    template: 'sale_subscription_dashboard.stat_box_content',

    init: function(parent, start_date, end_date, filters, currency_id, stat_types, box_name, stat_type, has_mrr) {
        this._super(parent);

        this.start_date = start_date;
        this.end_date = end_date;

        this.filters = filters;
        this.currency_id = currency_id;
        this.stat_types = stat_types;
        this.box_name = box_name;
        this.stat_type = stat_type;
        this.has_mrr = has_mrr;

        this.chart_div_id = 'chart_div_' + this.stat_type;
        this.added_symbol = this.stat_types[this.stat_type].add_symbol;
        this.is_monetary = this.added_symbol === 'currency';
        this.render_monetary_field = render_monetary_field;

        this.demo_values = {
            'mrr': 1000,
            'net_revenue': 55000,
            'nrr': 27000,
            'arpu': 20,
            'arr': 12000,
            'ltv': 120,
            'logo_churn': 7,
            'revenue_churn': 5,
            'nb_contracts': 50,
        };
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return $.when(self.compute_graph());
        });
    },

    start: function() {
        var self = this;
        var display_tooltip = '<b>' + this.box_name + '</b><br/>' + _t('Current Value: ') + this.value;
        this.$el.tooltip({title: display_tooltip, trigger: 'hover'});
        return this._super().then(function() {
            load_chart('#'+self.chart_div_id, false, self.computed_graph, false, !self.has_mrr);
        });
    },

    compute_graph: function() {
        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/compute_graph_and_stats', 'call', {
            'stat_type': this.stat_type,
            'start_date' : this.start_date.format('YYYY-MM-DD'),
            'end_date': this.end_date.format('YYYY-MM-DD'),
            'points_limit': 30,
            'filters': this.filters,
        }).done(function(result){
            self.value = result.stats.value_2;
            self.perc = result.stats.perc;
            self.color = get_color_class(result.stats.perc, self.stat_types[self.stat_type].dir);
            self.computed_graph = result.graph;
        });
    },

    format_number: function(value) {
        value = utils.human_number(value);
        if (this.is_monetary) {
            return render_monetary_field(value, this.currency_id);
        } else {
            return value + this.added_symbol;
        }
    },
});

var SaleSubscriptionDashboardForecastBox = Widget.extend({
    template: 'sale_subscription_dashboard.forecast_stat_box_content',

    init: function(parent, end_date, filters, forecast_stat_types, box_name, stat_type, currency_id, has_mrr) {
        this._super(parent);
        this.end_date = end_date;
        this.filters = filters;

        this.currency_id = currency_id;
        this.forecast_stat_types = forecast_stat_types;
        this.box_name = box_name;
        this.stat_type = stat_type;
        this.has_mrr = has_mrr;

        this.added_symbol = this.forecast_stat_types[this.stat_type].add_symbol;
        this.is_monetary = this.added_symbol === 'currency';
        this.chart_div_id = 'chart_div_' + this.stat_type;
        this.render_monetary_field = render_monetary_field;

        this.demo_values = {
            'mrr_forecast': 12000,
            'contracts_forecast': 240,
        };
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return $.when(
                self.compute_numbers()
            );
        });
    },

    start: function() {
        var self = this;
        var display_tooltip = '<b>' + this.box_name + '</b><br/>' + _t('Current Value: ') + this.value;
        this.$el.tooltip({title: display_tooltip, trigger: 'hover'});
        return this._super().then(function() {
            load_chart('#'+self.chart_div_id, false, self.computed_graph, false, !self.has_mrr);
        });
    },

    compute_numbers: function() {

        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/get_default_values_forecast', 'call', {
            'forecast_type': this.stat_type,
            'end_date': this.end_date.format('YYYY-MM-DD'),
            'filters': this.filters,
        }).done(function(result){
            self.computed_graph = compute_forecast_values(
                result.starting_value,
                result.projection_time,
                'linear',
                result.churn,
                result.linear_growth,
                0
            );
            self.value = self.computed_graph[self.computed_graph.length - 1][1];
        });
    },

    format_number: function(value) {
        value = utils.human_number(value);
        if (this.is_monetary) {
            return render_monetary_field(value, this.currency_id);
        } else {
            return value + this.added_symbol;
        }
    },
});

var sale_subscription_dashboard_salesman = sale_subscription_dashboard_abstract.extend({

    init: function() {
        this._super.apply(this, arguments);
        this.start_date = moment().startOf('month');
        this.end_date = moment().endOf('month');
    },

    willStart: function() {
        return $.when(
            this._super.apply(this, arguments),
            this.fetch_salesmen()
        );
    },

    fetch_salesmen: function() {
        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/fetch_salesmen', 'call', {
        }).then(function (result) {
            self.salesman_ids = result.salesman_ids;
            self.salesman = result.default_salesman || {};
            self.currency_id = result.currency_id;
        });
    },

    render_dashboard: function() {
        this.$el.empty().append(QWeb.render("sale_subscription_dashboard.salesman", {
            salesman_ids: this.salesman_ids,
            salesman: this.salesman,
            start_date: this.start_date,
            end_date: this.end_date,
        }));

        this.update_cp();

        if (!jQuery.isEmptyObject(this.salesman)) {
            this.render_dashboard_additionnal();
        }
    },

    render_dashboard_additionnal: function() {
        var self = this;
        addLoader(this.$('#mrr_growth_salesman'));

        ajax.jsonRpc('/sale_subscription_dashboard/get_values_salesman', 'call', {
            'start_date': this.start_date.format('YYYY-MM-DD'),
            'end_date': this.end_date.format('YYYY-MM-DD'),
            'salesman_id': this.salesman.id,
        }).done(function(result){
            load_chart_mrr_salesman('#mrr_growth_salesman', result);
            self.$('#mrr_growth_salesman div.o_loader').hide();

            // 1. Subscriptions modifcations
            var ICON_BY_TYPE = {
                'churn': 'o_red fa fa-remove',
                'new': 'o_green fa fa-plus',
                'down': 'o_red fa fa-arrow-down',
                'up': 'o_green fa fa-arrow-up',
            };

            _.each(result.contract_modifications, function(v) {
                v.class_type = ICON_BY_TYPE[v.type];
            });

            var html_modifications = QWeb.render('sale_subscription_dashboard.contract_modifications', {
                modifications: result.contract_modifications,
                get_color_class: get_color_class,
                currency_id: self.currency_id,
                format_number: self.format_number,
            });
            self.$('#contract_modifications').append(html_modifications);

            // 2. NRR invoices
            var html_nrr_invoices = QWeb.render('sale_subscription_dashboard.nrr_invoices', {
                invoices: result.nrr_invoices,
                currency_id: self.currency_id,
                format_number: self.format_number,
            });
            self.$('#NRR_invoices').append(html_nrr_invoices);

            // 3. Summary
            var html_summary = QWeb.render('sale_subscription_dashboard.salesman_summary', {
                mrr: result.net_new,
                nrr: result.nrr,
                currency_id: self.currency_id,
                format_number: self.format_number,
            });
            self.$('#mrr_growth_salesman').before(html_summary);
        });

        function load_chart_mrr_salesman(div_to_display, result) {
            var data_chart = [{
                key: _t("MRR Growth"),
                values: [
                    { 
                        "label" : _t("New MRR"),
                        "value" : result.new
                    } , 
                    { 
                        "label" : _t("Churned MRR"),
                        "value" : result.churn
                    } , 
                    { 
                        "label" : _t("Expansion MRR"),
                        "value" : result.up
                    } , 
                    { 
                        "label" : _t("Down MRR"),
                        "value" : result.down
                    } , 
                    { 
                        "label" : _t("Net New MRR"),
                        "value" : result.net_new
                    } , 
                    { 
                        "label" : _t("NRR"),
                        "value" : result.nrr
                    } ,
                ]
            }];

            nv.addGraph(function() {
                var chart = nv.models.discreteBarChart()
                    .x(function(d) { return d.label; })
                    .y(function(d) { return d.value; })
                    .staggerLabels(true)
                    .showValues(true)
                    .duration(350);

                chart.tooltip.enabled(false);

                var svg = d3.select(div_to_display)
                    .append("svg")
                    .attr("height", '20em');
                svg
                    .datum(data_chart)
                    .call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        }
    },

    format_number: function(value) {
        value = utils.human_number(value);
        return render_monetary_field(value, this.currency_id);
    },

    on_update_options: function() {
        this.start_date = this.start_picker.getValue() || '0001-02-01';
        this.end_date = this.end_picker.getValue()  || '9999-12-31';
        var selected_salesman_id = Number(this.$searchview.find('option[name="salesman"]:selected').val());
        this.salesman = _.findWhere(this.salesman_ids, {id: selected_salesman_id});
        this.render_dashboard();
    },

    update_cp: function() {
        this.$searchview = $(QWeb.render("sale_subscription_dashboard.salesman_searchview", {
            salesman_ids: this.salesman_ids,
            salesman: this.salesman,
        }));
        this.$searchview.on('click', '.o_update_options', this.on_update_options);

        this.set_up_datetimepickers();
        this.update_control_panel({
            cp_content: {
                $searchview: this.$searchview,
            },
            breadcrumbs: this.getParent().get_breadcrumbs(),
        });
    },
});


// Cohort Analysis
var sale_subscription_dashboard_cohort = sale_subscription_dashboard_abstract.extend({

    events: {
        'click .js_to_subs': 'on_cohort_table',
    },

    init: function(parent, context) {
        this._super(parent, context);

        this.action_id = context.id;
        this.date_start = moment().startOf('year');
        this.cohort_period = 'month';
        this.cohort_periods = [['day', _t('By Day')], ['week', _t('By Week')], ['month', _t('By Month')], ['year', _t('By Year')]];
        this.cohort_interest = 'number';
        this.cohort_interests = [['number', _t('Number of Subscriptions')], ['value', _t('Recurring Revenue (MRR)')]];
        this.filters = {
            'template_ids': [],
            'tag_ids': [],
            'company_ids': [session.company_id],
        };
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return $.when(self.fetch_cohort_report());
        });
    },

    fetch_cohort_report: function() {
        var self = this;
        return ajax.jsonRpc('/sale_subscription_dashboard/fetch_cohort_report', 'call', {
            'date_start': this.date_start.format('YYYY-MM-DD'),
            'cohort_period': this.cohort_period,
            'cohort_interest': this.cohort_interest,
            'filters': this.filters,
        }).then(function (result) {
            self.cohort_report = result.cohort_report;
            self.contract_templates = result.contract_templates;
            self.tags = result.tags;
            self.companies = result.companies;
            self.currency_id = result.currency_id;
        });
    },

    render_dashboard: function() {
        this.$el.empty().append(QWeb.render("sale_subscription_dashboard.cohort_report", {
            cohort_report: this.cohort_report,
            cohort_interest: this.cohort_interest,
            currency_id: this.currency_id,
            format_number: this.format_number,
        }));

        this.update_cp();

        var self = this;
        _.each(this.$('.js_heat'), function(el) {
            var perc = 1 - $(el).data('value')/100;
            el.style.backgroundColor = self.shadeRGB_color("rbg(63,131,163)", perc);
            if (perc < 0.4) {
                el.style.color = "white";
            }
        });
    },

    on_cohort_table: function(ev) {

        var row = $(ev.currentTarget).data().row;
        var column = $(ev.currentTarget).data().column;

        var cell_content = this.cohort_report[row].values[column] || this.cohort_report[row];
        var subs_domain = cell_content && cell_content.domain || [];

        if (!subs_domain.length) {
            return;
        }

        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };

        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'sale.subscription',
            views: [[false, 'list'], [false, 'form']],
            name: column === undefined && _t('Subscriptions') || _t('Churned Subscriptions'),
            domain: subs_domain,
        }, options);
    },

    on_reverse_breadcrumb: function() {
        this.update_cp();
        web_client.do_push_state({action: this.action_id});
    },

    on_update_options: function() {
        this.date_start = this.date_picker.getValue() || '0001-02-01';
        this.cohort_period = this.$searchview.find('option[name="period"]:selected').val();
        this.cohort_interest = this.$searchview.find('option[name="interest"]:selected').val();
        this.filters.template_ids = this.get_filtered_template_ids();
        this.filters.tag_ids = this.get_filtered_tag_ids();
        this.filters.company_ids = this.get_filtered_company_ids();

        var self = this;
        addLoader(this.$('.o_cohort_analysis').empty());
        this.fetch_cohort_report().done(function() {
            self.render_dashboard();
        });
    },

    get_filtered_template_ids: function() {
        var $contract_inputs = this.$searchview_buttons.find(".selected > .o_contract_template_filter");
        return _.map($contract_inputs, function(el) { return $(el).data('id'); });
    },

    get_filtered_tag_ids: function() {
        var $tag_inputs = this.$searchview_buttons.find(".selected > .o_tags_filter");
        return _.map($tag_inputs, function(el) { return $(el).data('id'); });
    },

    get_filtered_company_ids: function() {
        var $company_inputs = this.$searchview_buttons.find(".selected > .o_companies_filter");
        return _.map($company_inputs, function(el) { return $(el).data('id'); });
    },

    set_up_datetimepickers: function() {
        this.date_picker = new datepicker.DateWidget(this, {
            viewMode: 'years',
        });
        var self = this;
        this.date_picker.prependTo(this.$searchview).then(function() {
            self.date_picker.setValue(moment(self.date_start));
        });
    },

    update_cp: function() {
        this.$searchview = $(QWeb.render("sale_subscription_dashboard.cohort_searchview", {widget: this}));
        this.$searchview.on('click', '.o_update_options', this.on_update_options);
        this.set_up_datetimepickers();
        this.render_filters();

        this.update_control_panel({
            cp_content: {
                $searchview: this.$searchview,
                $searchview_buttons: this.$searchview_buttons,
            },
            breadcrumbs: this.getParent().get_breadcrumbs(),
        });

    },

    shadeRGB_color: function(color, percent) {
        var f = color.split(","), t = percent<0?0:255 , p = percent < 0 ? percent * -1: percent, R = parseInt(f[0].slice(4)), G=parseInt(f[1]), B=parseInt(f[2]);
        return "rgb("+(Math.round((t-R)*p)+R)+","+(Math.round((t-G)*p)+G)+","+(Math.round((t-B)*p)+B)+")";
    },

    format_number: function(value) {
        value = utils.human_number(value);
        return render_monetary_field(value, this.currency_id);
    },

});

// Utility functions

function addLoader(selector) {
    var loader = '<span class="fa fa-3x fa-spin fa-spinner fa-pulse"/>';
    selector.html("<div class='o_loader'>" + loader + "</div>");
}

function getMinY(l) {
    var min = Math.min.apply(Math,l.map(function(o){return o[1];}));
    var max = Math.max.apply(Math,l.map(function(o){return o[1];}));
    return Math.max(0, min - (max-min)/2);
}
function getDate(d) { return new Date(d[0]); }
function getValue(d) { return d[1]; }
function getPrunedTickValues(ticks, nb_desired_ticks) {
    var nb_values = ticks.length;
    var keep_one_of = Math.max(1, Math.floor(nb_values / nb_desired_ticks));

    return _.filter(ticks, function(d, i) {
        return i % keep_one_of === 0;
    });
}

function compute_forecast_values(starting_value, projection_time, growth_type, churn, linear_growth, expon_growth) {
    var values = [];
    var cur_value = starting_value;

    for(var i = 1; i <= projection_time ; i++) {
        var cur_date = moment().add(i, 'months');
        if (growth_type === 'linear') {
            cur_value = cur_value*(1-churn/100) + linear_growth;
        }
        else {
            cur_value = cur_value*(1-churn/100)*(1+expon_growth/100);
        }
        values.push({
            '0': cur_date,
            '1': cur_value,
        });
    }
    return values;
}

function load_chart(div_to_display, key_name, result, show_legend, show_demo) {

    if (show_demo) {
        // As we do not show legend for demo graphs, we do not care about the dates.
        result = [
          {
            "0": "2015-08-01",
            "1": 10
          },
          {
            "0": "2015-08-02",
            "1": 20
          },
          {
            "0": "2015-08-03",
            "1": 29
          },
          {
            "0": "2015-08-04",
            "1": 37
          },
          {
            "0": "2015-08-05",
            "1": 44
          },
          {
            "0": "2015-08-06",
            "1": 50
          },
          {
            "0": "2015-08-07",
            "1": 55
          },
          {
            "0": "2015-08-08",
            "1": 59
          },
          {
            "0": "2015-08-09",
            "1": 62
          },
          {
            "0": "2015-08-10",
            "1": 64
          },
          {
            "0": "2015-08-11",
            "1": 65
          },
          {
            "0": "2015-08-12",
            "1": 66
          },
          {
            "0": "2015-08-13",
            "1": 67
          },
          {
            "0": "2015-08-14",
            "1": 68
          },
          {
            "0": "2015-08-15",
            "1": 69
          },
        ];
    }
    var data_chart = [
    {
        values: result,
        key: key_name,
        color: '#2693d5',
        area: true
    },
    ];
    nv.addGraph(function() {
        var chart = nv.models.lineChart()
            .interpolate("monotone")
            .forceY([getMinY(result)])
            .x(function(d) { return getDate(d); })
            .y(function(d) { return getValue(d); });
        if (show_legend){
            chart
            .margin({left: 100})
            .useInteractiveGuideline(true)
            .duration(350)
            .showLegend(true)
            .showYAxis(true)
            .showXAxis(true);
        }
        else {
            chart
            .margin({left: 0, top: 0, bottom: 0, right: 0})
            .useInteractiveGuideline(false)
            .duration(350)
            .showLegend(false)
            .showYAxis(false)
            .showXAxis(false)
            .interactive(false);
        }

        var tick_values = getPrunedTickValues(data_chart[0].values, 10);
        chart.xAxis
            .tickFormat(function(d) { return d3.time.format(core._t.database.parameters.date_format)(new Date(d)); })
            .tickValues(_.map(tick_values, function(d) { return getDate(d); }))
            .rotateLabels(-30);

        chart.yAxis
            .axisLabel(key_name)
            .tickFormat(function(d) { return field_utils.format.float(d);});

        var svg = d3.select(div_to_display).append("svg");
        if (show_legend){
            svg.attr("height", '20em');
        }
        svg
        .datum(data_chart)
        .call(chart);

        nv.utils.windowResize(chart.update);
        return chart;
    });
}

function render_monetary_field(value, currency_id) {
    var currency = session.get_currency(currency_id);
    if (currency) {
        if (currency.position === "after") {
            value += currency.symbol;
        } else {
            value = currency.symbol + value;
        }
    }
    return value;
}

function get_color_class(value, direction) {
    var color = 'o_black';

    if (value !== 0 && direction === 'up') {
        color = (value > 0) && 'o_green' || 'o_red';
    }
    if (value !== 0 && direction !== 'up') {
        color = (value < 0) && 'o_green' || 'o_red';
    }

    return color;
}

// Add client actions

core.action_registry.add('sale_subscription_dashboard_main', sale_subscription_dashboard_main);
core.action_registry.add('sale_subscription_dashboard_cohort', sale_subscription_dashboard_cohort);
core.action_registry.add('sale_subscription_dashboard_detailed', sale_subscription_dashboard_detailed);
core.action_registry.add('sale_subscription_dashboard_forecast', sale_subscription_dashboard_forecast);
core.action_registry.add('sale_subscription_dashboard_salesman', sale_subscription_dashboard_salesman);

});
