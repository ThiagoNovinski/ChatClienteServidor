import os
import threading
import json
import time
from websocket_server import WebsocketServer

# Controle da instância atual do servidor e dos usuários conectados
servidor_atual = None
tid_atual = None
usuarios_conectados = {}

# ==========================================
# 1. SERVIDOR DE CHAT (RÉPLICA)
# ==========================================
def client_conectou(cliente, servidor):
    # Alguns serviços de hospedagem fazem requisições automáticas
    # para verificar se o servidor está online. Nesse caso, ignora.
    if cliente is None:
        return
        
    tid_cliente = threading.get_native_id()

    print(f"[Thread {tid_cliente}] Cliente {cliente['id']} conectado na Réplica TID {tid_atual}")
    
    # Envia informações da thread do servidor e do cliente
    info_thread = {
        "tipo": "sistema",
        "tid_servidor": tid_atual,
        "tid_cliente": tid_cliente
    }
    servidor.send_message(cliente, json.dumps(info_thread))

    # Mensagem inicial exibida ao conectar
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

        # Quando o usuário entra na sala
        if dados.get("tipo") == "join":
            nome = dados.get("user", "Desconhecido")

            # Guarda o nome associado ao ID do cliente
            usuarios_conectados[cliente['id']] = nome
            
            msg_entrou = {
                "tipo": "chat",
                "user": "SISTEMA",
                "color": "#00cc44",
                "text": f"{nome} entrou na sala."
            }

            # Notifica todos os clientes conectados
            servidor.send_message_to_all(json.dumps(msg_entrou))
            return

        # Simula a queda da réplica
        if dados.get("tipo") == "crash":
            aviso = {
                "tipo": "chat",
                "comando": "forcar_desconexao",
                "user": "SISTEMA",
                "color": "#ff0000",
                "text": f"O servidor de TID: {tid_atual} caiu!"
            }

            # Avisa todos antes de derrubar o servidor
            servidor.send_message_to_all(json.dumps(aviso))

            # Derruba o servidor em uma thread separada
            threading.Thread(target=desligar_servidor).start()
            return

        # Trata mensagens normais do chat
        dados['tipo'] = 'chat'
        servidor.send_message_to_all(json.dumps(dados))

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def client_desconectou(cliente, servidor):
    # Ignora desconexões automáticas geradas pelo serviço de hospedagem
    if cliente is None:
        return
        
    tid = threading.get_native_id()

    print(f"[Thread {tid}] Cliente {cliente['id']} desconectou.")
    
    # Remove o usuário da lista de conectados
    if cliente['id'] in usuarios_conectados:
        nome = usuarios_conectados.pop(cliente['id'])

        msg_saiu = {
            "tipo": "chat",
            "user": "SISTEMA",
            "color": "#cc0000",
            "text": f"{nome} saiu da sala."
        }

        # Informa aos demais usuários que ele saiu
        servidor.send_message_to_all(json.dumps(msg_saiu))

def desligar_servidor():
    global servidor_atual

    print(f"[!] DERRUBANDO A RÉPLICA DE TID {tid_atual}...")

    if servidor_atual:
        # Limpa os usuários registrados
        usuarios_conectados.clear()

        # Fecha manualmente as conexões abertas
        for cliente in list(servidor_atual.clients):
            try:
                cliente['handler'].request.close()
            except:
                pass

        # Finaliza o servidor
        servidor_atual.shutdown()
        servidor_atual.server_close()

def rodar_servidor_websocket():
    global servidor_atual, tid_atual

    # Guarda o ID da thread atual
    tid_atual = threading.get_native_id()
    
    # Em produção, a porta vem da variável de ambiente
    porta_nuvem = int(os.environ.get("PORT", 9001))
    
    print(f"\n[+] Iniciando WebSocket na porta {porta_nuvem} (TID: {tid_atual})...")

    # Cria o servidor websocket
    servidor_atual = WebsocketServer(host='0.0.0.0', port=porta_nuvem)
    
    # Define os callbacks de eventos
    servidor_atual.set_fn_new_client(client_conectou)
    servidor_atual.set_fn_client_left(client_desconectou)
    servidor_atual.set_fn_message_received(mensagem_recebida)

    # Mantém o servidor executando continuamente
    servidor_atual.run_forever()

    print(f"[-] Réplica TID {tid_atual} morta e desalocada.")

# ==========================================
# 2. WATCHER - TOLERÂNCIA A FALHAS
# ==========================================
if __name__ == '__main__':

    # Thread principal responsável por monitorar o servidor
    tid_principal = threading.get_native_id()

    print(f"[*] Processo Mestre rodando no TID: {tid_principal}")
    
    while True:
        # Cria uma nova thread para executar a réplica do servidor
        thread_servidor = threading.Thread(target=rodar_servidor_websocket)

        thread_servidor.start()
        
        # Aguarda a thread terminar
        thread_servidor.join()

        # Se chegou aqui, o servidor caiu
        print("[ALERTA] Falha detectada! O servidor caiu.")
        print("[ALERTA] Reiniciando em 2 segundos...")

        # Pequeno atraso antes de recriar a réplica
        time.sleep(2)