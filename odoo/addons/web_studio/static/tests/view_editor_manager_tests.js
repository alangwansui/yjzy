odoo.define('web_studio.ViewEditorManager_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var ListRenderer = require('web.ListRenderer');
var testUtils = require("web.test_utils");
var Widget = require('web.Widget');

var ViewEditorManager = require('web_studio.ViewEditorManager');

var createViewEditorManager = function (params) {
    var $target = $('#qunit-fixture');
    if (params.debug) {
        $target = $('body');
    }

    // reproduce the DOM environment of Studio
    var $web_client = $('<div>').addClass('o_web_client o_in_studio').appendTo($target);
    var $content = $('<div>').addClass('o_content').appendTo($web_client);
    var $client_action = $('<div>').addClass('o_web_studio_client_action').appendTo($content);

    var widget = new Widget();
    params.mockRPC = params.mockRPC || function(route, args) {
        if (route === '/web_studio/get_default_value') {
            return $.when({});
        }
        return this._super(route, args);
    };
    var mockServer = testUtils.addMockEnvironment(widget, params);
    var fieldsView = mockServer.fieldsViewGet(params);
    if (params.viewID) {
        fieldsView.view_id = params.viewID;
    }
    var env = {
        modelName: params.model,
        ids: 'res_id' in params ? [params.res_id] : undefined,
        currentId: 'res_id' in params ? params.res_id : undefined,
        domain: params.domain || [],
        context: params.context || {},
        groupBy: params.groupBy || [],
    };
    var vem = new ViewEditorManager(widget, {
        fields_view: fieldsView,
        view_env: env,
        studio_view_id: params.studioViewID,
    });
    vem.appendTo($client_action);
    return vem;
};

QUnit.module('ViewEditorManager', {
    beforeEach: function () {
        this.data = {
            coucou: {
                fields: {
                    display_name: {
                        string: "Display Name",
                        type: "char"
                    },
                    char_field: {
                        string:"A char",
                        type: "char",
                    },
                    m2o: {
                        string: "M2O",
                        type: "many2one",
                        relation: 'product',
                    },
                    product_ids: {string: "Products", type: "one2many", relation: "product", searchable: true},
                },
            },
            product: {
                fields: {
                    display_name: {string: "Display Name", type: "char", searchable: true},
                    m2o: {string: "M2O", type: "many2one", relation: 'partner', searchable: true},
                    partner_ids: {string: "Partners", type: "one2many", relation: "partner", searchable: true},
                    coucou_id: {string: "coucou", type: "many2one", relation: "coucou"},
                },
                records: [{
                    id: 37,
                    display_name: 'xpad',
                    m2o: 7,
                    partner_ids: [4],
                }, {
                    id: 42,
                    display_name: 'xpod',
                }],
            },
            partner: {
                fields: {
                    display_name: {string: "Display Name", type: "char"},
                },
                records: [{
                    id: 4,
                    display_name: "jean",
                }, {
                    id: 7,
                    display_name: "jacques",
                }],
            },
        };
    }
}, function () {

    QUnit.module('List');

    QUnit.test('list editor sidebar', function(assert) {
        assert.expect(5);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree/>",
        });

        assert.strictEqual(vem.$('.o_web_studio_sidebar').length, 1,
            "there should be a sidebar");
        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_new').hasClass('active'),
            "the Add tab should be active in list view");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('.o_web_studio_field_type_container').length, 2,
            "there should be two sections in Add (new & existing fields");

        vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').click();

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').hasClass('active'),
            "the View tab should now be active");
        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('disabled'),
            "the Properties tab should now be disabled");

        vem.destroy();
    });

    QUnit.test('empty list editor', function(assert) {
        assert.expect(5);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree/>",
        });

        assert.strictEqual(vem.view_type, 'list',
            "view type should be list");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor').length, 1,
            "there should be a list editor");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor table thead th.o_web_studio_hook').length, 1,
            "there should be one hook");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 0,
            "there should be no node");
        var nbFields = _.size(this.data.coucou.fields);
        assert.strictEqual(vem.$('.o_web_studio_sidebar .o_web_studio_existing_fields').children().length, nbFields,
            "all fields should be available");

        vem.destroy();
    });

    QUnit.test('list editor', function(assert) {
        assert.expect(3);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
        });

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.strictEqual(vem.$('table thead th.o_web_studio_hook').length, 2,
            "there should be two hooks (before & after the field)");
        var nbFields = _.size(this.data.coucou.fields) - 1; // - display_name
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('.o_web_studio_existing_fields').children().length, nbFields,
            "fields that are not already in the view should be available");

        vem.destroy();
    });

    QUnit.test('invisible list editor', function(assert) {
        assert.expect(4);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree><field name='display_name' invisible='1'/></tree>",
        });

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 0,
            "there should be no node");
        assert.strictEqual(vem.$('table thead th.o_web_studio_hook').length, 1,
            "there should be one hook");

        // click on show invisible
        vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').click();
        vem.$('.o_web_studio_sidebar').find('input#show_invisible').click();

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should be one node (the invisible one)");
        assert.strictEqual(vem.$('table thead th.o_web_studio_hook').length, 2,
            "there should be two hooks (before & after the field)");

        vem.destroy();
    });

    QUnit.test('list editor field', function(assert) {
        assert.expect(5);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
        });

        // click on the field
        vem.$('.o_web_studio_list_view_editor [data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_list_view_editor [data-node-id]').hasClass('o_clicked'),
            "the column should have the clicked style");

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the label in sidebar should be Display Name");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "",
            "the widget in sidebar should be emtpy");

        vem.destroy();
    });

    QUnit.module('Form');

    QUnit.test('empty form editor', function(assert) {
        assert.expect(4);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<form/>",
        });

        assert.strictEqual(vem.view_type, 'form',
            "view type should be form");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor').length, 1,
            "there should be a form editor");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [data-node-id]').length, 0,
            "there should be no node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 0,
            "there should be no hook");

        vem.destroy();
    });

    QUnit.test('form editor', function(assert) {
        assert.expect(6);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='display_name'/>" +
                    "</sheet>" +
                "</form>",
        });

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        vem.$('.o_web_studio_form_view_editor [data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.ok(vem.$('.o_web_studio_form_view_editor [data-node-id]').hasClass('o_clicked'),
            "the column should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "",
            "the widget in sidebar should be empty");

        vem.destroy();
    });

    QUnit.test('many2one field edition', function (assert) {
        assert.expect(3);

        this.data.product.records = [{
            id: 42,
            display_name: "A very good product",
        }];
        this.data.coucou.records = [{
            id: 1,
            display_name: "Kikou petite perruche",
            m2o: 42,
        }];

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='m2o'/>" +
                    "</sheet>" +
                "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_action') {
                    throw new Error("The many2one form view should not be opened");
                }
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [data-node-id]').length, 1,
            "there should be one node");

        // edit the many2one
        vem.$('.o_web_studio_form_view_editor [data-node-id]').click();

        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.ok(vem.$('.o_web_studio_form_view_editor [data-node-id]').hasClass('o_clicked'),
            "the column should have the clicked style");
        vem.destroy();
    });

    QUnit.test('invisible form editor', function(assert) {
        assert.expect(6);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='display_name' invisible='1'/>" +
                    "</sheet>" +
                "</form>",
        });

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_invisible_modifier[data-node-id]').length, 1,
            "there should be one invisible node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [data-node-id]:not(.o_invisible_modifier)').length, 0,
            "there should be no visible node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        // click on show invisible
        vem.$('.o_web_studio_sidebar').find('.o_web_studio_view').click();
        vem.$('.o_web_studio_sidebar').find('input#show_invisible').click();

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_show_invisible[data-node-id]').length, 1,
            "there should be one visible node (the invisible one)");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_invisible_modifier[data-node-id]').length, 0,
            "there should be no invisible node");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        vem.destroy();
    });

    QUnit.test('form editor - chatter edition', function(assert) {
        assert.expect(5);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='display_name'/>" +
                    "</sheet>" +
                    "<div class='oe_chatter'/>" +
                "</form>",
            mockRPC: function(route, args) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/get_email_alias') {
                    return $.when({email_alias: 'coucou'});
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .oe_chatter[data-node-id]').length, 1,
            "there should be a chatter node");

        // click on the chatter
        vem.$('.o_web_studio_form_view_editor .oe_chatter[data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_sidebar .o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_chatter').length, 1,
            "the sidebar should now display the chatter properties");
        assert.ok(vem.$('.o_web_studio_form_view_editor .oe_chatter[data-node-id]').hasClass('o_clicked'),
            "the chatter should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar input[name="email_alias"]').val(), "coucou",
            "the email alias in sidebar should be fetched");

        vem.destroy();
    });

    QUnit.test('fields without value and label (outside of groups) are shown in form', function(assert) {
        assert.expect(6);

        this.data.coucou.records = [{
            id: 1,
            display_name: "Kikou petite perruche",
        }];

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<group>" +
                            "<field name='id'/>" +
                            "<field name='m2o'/>" +
                        "</group>" +
                        "<field name='display_name'/>" +
                        "<field name='char_field'/>" +
                    "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.ok(!vem.$('.o_web_studio_form_view_editor [name="id"]').hasClass('o_web_studio_widget_empty'),
            "non empty field in group should label should not be special");
        assert.ok(!vem.$('.o_web_studio_form_view_editor [name="m2o"]').hasClass('o_web_studio_widget_empty'),
            "empty field in group should have without label should not be special");
        assert.ok(vem.$('.o_web_studio_form_view_editor [name="m2o"]').hasClass('o_field_empty'),
            "empty field in group should have without label should still have the normal empty class");
        assert.ok(!vem.$('.o_web_studio_form_view_editor [name="display_name"]').hasClass('o_web_studio_widget_empty'),
            "non empty field without label should not be special");
        assert.ok(vem.$('.o_web_studio_form_view_editor [name="char_field"]').hasClass('o_web_studio_widget_empty'),
            "empty field without label should be special");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [name="char_field"]').text(), "A char",
            "empty field without label should have its string as label");

        vem.destroy();
    });

    QUnit.test('notebook edition', function(assert) {
        assert.expect(8);

        var arch = "<form>" +
            "<sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                "</group>" +
                "<notebook>" +
                    "<page string='Kikou'>" +
                        "<field name='id'/>" +
                    "</page>" +
                "</notebook>" +
            "</sheet>" +
        "</form>";
        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.tag, 'page',
                        "a page should be added");
                    assert.strictEqual(args.operations[0].node.attrs.string, 'New Page',
                        "the string attribute should be set");
                    assert.strictEqual(args.operations[0].position, 'inside',
                        "a page should be added inside the notebook");
                    assert.strictEqual(args.operations[0].target.tag, 'notebook',
                        "the target should be the notebook in edit_view");
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = arch;
                    return $.when({
                        fields_views: {
                            form: fieldsView,
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        assert.strictEqual(vem.$('.o_notebook li').length, 2,
            "there should be one existing page and a fake one");

        // click on existing tab
        var $page = vem.$('.o_notebook li:first');
        $page.click();
        assert.ok($page.hasClass('o_clicked'), "the page should be clickable");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_page').length, 1,
            "the sidebar should now display the page properties");
        var $pageInput = vem.$('.o_web_studio_sidebar_content.o_display_page input[name="string"]');
        assert.strictEqual($pageInput.val(), "Kikou", "the page name in sidebar should be set");

        // add a new page
        vem.$('.o_notebook li:eq(1) > a').click();

        vem.destroy();
    });

    QUnit.test('label edition', function(assert) {
        assert.expect(9);

        var arch = "<form>" +
            "<sheet>" +
                "<group>" +
                    "<label for='display_name' string='Kikou'/>" +
                    "<div><field name='display_name' nolabel='1'/></div>" +
                "</group>" +
                "<group>" +
                    "<field name='char_field'/>" +
                "</group>" +
            "</sheet>" +
        "</form>";
        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0].target, {
                        tag: 'label',
                        attrs: {
                            for: 'display_name',
                        },
                    }, "the target should be set in edit_view");
                    assert.deepEqual(args.operations[0].new_attrs, {string: 'Yeah'},
                        "the string attribute should be set in edit_view");
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = arch;
                    return $.when({
                        fields_views: {
                            form: fieldsView,
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        var $label = vem.$('.o_web_studio_form_view_editor label[data-node-id="1"]');
        assert.strictEqual($label.text(), "Kikou",
            "the label should be correctly set");

        $label.click();
        assert.ok($label.hasClass('o_clicked'), "the label should be clickable");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_label').length, 1,
            "the sidebar should now display the label properties");
        var $labelInput = vem.$('.o_web_studio_sidebar_content.o_display_label input[name="string"]');
        assert.strictEqual($labelInput.val(), "Kikou", "the label name in sidebar should be set");
        $labelInput.val('Yeah').trigger('change');

        var $fieldLabel = vem.$('.o_web_studio_form_view_editor label:contains("A char")');
        assert.strictEqual($fieldLabel.length, 1, "there should be a label for the field");
        $fieldLabel.click();
        assert.notOk($fieldLabel.hasClass('o_clicked'), "the field label should not be clickable");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");

        vem.destroy();
    });

    QUnit.module('Kanban');

    QUnit.test('empty kanban editor', function(assert) {
        assert.expect(4);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<kanban>" +
                    "<templates><t t-name='kanban-box'/></templates>" +
                "</kanban>",
        });

        assert.strictEqual(vem.view_type, 'kanban',
            "view type should be kanban");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor').length, 1,
            "there should be a kanban editor");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').length, 0,
            "there should be no node");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor .o_web_studio_hook').length, 0,
            "there should be no hook");

        vem.destroy();
    });

    QUnit.test('kanban editor', function(assert) {
        assert.expect(13);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.ok(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').hasClass('o_web_studio_widget_empty'),
            "the empty node should have the empty class");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_kanban_tags').length, 1,
            "there should be the hook for tags");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_dropdown').length, 1,
            "there should be the hook for dropdown");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_priority').length, 1,
            "there should be the hook for priority");
        assert.strictEqual(vem.$('.o_kanban_record .o_web_studio_add_kanban_image').length, 1,
            "there should be the hook for image");

        vem.$('.o_web_studio_kanban_view_editor [data-node-id]').click();

        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.ok(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').hasClass('o_clicked'),
            "the field should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "",
            "the widget in sidebar should be empty");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="display"]').val(), "false",
            "the display attribute should be Default");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the field should have the label Display Name in the sidebar");

        vem.destroy();
    });

    QUnit.test('grouped kanban editor', function(assert) {
        assert.expect(4);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<kanban default_group_by='display_name'>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.ok(vem.$('.o_web_studio_kanban_view_editor').hasClass('o_kanban_grouped'),
            "the editor should be grouped");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.ok(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').hasClass('o_web_studio_widget_empty'),
            "the empty node should have the empty class");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        vem.destroy();
    });

    QUnit.test('grouped kanban editor with record', function(assert) {
        assert.expect(4);

        this.data.coucou.records = [{
            id: 1,
            display_name: 'coucou 1',
        }];

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<kanban default_group_by='display_name'>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.ok(vem.$('.o_web_studio_kanban_view_editor').hasClass('o_kanban_grouped'),
            "the editor should be grouped");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.notOk(vem.$('.o_web_studio_kanban_view_editor [data-node-id]').hasClass('o_web_studio_widget_empty'),
            "the empty node should not have the empty class");
        assert.strictEqual(vem.$('.o_web_studio_kanban_view_editor .o_web_studio_hook').length, 1,
            "there should be one hook");

        vem.destroy();
    });

    QUnit.test('enable stages in kanban editor', function (assert) {
        assert.expect(6);

        this.data.x_coucou_stage = {
            fields: {},
        };
        this.data.coucou.fields.x_stage_id = {type: 'many2one', relation: 'x_coucou_stage', string: 'Stage', store: true};

        var fieldsView;
        var nbEditView = 0;
        var arch =
            "<kanban>" +
                "<templates>" +
                    "<t t-name='kanban-box'>" +
                        "<div class='o_kanban_record'>" +
                            "<field name='display_name'/>" +
                        "</div>" +
                    "</t>" +
                "</templates>" +
            "</kanban>";
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/create_stages_model') {
                    assert.strictEqual(args.model_name, 'coucou',
                        "should create the stages model for the current model");
                    return $.when();
                }
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    nbEditView++;
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = "<kanban default_group_by='x_stage_id'>" +
                            "<templates>" +
                                "<field name='x_stage_id'/>" +
                                "<t t-name='kanban-box'>" +
                                    "<div class='o_kanban_record'>" +
                                        "<field name='display_name'/>" +
                                    "</div>" +
                                "</t>" +
                            "</templates>" +
                        "</kanban>";
                    return $.when({
                        fields_views: {
                            kanban: fieldsView,
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        assert.strictEqual(vem.$('.o_web_studio_sidebar input[name="enable_stage"]').attr('checked'), undefined,
            "the stages shouldn't be enabled");
        assert.strictEqual(vem.$('.o_web_studio_sidebar select[name="default_group_by"]').val(), "",
            "the kanban should not be grouped");

        vem.$('.o_web_studio_sidebar input[name="enable_stage"]').click();

        assert.strictEqual(nbEditView, 2,
            "should edit the view twice: add field in view & set the default_group_by");

        assert.strictEqual(vem.$('.o_web_studio_sidebar input[name="enable_stage"]').attr('checked'), 'checked',
            "the stages should be enabled");
        assert.strictEqual(vem.$('.o_web_studio_sidebar select[name="default_group_by"]').val(), "x_stage_id",
            "the kanban should be grouped by stage");

        vem.destroy();
    });

    QUnit.module('Search');

    QUnit.test('empty search editor', function(assert) {
        assert.expect(6);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<search/>",
        });

        assert.strictEqual(vem.view_type, 'search',
            "view type should be search");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor').length, 1,
            "there should be a search editor");
        assert.strictEqual(vem.$('.o_web_studio_search_autocompletion_fields.table tbody tr.o_web_studio_hook').length, 1,
            "there should be one hook in the autocompletion fields");
        assert.strictEqual(vem.$('.o_web_studio_search_filters.table tbody tr.o_web_studio_hook').length, 1,
            "there should be one hook in the filters");
        assert.strictEqual(vem.$('.o_web_studio_search_group_by.table tbody tr.o_web_studio_hook').length, 1,
            "there should be one hook in the group by");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor [data-node-id]').length, 0,
            "there should be no node");
        vem.destroy();
    });

    QUnit.test('search editor', function(assert) {
        assert.expect(14);

        var arch = "<search>" +
                "<field name='display_name'/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<filter string='My Name2' " +
                    "name='my_name2' " +
                    "domain='[(\"display_name\",\"=\",coucou2)]'" +
                "/>" +
                "<group expand='0' string='Group By'>" +
                    "<filter name='groupby_display_name' " +
                    "domain='[]' context=\"{'group_by':'display_name'}\"/>" +
                "</group>" +
            "</search>";
        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0].node.attrs, {name: 'display_name'},
                        "we should only specify the name (in attrs) when adding a field");
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = arch;
                    return $.when({
                        fields_views: {
                            search: fieldsView,
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        // try to add a field in the autocompletion section
        testUtils.dragAndDrop(vem.$('.o_web_studio_existing_fields > .ui-draggable:first'), $('.o_web_studio_search_autocompletion_fields .o_web_studio_hook:first'));

        assert.strictEqual(vem.view_type, 'search',
            "view type should be search");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor').length, 1,
            "there should be a search editor");
        assert.strictEqual(vem.$('.o_web_studio_search_autocompletion_fields.table tbody tr.o_web_studio_hook').length, 2,
            "there should be two hooks in the autocompletion fields");
        assert.strictEqual(vem.$('.o_web_studio_search_filters.table tbody tr.o_web_studio_hook').length, 3,
            "there should be three hook in the filters");
        assert.strictEqual(vem.$('.o_web_studio_search_group_by.table tbody tr.o_web_studio_hook').length, 2,
            "there should be two hooks in the group by");
        assert.strictEqual(vem.$('.o_web_studio_search_autocompletion_fields.table [data-node-id]').length, 1,
            "there should be 1 node in the autocompletion fields");
        assert.strictEqual(vem.$('.o_web_studio_search_filters.table [data-node-id]').length, 2,
            "there should be 2 nodes in the filters");
        assert.strictEqual(vem.$('.o_web_studio_search_group_by.table [data-node-id]').length, 1,
            "there should be 1 nodes in the group by");
        assert.strictEqual(vem.$('.o_web_studio_search_view_editor [data-node-id]').length, 4,
            "there should be 4 nodes");

        // edit the autocompletion field
        $('.o_web_studio_search_view_editor .o_web_studio_search_autocompletion_container [data-node-id]').click();


        assert.ok(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties').hasClass('active'),
            "the Properties tab should now be active");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should now display the field properties");
        assert.ok(vem.$('.o_web_studio_search_view_editor .o_web_studio_search_autocompletion_container [data-node-id]').hasClass('o_clicked'),
            "the field should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the field should have the label Display Name in the sidebar");

        vem.destroy();
    });

    QUnit.module('Pivot');

    QUnit.test('empty pivot editor', function(assert) {
        assert.expect(3);

        this.data.coucou.records = [{
            id: 1,
            display_name: 'coucou',
        }];

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<pivot/>",
        });

        assert.strictEqual(vem.view_type, 'pivot',
            "view type should be pivot");
        assert.strictEqual(vem.$('.o_web_studio_view_renderer .o_pivot').length, 1,
            "there should be a pivot renderer");
        assert.strictEqual(vem.$('.o_web_studio_view_renderer > .o_pivot > table').length, 1,
            "the table should be the direct child of pivot");

        vem.$('.o_web_studio_sidebar_header [name="view"]').click();

        vem.destroy();
    });

    QUnit.module('Graph');

    QUnit.test('empty graph editor', function(assert) {
        var done = assert.async();
        assert.expect(3);

        this.data.coucou.records = [{
            id: 1,
            display_name: 'coucou',
        }];

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<graph/>",
        });

        assert.strictEqual(vem.view_type, 'graph',
            "view type should be graph");
        return concurrency.delay(0).then(function () {
            assert.strictEqual(vem.$('.o_web_studio_view_renderer .o_graph').length, 1,
                "there should be a graph renderer");
            assert.strictEqual(vem.$('.o_web_studio_view_renderer > .o_graph > .o_graph_svg_container > svg').length, 1,
                "the graph should be the direct child of its container");
            vem.destroy();
            done();
        });
    });

    QUnit.module('Others');

    QUnit.test('error during tree rendering: undo', function(assert) {
        assert.expect(4);

        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree><field name='id'/></tree>",
            mockRPC: function (route) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = "<tree><field name='id'/></tree>";
                    return $.when({
                        fields_views: {
                            list: fieldsView,
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        testUtils.intercept(vem, 'studio_error', function (event) {
            assert.strictEqual(event.data.error, 'view_rendering',
                "should have raised an error");
        });

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        // make the rendering crashes only the first time (the operation will
        // be undone and we will re-render with the old arch the second time)
        var oldRenderView = ListRenderer.prototype._renderView;
        var firstExecution = true;
        ListRenderer.prototype._renderView = function () {
            if (firstExecution) {
                firstExecution = false;
                throw "Error during rendering";
            } else {
                return oldRenderView.apply(this, arguments);
            }
        };

        // delete a field to generate a view edition
        vem.$('.o_web_studio_list_view_editor [data-node-id]').click();
        vem.$('.o_web_studio_sidebar .o_web_studio_remove').click();
        $('.modal-dialog .btn-primary').click();

        assert.strictEqual($('.o_web_studio_view_renderer').length, 1,
            "there should only be one renderer");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "the view should be back as normal with 1 field");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_view').length, 1,
            "the sidebar should have reset to its default mode");

        ListRenderer.prototype._renderView = oldRenderView;

        vem.destroy();
    });

    QUnit.test('add a monetary field without currency_id', function(assert) {
        assert.expect(7);

        this.data.product.fields.monetary_field = {
            string: 'Monetary',
            type: 'monetary',
            searchable: true,
        };
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    assert.ok(false, "should not edit the view");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should be one node");

        // add a monetary field
        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_monetary'), vem.$('th.o_web_studio_hook').first());
        assert.strictEqual($('.modal-body').text(), "This field type cannot be dropped on this model.",
            "this should trigger an alert");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should still be one node");
        $('.modal-footer .btn-primary:first').click(); // confirm
        assert.strictEqual($('.modal').length, 0, "there should be no modal anymore");

        // add a related monetary field
        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), vem.$('th.o_web_studio_hook').first());
        assert.strictEqual($('.modal .o_field_selector').length, 1,
            "a modal with a field selector should be opened to selected the related field");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        $('.o_field_selector_popover li[data-name=m2o]').click();
        $('.o_field_selector_popover li[data-name=monetary_field]').click();
        $('.modal-footer .btn-primary:first').click(); // confirm
        assert.strictEqual($('.modal-body').text(), "This field type cannot be dropped on this model.",
            "this should trigger an alert");
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should still be one node");

        vem.destroy();
    });

    QUnit.test('add a monetary field with currency_id', function(assert) {
        assert.expect(5);

        this.data.product.fields.monetary_field = {
            string: 'Monetary',
            type: 'monetary',
            searchable: true,
        };

        this.data.coucou.fields.x_currency_id = {
            string: "Currency",
            type: 'many2one',
            relation: "res.currency",
        };

        var arch = "<tree><field name='display_name'/></tree>";
        var fieldsView;
        var nbEdit = 0;

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    nbEdit++;
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = arch;
                    return $.when({
                        fields_views: {
                            list: fieldsView,
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        // add a monetary field
        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should be one node");
        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_monetary'), $('.o_web_studio_hook'));
        assert.strictEqual(nbEdit, 1, "the view should have been updated");
        assert.strictEqual($('.modal').length, 0, "there should be no modal");

        // add a related monetary field
        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), vem.$('th.o_web_studio_hook').first());
        assert.strictEqual($('.modal .o_field_selector').length, 1,
            "a modal with a field selector should be opened to selected the related field");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        $('.o_field_selector_popover li[data-name=m2o]').click();
        $('.o_field_selector_popover li[data-name=monetary_field]').click();
        $('.modal-footer .btn-primary:first').click(); // confirm
        assert.strictEqual(nbEdit, 2, "the view should have been updated");

        vem.destroy();
    });

    QUnit.test('add a related field', function(assert) {
        assert.expect(12);


        this.data.coucou.fields.related_field = {
            string: "Related",
            type: 'related',
        };

        var nbEdit = 0;
        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    if (nbEdit === 0) {
                        assert.strictEqual(args.operations[0].node.field_description.related,
                            'm2o.display_name', "related arg should be correct");
                        fieldsView.arch = "<tree><field name='display_name'/><field name='related_field'/></tree>";
                    } else if (nbEdit === 1) {
                        assert.strictEqual(args.operations[1].node.field_description.related,
                            'm2o.m2o', "related arg should be correct");
                        assert.strictEqual(args.operations[1].node.field_description.relation,
                            'partner', "relation arg should be correct for m2o");
                    } else if (nbEdit === 2) {
                        assert.strictEqual(args.operations[2].node.field_description.related,
                            'm2o.partner_ids', "related arg should be correct");
                        assert.strictEqual(args.operations[2].node.field_description.relational_model,
                            'product', "relational model arg should be correct for o2m");
                    }
                    nbEdit++;
                    return $.when({
                        fields_views: {
                            list: fieldsView,
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), $('.o_web_studio_hook'));

        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");

        // try to create an empty related field
        $('.modal button:contains("Confirm")').click();
        assert.strictEqual($('.modal').length, 2, "an alert should be displayed");

        // remove the alert
        $('.modal:eq(1) button:contains("Ok")').click();
        assert.strictEqual(nbEdit, 0, "should not have edited the view");
        assert.strictEqual($('.modal').length, 1, "the first  modal should still be displayed");

        $('.modal .o_field_selector').focusin(); // open the selector popover
        $('.o_field_selector_popover li[data-name=m2o]').click();
        $('.o_field_selector_popover li[data-name=display_name]').click();
        $('.modal-footer .btn-primary:first').click(); // confirm

        // create a new many2one related field
        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        $('.o_field_selector_popover li[data-name=m2o]').click();
        $('.o_field_selector_popover li[data-name=m2o]').click();
        $('.modal .o_field_selector .o_field_selector_close').click(); // close the selector popover
        $('.modal-footer .btn-primary:first').click(); // confirm

        // create a new one2many related field
        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        $('.o_field_selector_popover li[data-name=m2o]').click();
        $('.o_field_selector_popover li[data-name=partner_ids]').click();
        $('.modal .o_field_selector .o_field_selector_close').click(); // close the selector popover
        $('.modal-footer .btn-primary:first').click(); // confirm

        assert.strictEqual(nbEdit, 3, "should have edited the view");

        vem.destroy();
    });

    QUnit.test('switch mode after element removal', function(assert) {
        assert.expect(5);

        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<tree><field name='id'/><field name='display_name'/></tree>",
            mockRPC: function (route) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    assert.ok(true, "should edit the view to delete the field");
                    fieldsView.arch = "<tree><field name='display_name'/></tree>";
                    return $.when({
                        fields_views: {
                            list: fieldsView,
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 2,
            "there should be two nodes");

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        vem.$('.o_web_studio_list_view_editor [data-node-id]:first').click();

        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 1,
            "the sidebar should display the field properties");

        // delete a field
        vem.$('.o_web_studio_sidebar .o_web_studio_remove').click();
        $('.modal-dialog .btn-primary').click();

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor [data-node-id]').length, 1,
            "there should be one node");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field').length, 0,
            "the sidebar should have switched mode");

        vem.destroy();
    });

    QUnit.test('open XML editor in read-only', function(assert) {
        assert.expect(1);

        var arch = "<form><sheet><field name='display_name'/></sheet></form>";
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_editor/get_assets_editor_resources') {
                    return $.when({
                        views: [{
                            active: true,
                            arch: arch,
                            id: 1,
                            inherit_id: false,
                        }],
                        less: [],
                    });
                }
                return this._super.apply(this, arguments);
            },
            viewID: 1,
        });

        vem.$('.o_web_studio_sidebar_header [name="view"]').click();
        vem.$('.o_web_studio_sidebar .o_web_studio_xml_editor').click();

        assert.strictEqual(vem.$('.o_web_studio_view_renderer .o_form_readonly').length, 1,
            "the form should be in read-only");

        vem.destroy();
    });

    QUnit.test('new button in buttonbox', function(assert) {
        assert.expect(4);

        var arch = "<form><sheet><field name='display_name'/></sheet></form>";
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
        });

        vem.$('.o_web_studio_form_view_editor .o_web_studio_button_hook').click();

        assert.strictEqual($('.modal:visible').length, 1, "there should be one modal");
        assert.strictEqual($('.o_web_studio_new_button_dialog').length, 1,
            "there should be a modal to create a button in the buttonbox");
        assert.strictEqual($('.o_web_studio_new_button_dialog .o_field_many2one').length, 1,
            "there should be a many2one for the related field");

        $('.o_web_studio_new_button_dialog .o_field_many2one input').focus();
        $('.o_web_studio_new_button_dialog .o_field_many2one input').val('test').trigger('keyup').trigger('focusout');

        assert.strictEqual($('.modal:visible').length, 1, "should not display the create modal");

        vem.destroy();
    });

    QUnit.test('element removal', function(assert) {
        assert.expect(8);

        var editViewCount = 0;
        var arch = "<form><sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                    "<field name='m2o'/>" +
                "</group>" +
                "<notebook><page name='page'><field name='id'/></page></notebook>" +
            "</sheet></form>";
        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    if (editViewCount === 1) {
                        assert.strictEqual(_.has(args.operations[0].target, 'xpath_info'), false,
                            'should not give xpath_info if we have the tag identifier attributes');
                    } else if (editViewCount === 2) {
                        assert.strictEqual(args.operations[1].target.tag, 'group',
                            'should compute correctly the parent node for the group');
                    } else if (editViewCount === 3) {
                        assert.strictEqual(args.operations[2].target.tag, 'notebook',
                            'should delete the notebook because the last page is deleted');
                        assert.strictEqual(_.last(args.operations[2].target.xpath_info).tag, 'notebook',
                            'should have the notebook as xpath last element');
                    }
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = arch;
                    return $.when({
                        fields_views: {
                            form: fieldsView,
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        // remove field
        vem.$('[name="display_name"]').click();
        vem.$('.o_web_studio_sidebar .o_web_studio_remove').click();
        assert.strictEqual($('.modal-body').text(), "Are you sure you want to remove this field from the view?",
            "should display the correct message");
        $('.modal-dialog .btn-primary').click();

        // remove group
        vem.$('.o_group[data-node-id]').click();
        vem.$('.o_web_studio_sidebar .o_web_studio_remove').click();
        assert.strictEqual($('.modal-body').text(), "Are you sure you want to remove this group from the view?",
            "should display the correct message");
        $('.modal-dialog .btn-primary').click();

        // remove page
        vem.$('.o_notebook li[data-node-id]').click();
        vem.$('.o_web_studio_sidebar .o_web_studio_remove').click();
        assert.strictEqual($('.modal-body').text(), "Are you sure you want to remove this page from the view?",
            "should display the correct message");
        $('.modal-dialog .btn-primary').click();

        assert.strictEqual(editViewCount, 3,
            "should have edit the view 3 times");
        vem.destroy();
    });

    QUnit.test('update sidebar after edition', function(assert) {
        assert.expect(4);

        var editViewCount = 0;
        var arch = "<form><sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                "</group>" +
                "<notebook><page><field name='id'/></page></notebook>" +
            "</sheet></form>";
        var fieldsView;
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    fieldsView.arch = arch;
                    return $.when({
                        fields_views: {
                            form: fieldsView,
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        testUtils.intercept(vem, 'node_clicked', function (event) {
            assert.step(event.data.node.tag);
        }, true);

        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);

        // remove field
        vem.$('[name="display_name"]').click();
        vem.$('.o_web_studio_sidebar [name="string"]').focus();
        vem.$('.o_web_studio_sidebar [name="string"]').val('test').trigger('change');

        assert.strictEqual(editViewCount, 1,
            "should have edit the view 1 time");
        assert.verifySteps(['field', 'field'],
            "should have clicked again on the node after edition to reload the sidebar");

        vem.destroy();
    });

    QUnit.test('notebook and group not drag and drop in a group', function(assert) {
        assert.expect(2);
        var editViewCount = 0;
        var arch = "<form><sheet>" +
                "<group>" +
                    "<group>" +
                        "<field name='display_name'/>" +
                    "</group>" +
                    "<group>" +
                    "</group>" +
                "</group>" +
            "</sheet></form>";
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                }
                return this._super.apply(this, arguments);
            },
        });
        testUtils.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_tabs'), $('.o_group .o_web_studio_hook'));
        assert.strictEqual(editViewCount, 0,
            "the notebook cannot be dropped inside a group");
        testUtils.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_columns'), $('.o_group .o_web_studio_hook'));
        assert.strictEqual(editViewCount, 0,
            "the group cannot be dropped inside a group");
        vem.destroy();
    });

    QUnit.test('drop monetary field outside of group', function(assert) {
        assert.expect(1);

        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: "<form><sheet/></form>",
        });

        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_monetary'), $('.o_web_studio_hook'), {disableDrop: true});
        assert.strictEqual(vem.$('.o_web_studio_nearest_hook').length, 0, "There should be no highlighted hook");

        vem.destroy();
    });

    QUnit.module('X2Many');

    QUnit.test('display one2many without inline views', function(assert) {
        assert.expect(1);

        var vem = createViewEditorManager({
            arch: "<form>" +
                "<sheet>" +
                    "<field name='display_name'/>" +
                    "<field name='product_ids'/>" +
                "</sheet>" +
            "</form>",
            model: "coucou",
            data: this.data,
            archs: {
                "product,false,list": '<tree><field name="display_name"/></tree>'
            },
        });
        var $one2many = vem.$('.o_field_one2many.o_field_widget');
        assert.strictEqual($one2many.children().length, 2,
            "The one2many widget should be displayed");
        vem.destroy();
    });

    QUnit.test('edit one2many list view', function(assert) {
        assert.expect(3);

        var fieldsView;
        var vem = createViewEditorManager({
            arch: "<form>" +
                "<sheet>" +
                    "<field name='display_name'/>" +
                    "<field name='product_ids'/>" +
                "</sheet>" +
            "</form>",
            model: "coucou",
            data: this.data,
            archs: {
                "product,false,list": '<tree><field name="display_name"/></tree>'
            },
            mockRPC: function (route) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    // We need to create the fieldsView here because the fieldsViewGet in studio
                    // has a specific behaviour so cannot use the mock server fieldsViewGet
                    assert.ok(true, "should edit the view to add the one2many field");
                    fieldsView = {};
                    fieldsView.arch = "<form>" +
                    "<sheet>" +
                        "<field name='display_name'/>" +
                        "<field name='product_ids'>" +
                            "<tree><field name='coucou_id'/><field name='display_name'/></tree>" +
                        "</field>" +
                    "</sheet>" +
                    "</form>";
                    fieldsView.model = "coucou";
                    fieldsView.fields = {
                        display_name: {
                            string: "Display Name",
                            type: "char",
                        },
                        product_ids: {
                            string: "product",
                            type: "one2many",
                            relation: "product",
                            views: {
                                list: {
                                    arch: "<tree><field name='coucou_id'/><field name='display_name'/></tree>",
                                    fields: {
                                        coucou_id: {
                                            string: "coucou",
                                            type: "many2one",
                                            relation: "coucou",
                                        },
                                        display_name: {
                                            string: "Display Name",
                                            type: "char",
                                        },
                                    },
                                },
                            },
                        }
                    };
                    return $.when({
                        fields_views: {
                            form: fieldsView,
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        vem.$('.o_web_studio_view_renderer .o_field_one2many').click();
        $(vem.$('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many')[0]).click();
        assert.strictEqual(vem.$('.o_web_studio_view_renderer thead tr [data-node-id]').length, 1,
            "there should be 1 nodes in the x2m editor.");
        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);
        testUtils.dragAndDrop(vem.$('.o_web_studio_existing_fields .o_web_studio_field_many2one'), $('.o_web_studio_hook'));
        assert.strictEqual(vem.$('.o_web_studio_view_renderer thead tr [data-node-id]').length, 2,
            "there should be 2 nodes after the drag and drop.");
        vem.destroy();
    });

    QUnit.test('edit one2many form view (2 level)', function(assert) {
        assert.expect(2);
        this.data.coucou.records = [{
            id: 11,
            display_name: 'Coucou 11',
            product_ids: [37],
        }];
        var fieldsView;
        var vem = createViewEditorManager({
            arch: "<form>" +
                "<sheet>" +
                    "<field name='display_name'/>" +
                    "<field name='product_ids'>" +
                        "<form>" +
                            "<sheet>" +
                                "<group>" +
                                    "<field name='partner_ids'>" +
                                        "<form><sheet><group><field name='display_name'/></group></sheet></form>" +
                                    "</field>" +
                                "</group>" +
                            "</sheet>" +
                        "</form>" +
                    "</field>" +
                "</sheet>" +
            "</form>",
            model: "coucou",
            data: this.data,
            res_id: 11,
            archs: {
                "product,false,list": "<tree><field name='display_name'/></tree>",
                "partner,false,list": "<tree><field name='display_name'/></tree>",
            },
            mockRPC: function (route) {
                if (route === '/web_studio/get_default_value') {
                    return $.when({});
                }
                if (route === '/web_studio/edit_view') {
                    // We need to create the fieldsView here because the fieldsViewGet in studio
                    // has a specific behaviour so cannot use the mock server fieldsViewGet
                    assert.ok(true, "should edit the view to add the one2many field");
                    fieldsView.arch = "<form>" +
                        "<sheet>" +
                            "<field name='display_name'/>" +
                            "<field name='product_ids'/>" +
                        "</sheet>" +
                    "</form>";
                    fieldsView.fields.product_ids.views = {
                        form: {
                            arch: "<form><sheet><group><field name='partner_ids'/></group></sheet></form>",
                            fields: {
                                partner_ids: {
                                    string: "partners",
                                    type: "one2many",
                                    relation: "partner",
                                    views: {
                                        form: {
                                            arch: "<form><sheet><group><field name='display_name'/></group></sheet></form>",
                                            fields: {
                                                display_name: {
                                                    string: "Display Name",
                                                    type: "char",
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    };
                    return $.when({
                        fields_views: {
                            form: fieldsView,
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        vem.$('.o_web_studio_view_renderer .o_field_one2many').click();
        $(vem.$('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="form"]')).click();
        vem.$('.o_web_studio_view_renderer .o_field_one2many').click();
        $(vem.$('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="form"]')).click();
        // used to generate the new fields view in mockRPC
        fieldsView = $.extend(true, {}, vem.fields_view);
        assert.strictEqual(vem.$('.o_field_char').eq(0).text(), 'jean',
            "the partner view form should be displayed.");
        testUtils.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_char'), $('.o_web_studio_hook'));
        vem.destroy();
    });

    QUnit.test('edit one2many list view that uses parent key', function(assert) {
        assert.expect(3);

        this.data.coucou.records = [{
            id: 11,
            display_name: 'Coucou 11',
            product_ids: [37],
        }];

        var vem = createViewEditorManager({
            arch: "<form>" +
                "<sheet>" +
                    "<field name='display_name'/>" +
                    "<field name='product_ids'>" +
                        "<form>" +
                            "<sheet>" +
                                "<field name='m2o'" +
                                " attrs=\"{'invisible': [('parent.display_name', '=', 'coucou')]}\"" +
                                " domain=\"[('display_name', '=', parent.display_name)]\"/>" +
                            "</sheet>" +
                        "</form>" +
                    "</field>" +
                "</sheet>" +
            "</form>",
            model: "coucou",
            data: this.data,
            res_id: 11,
            archs: {
                "product,false,list": '<tree><field name="display_name"/></tree>'
            },
        });

        // edit the x2m form view
        vem.$('.o_web_studio_form_view_editor .o_field_one2many').click();
        vem.$('.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]').click();
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_field_widget[name="m2o"]').text(), "jacques",
            "the x2m form view should be correctly rendered");
        vem.$('.o_web_studio_form_view_editor .o_field_widget[name="m2o"]').click();

        // open the domain editor
        assert.strictEqual($('.modal .o_domain_selector').length, 0,
            "the domain selector should not be opened");
        vem.$('.o_web_studio_sidebar_content input[name="domain"]').trigger('focusin');
        assert.strictEqual($('.modal .o_domain_selector').length, 1,
            "the domain selector should be correctly opened");

        vem.destroy();
    });

    QUnit.test('notebook and group drag and drop after a group', function(assert) {
        assert.expect(2);
        var arch = "<form><sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                "</group>" +
            "</sheet></form>";
        var vem = createViewEditorManager({
            data: this.data,
            model: 'coucou',
            arch: arch,
        });
        var $afterGroupHook = vem.$('.o_form_sheet > .o_web_studio_hook');
        testUtils.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_tabs'),
            $afterGroupHook, {disableDrop: true});
        assert.strictEqual(vem.$('.o_web_studio_nearest_hook').length, 1, "There should be 1 highlighted hook");
        testUtils.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_columns'),
            $afterGroupHook, {disableDrop: true});
        assert.strictEqual(vem.$('.o_web_studio_nearest_hook').length, 1, "There should be 1 highlighted hook");
        vem.destroy();
    });
});

});
