import logging

#  will choose the FIRST match it comes too
#  or define routes in your controller using @route(r'')
route_list = [
    # (r"/", my_controller.MyHandler ),
]


class route(object):
    """
    taken from http://gist.github.com/616347

    decorates RequestHandlers and builds up a list of routables handlers

    Tech Notes (or "What the *@# is really happening here?")
    --------------------------------------------------------

    Everytime @route('...') is called, we instantiate a new route object which
    saves off the passed in URI.  Then, since it's a decorator, the function is
    passed to the route.__call__ method as an argument.  We save a reference to
    that handler with our uri in our class level routes list then return that
    class to be instantiated as normal.

    Later, we can call the classmethod route.get_routes to return that list of
    tuples which can be handed directly to the tornado.web.Application
    instantiation.

    Example
    -------

    @route('/some/path')
    class SomeRequestHandler(RequestHandler):
        pass

    my_routes = route.get_routes()
    """

    _routes = []

    def __init__(self, uri):
        self._uri = uri

    def __call__(self, _handler):
        """gets called when we class decorate"""
        self._routes.append((self._uri, _handler))
        return _handler

    @classmethod
    def get_routes(self):
        return self._routes


class RouteLoader(object):
    """ taken from https://github.com/trendrr/whirlwind/blob/master/whirlwind/core/routes.py """

    @staticmethod
    def load(package_name, include_routes_file=True):
        loader = RouteLoader()
        return loader.init_routes(package_name, include_routes_file)

    def init_routes(self, package_name, include_routes_file=True):
        import pkgutil, sys

        package = __import__(package_name)
        controllers_module = sys.modules[package_name]

        prefix = controllers_module.__name__ + "."

        for importer, modname, ispkg in pkgutil.iter_modules(
            controllers_module.__path__, prefix
        ):
            logging.info("init route: %s" % modname)
            module = __import__(modname)

        # grab the routes defined via the route decorator
        url_routes = route.get_routes()

        # add the routes from our route file
        if include_routes_file:
            url_routes.extend(route_list)

        return url_routes
