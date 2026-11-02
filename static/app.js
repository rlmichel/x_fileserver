/**
 * Fileserver v1.0 - Frontend Engine
 * Desenvolvido em JavaScript Vanilla puro, consumindo a API REST do servidor.
 */

(() => {
  // Estado da aplicação
  const state = {
    currentPath: '',
    parentPath: null,
    items: [],
    serverInfo: null,
    sortColumn: 'name',
    sortAsc: true,
    searchQuery: '',
    selectedFiles: new Set(),
    theme: localStorage.getItem('fileserver_theme') || 'dark',
  };

  // Elementos do DOM
  const elements = {
    html: document.documentElement,
    themeToggleBtn: document.getElementById('btn-toggle-theme'),
    themeIcon: document.getElementById('theme-icon'),
    lanIpText: document.getElementById('lan-ip-text'),
    btnCopyUrl: document.getElementById('btn-copy-url'),
    breadcrumbs: document.getElementById('breadcrumbs'),
    searchInput: document.getElementById('input-search'),
    fileInput: document.getElementById('input-file'),
    dropzone: document.getElementById('dropzone'),
    uploadContainer: document.getElementById('upload-progress-container'),
    uploadFilename: document.getElementById('upload-filename'),
    uploadPercentage: document.getElementById('upload-percentage'),
    uploadProgressBar: document.getElementById('upload-progress-bar'),
    folderStats: document.getElementById('folder-stats'),
    btnToggleSelectAll: document.getElementById('btn-toggle-select-all'),
    thSelectAll: document.getElementById('th-select-all'),
    tableBody: document.getElementById('file-table-body'),
    mobileCards: document.getElementById('file-cards-mobile'),
    emptyState: document.getElementById('empty-state'),
    sortName: document.getElementById('sort-name'),
    sortSize: document.getElementById('sort-size'),
    sortDate: document.getElementById('sort-date'),
    toastContainer: document.getElementById('toast-container'),
    // Barra de seleção em lote
    selectionBar: document.getElementById('selection-bar'),
    selectedCountBadge: document.getElementById('selected-count-badge'),
    btnDownloadZip: document.getElementById('btn-download-zip'),
    btnDownloadIndividual: document.getElementById('btn-download-individual'),
    btnClearSelection: document.getElementById('btn-clear-selection'),
    // Modal Ferramentas
    btnOpenTools: document.getElementById('btn-open-tools'),
    modalTools: document.getElementById('modal-tools'),
    btnCloseTools: document.getElementById('btn-close-tools'),
    btnSaveTools: document.getElementById('btn-save-tools'),
    toggleFtp: document.getElementById('toggle-ftp'),
    toggleFilezilla: document.getElementById('toggle-filezilla'),
    // Modal Preview
    modalPreview: document.getElementById('modal-preview'),
    previewFilename: document.getElementById('preview-filename'),
    previewBody: document.getElementById('preview-body'),
    previewIcon: document.getElementById('preview-icon'),
    previewDownloadLink: document.getElementById('preview-download-link'),
    btnClosePreview: document.getElementById('btn-close-preview'),
    // Modal Roadmap
    btnOpenRoadmap: document.getElementById('btn-open-roadmap'),
    modalRoadmap: document.getElementById('modal-roadmap'),
    btnCloseRoadmap: document.getElementById('btn-close-roadmap'),
    btnDismissRoadmap: document.getElementById('btn-dismiss-roadmap'),
  };

  // =========================================================================
  // TEMA (Dark / Light Mode)
  // =========================================================================
  function applyTheme(theme) {
    state.theme = theme;
    localStorage.setItem('fileserver_theme', theme);
    if (theme === 'dark') {
      elements.html.classList.add('dark');
      elements.themeIcon.setAttribute('data-lucide', 'moon');
    } else {
      elements.html.classList.remove('dark');
      elements.themeIcon.setAttribute('data-lucide', 'sun');
    }
    refreshLucideIcons();
  }

  function toggleTheme() {
    applyTheme(state.theme === 'dark' ? 'light' : 'dark');
  }

  // =========================================================================
  // TOAST NOTIFICAÇÕES
  // =========================================================================
  function showToast(message, type = 'info', duration = 3500) {
    const toast = document.createElement('div');
    const colors = {
      success: 'bg-emerald-600 text-white border-emerald-500',
      error: 'bg-rose-600 text-white border-rose-500',
      info: 'bg-indigo-600 text-white border-indigo-500',
      warning: 'bg-amber-600 text-white border-amber-500',
    };
    const iconName = {
      success: 'check-circle-2',
      error: 'alert-triangle',
      info: 'info',
      warning: 'alert-circle',
    }[type] || 'info';

    toast.className = `pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-lg text-xs sm:text-sm font-medium animate-slide-in ${colors[type]}`;
    toast.innerHTML = `
      <i data-lucide="${iconName}" class="w-4 h-4 flex-shrink-0"></i>
      <span class="flex-1">${escapeHtml(message)}</span>
    `;

    elements.toastContainer.appendChild(toast);
    refreshLucideIcons();

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease-in';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // =========================================================================
  // CARREGAR INFORMAÇÕES DO SERVIDOR (/api/info)
  // =========================================================================
  async function fetchServerInfo() {
    try {
      const res = await fetch('/api/info');
      if (!res.ok) throw new Error('Falha ao obter dados do servidor');
      const data = await res.json();
      state.serverInfo = data;

      // Exibir URL com IP da LAN em destaque
      const lanUrl = data.lan_url || `http://${data.lan_ip}:${data.port}`;
      elements.lanIpText.textContent = lanUrl;
      elements.btnCopyUrl.setAttribute('data-copy-val', lanUrl);

      // Atualiza toggles de ferramentas
      if (elements.toggleFtp) {
        elements.toggleFtp.checked = Boolean(data.ftp_enabled);
      }
      if (elements.toggleFilezilla) {
        elements.toggleFilezilla.checked = Boolean(data.filezilla_manager_enabled);
      }
    } catch (err) {
      console.error('Erro ao consultar /api/info:', err);
      elements.lanIpText.textContent = window.location.origin;
      elements.btnCopyUrl.setAttribute('data-copy-val', window.location.origin);
    }
  }

  // =========================================================================
  // CARREGAR LISTAGEM DE ARQUIVOS (/api/list)
  // =========================================================================
  async function loadDirectory(path = state.currentPath) {
    try {
      const url = `/api/list?path=${encodeURIComponent(path)}`;
      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok) {
        showToast(data.error || 'Erro ao carregar diretório', 'error');
        return;
      }

      state.currentPath = data.path || '';
      state.parentPath = data.parent !== undefined ? data.parent : null;
      state.items = data.entries || [];
      state.selectedFiles.clear();

      renderBreadcrumbs();
      renderItems();
      updateSelectionUI();

      // Atualiza dica de destino do upload
      const dropDest = document.getElementById('drop-dest-text');
      if (dropDest) {
        dropDest.textContent = state.currentPath.startsWith('shared') ? 'shared/uploads/' : 'uploads/';
      }
    } catch (err) {
      showToast('Falha na conexão com o servidor', 'error');
      console.error('Erro ao carregar diretório:', err);
    }
  }

  // =========================================================================
  // RENDERIZAÇÃO DE BREADCRUMBS
  // =========================================================================
  function renderBreadcrumbs() {
    elements.breadcrumbs.innerHTML = '';

    // Botão Raiz
    const rootBtn = document.createElement('button');
    rootBtn.className = 'breadcrumb-item flex items-center gap-1.5 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors px-2 py-1 rounded-md hover:bg-slate-200/60 dark:hover:bg-slate-800/80';
    rootBtn.innerHTML = `
      <i data-lucide="home" class="w-4 h-4 text-indigo-500"></i>
      <span>Raiz</span>
    `;
    rootBtn.onclick = () => loadDirectory('');
    elements.breadcrumbs.appendChild(rootBtn);

    if (!state.currentPath) {
      refreshLucideIcons();
      return;
    }

    const segments = state.currentPath.split('/').filter(Boolean);
    let accumPath = '';

    segments.forEach((seg, idx) => {
      accumPath += (accumPath ? '/' : '') + seg;
      const thisPath = accumPath;

      // Separador
      const sep = document.createElement('span');
      sep.className = 'text-slate-400 text-xs px-0.5 select-none';
      sep.textContent = '/';
      elements.breadcrumbs.appendChild(sep);

      // Segmento
      const segBtn = document.createElement('button');
      const isLast = idx === segments.length - 1;
      segBtn.className = `flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
        isLast
          ? 'font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/40'
          : 'hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-200/60 dark:hover:bg-slate-800/80'
      }`;
      segBtn.textContent = seg;
      if (!isLast) {
        segBtn.onclick = () => loadDirectory(thisPath);
      }
      elements.breadcrumbs.appendChild(segBtn);
    });

    refreshLucideIcons();
  }

  // =========================================================================
  // ÍCONES E CLASSIFICAÇÃO POR TIPO
  // =========================================================================
  function getFileIconInfo(item) {
    if (item.is_shared) {
      return { icon: 'share-2', color: 'text-indigo-500 dark:text-indigo-400', isShared: true };
    }
    if (item.is_dir) {
      return { icon: 'folder', color: 'text-amber-500 dark:text-amber-400' };
    }
    const ext = item.name.split('.').pop()?.toLowerCase() || '';
    const mime = item.mime || '';

    if (mime.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) {
      return { icon: 'image', color: 'text-emerald-500 dark:text-emerald-400', isImage: true };
    }
    if (mime.startsWith('video/') || ['mp4', 'mkv', 'avi', 'mov', 'webm'].includes(ext)) {
      return { icon: 'film', color: 'text-rose-500 dark:text-rose-400' };
    }
    if (mime.startsWith('audio/') || ['mp3', 'wav', 'ogg', 'flac', 'm4a'].includes(ext)) {
      return { icon: 'music', color: 'text-violet-500 dark:text-violet-400' };
    }
    if (ext === 'pdf') {
      return { icon: 'file-text', color: 'text-red-500 dark:text-red-400' };
    }
    if (['zip', 'rar', '7z', 'tar', 'gz', 'bz2'].includes(ext)) {
      return { icon: 'archive', color: 'text-amber-600 dark:text-amber-500' };
    }
    if (['py', 'js', 'html', 'css', 'json', 'ts', 'jsx', 'tsx', 'php', 'c', 'cpp', 'rs', 'go', 'sh', 'bat'].includes(ext)) {
      return { icon: 'code', color: 'text-sky-500 dark:text-sky-400', isText: true };
    }
    if (mime.startsWith('text/') || ['txt', 'md', 'log', 'ini', 'cfg', 'csv', 'yaml', 'yml'].includes(ext)) {
      return { icon: 'file-text', color: 'text-blue-500 dark:text-blue-400', isText: true };
    }
    return { icon: 'file', color: 'text-slate-400 dark:text-slate-500' };
  }

  // =========================================================================
  // GESTÃO DE SELEÇÃO DE ARQUIVOS
  // =========================================================================
  function toggleSelect(relPath) {
    if (state.selectedFiles.has(relPath)) {
      state.selectedFiles.delete(relPath);
    } else {
      state.selectedFiles.add(relPath);
    }
    renderItems();
    updateSelectionUI();
  }

  function toggleSelectAll() {
    const fileEntries = state.items.filter((i) => !i.is_dir);
    if (fileEntries.length === 0) return;

    const allSelected = fileEntries.every((i) => state.selectedFiles.has(i.rel_path));
    if (allSelected) {
      state.selectedFiles.clear();
    } else {
      fileEntries.forEach((i) => state.selectedFiles.add(i.rel_path));
    }
    renderItems();
    updateSelectionUI();
  }

  function updateSelectionUI() {
    const count = state.selectedFiles.size;
    elements.selectedCountBadge.textContent = count;

    if (count > 0) {
      elements.selectionBar.classList.remove('translate-y-24', 'opacity-0', 'pointer-events-none');
      elements.selectionBar.classList.add('translate-y-0', 'opacity-100');
    } else {
      elements.selectionBar.classList.add('translate-y-24', 'opacity-0', 'pointer-events-none');
      elements.selectionBar.classList.remove('translate-y-0', 'opacity-100');
    }

    const fileEntries = state.items.filter((i) => !i.is_dir);
    const hasFiles = fileEntries.length > 0;
    const allSelected = hasFiles && fileEntries.every((i) => state.selectedFiles.has(i.rel_path));

    if (elements.thSelectAll) {
      elements.thSelectAll.checked = allSelected;
      elements.thSelectAll.disabled = !hasFiles;
    }
    if (elements.btnToggleSelectAll) {
      elements.btnToggleSelectAll.textContent = allSelected ? 'Desmarcar todos' : 'Selecionar todos';
      elements.btnToggleSelectAll.style.display = hasFiles ? 'inline-block' : 'none';
    }
  }

  // =========================================================================
  // DOWNLOAD EM LOTE (ZIP e INDIVIDUAIS)
  // =========================================================================
  async function downloadSelectedZip() {
    const files = Array.from(state.selectedFiles);
    if (files.length === 0) return;

    showToast(`Gerando pacote ZIP com ${files.length} arquivo(s)...`, 'info', 4000);

    try {
      const res = await fetch('/api/download-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files }),
      });

      if (!res.ok) {
        let errMsg = 'Falha ao compor arquivo ZIP';
        try {
          const errData = await res.json();
          if (errData.error) errMsg = errData.error;
        } catch {}
        throw new Error(errMsg);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
      a.download = `fileserver_${timestamp}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();

      showToast('Download do pacote ZIP iniciado com sucesso!', 'success');
    } catch (err) {
      showToast(err.message || 'Erro ao gerar ZIP', 'error');
    }
  }

  async function downloadSelectedIndividual() {
    const files = Array.from(state.selectedFiles);
    if (files.length === 0) return;

    showToast(`Iniciando download individual de ${files.length} arquivo(s)...`, 'info', 2500);

    for (let i = 0; i < files.length; i++) {
      const relPath = files[i];
      const fileName = relPath.split('/').pop() || 'download';
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = `/files/${encodeURIComponent(relPath)}`;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();

      // Intervalo de segurança para o navegador não bloquear popups
      if (i < files.length - 1) {
        await new Promise((r) => setTimeout(r, 300));
      }
    }
  }

  // =========================================================================
  // RENDERIZAÇÃO DOS ITENS (Tabela Desktop e Cards Mobile)
  // =========================================================================
  function renderItems() {
    // 1. Filtragem por busca
    let filtered = state.items.filter((item) => {
      if (!state.searchQuery) return true;
      return item.name.toLowerCase().includes(state.searchQuery.toLowerCase());
    });

    // 2. Ordenação
    filtered.sort((a, b) => {
      // Pastas sempre no topo se ordenado por nome
      if (a.is_dir !== b.is_dir) {
        return a.is_dir ? -1 : 1;
      }
      let valA = a[state.sortColumn];
      let valB = b[state.sortColumn];

      if (typeof valA === 'string') {
        valA = valA.toLowerCase();
        valB = (valB || '').toLowerCase();
      }

      if (valA < valB) return state.sortAsc ? -1 : 1;
      if (valA > valB) return state.sortAsc ? 1 : -1;
      return 0;
    });

    // Estatísticas
    const totalCount = filtered.length;
    const filesOnly = filtered.filter((i) => !i.is_dir);
    const totalBytes = filesOnly.reduce((acc, curr) => acc + (curr.size || 0), 0);
    elements.folderStats.textContent = `${totalCount} item(ns)${
      filesOnly.length > 0 ? ` (${formatBytes(totalBytes)} em arquivos)` : ''
    }`;

    // Estado vazio
    if (filtered.length === 0) {
      elements.tableBody.innerHTML = '';
      elements.mobileCards.innerHTML = '';
      elements.emptyState.classList.remove('hidden');
      return;
    }
    elements.emptyState.classList.add('hidden');

    // Monta Tabela Desktop
    let tableHtml = '';
    let cardsHtml = '';

    // Se estiver em subpasta, adiciona item para subir um nível
    if (state.currentPath && !state.searchQuery) {
      tableHtml += `
        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors group" onclick="window.fileserver.goParent()">
          <td colspan="5" class="py-2.5 px-4 font-semibold text-indigo-600 dark:text-indigo-400">
            <div class="flex items-center gap-2">
              <i data-lucide="corner-left-up" class="w-4 h-4 text-indigo-500"></i>
              <span>.. (subir um nível)</span>
            </div>
          </td>
        </tr>
      `;
    }

    filtered.forEach((item) => {
      const iconInfo = getFileIconInfo(item);
      const downloadUrl = `/files/${encodeURIComponent(item.rel_path)}`;
      const canPreview = iconInfo.isImage || iconInfo.isText;
      const isSelected = state.selectedFiles.has(item.rel_path);

      // HTML da linha da tabela desktop (5 colunas)
      tableHtml += `
        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group ${isSelected ? 'bg-indigo-50/50 dark:bg-indigo-950/30' : ''}">
          <td class="py-3 px-3 text-center">
            ${
              !item.is_dir
                ? `<input type="checkbox" class="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 cursor-pointer" ${isSelected ? 'checked' : ''} onchange="window.fileserver.toggleSelect('${escapeAttr(item.rel_path)}')">`
                : `<span class="text-slate-300 dark:text-slate-700 select-none text-xs">•</span>`
            }
          </td>
          <td class="py-3 px-3 font-medium text-slate-800 dark:text-slate-200">
            <div class="flex items-center gap-3">
              <i data-lucide="${iconInfo.icon}" class="w-5 h-5 flex-shrink-0 ${iconInfo.color}"></i>
              ${
                item.is_dir
                  ? `<button onclick="window.fileserver.openDir('${escapeAttr(item.rel_path)}')" class="hover:text-indigo-600 dark:hover:text-indigo-400 text-left font-semibold hover:underline inline-flex items-center gap-1.5">
                      <span>${escapeHtml(item.name)}</span>
                      ${item.is_shared ? '<span class="px-1.5 py-0.2 text-[10px] font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 rounded border border-indigo-200 dark:border-indigo-800">Shared</span>' : ''}
                     </button>`
                  : `<span class="truncate max-w-md">${escapeHtml(item.name)}</span>`
              }
            </div>
          </td>
          <td class="py-3 px-4 text-slate-500 dark:text-slate-400 whitespace-nowrap text-xs">
            ${item.size_formatted}
          </td>
          <td class="py-3 px-4 text-slate-500 dark:text-slate-400 whitespace-nowrap text-xs">
            ${item.mtime_iso}
          </td>
          <td class="py-3 px-4 text-right whitespace-nowrap">
            <div class="flex items-center justify-end gap-1">
              ${
                canPreview
                  ? `<button onclick="window.fileserver.previewItem('${escapeAttr(item.rel_path)}', '${escapeAttr(item.name)}', ${Boolean(iconInfo.isImage)})" class="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors" title="Visualizar">
                      <i data-lucide="eye" class="w-4 h-4"></i>
                     </button>`
                  : ''
              }
              ${
                !item.is_dir
                  ? `<a href="${downloadUrl}" download="${escapeAttr(item.name)}" class="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors inline-block" title="Baixar">
                      <i data-lucide="download" class="w-4 h-4"></i>
                     </a>`
                  : `<button onclick="window.fileserver.openDir('${escapeAttr(item.rel_path)}')" class="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors" title="Abrir pasta">
                      <i data-lucide="chevron-right" class="w-4 h-4"></i>
                     </button>`
              }
            </div>
          </td>
        </tr>
      `;

      // HTML do Card Mobile
      cardsHtml += `
        <div class="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm flex items-center justify-between gap-2.5 transition-colors ${isSelected ? 'border-indigo-400 dark:border-indigo-600 bg-indigo-50/40 dark:bg-indigo-950/30' : ''}">
          <div class="flex items-center gap-2.5 min-w-0 flex-1">
            ${
              !item.is_dir
                ? `<div class="flex items-center flex-shrink-0">
                    <input type="checkbox" class="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 cursor-pointer" ${isSelected ? 'checked' : ''} onchange="window.fileserver.toggleSelect('${escapeAttr(item.rel_path)}')">
                   </div>`
                : ''
            }
            <div class="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 flex-shrink-0">
              <i data-lucide="${iconInfo.icon}" class="w-4 h-4 sm:w-5 sm:h-5 ${iconInfo.color}"></i>
            </div>
            <div class="min-w-0 flex-1">
              ${
                item.is_dir
                  ? `<button onclick="window.fileserver.openDir('${escapeAttr(item.rel_path)}')" class="font-semibold text-xs sm:text-sm text-slate-900 dark:text-slate-100 hover:text-indigo-600 dark:hover:text-indigo-400 truncate block text-left">
                      <span>${escapeHtml(item.name)}</span>
                      ${item.is_shared ? '<span class="px-1.5 py-0.2 text-[9px] font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 rounded border border-indigo-200 dark:border-indigo-800 ml-1">Shared</span>' : ''}
                     </button>`
                  : `<p class="font-medium text-xs sm:text-sm text-slate-800 dark:text-slate-200 truncate">
                      ${escapeHtml(item.name)}
                     </p>`
              }
              <div class="flex items-center gap-1.5 mt-0.5 text-[11px] text-slate-400">
                <span>${item.size_formatted}</span>
                <span>•</span>
                <span>${item.mtime_iso.split(' ')[0]}</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-1 flex-shrink-0">
            ${
              canPreview
                ? `<button onclick="window.fileserver.previewItem('${escapeAttr(item.rel_path)}', '${escapeAttr(item.name)}', ${Boolean(iconInfo.isImage)})" class="p-1.5 text-slate-500 dark:text-slate-400 hover:text-indigo-600 rounded-lg bg-slate-50 dark:bg-slate-800" title="Ver">
                    <i data-lucide="eye" class="w-4 h-4"></i>
                   </button>`
                : ''
            }
            ${
              !item.is_dir
                ? `<a href="${downloadUrl}" download="${escapeAttr(item.name)}" class="p-1.5 text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg inline-flex items-center justify-center shadow-sm" title="Baixar">
                    <i data-lucide="download" class="w-4 h-4"></i>
                   </a>`
                : `<button onclick="window.fileserver.openDir('${escapeAttr(item.rel_path)}')" class="p-1.5 text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 rounded-lg bg-slate-100 dark:bg-slate-800">
                    <i data-lucide="chevron-right" class="w-4 h-4"></i>
                   </button>`
            }
          </div>
        </div>
      `;
    });

    elements.tableBody.innerHTML = tableHtml;
    elements.mobileCards.innerHTML = cardsHtml;
    refreshLucideIcons();
  }

  // =========================================================================
  // UPLOAD DE ARQUIVOS COM BARRA DE PROGRESSO
  // =========================================================================
  function uploadFiles(fileList) {
    if (!fileList || fileList.length === 0) return;

    const files = Array.from(fileList);
    const formData = new FormData();
    for (const f of files) {
      formData.append('files', f);
    }

    elements.uploadContainer.classList.remove('hidden');
    elements.uploadFilename.textContent = files.length === 1 ? files[0].name : `${files.length} arquivos selecionados`;
    elements.uploadPercentage.textContent = '0%';
    elements.uploadProgressBar.style.width = '0%';

    const xhr = new XMLHttpRequest();
    const uploadUrl = `/upload?path=${encodeURIComponent(state.currentPath || '')}`;
    xhr.open('POST', uploadUrl, true);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        elements.uploadPercentage.textContent = `${percent}%`;
        elements.uploadProgressBar.style.width = `${percent}%`;
      }
    };

    xhr.onload = () => {
      elements.uploadContainer.classList.add('hidden');
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText);
          showToast(res.message || 'Arquivo(s) enviado(s) com sucesso!', 'success');
        } catch {
          showToast('Upload concluído com sucesso!', 'success');
        }
        loadDirectory(state.currentPath);
      } else {
        let errMessage = 'Erro no envio do arquivo.';
        try {
          const res = JSON.parse(xhr.responseText);
          if (res.error) errMessage = res.error;
        } catch {}
        showToast(errMessage, 'error');
      }
      elements.fileInput.value = '';
    };

    xhr.onerror = () => {
      elements.uploadContainer.classList.add('hidden');
      showToast('Erro de rede ao tentar enviar arquivo', 'error');
      elements.fileInput.value = '';
    };

    xhr.send(formData);
  }

  // =========================================================================
  // PREVIEW MODAL
  // =========================================================================
  async function openPreview(relPath, filename, isImage) {
    elements.previewFilename.textContent = filename;
    elements.previewDownloadLink.href = `/files/${encodeURIComponent(relPath)}`;
    elements.previewDownloadLink.download = filename;
    elements.previewBody.innerHTML = `
      <div class="flex items-center gap-2 text-slate-500 py-12">
        <i data-lucide="loader-2" class="w-6 h-6 animate-spin"></i>
        <span>Carregando visualização...</span>
      </div>
    `;
    elements.modalPreview.classList.remove('hidden');
    refreshLucideIcons();

    const fileUrl = `/files/${encodeURIComponent(relPath)}?inline=1`;

    if (isImage) {
      const img = new Image();
      img.src = fileUrl;
      img.className = 'max-h-[65vh] max-w-full rounded-lg object-contain shadow-md';
      img.onload = () => {
        elements.previewBody.innerHTML = '';
        elements.previewBody.appendChild(img);
      };
      img.onerror = () => {
        elements.previewBody.innerHTML = `<p class="text-rose-500 text-sm">Não foi possível carregar a imagem.</p>`;
      };
    } else {
      // Texto simples / código
      try {
        const res = await fetch(fileUrl);
        if (!res.ok) throw new Error('Falha ao baixar arquivo');
        const text = await res.text();
        elements.previewBody.innerHTML = `
          <pre class="w-full text-xs font-mono p-4 rounded-lg bg-slate-900 text-slate-200 overflow-x-auto max-h-[65vh] select-text"><code>${escapeHtml(text)}</code></pre>
        `;
      } catch {
        elements.previewBody.innerHTML = `<p class="text-rose-500 text-sm">Erro ao carregar conteúdo do arquivo.</p>`;
      }
    }
  }

  function closePreview() {
    elements.modalPreview.classList.add('hidden');
    elements.previewBody.innerHTML = '';
  }

  // =========================================================================
  // MODAL FERRAMENTAS & INTEGRAÇÕES
  // =========================================================================
  function openTools() {
    elements.modalTools.classList.remove('hidden');
  }

  function closeTools() {
    elements.modalTools.classList.add('hidden');
  }

  async function handleFtpToggle(enabled) {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ftp_enabled: enabled }),
      });
      if (!res.ok) throw new Error();
      showToast(
        enabled
          ? 'FTP habilitado no config. O serviço FTP nativo será iniciado na v1.2!'
          : 'FTP desativado.',
        'info'
      );
    } catch {
      showToast('Erro ao salvar configuração do FTP', 'error');
    }
  }

  async function handleFilezillaToggle(enabled) {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filezilla_manager_enabled: enabled }),
      });
      if (!res.ok) throw new Error();
      showToast(
        enabled
          ? 'Modo FileZilla salvo. Interface dual-pane em breve na v1.3!'
          : 'Modo FileZilla desativado.',
        'info'
      );
    } catch {
      showToast('Erro ao salvar configuração', 'error');
    }
  }

  // =========================================================================
  // UTILS & HELPERS
  // =========================================================================
  function refreshLucideIcons() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // =========================================================================
  // BINDING DE EVENTOS
  // =========================================================================
  function setupEventListeners() {
    // Tema
    elements.themeToggleBtn.addEventListener('click', toggleTheme);

    // Copiar URL do IP da LAN
    elements.btnCopyUrl.addEventListener('click', async () => {
      const textToCopy = elements.btnCopyUrl.getAttribute('data-copy-val') || window.location.origin;
      try {
        await navigator.clipboard.writeText(textToCopy);
        showToast('URL copiada para a área de transferência!', 'success', 2000);
      } catch {
        // Fallback
        const input = document.createElement('input');
        input.value = textToCopy;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        showToast('URL copiada!', 'success', 2000);
      }
    });

    // Seleção em lote
    if (elements.thSelectAll) {
      elements.thSelectAll.addEventListener('change', toggleSelectAll);
    }
    if (elements.btnToggleSelectAll) {
      elements.btnToggleSelectAll.addEventListener('click', toggleSelectAll);
    }
    if (elements.btnDownloadZip) {
      elements.btnDownloadZip.addEventListener('click', downloadSelectedZip);
    }
    if (elements.btnDownloadIndividual) {
      elements.btnDownloadIndividual.addEventListener('click', downloadSelectedIndividual);
    }
    if (elements.btnClearSelection) {
      elements.btnClearSelection.addEventListener('click', () => {
        state.selectedFiles.clear();
        renderItems();
        updateSelectionUI();
      });
    }

    // Busca
    elements.searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      renderItems();
    });

    // Ordenação clicável dos cabeçalhos
    function handleSort(col) {
      if (state.sortColumn === col) {
        state.sortAsc = !state.sortAsc;
      } else {
        state.sortColumn = col;
        state.sortAsc = true;
      }
      renderItems();
    }

    elements.sortName.addEventListener('click', () => handleSort('name'));
    elements.sortSize.addEventListener('click', () => handleSort('size'));
    elements.sortDate.addEventListener('click', () => handleSort('mtime'));

    // Upload por input file
    elements.fileInput.addEventListener('change', (e) => {
      uploadFiles(e.target.files);
    });

    // Drag and drop
    elements.dropzone.addEventListener('click', () => elements.fileInput.click());

    ['dragenter', 'dragover'].forEach((eventName) => {
      elements.dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        elements.dropzone.classList.add('drag-active');
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      elements.dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        elements.dropzone.classList.remove('drag-active');
      });
    });

    elements.dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files) {
        uploadFiles(e.dataTransfer.files);
      }
    });

    // Modal Ferramentas
    elements.btnOpenTools.addEventListener('click', openTools);
    elements.btnCloseTools.addEventListener('click', closeTools);
    elements.btnSaveTools.addEventListener('click', closeTools);
    elements.toggleFtp.addEventListener('change', (e) => handleFtpToggle(e.target.checked));
    elements.toggleFilezilla.addEventListener('change', (e) => handleFilezillaToggle(e.target.checked));

    // Modal Preview
    elements.btnClosePreview.addEventListener('click', closePreview);

    // Modal Roadmap
    elements.btnOpenRoadmap.addEventListener('click', () => elements.modalRoadmap.classList.remove('hidden'));
    elements.btnCloseRoadmap.addEventListener('click', () => elements.modalRoadmap.classList.add('hidden'));
    elements.btnDismissRoadmap.addEventListener('click', () => elements.modalRoadmap.classList.add('hidden'));

    // Fechar modais ao clicar no backdrop escuro
    [elements.modalTools, elements.modalPreview, elements.modalRoadmap].forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.add('hidden');
        }
      });
    });

    // Tecla ESC fecha modais
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        elements.modalTools.classList.add('hidden');
        elements.modalPreview.classList.add('hidden');
        elements.modalRoadmap.classList.add('hidden');
      }
    });
  }

  // Funções expostas globalmente para os onclicks das linhas
  window.fileserver = {
    openDir: (relPath) => loadDirectory(relPath),
    goParent: () => loadDirectory(state.parentPath || ''),
    previewItem: (relPath, filename, isImage) => openPreview(relPath, filename, isImage),
    toggleSelect: (relPath) => toggleSelect(relPath),
    toggleSelectAll: () => toggleSelectAll(),
  };

  // Inicialização
  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(state.theme);
    setupEventListeners();
    fetchServerInfo();
    loadDirectory('');
  });
})();
