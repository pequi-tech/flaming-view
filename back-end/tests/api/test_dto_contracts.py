"""DTOs are the documented and runtime-validated contract at every HTTP route."""
import unittest

from fastapi.testclient import TestClient

from tests.fixtures import ApiCase, PANTANAL


class TestOutputDTOs(ApiCase):
    def test_success_routes_return_their_declared_shapes(self):
        requests = [
            ('/health', {}, {'status', 'release', 'years', 'realtime'}),
            ('/method', {}, {'release', 'contract_version', 'years', 'rows', 'unit', 'metrics', 'quality',
                             'model', 'ipp', 'rules', 'sources', 'partial_years', 'coverage_2026'}),
            ('/calendar', {'bbox': PANTANAL}, {'area', 'unit', 'release', 'baseline_years', 'months'}),
            ('/series', {'bbox': PANTANAL}, {'area', 'unit', 'release', 'years'}),
            ('/cells', {'year': 2013, 'month': 8}, {'year', 'month', 'res', 'unit', 'release', 'cells',
                                                    'layer', 'horizon', 'shape', 'h3_res', 'cuts'}),
            ('/current', {'bbox': PANTANAL}, {
                'area', 'unit', 'year', 'month', 'day', 'days_in_month', 'value_to_date', 'projected',
                'median', 'p75', 'p90', 'ratio', 'level', 'source', 'satellite', 'stale',
            }),
        ]
        for path, params, expected in requests:
            with self.subTest(path=path):
                response = self.client.get(path, params=params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.json()), expected)

    def test_openapi_declares_response_dtos(self):
        schema = self.client.get('/openapi.json').json()
        for path, expected in {
            '/health': 'HealthResponseDTO', '/method': 'MethodResponseDTO',
            '/calendar': 'CalendarResponseDTO', '/series': 'SeriesResponseDTO',
            '/cells': 'CellsResponseDTO', '/current': 'CurrentResponseDTO',
        }.items():
            with self.subTest(path=path):
                response = schema['paths'][path]['get']['responses']['200']['content']['application/json']['schema']
                self.assertEqual(response['$ref'], f'#/components/schemas/{expected}')


class TestErrorDTOs(ApiCase):
    def test_validation_errors_share_one_envelope(self):
        for path, params in [
            ('/calendar', {'bbox': 'invalid'}),
            ('/calendar', {'bbox': PANTANAL, 'from_year': 2013, 'to_year': 2012}),
            ('/cells', {'year': 2013, 'month': 13}),
            ('/cells', {'year': 2013, 'month': 8, 'res': 3}),
        ]:
            with self.subTest(path=path, params=params):
                response = self.client.get(path, params=params)
                self.assertEqual(response.status_code, 422)
                body = response.json()
                self.assertEqual(set(body), {'error'})
                self.assertEqual(body['error']['code'], 'invalid_request')
                self.assertTrue(body['error']['details'])

    def test_not_found_uses_error_dto(self):
        response = self.client.get('/not-a-route')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error']['code'], 'not_found')

    def test_unexpected_route_error_is_safe_and_standardized(self):
        app = self.client.app

        @app.get('/test-error')
        def fail():
            raise RuntimeError('sensitive internal detail')

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/test-error')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {
            'error': {'code': 'internal_error', 'message': 'Erro interno do serviço.'},
        })


if __name__ == '__main__':
    unittest.main()
