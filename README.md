# Chat Cliente-Servidor com Tolerância a Falhas

Este projeto é um sistema de chat em tempo real multiusuário, desenvolvido com arquitetura Cliente-Servidor e comunicação via WebSockets. Ele possui mecanismos de concorrência (Threads) e tolerância a falhas, rodando 100% na nuvem.

## Como acessar (Deploy Online)
O sistema está hospedado na nuvem e pode ser acessado de qualquer navegador (PC ou Mobile) sem necessidade de instalação.

- **Acesse o Chat aqui:** `https://chat-cliente-servidor.vercel.app` *(Nota: Pode levar ~20 segundos para o servidor despertar no primeiro acesso do dia).*

## Tecnologias Utilizadas
- **Front-end:** HTML, CSS, JavaScript Vanilla (Hospedado na Vercel)
- **Back-end:** Python 3, biblioteca `websocket-server` (Hospedado no Render)
- **Comunicação:** Protocolo `wss://` (WebSocket Secure)

## Como executar localmente (Para testes)
Caso o avaliador deseje rodar a infraestrutura em sua própria máquina, siga os passos:
1. Clone o repositório.
2. Instale as dependências executando: `pip install -r requirements.txt`
3. Execute o script mestre: `python server.py`
4. Mude a linha (100) do WebSocket no arquivo `chat.html` de `wss://...` para `ws://localhost:9001`
5. Abra o arquivo `index.html` no seu navegador.

## Principais Funcionalidades
- **Concorrência:** O servidor instacia uma thread para cada cliente conectado.
- **Tolerância a Falhas:** Um processo "Watcher" monitora a thread principal do servidor e a reinicia automaticamente em caso de queda.
- **Botão do Caos:** Um botão "Derrubar" na interface simula uma falha crítica no servidor para demonstrar a tolerância a falhas operando ao vivo.