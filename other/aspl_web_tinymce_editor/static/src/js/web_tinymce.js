odoo.define('aspl_web_tinymce_editor.web_tinymce', function (require) {
"use strict";

var editor_backend = require('web_editor.backend');
var config = require('web.config');
var is_tinymce = false;

var FieldTextHtmlSimple = editor_backend.FieldTextHtmlSimple.include({

    _renderEdit: function () {
        var self = this
        this.$textarea = $('<textarea>');
        this.$textarea.appendTo(this.$el);
        this._rpc({
                    model: 'ir.config_parameter',
                    method: 'get_param',
                    args: ['aspl_web_tinymce_editor.is_tinymce'],
                }, {
                    async: false
                })
                .then(function(res) {
                    if (res) {
                        is_tinymce = true
                    }
                })
        if (is_tinymce) {
            this.$el.find('textarea').attr("class", self.name);
            this.$el.find('textarea').attr("data-text-id", self.name);
            this.$textarea.val(self._textToHtml(self.value));
            setTimeout(function() {
                tinymce.init({
                    selector: '.oe_form_field_html_text textarea',
                    custom_ui_selector: '.' + self.name,
                    height: 300,
                    width: 'auto',
                    resize: false,
                    theme: 'modern',
                    plugins: [
                        'advlist autolink link image imagetools lists colorpicker insertdatetime charmap print fullpage fullscreen preview hr media table emoticons imagetools code nonbreaking pagebreak searchreplace tabfocus textcolor textpattern wordcount autosave save'
                    ],
                    autosave_interval: "5s",
                    image_advtab: true,
                    theme_advanced_buttons3_add: "save",
                    autosave_ask_before_unload: false,
                    save_enablewhendirty: true,
                    save_onsavecallback: function() {
                        $(document).find('.o_form_button_save').trigger('click')
                        alert("Record Saved")
                        $(document).find('.o_form_button_edit').trigger('click')
                    },
                    toolbar: 'undo redo save | formatselect | sizeselect |  fontselect |  fontsizeselect | bold italic underline forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | insertdatetime image media link table hr nonbreaking pagebreak | removeformat | fullscreen',
                });
            }, 100);
        } else {
            this.$textarea.summernote(this._getSummernoteConfig());
        }
        this.$content = this.$('.note-editable:first');
        this.$content.html(this._textToHtml(this.value));
        // trigger a mouseup to refresh the editor toolbar
        var mouseupEvent = $.Event('mouseup', {
            'setStyleInfoFromEditable': true
        });
    },

    _getValue: function () {
	    for (var inst in tinyMCE.editors) {
	    	    if (tinyMCE.editors[inst].getContent){
	    	        var id = '#'+tinyMCE.editors[inst].id
	    	    	if($(id).data('text-id') == this.name){
                        return tinyMCE.editors[inst].getContent()
	    	    	}
	    	    }
	    	}

    },
});
});