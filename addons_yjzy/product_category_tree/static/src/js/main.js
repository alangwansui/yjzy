odoo.define('product_category_tree.Main', function (require) {
    "use strict";
    var core = require('web.core');
    var FieldMany2Many = require('web.relational_fields').FieldMany2Many;
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var dialogs = require('web.view_dialogs');
    var AbstractField = require('web.AbstractField');
    var ListController = require('web.ListController');
    var SearchView = require('web.SearchView');

    var _t = core._t;

    ListController.include({
        start: function () {
            var ret = this._super.apply(this, arguments);
            var self = this;
            self.bExpand = true;

            var rpc = this._rpc({
                model: self.modelName,
                method: 'get_categories',
                args: [[], self.context],
            }).then(function (result) {
                if (!result.do_flag) return;
                var data = result.data;
                var title = result.title;
                self.field = result.field;

                self.$el.addClass("ji_flex_display_row");

                var $list = self.$el.find("div.table-responsive");
                $list.addClass("ji_flex_auto");

                var $div = $('<div>', {class: "ji_category"});
                var $titlebar = $('<div>', {class: 'ji_category_title'});

                var $expand = $('<span>', {class: 'fa fa-arrows-alt btn btn-icon ji_category_title_button'});
                $expand.tooltip({
                    delay: {show: 1000, hide: 0},
                    title: function () {
                        return _t("Expand all categories");
                    }
                });
                $expand.on('click', _.bind(self.on_category_expand, self));
                $expand.appendTo($titlebar);

                var $title = $('<div>', {class: 'ji_flex_auto', style: "line-height:32px;font-weight:bold;margin-left:6px;"});
                $title.text(title);
                $title.appendTo($titlebar);

                $titlebar.appendTo($div);
                self.$tree = $('<div>', {class: 'ji_category_tree ztree'});
                self.$tree.appendTo($div);

                $div.insertBefore( $list );

//append，appendTo，after，before，insertAfter，insertBefore，appendChild

                var setting = {
                    callback: {
                        onClick: _.bind(self.on_click_treeitem, self)
                    },
                    data: {
                        simpleData: {
                            enable: true,
                            idKey: "id",
                            pIdKey: "pid",
                            rootPId: 0

                        }
                    }
                };
                self.$ztree = $.fn.zTree.init(self.$tree, setting, data);
                //self.$ztree.expandAll(true);

            });

            return $.when(ret, rpc);
        },

        make_domain: function (treeNode) {
            var self = this;
            var mydomain = [self.initialState.domain];

            console.info('===make_domain==', mydomain, treeNode.special_domain)

            if (treeNode.special_domain){
                mydomain = mydomain.concat([treeNode.special_domain]);
            }else{

                console.info('===make_domain==2', treeNode.model,  treeNode.domain_fd)
                if (treeNode.model == 'res.parter'){
                    if (treeNode == -1) {
                        mydomain = mydomain.concat([[[self.field, "=", 0]]]);
                    } else {
                        mydomain = mydomain.concat([['|',
                        [self.field, 'in', [treeNode.id]],
                        [self.field, 'child_of', [treeNode.id]],
                        ]]);
                    }
                }else if(treeNode.model == 'personal.partner'){
                        mydomain = mydomain.concat([[[treeNode.domain_fd, "in", [treeNode.id]]]]);
                }else if(treeNode.model == 'res.users'){
                        mydomain = mydomain.concat([[[treeNode.domain_fd, "in", [treeNode.id]]]]);
                }


            }
            return {contexts: self.initialState.context, domains: mydomain, groupbys: self.initialState.groupedBy}
        },

        on_click_treeitem: function (event, treeId, treeNode, clickFlag) {
            if (treeNode.id == 'newmail') {
                return this.do_action({
                    type: 'ir.actions.act_window',
                    view_type: 'form',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {'default_force_notify_email':1 },
                    res_model: 'mail.compose.message',
                });
            };


            console.info('=====on_click_treeitem==', event, treeId, treeNode, clickFlag);
            if (!treeNode.no_action) {
                var domain = this.make_domain(treeNode);
                console.info('=====domain==', domain);
                this.trigger_up('search', domain);
            }


        },

        on_category_expand: function () {
            if (this.$ztree) {
                this.bExpand = !this.bExpand;
                this.$ztree.expandAll(this.bExpand);
            }
        }
    });
});
