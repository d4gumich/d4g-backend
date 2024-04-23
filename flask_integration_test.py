# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 23:11:25 2024

@author: socam
"""

import io
import unittest

from wsgi import app

class flaskintegrationtestcase(unittest.TestCase):
    
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        
    def test_get_metadata(self):
        for i in range(6):
            self.client.post(file , 5)