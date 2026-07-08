from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from spectree import SecurityScheme, SpecTree
from spectree.page import PAGE_TEMPLATES
from flask_jwt_extended import JWTManager
from sqlalchemy import select
from flask_cors import CORS

SWAGGER_UI_TEMPLATE = """
<!-- HTML for static distribution bundle build -->
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="SwaggerUI"/>
        <title>SwaggerUI</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
    </head>

    <body>
        <div id="swagger-ui"></div>

        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js" crossorigin></script>
        <script>
        window.onload = function() {{
        var full = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '');
        const ui = SwaggerUIBundle({{
            url: "{spec_url}",
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            layout: "StandaloneLayout",
            deepLinking: true,
            displayRequestDuration: true,
            persistAuthorization: true,
            tryItOutEnabled: true,
            oauth2RedirectUrl: full + "/{spec_path}/swagger/oauth2-redirect.html",
        }});
        ui.initOAuth({{
            clientId: "{client_id}",
            clientSecret: "{client_secret}",
            realm: "{realm}",
            appName: "{app_name}",
            scopeSeparator: "{scope_separator}",
            additionalQueryStringParams: {additional_query_string_params},
            useBasicAuthenticationWithAccessCodeGrant: {use_basic_authentication_with_access_code_grant},
            usePkceWithAuthorizationCodeGrant: {use_pkce_with_authorization_code_grant},
        }});

        window.ui = ui;
        }}
    </script>
    </body>
</html>"""

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
api = SpecTree(
    "flask",
    title="Flask Backend Template",
    version="v1.0",
    path="docs",
    validation_error_status=400,
    page_templates={
        **PAGE_TEMPLATES,
        "swagger": SWAGGER_UI_TEMPLATE,
    },
    security_schemes=[
        SecurityScheme(
            name="api_key",
            data={"type": "apiKey", "name": "Authorization", "in": "header"},
        )
    ],
    security={"api_key": []},
)


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config.from_object(Config)

    from models import User

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    @jwt.user_lookup_loader
    def user_load(header, data):
        current_user = db.session.scalars(
            select(User).filter_by(email=data["sub"])
        ).first()

        return current_user

    from controllers import user_controller, auth_controller, owner_controller

    app.register_blueprint(user_controller)
    app.register_blueprint(auth_controller)
    app.register_blueprint(owner_controller)

    @app.route("/")
    def index():
        return "Welcome to the Flask Backend Template! Test"

    api.register(app)

    return app
