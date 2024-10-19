from flask import jsonify

from myapp import app
# myapp = Flask(__name__)

@app.route('/rss/ai-summary', methods=['GET'])
def miniflux_ai_summary(miniflux_client):
    # Todo 根据需要获取最近时间内的文章，或总结后的列表
    entries = miniflux_client.get_entries(status=['unread'], limit=10000)
    return jsonify(entries)
