import os
import threading
import json
import time

from websocket_server import WebsocketServer


# ==========================================
# VARIÁVEIS GLOBAIS
# ==========================================

# Instância atual do servidor websocket
servidor_atual = None

# Guarda o TID da thread do servidor
tid_atual = None

# Usuários conectados no momento
# Estrutura:
# { id_cliente : nome_usuario }
usuarios_conectados = {}


# ==========================================
# ATUALIZA LISTA DE USUÁRIOS
# ==========================================
def atualizar_lista_usuarios(servidor):

    # Evita tentar enviar dados
    # para um servidor inexistente
    if servidor is None:
        return

    # Pega somente os nomes dos usuários
    nomes_online = list(
        usuarios_conectados.values()
    )

    # Estrutura enviada para o frontend
    msg = {
        "tipo": "lista_usuarios",
        "usuarios": nomes_online
    }

    # Dispara a lista atualizada
    # para todos os clientes
    servidor.send_message_to_all(
        json.dumps(msg)
    )


# ==========================================
# CLIENTE CONECTOU
# ==========================================
def client_conectou(cliente, servidor):

    # Alguns health checks do Render
    # criam conexões inválidas
    if cliente is None:
        return

    # TID da thread atual
    tid_cliente = threading.get_native_id()

    print(
        f"[Thread {tid_cliente}] "
        f"Cliente {cliente['id']} "
        f"conectado na Réplica TID {tid_atual}"
    )

    # Dados usados para demonstrar
    # concorrência no frontend
    info_thread = {
        "tipo": "sistema",
        "tid_servidor": tid_atual,
        "tid_cliente": tid_cliente
    }

    # Envia os dados apenas
    # para o cliente recém conectado
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
# MENSAGEM RECEBIDA
# ==========================================
def mensagem_recebida(
    cliente,
    servidor,
    mensagem
):

    # Proteção contra conexões inválidas
    if cliente is None or servidor is None:
        return

    try:

        # Converte JSON recebido
        # para dicionário Python
        dados = json.loads(mensagem)

        # ----------------------------------
        # LOGIN DO USUÁRIO
        # ----------------------------------
        if dados.get("tipo") == "join":

            # Nome enviado pelo cliente
            nome = dados.get(
                "user",
                "Desconhecido"
            )

            # Associa o nome ao ID da conexão
            usuarios_conectados[
                cliente['id']
            ] = nome

            # Mensagem avisando entrada
            msg_entrou = {
                "tipo": "chat",
                "user": "SISTEMA",
                "color": "#00cc44",
                "text": (
                    f"{nome} entrou na sala."
                )
            }

            # Envia aviso para todos
            servidor.send_message_to_all(
                json.dumps(msg_entrou)
            )

            # Atualiza lista lateral
            atualizar_lista_usuarios(
                servidor
            )

            return

        # ----------------------------------
        # COMANDO DE CRASH
        # ----------------------------------
        if dados.get("tipo") == "crash":

            # Mensagem de aviso
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

            # Avisa todos os clientes
            servidor.send_message_to_all(
                json.dumps(aviso)
            )

            # Cria thread separada
            # para desligar o servidor
            threading.Thread(
                target=desligar_servidor
            ).start()

            return

        # ----------------------------------
        # MENSAGEM NORMAL DO CHAT
        # ----------------------------------

        # Define o tipo da mensagem
        dados['tipo'] = 'chat'

        # Reenvia para todos os clientes
        servidor.send_message_to_all(
            json.dumps(dados)
        )

    except Exception as e:

        print(
            f"Erro ao processar mensagem: {e}"
        )


# ==========================================
# CLIENTE DESCONECTOU
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

    # Verifica se o cliente
    # estava registrado
    if cliente['id'] in usuarios_conectados:

        # Remove usuário do dicionário
        nome = usuarios_conectados.pop(
            cliente['id']
        )

        # Mensagem de saída
        msg_saiu = {
            "tipo": "chat",
            "user": "SISTEMA",
            "color": "#cc0000",
            "text": (
                f"{nome} saiu da sala."
            )
        }

        # Avisa todos os clientes
        servidor.send_message_to_all(
            json.dumps(msg_saiu)
        )

        # Atualiza lista de usuários
        atualizar_lista_usuarios(
            servidor
        )


# ==========================================
# DESLIGA O SERVIDOR
# ==========================================
def desligar_servidor():

    global servidor_atual

    print(
        f"[!] DERRUBANDO A RÉPLICA "
        f"DE TID {tid_atual}..."
    )

    if servidor_atual:

        # Limpa usuários online
        usuarios_conectados.clear()

        # Fecha todas as conexões
        for cliente in list(
            servidor_atual.clients
        ):

            try:

                cliente[
                    'handler'
                ].request.close()

            except:
                pass

        # Finaliza o servidor
        servidor_atual.shutdown()

        servidor_atual.server_close()


# ==========================================
# INICIA SERVIDOR WEBSOCKET
# ==========================================
def rodar_servidor_websocket():

    global servidor_atual
    global tid_atual

    # TID da thread atual
    tid_atual = threading.get_native_id()

    # Porta fornecida pela Render
    porta_nuvem = int(
        os.environ.get("PORT", 9001)
    )

    print(
        f"\n[+] Iniciando WebSocket "
        f"na porta {porta_nuvem} "
        f"(TID: {tid_atual})..."
    )

    # Cria servidor websocket
    servidor_atual = WebsocketServer(
        host='0.0.0.0',
        port=porta_nuvem
    )

    # Callbacks do servidor
    servidor_atual.set_fn_new_client(
        client_conectou
    )

    servidor_atual.set_fn_client_left(
        client_desconectou
    )

    servidor_atual.set_fn_message_received(
        mensagem_recebida
    )

    # Mantém servidor ativo
    servidor_atual.run_forever()

    print(
        f"[-] Réplica TID "
        f"{tid_atual} morta e desalocada."
    )


# ==========================================
# WATCHER DE TOLERÂNCIA A FALHAS
# ==========================================
if __name__ == '__main__':

    # TID da thread principal
    tid_principal = threading.get_native_id()

    print(
        f"[*] Processo Mestre "
        f"de Tolerância a Falhas "
        f"rodando no TID: "
        f"{tid_principal}"
    )

    # Loop infinito de monitoramento
    while True:

        # Cria thread do servidor
        thread_servidor = threading.Thread(
            target=rodar_servidor_websocket
        )

        # Inicia thread
        thread_servidor.start()

        # O watcher espera até
        # a thread morrer
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

        # Pequena pausa antes
        # de recriar o servidor
        time.sleep(2)