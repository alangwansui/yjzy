odoo.define('odoo_inbox.page_note', function(require) {
    'use strict';

    require('web.dom_ready');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');

    // var _t = core._t;
    // setInterval(page_refresh, 5 * 60000);
    // new gnMenu(document.getElementById('gn-menu'));
    // $('#compose_partner').select2();
    // $('#reply_partner').select2();

    var datepickers_options = {
        calendarWeeks: true,
        icons: {
            time: 'fa fa-clock-o',
            date: 'fa fa-calendar',
            up: 'fa fa-chevron-up',
            down: 'fa fa-chevron-down'
        },
    }

    $('.snooze_custome_time').datetimepicker(datepickers_options);

    $(document).ready(function() {
        $(".message__summary").click(function() {
            var $remove = $(this);
            var message = $(this).data('message');
            console.log("/////user/////", message)
            $('#wrapper .message').removeClass("message--open").css('margin-top', '0%').css('margin-bottom', '0%');
            $(this).closest('.message').addClass("message--open");
            $(this).closest('.message').css('margin-top', '3%').css('margin-bottom', '3%');
            ajax.jsonRpc('/odoo/message_read', 'call', {
                message: message,
            }).then(function(data) {
                data['msg_unread']
                $remove.removeClass('gmail_unread');
                $remove.addClass('gmail_read');
            });
        });

        $(".message__details__header").click(function() {
            $(this).closest('.message').removeClass("message--open");
            $(this).closest('.message').css('margin-top', '0%').css('margin-bottom', '0%');
            $(this).parent().find('.message__details__footer_reply').hide()
            $(this).parent().find('.message__details__footer').show()

        });

        $('.right a.button-exit').click(function() {
            var para = $('para')
            $("#newmail").hide();
            $(this).parents().find('.min-hide input:text').val('')
            $(this).parents().find("#compose_partner").select2("val", "");
            $(this).parents().find('#header-newmail .note-editable').html('').html(para);
        });

        $('.list').click(function() {
            $('.head-menu .list').removeClass('active');
            $(this).addClass('active');
        });

        $('textarea.load_editor').each(function() {
            var $textarea = $(this);
            if (!$textarea.val().match(/\S/)) {
                $textarea.val("<p><br/></p>");
            }
            var $form = $textarea.closest('form');
            var toolbar = [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['history', ['undo', 'redo']],
            ];
            $textarea.summernote({
                height: 275,
                toolbar: toolbar,
                styleWithSpan: false,
                placeholder: 'Say something'
            });

            $form.on('click', 'button, .a-submit', function() {
                $textarea.html($form.find('.note-editable').code());
            });
        });


        $.ajax({
            url: 'https://api.github.com/emojis',
            async: false
        }).then(function(data) {
            window.emojis = Object.keys(data);
            window.emojiUrls = data;
        });;

        // document.emojiType = 'unicode'; // default: image

        document.emojiSource = '/odoo_inbox/static/src/img/';

        $('textarea.load_editor1').each(function() {
            var $textarea = $(this);
            if (!$textarea.val().match(/\S/)) {
                $textarea.val("<p><br/></p>");
            }
            var $form = $textarea.closest('form');
            var toolbar = [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['history', ['undo', 'redo']],
                // ['insert', ['emoji']],
                ['code', ['codeview']]
            ];
            $textarea.summernote({
                height: 100,
                toolbar: toolbar,
                styleWithSpan: false,
                hint: {
                    match: /:([\-+\w]+)$/,
                    search: function(keyword, callback) {
                        callback($.grep(emojis, function(item) {
                            return item.indexOf(keyword) === 0;
                        }));
                    },
                    template: function(item) {
                        var content = emojiUrls[item];
                        return '<img src="' + content + '" width="20" /> :' + item + ':';
                    },
                    content: function(item) {
                        var url = emojiUrls[item];
                        if (url) {
                            return $('<img />').attr('src', url).css('width', 20)[0];
                        }
                        return '';
                    }
                },
                callbacks: {
                    onKeyup: function(event) {
                        setTimeout(function(){
                            var content = $(".load_editor1").val().replace(/<\/?[^>]+(>|$)/g, "");
                            var entered = content.split(' ').pop();
                            if (entered.length > 1 && entered.substring(0,1) == '@') {
                                var search = entered.substring(1, entered.length);
                                rpc.query({
                                    model: 'res.partner', method: 'get_mention_suggestions',
                                    args: [search, 5]
                                }).then(function (res) {
                                    var scontent = '';
                                    $.each(res[0], function (index, suggestion) {
                                        var tml = '<li class="o_mention_proposition" data-id="'+ suggestion.id +'"><span class="o_mention_name">' + suggestion.name + '</span><span class="o_mention_info">(' + suggestion.email + ')</span></li>';
                                        scontent += tml;
                                    });
                                    $('div.o_composer_mention_dropdown ul').html(scontent);
                                    $('div.o_composer_mention_dropdown').addClass('open');
                                    $('div.o_composer_mention_dropdown').attr('data-content', entered);

                                    $('div.o_composer_mention_dropdown li').click(function() {
                                        var user_id = $(this).attr('data-id');
                                        var username = $(this).find('.o_mention_name').text();
                                        var data_content = $('div.o_composer_mention_dropdown').attr('data-content');
                                        var upt_content = $(".load_editor1").val().replace(data_content, username);
                                        $('.load_editor1').summernote('code', upt_content);

                                        var $input_user_ids = $(this).parents('.reply_body_content').find('input[name=users_ids]');
                                        if ($input_user_ids.val()) {
                                            var updated_values = $input_user_ids.val() + ',' + user_id;
                                            $input_user_ids.val(updated_values);
                                        } else {
                                            $input_user_ids.val(user_id);
                                        }
                                        $('div.o_composer_mention_dropdown').removeClass('open');
                                    });
                                });
                            } else {
                                $('div.o_composer_mention_dropdown').removeClass('open');
                            }
                        },200);
                    }
                }
            });

            $form.on('click', 'button, .a-submit', function() {
                // $textarea.html($form.find('.note-editable').code());
            });
        });

        $('.message__details__footer').click(function() {
            $(this).hide();
            $(this).next().show();
        });

        $('.reply_delete_bttn').click(function() {
            var para = $('para')
            $(this).parents('.message__details__footer_reply').hide();
            $(this).parents('.message__details__footer_reply').prev().show();
            $(this).parents().find('.reply_body_content .note-editable').html('').html(para);
            // $(this).parents().find('.reply_body_content input[type=file]').val('');

        });


        $('.starred_btn i').on('click', function() {
            var message = $(this).parent().data('message');
            console.log('message__________', message)
            if ($(this).hasClass('fa fa-star-o')) {
                var action = 'add'
                $(this).removeClass('fa fa-star-o').addClass('fa fa-star');
            } else {
                var action = 'remove'
                $(this).removeClass('fa fa-star').addClass('fa fa-star-o');
            }
            ajax.jsonRpc('/odoo/starred/message', 'call', {
                action: action,
                message: message
            }).then(function() {
                window.location.reload();
            });
        });

        $('.mark_as_done i').on('click', function() {
            $(this).css('color', 'green')
            var message = $(this).parent().data('message');
            var $remove = $(this)
            console.log('mark_as_done>>>>>', message)
            if (message) {
                return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                    model: 'mail.message',
                    method: 'set_message_done',
                    args: [message],
                    kwargs: {}
                });
                // .then(function(){
                //     console.log('ttttttttttttttttt')
                //     $remove.parents('.message__details__body').remove();
                //     // if ($remove.length === 1): {
                //     //     $remove.parents('.message').remove();
                //     // } else {
                //     //     $remove.parents('.message__details__body').remove();
                //     // }
                // });
            } else {
                return $.when();
            }
        });

        function validateEmail(email) {
    var re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(email);
}

        $('#compose_partner').select2({
            tags: true,
            width: '100%',
            placeholder: "To",
            allowClear: true,
            createTag: function (params) {
               var value = params.term;
                if(validateEmail(value)) {
                    return {
                      id: value,
                      text: value,
                      newTag: true,
                    };
                }
                return null;
              },
        }).on('select2:select', function (evt) {
            if (evt.params.data.newTag){
                ajax.jsonRpc('/odoo/partner_create', 'call', {
                    email_address: evt.params.data.text,
                }).then(function(data) {
                    $('#compose_partner option[value="'+evt.params.data.text+'"]').text(data.partner_name);
                    $('#compose_partner option[value="'+evt.params.data.text+'"]').attr('value', data.partner_id);1
                });
            }
        });

        function tags_dropdown_menu(){
            $('.tag-dropdown-menu, .label-container').click(function(e) {
                e.stopPropagation();
            });
            // $('.tag-dropdown-menu').find('input').change(function(e){
            //     $(this).closest('.tag-dropdown-menu').find('.apply_button').removeClass('hidden');
            // });
            $('.tag-dropdown-menu .apply_button a').click(function(e){
                var tag_ids = new Array();
                var this_val = $(this);
                var message_id = $(this).attr('data-message');
                var checked_box = $(this).closest('.tag_dropdown').find('input[type="checkbox"]:checked');
                $.each($(checked_box), function (key, value) {
                    tag_ids.push(parseInt($(value).val()));
                });
                var create_tag_input = $(this).closest('ul').find('.create_tag_input').val();
                if (message_id)
                {
                    if (!!create_tag_input)
                    {
                        create_tag_input = create_tag_input;
                    }
                    else
                    {
                        create_tag_input = false;
                    }
                    ajax.jsonRpc('/odoo/message_tag_assign', 'call', {
                        message_id: parseInt(message_id),
                        tag_ids: tag_ids,
                        create_tag_input: create_tag_input,
                    }).then(function(data) {
                        if(!!data.message_tag_list){
                            this_val.closest('.message').find('.message_tag_list_details_body').html(data.message_tag_list);
                            this_val.closest('.message').find('.message_tag_dropdown_details').html(data.message_tag_dropdown);
                            this_val.closest('.tag_dropdown').removeClass('open');
                            remove_tag_function();
                            tags_dropdown_menu();
                        }
                    });
                }
            });
          }
        tags_dropdown_menu();
        function remove_tag_function(){
            $('.remove_tag').click(function(e){
                var this_val = $(this);
                var tag_data = $(this).data();
                if (tag_data.tag && tag_data.message){
                    ajax.jsonRpc('/odoo/message_tag_delete', 'call', {
                        message_id: parseInt(tag_data.message),
                        tag_id: parseInt(tag_data.tag),
                    }).then(function(data) {
                          if(!!data.message_tag_list){
                            this_val.closest('.message').find('.message_tag_dropdown_details').html(data.message_tag_dropdown);
                             this_val.closest('.message').find('.message_tag_list_details_body').html(data.message_tag_list);
                            remove_tag_function();
                            tags_dropdown_menu();
                        }
                    });
                }
            });
        }
        remove_tag_function();

        $('.tag_edit_save_btn').click(function(e){
            $(this).closest('form').submit();
        }); 
        $('.tag_delete_save_btn').click(function(e){
            $(this).closest('form').submit();
        });
        $('.folder_edit_save_btn').click(function(e){
            $(this).closest('form').submit();
        }); 
        $('.folder_delete_save_btn').click(function(e){
            $(this).closest('form').submit();
        });
        $('.create_folder_input, .folder-dropdown-menu .apply_button').click(function(e) {
            e.stopPropagation();
        });
    });
});