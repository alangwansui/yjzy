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


            var ctx = self.getContext();
            _.extend(ctx, this.initialState.context);

            console.info('=ctx==', ctx, this.initialState.context);

            var rpc = this._rpc({
                model: self.modelName,
                method: 'get_categories',
                args: [],
                context: ctx

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
                //$div.appendTo(self.$el);

//append，appendTo，after，before，insertAfter，insertBefore，appendChild

                var setting = {
                    check: {
                        enable: true,
                        nocheckInherit: true,

                    },

                    callback: {
                        onClick: _.bind(self.on_click_treeitem, self),


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


        on_category_expand: function () {
            if (this.$ztree) {
                this.bExpand = !this.bExpand;
                this.$ztree.expandAll(this.bExpand);
            }
        },

        make_domain_message: function (treeNode) {
            var self = this;
            var mydomain = this.getParent().searchview.build_search_data().domains;
            if (treeNode.special_domain){
                mydomain = mydomain.concat([treeNode.special_domain]);
            }else{
                console.info('===make_domain==2', treeNode.model,  treeNode.domain_fd)
                if (treeNode.model == 'res.partner'){
                    if (treeNode == -1) {
                        mydomain = mydomain.concat([[[self.field, "=", 0], ['state_delete', '!=', 'recycle'],]]);
                    } else {
                        mydomain = mydomain.concat([['|',
                        [self.field, 'in', [treeNode.dbid]],
                        [self.field, 'child_of', [treeNode.dbid]],
                        ['state_delete', '!=', 'recycle'],
                        ['is_repeated', '=', false],
                        ]]);
                    }
                }else if(treeNode.model == 'personal.partner'){
                        mydomain = mydomain.concat([[[treeNode.domain_fd, "in", [treeNode.dbid]]]]);
                }else if(treeNode.model == 'res.users'){
                        mydomain = mydomain.concat([['|',
                        ['alias_user_id', '=', [treeNode.dbid]],'&',
                        ['author_id.user_ids', '=', [treeNode.dbid]],
                        ['process_type', '=', 'out'],
                        ]]);
                }


            }
            return {contexts: self.initialState.context, domains: mydomain, groupbys: self.initialState.groupedBy}
        },

        make_domain_compose: function (treeNode) {
            var self = this;
            var mydomain = this.getParent().searchview.build_search_data().domains;
            if (treeNode.special_domain){
                mydomain = mydomain.concat([treeNode.special_domain]);
            }else{
                console.info('===make_domain==2', treeNode.model,  treeNode.domain_fd)
                if (treeNode.model == 'res.partner'){
                    if (treeNode == -1) {
                        mydomain = mydomain.concat([[[self.field, "=", 0], ['state_delete', '!=', 'recycle'],]]);
                    } else {
                        mydomain = mydomain.concat([[['all_partner_ids', 'in', [treeNode.dbid]]]]);
                    }
                }else if(treeNode.model == 'personal.partner'){
                        mydomain = mydomain.concat([[['all_personal_ids', "in", [treeNode.dbid]]]]);
                }else if(treeNode.model == 'res.users'){
                        mydomain = mydomain.concat([['|',
                        ['all_user_ids', 'in', [treeNode.dbid]],
                        ['all_user_ids.sup_message_uids', 'in', [treeNode.dbid]],
                        ['state_delete', '!=', 'recycle'],
                        ]]);
                }


            }
            return {contexts: self.initialState.context, domains: mydomain, groupbys: self.initialState.groupedBy}
        },


        on_click_treeitem: function (event, treeId, treeNode, clickFlag) {
            console.info('=on_click_treeitem=:', this.modelName);


            console.info('=on_click_treeitem=2:',this.initialState);



            //撰写邮件
            if (treeNode.id == 'newmail') {
                return this.do_action({
                    type: 'ir.actions.act_window',
                    view_type: 'form',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {default_force_notify_email:1 , default_subject: ' '},
                    res_model: 'mail.compose.message',
                });
            }

            //判断当前模型，决定是否切换模型

            if(this.modelName == 'mail.message'){
                //消息下点击 非草稿，启用过滤
                //console.info('=====on_click_treeitem==', event, treeId, treeNode, clickFlag);
                if (!treeNode.no_action) {
                    var domain = this.make_domain_message(treeNode);
                    console.info('=====domain==', domain);
                    this.trigger_up('search', domain);
                }

            }else{
                //撰稿模型下点击非 草稿
                //console.info('=====撰稿模型下点击非 草稿==', odoo, this.modelName,treeNode.id);
                if (!treeNode.no_action) {
                    var domain = this.make_domain_compose(treeNode);
                    console.info('=====domain==', domain);
                    this.trigger_up('search', domain);
                }



            }








        }








    });
});
