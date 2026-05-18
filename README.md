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

### 1. Criar ambiente virtual

```bash
python -m venv venv
```

### 2. Ativar ambiente virtual

#### Windows
```bash
venv\Scripts\activate
```

#### Linux/macOS
```bash
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Alterar a conexão WebSocket no arquivo `chat.html`

Troque:

```javascript
socket = new WebSocket(
    'wss://chatclienteservidor.onrender.com'
);
```

Por:

```javascript
socket = new WebSocket(
    'ws://localhost:9001'
);
```

### 5. Executar o servidor Python

```bash
python server.py
```

### 6. Abrir o front-end

Abra o `index.html` localmente no navegador (ou utilize Live Server).