from flasgger import Swagger
from myapp import app

app.config['SWAGGER'] = {
    'title': 'miniflux-AI API',
    'description': 'An API for Miniflux with AI.',
    'version': '0.1.0',
    "specs_route": "/api/docs",
}

swagger = Swagger(app)
