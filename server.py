import os
import multiprocessing
import threading
import json
import time
from websocket_server import WebsocketServer

servidor_atual = None
usuarios_conectados = {}

# ==========================================
# 1. LÓGICA DO SERVIDOR DE CHAT (RÉPLICA)
# ==========================================

def atualizar_lista_usuarios(servidor):
    if servidor is None: return
    nomes_online = list(usuarios_conectados.values())
    msg = {
        "tipo": "lista_usuarios",
        "usuarios": nomes_online
    }
    servidor.send_message_to_all(json.dumps(msg))

def client_conectou(cliente, servidor):
    if cliente is None: return
    
    # Captura o PID do Servidor e a Thread REAL exclusiva deste usuário
    pid_atual = os.getpid()
    tid_cliente = threading.get_native_id()
    
    print(f"[PID {pid_atual} | Thread {tid_cliente}] Cliente {cliente['id']} conectado.")
    
    info_thread = {
        "tipo": "sistema",
        "pid_servidor": pid_atual,
        "tid_cliente": tid_cliente
    }
    servidor.send_message(cliente, json.dumps(info_thread))

    msg_init = {
        "tipo": "chat",
        "user": "SISTEMA",
        "color": "#ffaa00",
        "text": f"Réplica ativa operando no Processo PID: {pid_atual}"
    }
    servidor.send_message(cliente, json.dumps(msg_init))

def mensagem_recebida(cliente, servidor, mensagem):
    if cliente is None or servidor is None: return
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
            atualizar_lista_usuarios(servidor)
            return

        if dados.get("tipo") == "crash":
            aviso = {
                "tipo": "chat",
                "comando": "forcar_desconexao", 
                "user": "SISTEMA",
                "color": "#ff0000",
                "text": f"O servidor de PID: {os.getpid()} foi intencionalmente derrubado!"
            }
            servidor.send_message_to_all(json.dumps(aviso))
            os._exit(1) # Suicídio do processo filho simulando falha crítica

        dados['tipo'] = 'chat'
        servidor.send_message_to_all(json.dumps(dados))
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def client_desconectou(cliente, servidor):
    if cliente is None: return
    
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
        atualizar_lista_usuarios(servidor)

def rodar_servidor_websocket():
    global servidor_atual
    pid_filho = os.getpid()
    porta_nuvem = int(os.environ.get("PORT", 9001))
    
    print(f"\n[+] INSTANCIANDO PROCESSO FILHO DE RÉPLICA (PID: {pid_filho}) na porta {porta_nuvem}...")
    
    servidor_atual = WebsocketServer(host='0.0.0.0', port=porta_nuvem)
    servidor_atual.set_fn_new_client(client_conectou)
    servidor_atual.set_fn_client_left(client_desconectou)
    servidor_atual.set_fn_message_received(mensagem_recebida)
    servidor_atual.run_forever()

# ==========================================
# 2. WATCHER - GERENCIADOR MESTRE DE PROCESSOS
# ==========================================
if __name__ == '__main__':
    pid_mestre = os.getpid()
    print(f"===========================================================")
    print(f"[*] PROCESSO MESTRE (WATCHER) INICIADO COM SUCESSO! PID: {pid_mestre}")
    print(f"===========================================================")
    
    while True:
        processo_servidor = multiprocessing.Process(target=rodar_servidor_websocket)
        processo_servidor.start()
        
        processo_servidor.join()

        print(f"\n[ALERTA CRÍTICO] O Processo Filho de Réplica morreu!")
        print(f"[ALERTA CRÍTICO] Mestre (PID {pid_mestre}) está agindo para reestabelecer o sistema...")
        print(f"[ALERTA CRÍTICO] Inicializando uma nova réplica isolada em 2 segundos...")
        
        time.sleep(2)