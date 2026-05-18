# Não esqueça dos imports no topo!
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

# NOVIDADE: Função para disparar a lista atualizada para todos
def atualizar_lista_usuarios(servidor):
    # PROTEÇÃO EXTR@: Não tenta mandar lista para servidor nulo
    if servidor is None: return
    
    # Pega apenas os nomes do dicionário e transforma em uma lista
    nomes_online = list(usuarios_conectados.values())
    
    msg = {
        "tipo": "lista_usuarios",
        "usuarios": nomes_online
    }
    servidor.send_message_to_all(json.dumps(msg))


def client_conectou(cliente, servidor):
    # PROTEÇÃO CRÍTICA DO RENDER: Ignora os pings de checagem de saúde
    if cliente is None:
        return
        
    tid_cliente = threading.get_native_id()
    print(f"[Thread {tid_cliente}] Cliente {cliente['id']} conectado na Réplica TID {tid_atual}")
    
    # Envia os TIDs de prova de concorrência
    info_thread = {
        "tipo": "sistema",
        "tid_servidor": tid_atual,
        "tid_cliente": tid_cliente
    }
    servidor.send_message(cliente, json.dumps(info_thread))

    # Mensagem de boas-vindas do sistema
    msg_init = {
        "tipo": "chat",
        "user": "SISTEMA",
        "color": "#ffaa00",
        "text": f"Inicializando servidor de TID: {tid_atual}"
    }
    servidor.send_message(cliente, json.dumps(msg_init))


def mensagem_recebida(cliente, servidor, mensagem):
    # PROTEÇÃO CRÍTICA DO RENDER
    if cliente is None or servidor is None: return

    try:
        dados = json.loads(mensagem)

        # 1. Apresentação do usuário (Login)
        if dados.get("tipo") == "join":
            nome = dados.get("user", "Desconhecido")
            # Salva o nome atrelado ao ID da conexão no dicionário
            usuarios_conectados[cliente['id']] = nome
            
            # Avisa todos com o nome correto
            msg_entrou = {
                "tipo": "chat",
                "user": "SISTEMA",
                "color": "#00cc44",
                "text": f"{nome} entrou na sala."
            }
            servidor.send_message_to_all(json.dumps(msg_entrou))
            
            # NOVIDADE: Atualiza a lista lateral para todos!
            atualizar_lista_usuarios(servidor)
            return

        # 2. Comando de Derrubar o Servidor (Tolerância a Falhas)
        if dados.get("tipo") == "crash":
            aviso = {
                "tipo": "chat",
                "comando": "forcar_desconexao", 
                "user": "SISTEMA",
                "color": "#ff0000",
                "text": f"O servidor de TID: {tid_atual} caiu!"
            }
            servidor.send_message_to_all(json.dumps(aviso))
            # Inicia uma thread para desligar sem travar a recepção de mensagens
            threading.Thread(target=desligar_servidor).start()
            return

        # 3. Mensagem de texto normal
        dados['tipo'] = 'chat'
        servidor.send_message_to_all(json.dumps(dados))
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")


def client_desconectou(cliente, servidor):
    # PROTEÇÃO CRÍTICA DO RENDER
    if cliente is None:
        return
        
    tid = threading.get_native_id()
    print(f"[Thread {tid}] Cliente {cliente['id']} desconectou.")
    
    # Verifica se a conexão que caiu tinha um nome registrado (Ignora desconexões fantasmas)
    if cliente['id'] in usuarios_conectados:
        nome = usuarios_conectados.pop(cliente['id']) # Pega o nome e remove do dicionário
        
        msg_saiu = {
            "tipo": "chat",
            "user": "SISTEMA",
            "color": "#cc0000",
            "text": f"{nome} saiu da sala."
        }
        servidor.send_message_to_all(json.dumps(msg_saiu))
        
        # NOVIDADE: Atualiza a lista para todos que ficaram!
        atualizar_lista_usuarios(servidor)


def desligar_servidor():
    global servidor_atual
    print(f"[!] DERRUBANDO A RÉPLICA DE TID {tid_atual}...")
    if servidor_atual:
        # Limpa o dicionário de usuários online para a próxima réplica
        usuarios_conectados.clear() 
        # Fecha as conexões de forma segura para os clientes tentarem reconectar
        for cliente in list(servidor_atual.clients):
            try:
                cliente['handler'].request.close()
            except:
                pass
        # Shutdown do servidor de forma limpa
        servidor_atual.shutdown()
        servidor_atual.server_close()


def rodar_servidor_websocket():
    global servidor_atual, tid_atual
    tid_atual = threading.get_native_id()
    
    # Captura a porta injetada pela nuvem do Render
    porta_nuvem = int(os.environ.get("PORT", 9001))
    
    print(f"\n[+] Iniciando WebSocket na porta {porta_nuvem} (TID: {tid_atual})...")
    
    # Instancia o servidor usando a porta da nuvem
    servidor_atual = WebsocketServer(host='0.0.0.0', port=porta_nuvem)
    
    servidor_atual.set_fn_new_client(client_conectou)
    servidor_atual.set_fn_client_left(client_desconectou)
    servidor_atual.set_fn_message_received(mensagem_recebida)

    # O código "trava" aqui enquanto o servidor estiver rodando
    servidor_atual.run_forever()
    print(f"[-] Réplica TID {tid_atual} morta e desalocada.")


# ==========================================
# 2. WATCHER - GERENCIADOR DE TOLERÂNCIA A FALHAS
# ==========================================
if __name__ == '__main__':
    tid_principal = threading.get_native_id()
    print(f"[*] Processo Mestre de Tolerância a Falhas rodando no TID: {tid_principal}")
    
    # LOOP INFINITO DE REPLICAÇÃO
    while True:
        # Instancia e inicia a thread do servidor de chat
        thread_servidor = threading.Thread(target=rodar_servidor_websocket)
        thread_servidor.start()
        
        # O Mestre fica aguardando aqui (.join()). Se a thread do servidor morrer, ele acorda e passa dessa linha
        thread_servidor.join()

        # O Mestre detecta a falha e entra em ação
        print("[ALERTA] Falha detectada! O servidor de chat caiu.")
        print("[ALERTA] Instanciando a próxima thread de réplica em 2 segundos...")
        
        # Pequeno delay para garantir que o SO liberou a porta de rede
        time.sleep(2)