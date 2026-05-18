# ==========================================
# IMPORTS
# ==========================================

# Manipulação de variáveis de ambiente
import os

# Criação e gerenciamento de threads
import threading

# Conversão de dados para JSON
import json

# Utilizado no delay do watcher
import time

# Biblioteca do servidor websocket
from websocket_server import WebsocketServer


# ==========================================
# VARIÁVEIS GLOBAIS
# ==========================================

# Guarda a instância atual do servidor
servidor_atual = None

# Armazena o TID da thread do servidor
tid_atual = None

# Dicionário de usuários online
# Estrutura:
# { id_cliente : nome_usuario }
usuarios_conectados = {}


# ==========================================
# 1. LÓGICA DO SERVIDOR DE CHAT
# ==========================================

def atualizar_lista_usuarios(servidor):

    # Evita tentar enviar mensagens
    # para um servidor inválido
    if servidor is None:
        return

    # Extrai apenas os nomes dos usuários online
    nomes_online = list(usuarios_conectados.values())

    # Mensagem contendo a lista atualizada
    msg = {
        "tipo": "lista_usuarios",
        "usuarios": nomes_online
    }

    # Envia a lista para todos os clientes
    servidor.send_message_to_all(json.dumps(msg))


# ==========================================
# NOVA CONEXÃO
# ==========================================
def client_conectou(cliente, servidor):

    # Alguns health checks do Render
    # geram conexões inválidas
    if cliente is None:
        return

    # TID da thread responsável pelo cliente
    tid_cliente = threading.get_native_id()

    print(
        f"[Thread {tid_cliente}] "
        f"Cliente {cliente['id']} "
        f"conectado na Réplica TID {tid_atual}"
    )

    # Envia informações das threads
    # para demonstrar concorrência
    info_thread = {
        "tipo": "sistema",
        "tid_servidor": tid_atual,
        "tid_cliente": tid_cliente
    }

    servidor.send_message(
        cliente,
        json.dumps(info_thread)
    )

    # Mensagem inicial do sistema
    msg_init = {
        "tipo": "chat",
        "user": "SISTEMA",
        "color": "#ffaa00",
        "text": (
            f"Inicializando servidor "
            f"de TID: {tid_atual}"
        )
    }

    servidor.send_message(
        cliente,
        json.dumps(msg_init)
    )


# ==========================================
# RECEBIMENTO DE MENSAGENS
# ==========================================
def mensagem_recebida(cliente, servidor, mensagem):

    # Proteção contra conexões inválidas
    if cliente is None or servidor is None:
        return

    try:

        # Converte a mensagem JSON
        # recebida para dicionário
        dados = json.loads(mensagem)

        # ----------------------------------
        # ENTRADA DE USUÁRIO NO CHAT
        # ----------------------------------
        if dados.get("tipo") == "join":

            # Nome enviado pelo cliente
            nome = dados.get(
                "user",
                "Desconhecido"
            )

            # Salva o usuário no dicionário
            usuarios_conectados[
                cliente['id']
            ] = nome

            # Mensagem avisando que entrou
            msg_entrou = {
                "tipo": "chat",
                "user": "SISTEMA",
                "color": "#00cc44",
                "text": (
                    f"{nome} entrou na sala."
                )
            }

            servidor.send_message_to_all(
                json.dumps(msg_entrou)
            )

            # Atualiza a lista lateral
            atualizar_lista_usuarios(
                servidor
            )

            return

        # ----------------------------------
        # COMANDO DE DERRUBAR SERVIDOR
        # ----------------------------------
        if dados.get("tipo") == "crash":

            # Mensagem de aviso para todos
            aviso = {
                "tipo": "chat",
                "comando": "forcar_desconexao",
                "user": "SISTEMA",
                "color": "#ff0000",
                "text": (
                    f"O servidor de TID: "
                    f"{tid_atual} caiu!"
                )
            }

            servidor.send_message_to_all(
                json.dumps(aviso)
            )

            # Cria uma thread separada
            # para desligar o servidor
            threading.Thread(
                target=desligar_servidor
            ).start()

            return

        # ----------------------------------
        # MENSAGEM NORMAL DO CHAT
        # ----------------------------------

        # Marca a mensagem como chat
        dados['tipo'] = 'chat'

        # Repassa para todos os clientes
        servidor.send_message_to_all(
            json.dumps(dados)
        )

    except Exception as e:

        print(
            f"Erro ao processar mensagem: {e}"
        )


