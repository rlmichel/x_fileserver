# 📁 Fileserver v1.0

Um servidor de arquivos local e de rede LAN leve, moderno e profissional, construído exclusivamente com a **biblioteca padrão (stdlib) do Python 3.10+**, sem nenhuma dependência externa e sem necessidade de etapas de compilação ou Node.js.

---

## 🚀 Como Executar

O fluxo oficial de execução foi desenhado para ser o mais simples possível:

### Windows (Fluxo Oficial)
1. **Dê um duplo clique no arquivo [`app.py`](app.py)**.
2. Uma janela do terminal abrirá automaticamente, exibindo o banner com a URL local e a URL da rede local (LAN).
3. Acesse a URL indicada no seu computador ou em qualquer celular/dispositivo conectado à mesma rede Wi-Fi.
4. Para encerrar o servidor com segurança, pressione `Ctrl + C` na janela do terminal. Se ocorrer qualquer falha inesperada, o terminal manterá a janela aberta exibindo o erro até você pressionar Enter.

### Linux / macOS
Execute no terminal:
```bash
python3 app.py
```

---

## 📋 Requisitos do Sistema

- **Python**: versão 3.10 ou superior (testado e homologado em Python 3.10, 3.12 e 3.13+).
- **Dependências externas**: **ZERO** (`pip freeze` permanece 100% limpo).
- **Frontend**: Servido diretamente pelo Python, utilizando recursos estáticos vanilla e CDNs (Tailwind CSS, Lucide Icons, Google Fonts).

---

## ⚙️ Configuração da Pasta Compartilhada (`X:\Shared`)

Por padrão, o servidor compartilha o diretório `X:\Shared` e armazena os envios em `X:\Shared\uploads\`.

As configurações são armazenadas no arquivo [`config.json`](config.json):

```json
{
  "port": 9876,
  "shared_dir": "X:\\Shared",
  "uploads_subfolder": "uploads",
  "ftp_enabled": false,
  "filezilla_manager_enabled": false,
  "theme": "dark",
  "version": "1.0.0"
}
```

- **`shared_dir`**: Caminho absoluto da pasta que será servida. No Windows, aponta para `X:\Shared`. Caso o caminho não esteja disponível ou em ambientes Linux/macOS sem essa unidade, o servidor cria e utiliza um diretório local `./shared` como fallback automático de segurança.
- **`uploads_subfolder`**: Subpasta criada automaticamente dentro da pasta compartilhada para receber os uploads via navegador.
- **`port`**: Porta TCP em que o servidor escutará (padrão `9876`).

---

## 🌟 Funcionalidades da Versão 1.0

1. **Descoberta Dinâmica de IP**:
   - Detecta o IP real da interface de rede (LAN) em tempo de execução via socket UDP sem conexões externas pesadas.
   - Mostra no terminal o IP local e o IP de LAN ao iniciar.
   - Mostra no cabeçalho da página o IP com botão de cópia com um clique para compartilhar o link facilmente.
2. **Interface Moderna & Responsiva**:
   - Desenvolvida em Tailwind CSS com tema escuro (Dark Mode) ativado por padrão.
   - Alternância entre tema claro e escuro persistida no `localStorage`.
   - **Desktop**: Tabela organizada com ordenação interativa por Nome, Tamanho e Data de Modificação.
   - **Mobile**: Cards adaptativos fluidos com ações táteis de download e visualização rápida.
   - Breadcrumb clicável para navegar entre pastas e subpastas sem perder o contexto.
   - Filtro de busca instantânea no lado do cliente.
3. **Uploads com Drag & Drop**:
   - Arraste e solte arquivos na área pontilhada ou selecione múltiplos arquivos pelo botão de upload.
   - Barra de progresso em tempo real com cálculo de porcentagem e alertas Toast.
   - Sanitização rigorosa de nomes de arquivos e proteção contra ataques de *path traversal* (`../`).
4. **Visualização Inline (Preview)**:
   - Preview rápido em modal para imagens (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`) e arquivos de texto/código (`.txt`, `.log`, `.json`, `.py`, `.md`).
5. **Menu "Ferramentas & Integrações"**:
   - Modal com opções de expansão arquitetural: toggle de persistência para "FTP Integrado" e "Gerenciador estilo FileZilla" (preparados para as versões 1.2 e 1.3).

---

