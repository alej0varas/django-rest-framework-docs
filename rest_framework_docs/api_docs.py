from importlib import import_module
from django.conf import settings
from django.core.exceptions import ViewDoesNotExist
from django.core.urlresolvers import RegexURLResolver, RegexURLPattern
from django.utils.module_loading import import_string
from rest_framework.views import APIView
from rest_framework_docs.api_endpoint import ApiEndpoint


class ApiDocumentation(object):

    def __init__(self, drf_router=None):
        self.endpoints = []
        self.drf_router = drf_router
        try:
            root_urlconf = import_string(settings.ROOT_URLCONF)
        except ImportError:
            # Handle a case when there's no dot in ROOT_URLCONF
            root_urlconf = import_module(settings.ROOT_URLCONF)
        if hasattr(root_urlconf, 'urls'):
            self.get_all_view_names(root_urlconf.urls.urlpatterns)
        else:
            self.get_all_view_names(root_urlconf.urlpatterns)

    def get_all_view_names(self, urlpatterns, parent_regex=''):
        for pattern in urlpatterns:
            if isinstance(pattern, RegexURLResolver):
                regex = '' if pattern._regex == "^" else pattern._regex
                self.get_all_view_names(urlpatterns=pattern.url_patterns, parent_regex=parent_regex + regex)
            elif isinstance(pattern, RegexURLPattern) and self._is_drf_view(pattern) and not self._is_format_endpoint(pattern):
                api_endpoint = ApiEndpoint(pattern, parent_regex, self.drf_router)
                self.endpoints.append(api_endpoint)

    # Modified version of django-extensions `show_urls` command method
    def extract_views_from_urlpatterns(self, urlpatterns, base='', namespace=None):
        """Return all the views in a list of urlpatterns"""
        views = []
        for p in urlpatterns:
            if isinstance(p, RegexURLPattern):
                try:
                    views.append((base + p.regex.pattern, p, namespace))
                except ViewDoesNotExist:
                    continue
            elif isinstance(p, RegexURLResolver):
                try:
                    patterns = p.url_patterns
                except ImportError:
                    continue
                if namespace and p.namespace:
                    _namespace = '{0}:{1}'.format(namespace, p.namespace)
                else:
                    _namespace = (p.namespace or namespace)
                views.extend(self.extract_views_from_urlpatterns(patterns, base + p.regex.pattern, namespace=_namespace))
            elif hasattr(p, '_get_callback'):
                try:
                    views.append((base + p.regex.pattern, p, namespace))
                except ViewDoesNotExist:
                    continue
            elif hasattr(p, 'url_patterns') or hasattr(p, '_get_url_patterns'):
                try:
                    patterns = p.url_patterns
                except ImportError:
                    continue
                views.extend(self.extract_views_from_urlpatterns(patterns, base + p.regex.pattern, namespace=namespace))
            else:
                raise TypeError("%s does not appear to be a urlpattern object" % p)
        return views

    def _is_drf_view(self, pattern):
        """
        Should check whether a pattern inherits from DRF's APIView
        """
        return hasattr(pattern.callback, 'cls') and issubclass(pattern.callback.cls, APIView)

    def _is_format_endpoint(self, pattern):
        """
        Exclude endpoints with a "format" parameter
        """
        return '?P<format>' in pattern._regex

    def get_endpoints(self):
        return self.endpoints
