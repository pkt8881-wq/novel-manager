import json
import os
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__, static_folder='static')
BASE = os.path.dirname(__file__)
Q_DIR = os.path.join(BASE, 'questions')

def load_questions(genre):
    path = os.path.join(Q_DIR, f'{genre}.json')
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/questions/<genre>')
def get_questions(genre):
    return jsonify(load_questions(genre))

@app.route('/api/image')
def get_image():
    # ComfyUI 연동 예정 — 현재는 placeholder 반환
    prompt = request.args.get('prompt', '')
    return jsonify({'url': '', 'prompt': prompt, 'status': 'comfyui_pending'})

if __name__ == '__main__':
    print('Quiz server: http://localhost:8879')
    app.run(host='0.0.0.0', port=8879, debug=False)
