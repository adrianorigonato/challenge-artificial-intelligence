# Acesse: https://challenge-ozlg.onrender.com/ para testar. (Obs.: aguarde de 30 a 80 segundos até terminar de carregar o deploy)

**Estrutura do Projeto**
```
/
├── app.py                     # App FastAPI principal
├── chunking.py               # Split de texto, embeddings e busca vetorial
├── config.py                 # Configuração de APIs e variáveis de ambiente
├── content_generation.py     # Geração de conteúdos personalizados
├── conversation.py           # Lógica de conversa para análise
├── conversation_analysis.py  # Avaliação pedagógica da conversa
├── db.py                     # Conexão e schema do banco
├── extract.py                # Ingestão e extração multimídia
├── orchestrator.py           # Fluxo completo RAG + análise + geração
└── frontend/
    ├── index.html            # Interface da aplicação :contentReference[oaicite:0]{index=0}
    └── main.js               # Lógica de UI/UX no navegador :contentReference[oaicite:1]{index=1}

```

---

**Como Funciona**

### 1. Ingestão de arquivos

O usuário pode enviar:

- PDF  
- TXT  
- JSON  
- Áudio (mp3, wav)  
- Vídeo (mp4, mov, webm...)  
- Imagens (png, jpg, webp...)

O sistema:

- Extrai texto (OCR, transcrição ou descrição de imagem)  
- Chunkifica o conteúdo (200–400 palavras com overlap)  
- Gera embeddings via OpenRouter  
- Armazena os chunks em Postgres com pgvector  

---

### 2. Chat com RAG

Cada mensagem é:

- Processada com busca vetorial  
- Contextualizada com os chunks mais relevantes  
- Respondida por modelo Groq, restrito ao contexto  

---

### 3. Análise pedagógica

A conversa é analisada por um modelo Groq que identifica:

- Subtemas  
- Nível do usuário: básico, intermediário, avançado, domina  
- Justificativa  

---

### 4. Geração de conteúdos personalizados

Para os subtemas com menor domínio, o sistema gera:

- Roteiros de vídeo  
- Roteiros de áudio  
- Textos explicativos  

Baseado somente nos trechos da base ingerida.

---

**Como Executar**

### 1. Clone o repositório
```bash
git clone https://github.com/seuusuario/rag-learning-web.git
cd rag-learning-web
```

### 2. Crie um ambiente virtual
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure variáveis de ambiente

Crie um arquivo `.env` com:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/database
OPENROUTER_API_KEY=...
GROQ_API_KEY=...
```

### 5. Execute o servidor
```bash
uvicorn app:app --reload
```

Acesse em:  
**http://localhost:8000**

---

**Endpoints Principais**

### POST `/api/ingest`
Envia arquivos para ingestão vetorial.

### POST `/api/conversation/start`
Cria uma nova conversa.

### POST `/api/conversation/chat`
Envia mensagem para o chat com RAG.

### POST `/api/conversation/{id}/analyze-and-generate`
Gera conteúdos de estudo personalizados.

---

🎨 **Interface**

A UI possui três abas:

**Chat**
- Conversa guiada pelo assistente  
- Escolha de formato de conteúdo preferido  
- Mensagens estilo “bubble chat”

**Estudar**
- Exibe somente os conteúdos gerados  
- Renderização automática ao trocar de aba  
- Cacheamento inteligente para evitar recomputação

**Ingestão**
- Upload de arquivos  
- Feedback sobre chunks inseridos  
