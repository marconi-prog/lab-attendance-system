"""Documento OpenAPI 3.1 gerado a partir do registro de rotas + Swagger UI.

Os schemas vêm dos modelos Pydantic declarados em `api_route` (corpo, query
e resposta). Todas as referências apontam para `#/components/schemas`, e o
documento é verificado por `openapi-spec-validator` nos testes.
"""
from __future__ import annotations

import copy
from typing import Any

from flask import Blueprint, current_app, jsonify
from pydantic import BaseModel

from app.routes.registry import PUBLIC, REGISTRY, RouteSpec
from app.schemas.common import ErrorResponse

docs_bp = Blueprint("docs", __name__, url_prefix="/api/docs")

REF_TEMPLATE = "#/components/schemas/{model}"

_ERROR_DESCRIPTIONS = {
    400: "Requisição inválida",
    401: "Não autenticado, token inválido, expirado ou revogado",
    403: "Perfil sem permissão para o recurso",
    404: "Recurso não encontrado",
    409: "Conflito com o estado atual",
    422: "Dados inválidos ou regra de negócio violada",
}

_ERROR_EXAMPLES = {
    401: {"error": {"code": "UNAUTHORIZED", "message": "Autenticação necessária."}},
    403: {"error": {"code": "FORBIDDEN", "message": "Você não tem permissão para acessar este recurso."}},
    404: {"error": {"code": "NOT_FOUND", "message": "Recurso não encontrado."}},
    409: {"error": {"code": "CONFLICT", "message": "A operação conflita com o estado atual."}},
    422: {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Dados inválidos.",
            "details": [{"field": "type", "message": "Input should be 'SP', 'SE' or 'SG'", "type": "enum"}],
        }
    },
}


class _Components:
    """Acumula os schemas Pydantic em components/schemas, sem duplicar."""

    def __init__(self) -> None:
        self.schemas: dict[str, Any] = {}

    def add_defs(self, schema: dict) -> dict:
        for name, definition in schema.pop("$defs", {}).items():
            self.schemas.setdefault(name, definition)
        return schema

    def ref(self, model: type[BaseModel], *, mode: str) -> dict:
        schema = self.add_defs(model.model_json_schema(ref_template=REF_TEMPLATE, mode=mode))
        self.schemas.setdefault(model.__name__, schema)
        return {"$ref": REF_TEMPLATE.format(model=model.__name__)}


def _simplify_optional(schema: dict) -> dict:
    """`anyOf: [X, null]` com default null → X (parâmetro opcional de query)."""
    schema = copy.deepcopy(schema)
    any_of = schema.get("anyOf")
    if any_of and len(any_of) == 2 and {"type": "null"} in any_of:
        inner = next(s for s in any_of if s != {"type": "null"})
        schema.pop("anyOf")
        schema = {**inner, **schema}
    if schema.get("default") is None:
        schema.pop("default", None)
    schema.pop("title", None)
    return schema


def _query_parameters(model: type[BaseModel], components: _Components) -> list[dict]:
    schema = components.add_defs(model.model_json_schema(ref_template=REF_TEMPLATE, mode="validation"))
    required = set(schema.get("required", []))
    params = []
    for name, prop in schema.get("properties", {}).items():
        prop = _simplify_optional(prop)
        param: dict[str, Any] = {"name": name, "in": "query", "required": name in required, "schema": prop}
        if prop.get("description"):
            param["description"] = prop.pop("description")
        params.append(param)
    return params


def _example(model: type[BaseModel]) -> Any:
    examples = (model.model_config.get("json_schema_extra") or {}).get("examples")  # type: ignore[union-attr]
    return examples[0] if examples else None


