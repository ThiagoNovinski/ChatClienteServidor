import os
import threading
import json
import time
from websocket_server import WebsocketServer

# Variáveis globais
servidor_atual = None
tid_atual = None
usuarios_conectados = {}

# ==========================================
# 1. LÓGICA DO SERVIDOR DE CHAT (REPLICA)
# ==========================================
def client_conectou(cliente, servidor):
    # PROTEÇÃO: Se não for um cliente real (ex: ping do Render), ignora e sai da função
    if cliente is None:
        return
        
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

        if dados.get("tipo") == "join":
            nome = dados.get("user", "Desconhecido")
            usuarios_conectados[cliente['id']] = nome
            
            msg_entrou = {
                "tipo": "chat",
                "user": "SISTEMA",
                "color": "#00cc44",
                "text": f"{nome} entrou na sala."
            }
            servidor.send_message_to_all(json.dumps(msg_entrou))
            return

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

        dados['tipo'] = 'chat'
        servidor.send_message_to_all(json.dumps(dados))
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def client_desconectou(cliente, servidor):
    # PROTEÇÃO: Ignora as desconexões geradas pelos pings do Render
    if cliente is None:
        return
        
    tid = threading.get_native_id()
    print(f"[Thread {tid}] Cliente {cliente['id']} desconectou.")
    
    if cliente['id'] in usuarios_conectados:
        nome = usuarios_conectados.pop(cliente['id'])
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
        usuarios_conectados.clear() 
        for cliente in list(servidor_atual.clients):
            try:
                cliente['handler'].request.close()
            except:
                pass
        servidor_atual.shutdown()
        servidor_atual.server_close()

def rodar_servidor_websocket():
    global servidor_atual, tid_atual
    tid_atual = threading.get_native_id()
    
    # Render injeta a porta aqui.
    porta_nuvem = int(os.environ.get("PORT", 9001))
    
    print(f"\n[+] Iniciando WebSocket na porta {porta_nuvem} (TID: {tid_atual})...")
    servidor_atual = WebsocketServer(host='0.0.0.0', port=porta_nuvem)
    
    servidor_atual.set_fn_new_client(client_conectou)
    servidor_atual.set_fn_client_left(client_desconectou)
    servidor_atual.set_fn_message_received(mensagem_recebida)

    servidor_atual.run_forever()
    print(f"[-] Réplica TID {tid_atual} morta e desalocada.")

# ==========================================
# 2. WATCHER - GERENCIADOR DE TOLERÂNCIA A FALHAS
# ==========================================
if __name__ == '__main__':
    tid_principal = threading.get_native_id()
    print(f"[*] Processo Mestre rodando no TID: {tid_principal}")
    
    while True:
        thread_servidor = threading.Thread(target=rodar_servidor_websocket)
        thread_servidor.start()
        
        thread_servidor.join()

        print("[ALERTA] Falha detectada! O servidor caiu.")
        print("[ALERTA] Reiniciando em 2 segundos...")
        time.sleep(2)