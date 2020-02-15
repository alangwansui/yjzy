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
                        enable: false,
                        nocheckInherit: true,

                    },

                    callback: {
                        onClick: _.bind(self.on_click_treeitem, self),
                        onCheck: _.bind(self.on_check_treeitem, self),

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
            //var mydomain = [self.initialState.domain];


            var mydomain = this.getParent().searchview.build_search_data().domains;

            console.info('===initdomain==', mydomain);

            //console.info('===getActiveDomain==', this.getActiveDomain() );



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
                        ]]);
                    }
                }else if(treeNode.model == 'personal.partner'){
                        mydomain = mydomain.concat([[[treeNode.domain_fd, "in", [treeNode.dbid]]]]);
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

        on_category_expand: function () {
            if (this.$ztree) {
                this.bExpand = !this.bExpand;
                this.$ztree.expandAll(this.bExpand);
            }
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
                    context: {'default_force_notify_email':1 },
                    res_model: 'mail.compose.message',
                });
            }

            //判断当前模型，决定是否切换模型

            if(this.modelName == 'mail.message'){
                if(treeNode.id == 'mail_list_draft') {
                    //消息下点击草稿，跳转草稿模型
                    return this.do_action({
                        name: '草稿箱',
                        type: 'ir.actions.act_window',
                        view_type: 'tree,form',
                        view_mode: 'form',
                        views: [[false, 'list'], [false, 'form']],
                        //target: 'new',
                        context: { },
                        res_model: 'mail.compose.message',
                        clear_breadcrumbs: true,
                    });
                }else{
                    //消息下点击 非草稿，启用过滤
                    //console.info('=====on_click_treeitem==', event, treeId, treeNode, clickFlag);
                    if (!treeNode.no_action) {
                        var domain = this.make_domain(treeNode);
                        console.info('=====domain==', domain);
                        this.trigger_up('search', domain);
                    }



                }

            }else{
                //撰稿模型下点击非 草稿
                //console.info('=====撰稿模型下点击非 草稿==', odoo, this.modelName,treeNode.id);
                if(treeNode.id != 'mail_list_draft') {

                    //UserMenu.menu_click(1);

                    return this.do_action({
                        name: treeNode.name,
                        type: 'ir.actions.act_window',
                        view_type: 'tree,form',
                        view_mode: 'form',
                        views: [[false, 'list'], [false, 'form']],
                        //target: 'new',
                        context: {},
                        res_model: 'mail.message',
                        clear_breadcrumbs: true,
                    });
                //撰稿模型下点击 草稿
                }else{
                    //console.info('=====撰稿模型下点击 草稿==');


                }



            }








        },

        on_check_treeitem: function(event, treeId, treeNode){
            //console.info(treeNode.checked);
            var mydomain = this.get_check_domain();

            var search_param = {contexts: this.initialState.context, domains: mydomain, groupbys: this.initialState.groupedBy};

            this.trigger_up('search', search_param);
        },

        get_check_domain: function(){
            //console.info('>>get_check_domain>>');

            var dm = [this.initialState.domain];

            var checked_nodes = this.$ztree.getCheckedNodes();

            for(var i in checked_nodes){
                var nd = checked_nodes[i];
                //console.info('===', checked_nodes[i], checked_nodes[i].special_domain);

                dm.concat(  nd.special_domain );
            }

            //console.info('>>get_check_domain>>', dm);

            return dm


        },

        filter_check_node: function(){

        }




    });
});
