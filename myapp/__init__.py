from flask import Flask
from flasgger import Swagger


app = Flask(__name__)

app.config['SWAGGER'] = {
    'title': 'miniflux-AI API',
    'description': 'An API for Miniflux with AI.',
    'version': '0.1.0',
    "specs_route": "/api/docs",
}
swagger = Swagger(app)

from myapp import webhook, ai_news
