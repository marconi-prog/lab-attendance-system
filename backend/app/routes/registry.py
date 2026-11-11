"""Declaração de rotas da API.

Cada rota é declarada uma única vez com `api_route`, que:
  1. aplica autenticação/autorização por perfil;
  2. valida corpo JSON e query string com Pydantic;
  3. registra metadados usados para gerar o documento OpenAPI (/api/docs).

Assim a documentação nunca diverge da implementação.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.middlewares.authorization import roles_required
from app.models import UserRole
from app.utils.errors import ValidationError

PUBLIC = None
AUTHENTICATED: tuple[UserRole, ...] = ()


@dataclass
class RouteSpec:
    path: str
    methods: list[str]
    summary: str
    tag: str
    roles: tuple[UserRole, ...] | None
    body: type[BaseModel] | None = None
    query: type[BaseModel] | None = None
    response: type[BaseModel] | None = None
    response_example: Any = None
    status: int = 200
    refresh: bool = False
    description: str = ""
    errors: list[int] = field(default_factory=list)


REGISTRY: list[RouteSpec] = []


def _format_errors(exc: PydanticValidationError) -> list[dict]:
    return [
        {"field": ".".join(str(p) for p in err["loc"]) or None, "message": err["msg"], "type": err["type"]}
        for err in exc.errors(include_url=False, include_input=False)
    ]


def _parse(model: type[BaseModel], data: Any) -> BaseModel:
    try:
        return model.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError("Dados inválidos.", details=_format_errors(exc)) from exc


def _to_response(result: Any, status: int) -> Response | tuple:
    if isinstance(result, Response):
        return result
    if isinstance(result, tuple):
        payload, status = result
    else:
        payload = result
    if payload is None:
        return "", 204
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    return jsonify(payload), status


def api_route(
    bp: Blueprint,
    rule: str,
    *,
    methods: list[str] | None = None,
    summary: str,
    roles: tuple[UserRole, ...] | None = AUTHENTICATED,
    body: type[BaseModel] | None = None,
    query: type[BaseModel] | None = None,
    response: type[BaseModel] | None = None,
    response_example: Any = None,
    status: int = 200,
    refresh: bool = False,
    description: str = "",
    errors: list[int] | None = None,
) -> Callable:
    methods = methods or ["GET"]

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def handler(**path_params):
            kwargs: dict[str, Any] = dict(path_params)
            if body is not None:
                if not request.is_json:
                    raise ValidationError("O corpo da requisição deve ser JSON (Content-Type: application/json).")
                kwargs["body"] = _parse(body, request.get_json(silent=True) or {})
            if query is not None:
                kwargs["query"] = _parse(query, request.args.to_dict())
            return _to_response(view(**kwargs), status)

        final = handler if roles is PUBLIC else roles_required(*roles, refresh=refresh)(handler)
        bp.add_url_rule(rule, endpoint=view.__name__, view_func=final, methods=methods)

        full_path = (bp.url_prefix or "") + rule
        REGISTRY.append(
            RouteSpec(
                path=re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", full_path),
                methods=methods,
                summary=summary,
                tag=bp.name,
                roles=roles,
                body=body,
                query=query,
                response=response,
                response_example=response_example,
                status=status,
                refresh=refresh,
                description=description or (view.__doc__ or "").strip(),
                errors=errors or [],
            )
        )
        return view

    return decorator
