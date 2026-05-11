from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma_chave_secreta_qualquer'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Rota principal agora renderiza apenas a tela de Login
@app.route('/')
def login():
    return render_template('login.html')

# Nova rota para a tela do Chat
@app.route('/chat')
def chat():
    return render_template('chat.html')

@socketio.on('connect')
def handle_connect():
    print("Novo cliente conectado.")

@socketio.on('message')
def handle_message(data):
    print(f"Mensagem recebida: {data}")
    send(data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)