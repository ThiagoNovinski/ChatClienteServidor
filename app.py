from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma_chave_secreta_qualquer'
# Inicializa o SocketIO. Em dev, ele usa o modelo de threads do Werkzeug.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
@app.route('/')
def index():
    return render_template('index.html')

# Evento acionado quando um cliente se conecta
@socketio.on('connect')
def handle_connect():
    print("Novo cliente conectado.")

# Evento acionado quando o servidor recebe uma mensagem
@socketio.on('message')
def handle_message(msg):
    print(f"Mensagem recebida: {msg}")
    # Envia a mensagem para todos os clientes conectados
    send(msg, broadcast=True)

if __name__ == '__main__':
    # debug=True inicia o servidor de desenvolvimento multithread do Flask
    socketio.run(app, debug=True)