## 🛠️ Detalhes de Arquitetura: Parser Multipart Nativo

No Python 3.13, o módulo legado `cgi` (e especificamente `cgi.FieldStorage`) foi definitivamente removido da stdlib ([PEP 594](https://peps.python.org/pep-0594/)).

Para garantir longevidade sem adicionar dependências externas, o Fileserver implementa uma classe [`MultipartParser`](server/handler.py) nativa em streaming:
- Lê o fluxo `self.rfile` em pedaços de 64 KB guiados pelo `boundary` do cabeçalho `Content-Type`.
- Escreve os arquivos diretamente no disco sem manter o arquivo completo em memória RAM.
- Suporta múltiplos arquivos no mesmo envio.
- Sanitiza o nome do arquivo com [`sanitize_filename`](server/files.py), evitando sobrescritas acidentais adicionando sufixos numéricos quando necessário.

---

## 📡 Documentação da API REST

A API REST foi padronizada para permitir que a versão web atual e o futuro aplicativo móvel (React Native) consumam os mesmos endpoints.

### 1. Metadados do Servidor
- **Rota**: `GET /api/info`
- **Exemplo de Resposta (200 OK)**:
```json
{
  "name": "Fileserver",
  "version": "1.0.0",
  "host": "0.0.0.0",
  "lan_ip": "192.168.0.42",
  "port": 9876,
  "local_url": "http://127.0.0.1:9876",
  "lan_url": "http://192.168.0.42:9876",
  "os": "Windows 10",
  "shared_dir": "X:\\Shared",
  "uploads_dir": "X:\\Shared\\uploads",
  "ftp_enabled": false,
  "filezilla_manager_enabled": false,
  "theme": "dark"
}
```

### 2. Listagem de Diretório
- **Rota**: `GET /api/list?path=<caminho_relativo>`
- **Exemplo de Resposta (200 OK)**:
```json
{
  "path": "documentos",
  "parent": "",
  "entries": [
    {
      "name": "relatorio.pdf",
      "rel_path": "documentos/relatorio.pdf",
      "is_dir": false,
      "size": 1048576,
      "size_formatted": "1.0 MB",
      "mtime": 1730582400.0,
      "mtime_iso": "2026-11-02 18:00:00",
      "mime": "application/pdf"
    }
  ]
}
```

### 3. Download / Stream de Arquivo
- **Rota**: `GET /files/<caminho_relativo>`
- **Parâmetros**: `?inline=1` (opcional, para visualização no navegador ao invés de forçar download).

### 4. Download em Lote (Pacote ZIP)
- **Rota**: `POST /api/download-batch` (ou `GET /api/download-zip?files=arq1,arq2`)
- **Corpo (POST)**: `{"files": ["relatorio.pdf", "foto.png"]}`
- **Resposta**: Arquivo compactado `.zip` gerado via `zipfile` (Python stdlib) contendo os arquivos selecionados.

### 5. Upload de Arquivo
- **Rota**: `POST /upload`
- **Formato**: `multipart/form-data`
- **Resposta (200 OK)**:
```json
{
  "ok": true,
  "message": "1 arquivo(s) enviado(s) com sucesso para a pasta de uploads.",
  "saved": [
    {
      "name": "foto.png",
      "size": 204800,
      "size_formatted": "200.0 KB",
      "saved_at": "2026-11-02 18:30:00"
    }
  ]
}
```

### 6. Configuração
- **Rota**: `POST /api/config`
- **Corpo**: JSON com opções a atualizar (ex: `{"ftp_enabled": true}`).

---

## 📂 Estrutura de Pastas

```
x_fileserver/
├── app.py                  # Entrypoint executável por duplo clique
├── config.json             # Configurações persistentes
├── README.md               # Documentação técnica
├── ROADMAP.md              # Próximas fases (v1.1 a v2.0)
├── server/                 # Módulos do backend
│   ├── __init__.py
│   ├── config.py           # Gestão de caminhos e config.json
│   ├── files.py            # Listagem, sanitização e formatação de dados
│   ├── handler.py          # HTTP RequestHandler customizado e MultipartParser
│   └── net.py              # Detecção dinâmica de IP da rede (LAN)
└── static/                 # Frontend servido diretamente
    ├── app.css             # Estilos adicionais e animações
    ├── app.js              # Lógica da interface, AJAX e drag-and-drop
    └── index.html          # Interface responsiva moderna
```
