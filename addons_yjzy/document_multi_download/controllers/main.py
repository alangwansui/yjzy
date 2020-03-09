# -*- coding: utf-8 -*-

import logging
import zipfile

try:
    from StringIO import StringIO as ZipIO
except ImportError:
    from io import BytesIO as ZipIO

from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.main import content_disposition

_logger = logging.getLogger(__name__)

class Binary(http.Controller):

    @http.route('/web/binary/download_attachment', type='http', auth='user')
    def download_attachment(self, model, id):
        attachment_model = request.env['ir.attachment']
        attachment_ids = attachment_model.search([('res_model', '=', model), ('res_id', '=', id)])
        file_dict = {}
        for attachment_id in attachment_ids:
            file_store = attachment_id.store_fname
            if file_store:
                file_name = attachment_id.name
                file_path = attachment_id._full_path(file_store)
                file_dict["%s:%s" % (file_store, file_name)] = dict(path=file_path, name=file_name)
        _logger.info("download attachment ready : %s" % file_dict)

        record_value = request.env[model].search_read(domain=[('id', '=', id)], fields=['name'])
        zip_filename = "attachment"
        if len(record_value) == 1:
            record_name = record_value[0].get("name", "")
            if record_name:
                zip_filename = record_name
        zip_filename = "%s.zip" % zip_filename

        strIO = ZipIO()
        zip_file = zipfile.ZipFile(strIO, "w", zipfile.ZIP_DEFLATED)
        for file_key, file_info in file_dict.items():
            zip_file.write(file_info["path"], file_info["name"])
        zip_file.close()
        _logger.info("download attachment pack : %s" % zip_filename)
        # _logger.info("download attachment pack : %s(%s)" % (zip_filename, strIO.len))

        return request.make_response(strIO.getvalue(), 
            headers=[('Content-Type', 'application/x-zip-compressed'), ('Content-Disposition', content_disposition(zip_filename))])
