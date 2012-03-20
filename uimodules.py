#!/usr/bin/python
# -*- coding: utf-8 -*-

import tornado.web

class AppBlockModule(tornado.web.UIModule):
    def render(self, app):
        html = self.render_string("modules/app.html", app=app)
        return html
