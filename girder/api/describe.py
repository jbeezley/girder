#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import cherrypy
import os

from girder.constants import ROOT_DIR, VERSION, PACKAGE_DIR
from . import docs, access
from .rest import Resource, RestException

"""
Whenever we add new return values or new options we should increment the
maintenance value. Whenever we add new endpoints, we should increment the minor
version. If we break backward compatibility in any way, we should increment the
major version.  This value is derived from the version number given in
the top level package.json.
"""
API_VERSION = VERSION['apiVersion']

SWAGGER_VERSION = "1.2"

# Save the path to the swagger-ui on load
_swagger_path = os.path.join(ROOT_DIR, 'clients')

if not os.path.exists(_swagger_path):
    # fallback to a web root served inside the girder package
    _swagger_path = os.path.join(PACKAGE_DIR, 'clients')

_swagger_path = os.path.join(
    _swagger_path,
    'web',
    'static',
    'built',
    'swagger',
    'swagger.html'
)


class Description(object):
    """
    This class provides convenient chainable semantics to allow api route
    handlers to describe themselves to the documentation. A route handler
    function can set a description property on itself to an instance of this
    class in order to describe itself.
    """
    def __init__(self, summary):
        self._summary = summary
        self._params = []
        self._responses = []
        self._consumes = []
        self._responseClass = None
        self._notes = None

    def asDict(self):
        """
        Returns this description object as an appropriately formatted dict
        """
        resp = {
            'summary': self._summary,
            'notes': self._notes,
            'parameters': self._params,
            'responseMessages': self._responses,
            'responseClass': self._responseClass
        }

        if self._consumes is not None:
            resp['consumes'] = self._consumes

        return resp

    def responseClass(self, obj):
        self._responseClass = obj
        return self

    def param(self, name, description, paramType='query', dataType='string',
              required=True, enum=None):
        """
        This helper will build a parameter declaration for you. It has the most
        common options as defaults, so you won't have to repeat yourself as much
        when declaring the APIs.
        """
        param = {
            'name': name,
            'description': description,
            'paramType': paramType,
            'type': dataType,
            'allowMultiple': False,
            'required': required
        }
        if enum:
            param['enum'] = enum
        self._params.append(param)
        return self

    def consumes(self, value):
        self._consumes.append(value)
        return self

    def notes(self, notes):
        self._notes = notes
        return self

    def errorResponse(self, reason='A parameter was invalid.', code=400):
        """
        This helper will build an errorResponse declaration for you. Many
        endpoints will be able to use the default parameter values for one of
        their responses.
        """
        self._responses.append({
            'message': reason,
            'code': code
        })
        return self


class ApiDocs(object):
    exposed = True

    def GET(self, **params):
        return cherrypy.lib.static.serve_file(
            _swagger_path,
            content_type='text/html'
        )

    def DELETE(self, **params):
        raise cherrypy.HTTPError(405)

    def PATCH(self, **params):
        raise cherrypy.HTTPError(405)

    def POST(self, **params):
        raise cherrypy.HTTPError(405)

    def PUT(self, **params):
        raise cherrypy.HTTPError(405)


class Describe(Resource):
    def __init__(self):
        self.route('GET', (), self.listResources, nodoc=True)
        self.route('GET', (':resource',), self.describeResource, nodoc=True)

    @access.public
    def listResources(self, params):
        return {
            'apiVersion': API_VERSION,
            'swaggerVersion': SWAGGER_VERSION,
            'basePath': cherrypy.url(),
            'apis': [{'path': '/{}'.format(resource)}
                     for resource in sorted(docs.discovery)]
        }

    def _compareRoutes(self, routeOp1, routeOp2):
        """
        Order routes based on path.  Alphabetize this, treating parameters as
        before fixed paths.
        :param routeOp1: tuple of (route, op) to compare
        :param routeOp2: tuple of (route, op) to compare
        :returns: negative if routeOp1<routeOp2, positive if routeOp1>routeOp2.
        """
        # replacing { with ' ' is a simple way to make ASCII sort do what we
        # want for routes.  We would have to do more work if we allow - in
        # routes
        return cmp(routeOp1[0].replace('{', ' '), routeOp2[0].replace('{', ' '))

    def _compareOperations(self, op1, op2):
        """
        Order operations in our preferred method order.  methods not in our
        list are put afterwards and sorted alphabetically.
        :param op1: first operation dictionary to compare.
        :param op2: second operation dictionary to compare.
        :returns: negative if op1<op2, positive if op1>op2.
        """
        methodOrder = ['GET', 'PUT', 'POST', 'PATCH', 'DELETE']
        method1 = op1.get('httpMethod', '')
        method2 = op2.get('httpMethod', '')
        if method1 in methodOrder and method2 in methodOrder:
            return cmp(methodOrder.index(method1), methodOrder.index(method2))
        if method1 in methodOrder or method2 in methodOrder:
            return cmp(method1 not in methodOrder, method2 not in methodOrder)
        return cmp(method1, method2)

    @access.public
    def describeResource(self, resource, params):
        if resource not in docs.routes:
            raise RestException('Invalid resource: {}'.format(resource))
        return {
            'apiVersion': API_VERSION,
            'swaggerVersion': SWAGGER_VERSION,
            'basePath': os.path.dirname(os.path.dirname(cherrypy.url())),
            'models': docs.models,
            'apis': [{'path': route,
                      'operations': sorted(op, self._compareOperations)}
                     for route, op in sorted(docs.routes[resource].iteritems(),
                                             self._compareRoutes)]
        }
