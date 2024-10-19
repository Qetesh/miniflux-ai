from flask import Flask
app = Flask(__name__)

from app import ai_news, ai_summary, my_swaggerui_blueprint