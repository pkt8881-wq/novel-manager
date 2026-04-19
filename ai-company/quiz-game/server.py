import json
import os
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__, static_folder='static')
BASE = os.path.dirname(__file__)
Q_DIR = os.path.join(BASE, 'questions')

GENRES = {
    'ai_tools':  {'label': 'AI 도구', 'icon': '🤖'},
    'agents':    {'label': 'AI 에이전트', 'icon': '🦾'},
    'local_llm': {'label': '로컬 LLM', 'icon': '💻'},
    'python':    {'label': '파이썬', 'icon': '🐍'},
    'server':    {'label': '서버 만들기', 'icon': '🌐'},
    'database':  {'label': '데이터베이스', 'icon': '🗄️'},
    'history':   {'label': '역사', 'icon': '📜'},
    'common':    {'label': '상식', 'icon': '🌍'},
}

def load_questions(genre):
    path = os.path.join(Q_DIR, f'{genre}.json')
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/genres')
def get_genres():
    result = {}
    for key, meta in GENRES.items():
        q = load_questions(key)
        result[key] = {**meta, 'count': len(q)}
    return jsonify(result)

@app.route('/api/questions/<genre>')
def get_questions(genre):
    if genre not in GENRES:
        return jsonify({'error': 'unknown genre'}), 404
    return jsonify(load_questions(genre))

@app.route('/api/image')
def get_image():
    prompt = request.args.get('prompt', '')
    # ComfyUI 연동 예정
    return jsonify({'url': '', 'prompt': prompt, 'status': 'pending'})

if __name__ == '__main__':
    print('Quiz Game running: http://localhost:8879')
    app.run(host='0.0.0.0', port=8879, debug=False)
