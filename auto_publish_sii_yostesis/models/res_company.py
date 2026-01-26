# -*- coding: utf-8 -*-

from odoo import _, fields, models, api
import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from odoo.exceptions import UserError
# from ..constants import *
from datetime import datetime

logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    sii_date_start = fields.Date(string="SII Start Date")
    sii_auto_upload = fields.Boolean(string="AutoPublish SII", default=False)
    sii_exonerated = fields.Boolean(string="SII Exonerated 390", default=False, help="The company utilizes SII and is Exonerated from model 390")
