from ..error import RequestSetupError, ResponseError, ResponseHandlingError
from ..objects.list import List


class Base(object):
    REST_CREATE = 'POST'
    REST_UPDATE = 'PATCH'
    REST_READ = 'GET'
    REST_LIST = 'GET'
    REST_DELETE = 'DELETE'
    DEFAULT_LIMIT = 10

    INCLUDES = []

    def __init__(self, client):
        self.client = client

    def get_resource_object(self, result):
        raise NotImplementedError()

    def get_resource_name(self):
        return self.__class__.__name__.lower()

    def get_params(self, include, params):
        if not include:
            return params

        if isinstance(include, str):
            include = [include]

        params = params if params else {}

        for inc in include:
            if inc not in self.INCLUDES:
                raise RequestSetupError("No such include for {}: {}".format(self.__class__.__name__, inc))

        params['include'] = ",".join(include)
        return params

    def create(self, data=None, **params):
        path = self.get_resource_name()
        result = self.perform_api_call(self.REST_CREATE, path, data, params)
        return self.get_resource_object(result)

    def get(self, resource_id, include=None, **params):
        path = self.get_resource_name() + '/' + str(resource_id)
        params = self.get_params(include, params)
        result = self.perform_api_call(self.REST_READ, path, params=params)
        return self.get_resource_object(result)

    def update(self, resource_id, data=None, **params):
        path = self.get_resource_name() + '/' + str(resource_id)
        result = self.perform_api_call(self.REST_UPDATE, path, data, params)
        return self.get_resource_object(result)

    def delete(self, resource_id, data=None):
        path = self.get_resource_name() + '/' + str(resource_id)
        return self.perform_api_call(self.REST_DELETE, path, data)

    def list(self, include=None, **params):
        path = self.get_resource_name()
        params = self.get_params(include, params)
        result = self.perform_api_call(self.REST_LIST, path, params=params)
        return List(result, self.get_resource_object({}).__class__, self.client)

    def perform_api_call(self, http_method, path, data=None, params=None):
        resp = self.client.perform_http_call(http_method, path, data, params)
        if 'application/hal+json' in resp.headers.get('Content-Type', ''):
            # set the content type according to the media type definition
            resp.encoding = 'utf-8'
        try:
            result = resp.json() if resp.status_code != 204 else {}
        except Exception:
            raise ResponseHandlingError(
                "Unable to decode Mollie API response (status code: {status}): '{response}'.".format(
                    status=resp.status_code, response=resp.text))
        if resp.status_code < 200 or resp.status_code > 299:
            if 'status' in result and (result['status'] < 200 or result['status'] > 299):
                # the factory will return the appropriate ResponseError subclass based on the result
                raise ResponseError.factory(result)
            else:
                raise ResponseHandlingError(
                    "Received HTTP error from Mollie API, but no status in payload "
                    "(status code: {status}): '{response}'.".format(
                        status=resp.status_code, response=resp.text))
        return result
