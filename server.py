import os
import threading
import json
import time
import http.server
import socketserver
from websocket_server import WebsocketServer

    # Variáveis globais para controle da réplica e dos usuários
servidor_atual = None
tid_atual = None
usuarios_conectados = {} # Dicionário para guardar qual ID pertence a qual Nome

    # ==========================================
    # 1. LÓGICA DO SERVIDOR DE CHAT (REPLICA)
    # ==========================================

def client_conectou(cliente, servidor):
    tid_cliente = threading.get_native_id()
    print(f"[Thread {tid_cliente}] Cliente {cliente['id']} conectado na Réplica TID {tid_atual}")
        
    info_thread = {
        "tipo": "sistema",
        "tid_servidor": tid_atual,
        "tid_cliente": tid_cliente
        }
    servidor.send_message(cliente, json.dumps(info_thread))

    msg_init = {
        "tipo": "chat",
        "user": "SISTEMA",
        "color": "#ffaa00",
        "text": f"Inicializando servidor de TID: {tid_atual}"
        }
    servidor.send_message(cliente, json.dumps(msg_init))

def mensagem_recebida(cliente, servidor, mensagem):
    try:
        dados = json.loads(mensagem)

        # 1. Se for uma mensagem de apresentação ("join")
        if dados.get("tipo") == "join":
            nome = dados.get("user", "Desconhecido")
            # Salva o nome atrelado ao ID da conexão
            usuarios_conectados[cliente['id']] = nome
                
            # Agora sim avisamos todo mundo com o nome correto!
            msg_entrou = {
                "tipo": "chat",
                "user": "SISTEMA",
                "color": "#00cc44",
                "text": f"{nome} entrou na sala."
            }
            servidor.send_message_to_all(json.dumps(msg_entrou))
            return

        # 2. Se for o comando de derrubar o servidor
        if dados.get("tipo") == "crash":
            aviso = {
                "tipo": "chat",
                "comando": "forcar_desconexao", 
                "user": "SISTEMA",
                "color": "#ff0000",
                "text": f"O servidor de TID: {tid_atual} caiu!"
            }
            servidor.send_message_to_all(json.dumps(aviso))
            threading.Thread(target=desligar_servidor).start()
            return

        # 3. Se for uma mensagem de texto normal
        dados['tipo'] = 'chat'
        servidor.send_message_to_all(json.dumps(dados))
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def client_desconectou(cliente, servidor):
    tid = threading.get_native_id()
    print(f"[Thread {tid}] Cliente {cliente['id']} desconectou.")
    
    # Busca o nome no dicionário (se não achar, usa "Um usuário") e já apaga da memória (.pop)
    nome = usuarios_conectados.pop(cliente['id'], "Um usuário")
    
    msg_saiu = {
        "tipo": "chat",
        "user": "SISTEMA",
        "color": "#cc0000",
        "text": f"{nome} saiu da sala."
    }
    servidor.send_message_to_all(json.dumps(msg_saiu))

def desligar_servidor():
    global servidor_atual
    print(f"[!] DERRUBANDO A RÉPLICA DE TID {tid_atual}...")
    if servidor_atual:
        # Limpa os usuários da memória, pois a réplica vai morrer
        usuarios_conectados.clear() 
        for cliente in list(servidor_atual.clients):
            try:
                cliente['handler'].request.close()
            except:
                pass
        servidor_atual.shutdown()
        servidor_atual.server_close()


# ==========================================
# 2. SERVIDOR HTTP EMBUTIDO (Requisito 1.1)
# ==========================================
def rodar_servidor_http():
    class RotasFlaskCustomizadas(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            # NOVIDADE: Finge que está tudo bem com o ícone, mas não envia nada.
            # Isso impede o navegador de travar procurando o arquivo.
            if self.path == '/favicon.ico':
                self.send_response(204) # 204 = No Content (Sem conteúdo)
                self.end_headers()
                return
            if self.path in ['/', '/login', '/login.html']:
                self.path = '/templates/login.html'
            elif self.path in ['/chat', '/chat.html']:
                self.path = '/templates/chat.html'
                
            try:
                return super().do_GET()
            except ConnectionAbortedError:
                pass
    # CORREÇÃO CRÍTICA: Agora o silenciador aceita qualquer quantidade de argumentos sem dar erro!
    RotasFlaskCustomizadas.log_message = lambda *args, **kwargs: None 
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", 8000), RotasFlaskCustomizadas) as httpd:
        print("[*] Servidor HTTP embutido rodando na porta 8000...")
        httpd.serve_forever()


def rodar_servidor_websocket():
    global servidor_atual, tid_atual
    tid_atual = threading.get_native_id()
    
    # Pega a porta que a nuvem (Render) mandar. Se não mandar, usa a 9001 (local)
    porta_nuvem = int(os.environ.get("PORT", 9001))
    
    print(f"\n[+] Iniciando nova réplica do WebSocket na porta {porta_nuvem} (TID: {tid_atual})...")
    # CRÍTICO: Você precisa instanciar o servidor usando a porta_nuvem antes de configurar!
    servidor_atual = WebsocketServer(host='0.0.0.0', port=porta_nuvem)
    
    servidor_atual.set_fn_new_client(client_conectou)
    servidor_atual.set_fn_client_left(client_desconectou)
    servidor_atual.set_fn_message_received(mensagem_recebida)
    # O código "trava" aqui enquanto o servidor estiver rodando
    servidor_atual.run_forever()
    print(f"[-] Réplica TID {tid_atual} morta e desalocada.")

# ==========================================
# 3. WATCHER - GERENCIADOR DE TOLERÂNCIA A FALHAS
# ==========================================
if __name__ == '__main__':
    tid_principal = threading.get_native_id()
    print(f"[*] Processo Mestre de Tolerância a Falhas rodando no TID: {tid_principal}")
    
    # Inicia o servidor HTTP em background (apenas para servir as páginas)
    threading.Thread(target=rodar_servidor_http, daemon=True).start()
    # LOOP DE REPLICAÇÃO: Fila infinita de threads substitutas
    while True:
        # Instancia e inicia a thread do servidor de chat
        thread_servidor = threading.Thread(target=rodar_servidor_websocket)
        thread_servidor.start()
        # O Mestre fica aguardando. Se a thread_servidor morrer, ele passa dessa linha
        thread_servidor.join()
        # O Mestre detecta a falha e entra em ação
        print("[ALERTA] Falha detectada! O servidor caiu.")
        print("[ALERTA] Instanciando a próxima thread de réplica em 2 segundos...")
        
        # Pequeno delay para o SO liberar a porta de rede (9001)
        time.sleep(2)