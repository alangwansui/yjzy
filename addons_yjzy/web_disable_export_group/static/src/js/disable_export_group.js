/* Copyright 2016 Onestein
   Copyright 2018 Tecnativa - David Vidal
   License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl). */
odoo.define("web_disable_export_group", function(require) {
"use strict";

    var core = require("web.core");
    var Sidebar = require("web.Sidebar");
    var session = require("web.session");
    var _t = core._t;

    Sidebar.include({
        _addItems: function (sectionCode, items) {
            console.info('===', sectionCode, items);
            var _items = items;
            if (!session.is_superuser && sectionCode === 'other' && items.length && !session.group_export_data) {
                _items = _.reject(_items, {label:_t("Export")});
            }

            //<jon>
            var menu_action_id = this.env.context.params.action;  //当前菜单的action_id

            // 取消回收站
            var huishouzhan_action_id = 758; //数字为需要显示的actionid, 可以通过‘菜单’ 查询得到
            if(menu_action_id == huishouzhan_action_id){
                _items = _.reject(_items, {label: "放入回收站"});

            };
             var huishouzhan1_action_id = 757; //数字为需要显示的actionid, 可以通过‘菜单’ 查询得到
            if(menu_action_id == huishouzhan1_action_id){
                _items = _.reject(_items, {label: "放入回收站"});

            };
            var chexiaohuishou_action_id = 758; //数字为需要显示的actionid, 可以通过‘菜单’ 查询得到
            if(menu_action_id != chexiaohuishou_action_id){
                _items = _.reject(_items, {label: "撤销回收"});

            };
            var move_action_id = 719; //数字为需要显示的actionid, 可以通过‘菜单’ 查询得到
            if(menu_action_id != move_action_id){
                _items = _.reject(_items, {label: "Move message"});

            };

            var move_action_id = 1443; //数字为需要显示的actionid, 可以通过‘菜单’ 查询得到
            if(menu_action_id != move_action_id){
                _items = _.reject(_items, {label: "创建付款指令"});
            };


//            var cjyfsq_action_id = 1335; //数字为需要显示的actionid, 可以通过‘菜单’ 查询得到
//            if(menu_action_id != cjyfsq_action_id){
//                _items = _.reject(_items, {label: "创建应付申请"});
//
//            };

            var cjyfsq_action_id = [1386,1387,1385,1405,1406,1407]; //数字为需要显示的actionid, 可以通过‘菜单’ 查询得到
            if (cjyfsq_action_id.indexOf(menu_action_id) == -1){
                _items = _.reject(_items, {label: "创建应付申请"});

            };



            this._super(sectionCode, _items);
        },
    });
});
