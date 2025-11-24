## Acesse: https://challenge-ozlg.onrender.com/ para testar. 
**(Obs.: aguarde de 30 a 80 segundos até terminar de carregar o deploy)**

##Decisão da arquitetura utilizada A arquitetura foi definida para
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

##Lista de bibliotecas de terceiros utilizadas 
###Backend Python / FastAPI
Psycopg2 PostgreSQL pgvector OpenRouter API (embeddings) Groq API (chat,
áudio, visão) pydantic pdfplumber.

###Frontend
 HTML5 Tailwind CSS (via CDN) JavaScript nativo

###Infra / Integração
Embeddings vetoriais 
Chunking inteligente de textos
Ingestão multimídia (PDF, áudio, vídeo, imagem, texto, JSON) Modelos de
Geração de conteúdo didático

##O que você melhoraria se tivesse mais tempo 1. Aprimoramento dos
1. Prompts e Experiência do Aluno
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

##Quais requisitos obrigatórios que não foram entregues geração de
Geração de conteúdos em formato de vídeo e áudio. Foi possível apenas criar os prompts de geração dos conteúdos nesses formatos.
