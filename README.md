# Chat Cliente-Servidor com Tolerância a Falhas

Sistema de chat em tempo real utilizando arquitetura cliente-servidor com comunicação via WebSocket, suporte a múltiplos usuários simultâneos e tolerância a falhas.

## Deploy

O projeto foi dividido em duas aplicações:

- Front-end: hospedado no Vercel
- Back-end (WebSocket em Python): hospedado no Render

### Link do Projeto

https://chat-cliente-servidor.vercel.app

---

## Execução Local

Para executar localmente:

1. Altere a conexão WebSocket no arquivo `chat.html`:

```javascript
socket = new WebSocket(
    'wss://chatclienteservidor.onrender.com'
);
```

Para:

```javascript
socket = new WebSocket(
    'ws://localhost:9001'
);
```

2. Execute o servidor Python:

```bash
python server.py
```

3. Abra o `index.html` localmente no navegador (ou utilize Live Server).