# -*- coding: utf-8 -*-

from odoo import models, fields, api


@api.model
def collect_hs_lines(self, lines):
    res = {}
    for line in lines:
        hs = line.product_id.hs_id
        if hs in res:
            res[hs].append(line)
        else:
            res[hs]=[line]
    return res

    #{'hs1':  [line1, line2, line3], 'hs2': [line3, line4]}