def _operation(spec: RouteSpec, method: str, components: _Components, tags: dict) -> dict:
    op: dict[str, Any] = {
        "tags": [tags.get(spec.tag, spec.tag)],
        "summary": spec.summary,
        "operationId": f"{method.lower()}_{spec.path.strip('/').replace('/', '_').replace('{', '').replace('}', '').replace('-', '_')}",
        "responses": {},
    }
    description = [spec.description] if spec.description else []

    params = [
        {"name": seg[1:-1], "in": "path", "required": True, "schema": {"type": "integer", "minimum": 1}}
        for seg in spec.path.split("/")
        if seg.startswith("{")
    ]
    if spec.query:
        params.extend(_query_parameters(spec.query, components))
    if params:
        op["parameters"] = params

    if spec.body:
        media: dict[str, Any] = {"schema": components.ref(spec.body, mode="validation")}
        if (example := _example(spec.body)) is not None:
            media["example"] = example
        op["requestBody"] = {
            # Corpo só é obrigatório quando o modelo tem algum campo obrigatório.
            "required": bool(spec.body.model_json_schema().get("required")),
            "content": {"application/json": media},
        }

    if spec.status == 204:
        op["responses"]["204"] = {"description": "Operação concluída (sem conteúdo)"}
    else:
        success: dict[str, Any] = {"description": "Sucesso" if spec.status == 200 else "Criado"}
        if spec.response:
            success["content"] = {"application/json": {"schema": components.ref(spec.response, mode="serialization")}}
        op["responses"][str(spec.status)] = success

    codes = set(spec.errors)
    if spec.body or spec.query:
        codes.add(422)
    if spec.roles is PUBLIC:
        op["security"] = []
    else:
        codes.add(401)
        if spec.roles:
            codes.add(403)
            description.append(f"**Perfis:** {', '.join(r.value for r in spec.roles)}.")
        if spec.refresh:
            op["security"] = [{"refreshToken": []}]
            description.append("Autentique com o **refresh token** (esquema `refreshToken`), não com o access token.")
        else:
            op["security"] = [{"bearerAuth": []}]
    error_ref = components.ref(ErrorResponse, mode="serialization")
    for code in sorted(codes):
        media = {"schema": error_ref}
        if code in _ERROR_EXAMPLES:
            media["example"] = _ERROR_EXAMPLES[code]
        op["responses"][str(code)] = {"description": _ERROR_DESCRIPTIONS.get(code, "Erro"), "content": {"application/json": media}}

    if description:
        op["description"] = "\n\n".join(description)
    return op


def build_openapi() -> dict:
    from app.routes import TAGS

    components = _Components()
    paths: dict[str, dict] = {}
    for spec in REGISTRY:
        for method in spec.methods:
            paths.setdefault(spec.path, {})[method.lower()] = _operation(spec, method, components, TAGS)
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "API — Sistema de Controle de Atendimento",
            "version": current_app.config["APP_VERSION"],
            "description": (
                "API REST do sistema de senhas do laboratório.\n\n"
                "**Autenticação:** faça `POST /api/auth/login`, clique em **Authorize** e cole o `access_token` "
                "em `bearerAuth` (o `refresh_token` vai em `refreshToken`, usado só em `/api/auth/refresh`).\n\n"
                "**Erros:** sempre no formato `{\"error\": {\"code\", \"message\", \"details\"}}`.\n\n"
                "**Datas:** ISO 8601 no fuso America/Recife.\n\n"
                "**Tempo real (Socket.IO):** namespace `/panel` (público, somente leitura: `ticket:called`, "
                "`ticket:recalled`, `panel:updated`) e `/staff` (JWT em `auth.token`: também `ticket:issued`, "
                "`ticket:updated`, `attendance:started`, `attendance:finished`, `queue:updated`)."
            ),
        },
        "servers": [{"url": "/", "description": "Este servidor"}],
        "tags": [{"name": name} for name in TAGS.values()],
        "paths": paths,
        "components": {
            "schemas": dict(sorted(components.schemas.items())),
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT", "description": "Access token"},
                "refreshToken": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT", "description": "Refresh token"},
            },
        },
    }


@docs_bp.get("/openapi.json")
def openapi_json():
    return jsonify(build_openapi())


_SWAGGER_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>API — Controle de Atendimento</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"
 integrity="sha384-wxLW6kwyHktdDGr6Pv1zgm/VGJh99lfUbzSn6HNHBENZlCN7W602k9VkGdxuFvPn" crossorigin="anonymous">
</head>
<body><div id="swagger"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"
 integrity="sha384-wmyclcVGX/WhUkdkATwhaK1X1JtiNrr2EoYJ+diV3vj4v6OC5yCeSu+yW13SYJep" crossorigin="anonymous"></script>
<script>
SwaggerUIBundle({
  url: "/api/docs/openapi.json",
  dom_id: "#swagger",
  persistAuthorization: true,
  displayRequestDuration: true,
  docExpansion: "list",
  filter: true,
  tryItOutEnabled: true,
  defaultModelsExpandDepth: 0
});
</script>
</body></html>"""


@docs_bp.get("")
@docs_bp.get("/")
def swagger_ui():
    return current_app.response_class(_SWAGGER_HTML, mimetype="text/html")
