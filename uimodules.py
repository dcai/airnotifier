#!/usr/bin/python
# -*- coding: utf-8 -*-

import tornado.web

class AppBlockModule(tornado.web.UIModule):
    def render(self, app):
        html = self.render_string("modules/app.html", app=app)
        return html


class AppSideBar(tornado.web.UIModule):
    def render(self, app, active=None):
        html = self.render_string("modules/sidebar.html", app=app, active=active)
        return html
