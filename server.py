
import os
import multiprocessing
import threading
import json
import time
from websocket_server import WebsocketServer


# ==========================================
# VARIÁVEIS GLOBAIS
# ==========================================

# Guarda a instância atual do servidor
servidor_atual = None

# Dicionário contendo os usuários online
# Estrutura:
# { id_cliente : nome_usuario }
usuarios_conectados = {}


# ==========================================
# 1. LÓGICA DO SERVIDOR DE CHAT (Instância)
# ==========================================

def atualizar_lista_usuarios(servidor):

    # Evita tentar enviar dados
    # para um servidor inexistente
    if servidor is None:
        return

    # Extrai somente os nomes dos usuários
    nomes_online = list(
        usuarios_conectados.values()
    )

    # Estrutura enviada ao frontend
    msg = {
        "tipo": "lista_usuarios",
        "usuarios": nomes_online
    }

    # Atualiza todos os clientes
    servidor.send_message_to_all(
        json.dumps(msg)
    )


# ==========================================
# CLIENTE CONECTOU
# ==========================================
def client_conectou(cliente, servidor):

    # Alguns health checks do Render
    # podem gerar clientes inválidos
    if cliente is None:
        return

    # PID do processo da instância
    pid_atual = os.getpid()

    # TID da thread responsável pelo cliente
    tid_cliente = threading.get_native_id()

    print(
        f"[PID {pid_atual} | "
        f"Thread {tid_cliente}] "
        f"Cliente {cliente['id']} conectado."
    )

    # Informações usadas para demonstrar
    # concorrência e isolamento de processos
    info_thread = {
        "tipo": "sistema",
        "pid_servidor": pid_atual,
        "tid_cliente": tid_cliente
    }

    # Envia os dados apenas
    # para o cliente conectado
    servidor.send_message(
        cliente,
        json.dumps(info_thread)
    )

    # Mensagem inicial exibida no chat
    msg_init = {
        "tipo": "chat",
        "user": "SISTEMA",
        "color": "#ffaa00",
        "text": (
            f"Instância ativa operando "
            f"no Processo PID: {pid_atual}"
        )
    }

    servidor.send_message(
        cliente,
        json.dumps(msg_init)
    )


# ==========================================
# RECEBIMENTO DE MENSAGENS
# ==========================================
def mensagem_recebida(
    cliente,
    servidor,
    mensagem
):

    # Ignora conexões inválidas
    if cliente is None or servidor is None:
        return

    try:

        # Converte o JSON recebido
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

            # Salva usuário conectado
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

            # Avisa todos os clientes
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

            # Mensagem de aviso geral
            aviso = {
                "tipo": "chat",
                "comando": "forcar_desconexao",
                "user": "SISTEMA",
                "color": "#ff0000",
                "text": (
                    f"O servidor de PID: "
                    f"{os.getpid()} "
                    f"foi intencionalmente "
                    f"derrubado!"
                )
            }

            # Envia aviso para todos
            servidor.send_message_to_all(
                json.dumps(aviso)
            )

            # Mata o processo filho
            # simulando falha crítica
            os._exit(1)

        # ----------------------------------
        # MENSAGEM NORMAL DO CHAT
        # ----------------------------------

        # Define o tipo da mensagem
        dados['tipo'] = 'chat'

        # Repassa mensagem para todos
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

    # TID da thread atual
    tid = threading.get_native_id()

    print(
        f"[Thread {tid}] "
        f"Cliente {cliente['id']} desconectou."
    )

    # Verifica se o usuário
    # estava registrado
    if cliente['id'] in usuarios_conectados:

        # Remove usuário do dicionário
        nome = usuarios_conectados.pop(
            cliente['id']
        )

        # Mensagem avisando saída
        msg_saiu = {
            "tipo": "chat",
            "user": "SISTEMA",
            "color": "#cc0000",
            "text": (
                f"{nome} saiu da sala."
            )
        }

        # Envia aviso para todos
        servidor.send_message_to_all(
            json.dumps(msg_saiu)
        )

        # Atualiza lista de usuários
        atualizar_lista_usuarios(
            servidor
        )


# ==========================================
# INICIALIZA SERVIDOR WEBSOCKET
# ==========================================
def rodar_servidor_websocket():

    global servidor_atual

    # PID do processo filho
    pid_filho = os.getpid()

    # Porta fornecida pela Render
    porta_nuvem = int(
        os.environ.get("PORT", 9001)
    )

    print(
        f"\n[+] INSTANCIANDO "
        f"PROCESSO FILHO DE RÉPLICA "
        f"(PID: {pid_filho}) "
        f"na porta {porta_nuvem}..."
    )

    # Cria o servidor websocket
    servidor_atual = WebsocketServer(
        host='0.0.0.0',
        port=porta_nuvem
    )

    # Define callbacks do servidor
    servidor_atual.set_fn_new_client(
        client_conectou
    )

    servidor_atual.set_fn_client_left(
        client_desconectou
    )

    servidor_atual.set_fn_message_received(
        mensagem_recebida
    )

    # Mantém servidor rodando
    servidor_atual.run_forever()


# ==========================================
# 2. WATCHER - GERENCIADOR MESTRE
# ==========================================
if __name__ == '__main__':

    # PID do processo principal
    pid_mestre = os.getpid()

    print(
        "==========================================="
    )

    print(
        f"[*] PROCESSO MESTRE "
        f"(WATCHER) INICIADO "
        f"COM SUCESSO! "
        f"PID: {pid_mestre}"
    )

    print(
        "==========================================="
    )

    # Loop infinito de supervisão
    while True:

        # Cria processo isolado
        # para a réplica do servidor
        processo_servidor = multiprocessing.Process(
            target=rodar_servidor_websocket
        )

        # Inicia processo filho
        processo_servidor.start()

        # Processo mestre fica aguardando
        # até o filho morrer
        processo_servidor.join()

        # Se chegou aqui,
        # o processo caiu
        print(
            f"\n[ALERTA CRÍTICO] "
            f"O Processo Filho "
            f"de Instância morreu!"
        )

        print(
            f"[ALERTA CRÍTICO] "
            f"Mestre (PID {pid_mestre}) "
            f"está agindo para "
            f"reestabelecer o sistema..."
        )

        print(
            f"[ALERTA CRÍTICO] "
            f"Inicializando uma nova "
            f"instância isolada "
            f"em 2 segundos..."
        )

        # Pequena pausa antes
        # de reiniciar a instância
        time.sleep(2)