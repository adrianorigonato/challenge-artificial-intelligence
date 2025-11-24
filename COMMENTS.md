**Acesse: https://challenge-ozlg.onrender.com/ para testar. (Obs.: aguarde de 30 a 80 segundos até carregar o deploy)**

## Decisão da arquitetura utilizada
A arquitetura foi definida para
manter, principalmente, o foco no objetivo pedagógico da aplicação, sem
abrir mão de boa modularidade e escalabilidade. A ideia foi organizar os
fluxos em uma sequência lógica e funcional, de modo que cada parte possa
evoluir de forma independente, sem impacto indesejado sobre o restante
do sistema.

A opção por módulos independentes (ingestão, chunking, busca vetorial,
conversa, análise e geração de conteúdo) garante um pipeline claro e de
fácil manutenção, facilitando testes, a substituição de componentes
(modelos e servidores de IA, formatos e tipos de arquivos etc) e
evolução incremental.
###

## Lista de bibliotecas de terceiros utilizadas 
### Backend Python / FastAPI
- Psycopg2
- PostgreSQL 
- pgvector 
- OpenRouter API (embeddings) 
- Groq API (chat, áudio, visão) 
- pydantic 
- pdfplumber.

### Frontend
- HTML5 
- Tailwind CSS (via CDN) 
- JavaScript nativo

### Infra / Integração
- Embeddings vetoriais 
- Chunking inteligente de textos
- Ingestão multimídia (PDF, áudio, vídeo, imagem, texto, JSON) Modelos de
- Geração de conteúdo didático

## O que você melhoraria se tivesse mais tempo 
1. Aprimoramento dos Prompts e Experiência do Aluno
Refinar os prompts utilizados pelo sistema para proporcionar uma
experiência mais natural, dinâmica e engajante. O objetivo é reduzir a
taxa de abandono, garantindo que o aluno se sinta orientado, motivado e
continuamente acompanhado durante toda a jornada de aprendizagem.

2.  Registro e Evolução do Aluno por Sessão
Implementar mecanismos robustos de registro e atualização das
informações de cada sessão, armazenando a evolução do aluno em cada
tema. Isso possibilitará análises históricas, recomendações mais
precisas e personalização progressiva do processo de ensino.

3.  Classificação Prévia de Conteúdos em Subtemas
Antes da ingestão final, realizar a classificação automática do conteúdo
em subtemas. Essa padronização facilitará a análise pedagógica,
permitindo identificar de forma mais confiável o nível de conhecimento
do aluno em cada área específica.

4.  Personalização de Formatos de Conteúdo
Além de gerar o formato preferido pelo aluno, adaptar o sistema para
priorizar mais fortemente esse formato e reduzir a ênfase nos demais.
Essa estratégia aumenta a aderência ao estilo de aprendizagem do usuário
e melhora o aproveitamento dos conteúdos gerados.

5.  Hash de Conteúdo Bruto para Controle de Versões
Durante o upload de arquivos para embedding, registrar uma hash do
conteúdo bruto --- e não apenas o nome do arquivo --- para evitar
duplicações, identificar mudanças e assegurar integridade.

6.  Ambiente Administrativo para Ingestão e Gestão de Dados
Desenvolver um ambiente administrativo dedicado, permitindo que usuários
internos façam ingestão, organização e acompanhamento de conteúdos,
conversas e sessões.

7.  Logging Estruturado e Testes Automatizados
Adicionar um sistema completo de logs (auditoria, performance e erros) e
uma suíte de testes automatizados (unitários e de integração).

8.  Utilizar Ferramentas Externas para Geração de Conteúdos em Áudio e
    Vídeo
Integrar serviços externos especializados para geração de conteúdo
multimídia, permitindo criar vídeos e áudios educacionais de alta
qualidade.

## Quais requisitos obrigatórios que não foram entregues
Geração de conteúdos em formato de vídeo e áudio. Foi possível apenas criar os prompts de geração dos conteúdos nesses formatos.
#
#
## Estrutura do Projeto
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
