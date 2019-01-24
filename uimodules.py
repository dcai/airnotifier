#!/usr/bin/python
# -*- coding: utf-8 -*-

import tornado.web


class AppSideBar(tornado.web.UIModule):
    def render(self, app, active=None):
        html = self.render_string("modules/sidebar.html", app=app, active=active)
        return html


class TabBar(tornado.web.UIModule):
    def render(self, app, active=None):
        html = self.render_string("modules/tabbar.html", app=app, active=active)
        return html


class NavBar(tornado.web.UIModule):
    def render(self, tab):
        html = self.render_string("modules/navbar.html", tab=tab)
        return html