# ==========================================
# DESCONEXÃO DE CLIENTE
# ==========================================
def client_desconectou(cliente, servidor):

    # Ignora desconexões inválidas
    if cliente is None:
        return

    tid = threading.get_native_id()

    print(
        f"[Thread {tid}] "
        f"Cliente {cliente['id']} desconectou."
    )

    # Verifica se o cliente tinha nome registrado
    if cliente['id'] in usuarios_conectados:

        # Remove do dicionário
        nome = usuarios_conectados.pop(
            cliente['id']
        )

        # Mensagem de saída
        msg_saiu = {
            "tipo": "chat",
            "user": "SISTEMA",
            "color": "#cc0000",
            "text": f"{nome} saiu da sala."
        }

        servidor.send_message_to_all(
            json.dumps(msg_saiu)
        )

        # Atualiza lista de usuários online
        atualizar_lista_usuarios(
            servidor
        )


# ==========================================
# DESLIGAMENTO DO SERVIDOR
# ==========================================
def desligar_servidor():

    global servidor_atual

    print(
        f"[!] DERRUBANDO A RÉPLICA "
        f"DE TID {tid_atual}..."
    )

    if servidor_atual:

        # Limpa lista de usuários
        usuarios_conectados.clear()

        # Fecha todas as conexões abertas
        for cliente in list(
            servidor_atual.clients
        ):

            try:

                cliente[
                    'handler'
                ].request.close()

            except:
                pass

        # Finaliza o servidor corretamente
        servidor_atual.shutdown()

        servidor_atual.server_close()


# ==========================================
# INICIALIZAÇÃO DO SERVIDOR
# ==========================================
def rodar_servidor_websocket():

    global servidor_atual, tid_atual

    # Guarda o TID da thread atual
    tid_atual = threading.get_native_id()

    # Porta fornecida pela plataforma Render
    porta_nuvem = int(
        os.environ.get("PORT", 9001)
    )

    print(
        f"\n[+] Iniciando WebSocket "
        f"na porta {porta_nuvem} "
        f"(TID: {tid_atual})..."
    )

    # Cria o servidor websocket
    servidor_atual = WebsocketServer(
        host='0.0.0.0',
        port=porta_nuvem
    )

    # Define os callbacks do servidor
    servidor_atual.set_fn_new_client(
        client_conectou
    )

    servidor_atual.set_fn_client_left(
        client_desconectou
    )

    servidor_atual.set_fn_message_received(
        mensagem_recebida
    )

    # Mantém o servidor rodando
    servidor_atual.run_forever()

    print(
        f"[-] Réplica TID "
        f"{tid_atual} morta e desalocada."
    )


# ==========================================
# 2. WATCHER DE TOLERÂNCIA A FALHAS
# ==========================================
if __name__ == '__main__':

    # TID da thread principal
    tid_principal = threading.get_native_id()

    print(
        f"[*] Processo Mestre "
        f"de Tolerância a Falhas "
        f"rodando no TID: {tid_principal}"
    )

    # Loop infinito de monitoramento
    while True:

        # Cria a thread do servidor
        thread_servidor = threading.Thread(
            target=rodar_servidor_websocket
        )

        # Inicia o servidor
        thread_servidor.start()

        # O watcher fica aguardando
        # até a thread morrer
        thread_servidor.join()

        # Se chegou aqui,
        # o servidor caiu
        print(
            "[ALERTA] Falha detectada! "
            "O servidor de chat caiu."
        )

        print(
            "[ALERTA] Instanciando "
            "a próxima réplica "
            "em 2 segundos..."
        )

        # Pequeno delay antes de recriar
        time.sleep(2)