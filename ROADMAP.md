# 🗺️ Roadmap do Fileserver

Este documento estabelece o plano de evolução do **Fileserver**, desde a versão v1.0 atual até o aplicativo móvel nativo na versão v2.0.

---

## 📍 v1.0 — Fundação Profissional (Versão Atual)
- [x] Motor 100% Python stdlib (sem dependências externas).
- [x] Execução amigável por duplo clique no Windows com recuperação de falhas.
- [x] Descoberta dinâmica do IP da LAN e exibição de URLs no terminal e na interface web.
- [x] Interface moderna, limpa e responsiva (Tailwind CSS CDN + Lucide Icons + Inter).
- [x] Tema escuro por padrão com alternância de tema claro/escuro persistente no navegador.
- [x] Listagem de arquivos com ordenação interativa (Nome, Tamanho, Data) e busca em tempo real.
- [x] Navegação de pastas por breadcrumbs clicáveis.
- [x] Upload por Drag & Drop e formulário padrão com barra de progresso em tempo real.
- [x] Sanitização de caminhos contra ataques de Path Traversal (`../`).
- [x] Parser streaming de multipart/form-data sem uso do módulo depreciado `cgi`.
- [x] Previews inline básicos de imagens e arquivos de texto.
- [x] Menu "Ferramentas" com toggles persistidos no `config.json`.
- [x] Definição estável da API REST (`/api/info`, `/api/list`, `/upload`, `/files/<path>`, `/api/config`).

---

## 🚀 v1.1 — Gestão de Arquivos & Multimídia
- [ ] **Operações de Arquivos**:
  - Exclusão de arquivos e pastas com diálogo modal de confirmação.
  - Renomeação de arquivos e pastas diretamente na interface.
  - Criação de novas pastas na raiz ou em subdiretórios.
- [ ] **Visualizador Multimídia Avançado**:
  - Player embutido para arquivos de áudio (`.mp3`, `.wav`, `.flac`, `.ogg`).
  - Player embutido para vídeos (`.mp4`, `.webm`).
  - Visualizador de arquivos `.pdf` em modal com suporte a paginação.
- [ ] **Aprimoramentos de Upload**:
  - Fila de uploads com possibilidade de pausar e cancelar envios individuais.
  - Suporte ao upload de pastas inteiras via `webkitdirectory`.
  - Notificações sonoras discretas de conclusão de upload.

---

## ⚡ v1.2 — FTP Integrado
- [ ] **Servidor FTP Concorrente**:
  - O toggle "FTP Integrado" no menu **Ferramentas** passa a iniciar/interromper o serviço FTP real em segundo plano.
  - Avaliação de arquitetura:
    - *Opção A*: Motor nativo leve baseado em sockets stdlib (`asyncore`/`asyncio` ou threads `socketserver`) mantendo a filosofia zero-dependências.
    - *Opção B*: Módulo opcional via `pyftpdlib` instalado sob demanda via script auxiliar caso o usuário deseje recursos FTP avançados.
  - Configuração de portas (padrão `21` ou porta alternativa `2121` sem privilégios administrativos no Windows/Linux).
  - Usuários anônimos ou autenticação com senha configurável no `config.json`.

---

## 🖥️ v1.3 — Gerenciador Visual estilo FileZilla
- [ ] **Interface Dual-Pane**:
  - Painel duplo: visualização do armazenamento local do cliente / visualização do Fileserver.
  - Arrastar e soltar entre painéis para transferência direta.
  - Barra de status inferior com histórico de transferências ativas, concluídas e falhas.
  - Sincronização visual de pastas e comparação de diferenças de tamanho/data entre diretórios.

---

## 📱 v2.0 — Aplicativo Mobile Nativo (React Native + NativeWind)
- [ ] **App Nativo para iOS e Android**:
  - Construído com React Native e estilizado com NativeWind (Tailwind CSS para React Native).
  - Consumo direto da mesma API REST implementada na v1.0:
    - Descoberta automática de servidores na rede local via mDNS / SSDP ou entrada de IP manual.
    - `GET /api/info` para checagem de integridade e metadados.
    - `GET /api/list` para listagem paginada e virtualizada de arquivos.
    - `POST /upload` para envio em segundo plano através do seletor nativo de documentos e fotos do smartphone.
    - `GET /files/...` para download com integração ao compartilhamento nativo do sistema operacional.
  - Armazenamento em cache offline de miniaturas de fotos e documentos recentes.

---

## 💡 Ideias em Avaliação para Versões Futuras
- **Acesso Rápido via QR Code**: Exibir um QR Code no cabeçalho ou menu para escanear com a câmera do celular e abrir o Fileserver instantaneamente sem precisar digitar o IP.
- **Autenticação Simples**: Proteção opcional por PIN numérico ou Token nas configurações para redes públicas/compartilhadas.
- **HTTPS Local**: Geração automatizada de certificados self-signed locais para conexões TLS cifradas na rede interna.
- **Compactação ZIP On-The-Fly**: Opção de baixar uma pasta inteira como `.zip` gerado em streaming.
