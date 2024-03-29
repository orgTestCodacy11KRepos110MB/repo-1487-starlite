from typing import Tuple, cast

import pytest

from starlite import Controller, HTTPRoute, Request, Router, Starlite
from starlite.handlers import HTTPRouteHandler
from starlite.openapi.path_item import create_path_item
from starlite.utils import find_index
from tests.openapi.utils import PersonController


@pytest.fixture()
def route() -> HTTPRoute:
    app = Starlite(route_handlers=[PersonController], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/{service_id}/person/{person_id}")
    return cast("HTTPRoute", app.routes[index])


@pytest.fixture()
def routes_with_router() -> Tuple[HTTPRoute, HTTPRoute]:
    class PersonControllerV2(PersonController):
        pass

    router_v1 = Router(path="/v1", route_handlers=[PersonController])
    router_v2 = Router(path="/v2", route_handlers=[PersonControllerV2])
    app = Starlite(route_handlers=[router_v1, router_v2], openapi_config=None)
    index_v1 = find_index(app.routes, lambda x: x.path_format == "/v1/{service_id}/person/{person_id}")
    index_v2 = find_index(app.routes, lambda x: x.path_format == "/v2/{service_id}/person/{person_id}")
    return cast("HTTPRoute", app.routes[index_v1]), cast("HTTPRoute", app.routes[index_v2])


@pytest.fixture()
def route_with_multiple_methods() -> HTTPRoute:
    class MultipleMethodsRouteController(Controller):
        path = "/"

        @HTTPRouteHandler("/", http_method=["GET", "HEAD"])
        async def root(self, *, request: Request[str, str]) -> None:
            pass

    app = Starlite(route_handlers=[MultipleMethodsRouteController], openapi_config=None)
    index = find_index(app.routes, lambda x: x.path_format == "/")
    return cast("HTTPRoute", app.routes[index])


def test_create_path_item(route: HTTPRoute) -> None:
    schema = create_path_item(route=route, create_examples=True, plugins=[], use_handler_docstrings=False)
    assert schema.delete
    assert schema.delete.operationId == "DeletePerson"
    assert schema.get
    assert schema.get.operationId == "GetPersonById"
    assert schema.patch
    assert schema.patch.operationId == "PartialUpdatePerson"
    assert schema.put
    assert schema.put.operationId == "UpdatePerson"


def test_unique_operation_ids_for_multiple_http_methods(route_with_multiple_methods: HTTPRoute) -> None:
    schema = create_path_item(
        route=route_with_multiple_methods, create_examples=True, plugins=[], use_handler_docstrings=False
    )
    assert schema.get
    assert schema.get.operationId
    assert schema.head
    assert schema.head.operationId
    assert schema.get.operationId != schema.head.operationId


def test_routes_with_different_paths_should_generate_unique_operation_ids(
    routes_with_router: Tuple[HTTPRoute, HTTPRoute]
) -> None:
    route_v1, route_v2 = routes_with_router
    schema_v1 = create_path_item(route=route_v1, create_examples=True, plugins=[], use_handler_docstrings=False)
    schema_v2 = create_path_item(route=route_v2, create_examples=True, plugins=[], use_handler_docstrings=False)
    assert schema_v1.get
    assert schema_v2.get
    assert schema_v1.get.operationId != schema_v2.get.operationId


def test_create_path_item_use_handler_docstring_false(route: HTTPRoute) -> None:
    schema = create_path_item(route=route, create_examples=True, plugins=[], use_handler_docstrings=False)
    assert schema.get
    assert schema.get.description is None
    assert schema.patch
    assert schema.patch.description == "Description in decorator"


def test_create_path_item_use_handler_docstring_true(route: HTTPRoute) -> None:
    schema = create_path_item(route=route, create_examples=True, plugins=[], use_handler_docstrings=True)
    assert schema.get
    assert schema.get.description == "Description in docstring."
    assert schema.patch
    assert schema.patch.description == "Description in decorator"
    assert schema.put
    assert schema.put.description
    # make sure multiline docstring is fully included
    assert "Line 3." in schema.put.description
    # make sure internal docstring indentation used to line up with the code
    # is removed from description
    assert "    " not in schema.put.description
