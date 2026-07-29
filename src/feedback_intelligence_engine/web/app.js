const API_BASE = '/api/v1';
const USER_ID = 'demo-user';

const state = {
  view: 'overview',
  health: null,
  projects: [],
  project: null,
  datasets: [],
  dataset: null,
  runs: [],
  run: null,
  summary: null,
  themeCards: [],
  selectedTheme: null,
  reports: [],
  logs: [],
  themeSearch: '',
  themeStatus: 'all',
  themePattern: 'all',
  mergeSelection: new Set(),
  splitSelection: new Set(),
  loading: true,
  busy: null,
  error: null,
};


function loadPreviewData() {
  const previewRows = [
    ['Incorrect information on your report: Loan', 'repeated', 0.62, 30, 28],
    ['Attempts to collect debt not owed', 'repeated', 0.62, 22, 22],
    ['Dealing with your lender or servicer: Payment', 'repeated', 0.59, 18, 18],
    ['Other transaction problem: Money', 'mixed', 0.60, 18, 18],
    ['Getting the loan', 'mixed', 0.60, 16, 16],
    ['Improper use of your report: Reporting', 'repeated', 0.63, 14, 12],
    ['Written notification about debt', 'repeated', 0.62, 13, 13],
    ['Dealing with your lender or servicer: Autopay', 'repeated', 0.59, 11, 11],
    ['Took or threatened legal action', 'repeated', 0.64, 11, 11],
    ['Closing an account: Bank', 'mixed', 0.59, 7, 7],
  ];
  state.health = { status: 'ok', database: 'connected', version: '1.0.0', synthesis_provider: 'heuristic', embedding_provider: 'tfidf', configured_llm_providers: ['github','ollama','heuristic'] };
  state.project = { id: 'preview-project', name: 'CFPB Customer Signals', description: 'Real public complaint narratives' };
  state.projects = [state.project];
  state.dataset = { id: 'preview-dataset', project_id: state.project.id, file_name: 'cfpb_feedback_sample.csv', total_rows: 250, valid_rows: 250, invalid_rows: 0, status: 'ready', validation_errors: Array.from({length:8}, (_,i) => ({severity:'warning', row:i+2})), column_mapping: { feedback_text:'feedback_text', source:'source', user_type:'user_type', product_area:'product_area', date:'date' }, created_at: new Date().toISOString() };
  state.datasets = [state.dataset];
  state.run = { id:'preview-run', status:'ready_for_review', provider:'heuristic', model:null, progress_percent:100, current_step:'complete' };
  state.runs = [state.run];
  state.summary = { run_id:'preview-run', total_feedback:250, assigned_feedback:250, coverage_percentage:100, theme_count:39, status_distribution:{needs_review:39}, pattern_distribution:{repeated:25,mixed:4,isolated:10}, approved_feedback_count:0, rejected_feedback_count:0 };
  const periods = ['2025-10','2025-11','2025-12','2026-01','2026-02','2026-03','2026-04','2026-05','2026-06','2026-07'];
  state.themeCards = previewRows.map((row, index) => ({
    theme: { id:`preview-theme-${index}`, analysis_run_id:'preview-run', title:row[0], summary:`Public complaint narratives describe recurring friction related to ${row[0].toLowerCase()}. This draft remains subject to human review.`, problem_statement:`Consumers cannot reliably resolve ${row[0].toLowerCase()}, creating repeated uncertainty and incomplete outcomes.`, pattern_type:row[1], confidence:row[2], uncertainty_reason:row[1] === 'mixed' ? 'The cluster spans more than one related sub-problem.' : null, status:'needs_review', historical_relationship:index < 3 ? 'recurring' : 'new', historical_theme_id:null, historical_similarity_score:null, merged_into_theme_id:null, approved_by:null, approved_at:null, rejected_at:null, rejection_reason:null, created_at:new Date().toISOString() },
    metrics: { feedback_count:row[3], unique_feedback_count:row[4], duplicate_count:row[3]-row[4], source_distribution:[{value:'Web',count:Math.max(1,Math.round(row[3]*.84)),percentage:84},{value:'Phone',count:Math.max(1,Math.round(row[3]*.1)),percentage:10},{value:'Referral',count:Math.max(1,Math.round(row[3]*.06)),percentage:6}], user_type_distribution:[{value:'Consumer',count:row[3],percentage:100}], product_area_distribution:[{value:row[0].split(':')[0],count:row[3],percentage:100}], frequency_over_time:periods.map((period,i)=>({period,count:Math.max(0,Math.round((row[3]/18)*(1+(i%4))))})), rating_summary:{rated_count:0,unrated_count:row[3],average:null,distribution:{}} }
  }));
  state.logs = [
    {id:'1',event_type:'analysis.started',step:'loading_feedback',request_id:'preview',duration_ms:null,created_at:new Date().toISOString()},
    {id:'2',event_type:'clustering.completed',step:'clustering_feedback',request_id:'preview',duration_ms:824,created_at:new Date().toISOString()},
    {id:'3',event_type:'synthesis.completed',step:'synthesising_themes',request_id:'preview',duration_ms:361,created_at:new Date().toISOString()},
    {id:'4',event_type:'analysis.completed',step:'complete',request_id:'preview',duration_ms:1433,created_at:new Date().toISOString()},
  ];
  state.reports = [];
  state.loading = false;
  state.error = null;
}

const iconPaths = {
  spark: '<path d="M4 15.5 8.2 11l3.4 3.3L20 6"/><path d="M16 6h4v4"/>',
  upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  layers: '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  arrow: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h6"/>',
  report: '<path d="M4 19.5V4.5A2.5 2.5 0 0 1 6.5 2H20v18H6.5A2.5 2.5 0 0 0 4 22.5"/><path d="M8 7h8M8 11h8M8 15h5"/>',
  activity: '<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1v.1h-4v-.1a1.7 1.7 0 0 0-.4-1 1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 3.8 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1-.4h-.1v-4h.1a1.7 1.7 0 0 0 1-.4 1.7 1.7 0 0 0 .6-1 1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 8.2 3.8a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1v-.1h4v.1a1.7 1.7 0 0 0 .4 1 1.7 1.7 0 0 0 1 .6 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 20.2 8.2a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1 .4h.1v4h-.1a1.7 1.7 0 0 0-1 .4 1.7 1.7 0 0 0-.6 1Z"/>',
  bell: '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/>',
  merge: '<path d="M7 3v4a5 5 0 0 0 5 5h5"/><path d="m14 9 3 3-3 3"/><path d="M7 21v-4a5 5 0 0 1 5-5"/>',
  split: '<path d="M17 3v4a5 5 0 0 1-5 5H7"/><path d="m10 9-3 3 3 3"/><path d="M17 21v-4a5 5 0 0 0-5-5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/><path d="M10 11v5M14 11v5"/>',
  refresh: '<path d="M20 7h-5V2"/><path d="M20 7a9 9 0 1 0 1 7"/>',
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
};

function icon(name, size = 18) {
  const body = iconPaths[name] || iconPaths.spark;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'X-User-Id': USER_ID,
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
    },
  });
  const isJson = response.headers.get('content-type')?.includes('application/json');
  const payload = isJson ? await response.json() : null;
  if (!response.ok) {
    const message = payload?.error?.message || payload?.detail || `Request failed (${response.status})`;
    const detail = payload?.error?.details;
    throw new Error(typeof detail === 'string' ? `${message}: ${detail}` : message);
  }
  return payload;
}

const escapeHtml = (value = '') => String(value)
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

const formatDate = (value) => value ? new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value)) : '—';
const formatTime = (value) => value ? new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '—';
const titleCase = (value = '') => value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
const pct = (value) => `${Math.round(Number(value || 0))}%`;

function toast(message, type = 'success') {
  const root = document.getElementById('toast-root');
  root.className = 'toast-stack';
  const node = document.createElement('div');
  node.className = `toast ${type}`;
  node.innerHTML = `${icon(type === 'error' ? 'x' : 'check', 17)}<span>${escapeHtml(message)}</span>`;
  root.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

function showBusy(title, message) {
  state.busy = { title, message };
  renderBusy();
}
function updateBusy(title, message) {
  state.busy = { title, message };
  renderBusy();
}
function hideBusy() {
  state.busy = null;
  renderBusy();
}
function renderBusy() {
  let node = document.getElementById('loading-overlay');
  if (!state.busy) {
    node?.remove();
    return;
  }
  if (!node) {
    node = document.createElement('div');
    node.id = 'loading-overlay';
    node.className = 'loading-overlay';
    document.body.appendChild(node);
  }
  node.innerHTML = `<div class="loading-card"><div class="spinner"></div><h2>${escapeHtml(state.busy.title)}</h2><p class="subtitle">${escapeHtml(state.busy.message)}</p></div>`;
}

function statusBadge(status) {
  return `<span class="status-badge ${status}">${status === 'approved' ? icon('check', 11) : ''}${escapeHtml(titleCase(status))}</span>`;
}

function nav() {
  const items = [
    ['overview', 'Overview'],
    ['themes', 'Themes'],
    ['datasets', 'Datasets'],
    ['reports', 'Reports'],
    ['activity', 'Activity'],
  ];
  return `<header class="topbar">
    <button class="brand" data-action="nav" data-view="overview" aria-label="Signalboard home">
      <span class="brand-mark">${icon('spark', 21)}</span>
      <span>Signalboard</span><span class="brand-beta">beta</span>
    </button>
    <nav class="main-nav" aria-label="Primary navigation">
      ${items.map(([view, label]) => `<button class="nav-button ${state.view === view ? 'active' : ''}" data-action="nav" data-view="${view}">${label}</button>`).join('')}
    </nav>
    <div class="top-actions">
      <div class="connection-pill" title="Backend connection status"><i class="connection-dot ${state.health ? '' : 'offline'}"></i><span>${state.health ? 'Engine online' : 'Engine unavailable'}</span></div>
      <button class="icon-button" data-action="open-settings" aria-label="Provider settings">${icon('settings', 18)}</button>
      <button class="icon-button" data-action="refresh" aria-label="Refresh data">${icon('refresh', 18)}</button>
    </div>
  </header>`;
}

function pageHeader(title, subtitle, actionLabel = 'Import feedback') {
  return `<div class="page-header">
    <div><p class="eyebrow">${state.project ? escapeHtml(state.project.name) : 'Evidence-grounded synthesis'}</p><h1>${title}</h1><p class="subtitle">${subtitle}</p></div>
    <button class="primary-button" data-action="open-import">${icon('upload', 16)}${actionLabel}</button>
  </div>`;
}

function emptyState() {
  return `<section class="empty-state">
    <div>
      <div class="empty-icon">${icon('database', 27)}</div>
      <h2>Start with a feedback dataset</h2>
      <p>Upload a CSV or run the included 250-row CFPB sample. The engine validates rows, groups related feedback, generates grounded themes and keeps every count deterministic.</p>
      <div class="empty-actions">
        <button class="primary-button" data-action="open-import">${icon('upload', 16)}Upload CSV</button>
        <button class="secondary-button" data-action="use-sample">${icon('spark', 16)}Run real sample</button>
        <a class="ghost-button" href="/app/cfpb_feedback_sample.csv" download>${icon('download', 16)}Download sample</a>
      </div>
    </div>
  </section>`;
}

function getStatusCounts() {
  const raw = state.summary?.status_distribution || {};
  return {
    needs_review: raw.needs_review || 0,
    approved: raw.approved || 0,
    rejected: raw.rejected || 0,
    merged: raw.merged || 0,
  };
}

function aggregateSources(cards) {
  const map = new Map();
  cards.filter(c => c.theme.status !== 'merged').forEach(card => {
    card.metrics.source_distribution.forEach(item => map.set(item.value, (map.get(item.value) || 0) + item.count));
  });
  return [...map.entries()].sort((a,b) => b[1]-a[1]).slice(0, 5).map(([value,count]) => ({value,count}));
}

function aggregateTimeline(cards) {
  const map = new Map();
  cards.filter(c => c.theme.status !== 'merged').forEach(card => {
    card.metrics.frequency_over_time.forEach(item => map.set(item.period, (map.get(item.period) || 0) + item.count));
  });
  return [...map.entries()].sort((a,b) => a[0].localeCompare(b[0])).slice(-10).map(([period,count]) => ({period,count}));
}

function sparkline(data) {
  const points = data.length ? data : [{period: '—', count: 0}, {period: '—', count: 0}];
  const width = 520, height = 112, padding = 8;
  const max = Math.max(...points.map(d => d.count), 1);
  const coords = points.map((d, i) => {
    const x = padding + (i * (width - padding * 2) / Math.max(points.length - 1, 1));
    const y = height - padding - (d.count / max) * (height - padding * 2);
    return [x, y];
  });
  const line = coords.map(([x,y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const area = `${line} L${coords.at(-1)[0]},${height} L${coords[0][0]},${height} Z`;
  return `<svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-label="Feedback frequency over time">
    <defs><linearGradient id="sparkGradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#ffd55c" stop-opacity=".48"/><stop offset="100%" stop-color="#ffd55c" stop-opacity="0"/></linearGradient></defs>
    <line class="gridline" x1="0" x2="${width}" y1="28" y2="28"/><line class="gridline" x1="0" x2="${width}" y1="60" y2="60"/><line class="gridline" x1="0" x2="${width}" y1="92" y2="92"/>
    <path class="area" d="${area}"/><path class="line" d="${line}"/>
    ${coords.map(([x,y], i) => i === coords.length - 1 ? `<circle cx="${x}" cy="${y}" r="5"/>` : '').join('')}
  </svg><div class="chart-labels"><span>${escapeHtml(points[0].period)}</span><span>${escapeHtml(points.at(-1).period)}</span></div>`;
}

function overview() {
  if (!state.run || !state.summary) return `${pageHeader('Turn feedback into evidence.', 'Upload structured feedback and produce reviewable, source-backed product themes without handing counts or prioritisation to the model.')}${emptyState()}`;
  const counts = getStatusCounts();
  const totalThemes = state.summary.theme_count || state.themeCards.length;
  const activeTotal = Math.max(counts.needs_review + counts.approved + counts.rejected + counts.merged, 1);
  const sources = aggregateSources(state.themeCards);
  const sourceMax = Math.max(...sources.map(s => s.count), 1);
  const timeline = aggregateTimeline(state.themeCards);
  const patterns = state.summary.pattern_distribution || {};
  const topThemes = [...state.themeCards]
    .filter(card => card.theme.status !== 'merged')
    .sort((a,b) => b.metrics.feedback_count - a.metrics.feedback_count)
    .slice(0, 6);
  const duplicates = state.themeCards.reduce((sum, card) => sum + card.metrics.duplicate_count, 0);
  const queue = state.themeCards.filter(card => card.theme.status === 'needs_review').sort((a,b) => b.metrics.feedback_count - a.metrics.feedback_count).slice(0,5);
  const quality = state.dataset ? Math.round((state.dataset.valid_rows / Math.max(state.dataset.total_rows,1)) * 100) : 0;

  return `${pageHeader('Turn feedback into evidence.', 'Review recurring customer problems, inspect every supporting comment and publish a synthesis only after human approval.')}
    <section class="metrics-strip">
      <div class="progress-overview">
        <div class="progress-labels"><strong>Review progress</strong><span>${counts.approved} approved · ${counts.needs_review} pending</span></div>
        <div class="segmented-bar" aria-label="Theme review status distribution">
          <span class="segment review" style="width:${counts.needs_review/activeTotal*100}%">${counts.needs_review || ''}</span>
          <span class="segment approved" style="width:${counts.approved/activeTotal*100}%">${counts.approved || ''}</span>
          <span class="segment rejected" style="width:${counts.rejected/activeTotal*100}%">${counts.rejected || ''}</span>
          <span class="segment merged" style="width:${counts.merged/activeTotal*100}%">${counts.merged || ''}</span>
        </div>
      </div>
      <div class="metric-block"><span class="metric-number">${state.summary.total_feedback}</span><span class="metric-label">${icon('database',14)}Feedback items</span></div>
      <div class="metric-block"><span class="metric-number">${totalThemes}</span><span class="metric-label">${icon('layers',14)}Candidate themes</span></div>
      <div class="metric-block"><span class="metric-number">${pct(state.summary.coverage_percentage)}</span><span class="metric-label">${icon('shield',14)}Evidence coverage</span></div>
      <div class="metric-block"><span class="metric-number">${duplicates}</span><span class="metric-label">${icon('file',14)}Duplicate links</span></div>
    </section>

    <section class="dashboard-grid">
      <article class="card">
        <div class="card-header"><div><h2>Dataset quality</h2><p class="card-subtitle">Deterministic ingestion checks</p></div><button class="card-link" data-action="nav" data-view="datasets">${icon('arrow',16)}</button></div>
        <div class="quality-layout">
          <div class="donut" style="--value:${quality}"><div class="donut-value"><strong>${quality}%</strong><span>valid rows</span></div></div>
          <div class="stat-list">
            <div class="stat-row"><span>Imported</span><strong>${state.dataset.total_rows}</strong></div>
            <div class="stat-row"><span>Accepted</span><strong>${state.dataset.valid_rows}</strong></div>
            <div class="stat-row"><span>Rejected</span><strong>${state.dataset.invalid_rows}</strong></div>
            <div class="stat-row"><span>Warnings</span><strong>${state.dataset.validation_errors?.filter(i => i.severity === 'warning').length || 0}</strong></div>
          </div>
        </div>
      </article>

      <article class="card">
        <div class="card-header"><div><h2>Pattern mix</h2><p class="card-subtitle">Repeated signals vs isolated comments</p></div><span class="tag">${escapeHtml(state.run.provider)}</span></div>
        <div class="bar-list">
          ${[['repeated','Repeated', ''], ['mixed','Mixed','yellow'], ['isolated','Isolated','grey'], ['uncertain','Uncertain','grey']].map(([key,label,color]) => {
            const value = patterns[key] || 0; const max = Math.max(...Object.values(patterns),1);
            return `<div class="bar-item"><span>${label}</span><div class="bar-track"><div class="bar-fill ${color}" style="width:${value/max*100}%"></div></div><strong>${value}</strong></div>`;
          }).join('')}
        </div>
      </article>

      <article class="card dark tall">
        <div class="card-header"><div><h2>Review queue</h2><p class="card-subtitle">Highest-evidence themes awaiting a decision</p></div><button class="card-link" data-action="nav" data-view="themes">${icon('arrow',16)}</button></div>
        <div class="review-score"><div><strong>${counts.needs_review}</strong><span>themes require review</span></div><span>${state.summary.approved_feedback_count} items approved</span></div>
        <div class="queue-list">
          ${queue.length ? queue.map((card,index) => `<button class="queue-item" data-action="open-theme" data-theme-id="${card.theme.id}">
            <span class="queue-icon">${icon(index % 2 ? 'file' : 'layers',15)}</span>
            <span class="queue-copy"><strong>${escapeHtml(card.theme.title)}</strong><span>${card.metrics.feedback_count} feedback · ${Math.round(card.theme.confidence*100)}% confidence</span></span>
            <i class="queue-status ${index < 2 ? 'high' : ''}"></i>
          </button>`).join('') : '<p class="card-subtitle">All themes have been reviewed.</p>'}
        </div>
      </article>

      <article class="card wide">
        <div class="card-header"><div><h2>Feedback frequency</h2><p class="card-subtitle">Deterministic count of assigned feedback over time</p></div><span class="tag">${timeline.length} periods</span></div>
        ${sparkline(timeline)}
      </article>

      <article class="card">
        <div class="card-header"><div><h2>Source mix</h2><p class="card-subtitle">Where the strongest signals originate</p></div></div>
        <div class="bar-list">
          ${sources.length ? sources.map((source,index) => `<div class="bar-item"><span title="${escapeHtml(source.value)}">${escapeHtml(source.value.slice(0,18))}</span><div class="bar-track"><div class="bar-fill ${index===0?'yellow':''}" style="width:${source.count/sourceMax*100}%"></div></div><strong>${source.count}</strong></div>`).join('') : '<p class="card-subtitle">No source distribution available.</p>'}
        </div>
      </article>

      <article class="card wide">
        <div class="card-header"><div><h2>Leading themes</h2><p class="card-subtitle">Counts are calculated from validated theme memberships</p></div><button class="card-link" data-action="nav" data-view="themes">${icon('arrow',16)}</button></div>
        <div style="overflow:auto"><table class="theme-table"><thead><tr><th>Theme</th><th>Pattern</th><th>Feedback</th><th>Confidence</th><th>Status</th></tr></thead><tbody>
          ${topThemes.map(card => `<tr data-action="open-theme" data-theme-id="${card.theme.id}" style="cursor:pointer"><td><span class="theme-name"><i class="theme-dot ${card.theme.pattern_type}"></i>${escapeHtml(card.theme.title)}</span></td><td>${titleCase(card.theme.pattern_type)}</td><td>${card.metrics.feedback_count}</td><td>${Math.round(card.theme.confidence*100)}%</td><td>${statusBadge(card.theme.status)}</td></tr>`).join('')}
        </tbody></table></div>
      </article>
    </section>`;
}

function filteredCards() {
  const query = state.themeSearch.trim().toLowerCase();
  return state.themeCards.filter(card => {
    if (card.theme.status === 'merged') return false;
    if (state.themeStatus !== 'all' && card.theme.status !== state.themeStatus) return false;
    if (state.themePattern !== 'all' && card.theme.pattern_type !== state.themePattern) return false;
    return !query || `${card.theme.title} ${card.theme.summary}`.toLowerCase().includes(query);
  });
}

function themesView() {
  if (!state.run) return `${pageHeader('Review grounded themes.', 'Every theme must remain traceable to its original feedback before it can enter a saved synthesis report.')}${emptyState()}`;
  const cards = filteredCards();
  const selected = state.selectedTheme;
  return `${pageHeader('Review grounded themes.', 'Rename, merge, split, reject or approve AI-assisted themes while preserving their complete evidence trail.')}
    <div class="toolbar">
      <div class="search-wrap">${icon('search',17)}<input class="search-input" id="theme-search" value="${escapeHtml(state.themeSearch)}" placeholder="Search themes or summaries" /></div>
      <div class="filter-row">
        <select class="select-input" id="theme-status"><option value="all">All statuses</option>${['needs_review','approved','rejected'].map(v => `<option value="${v}" ${state.themeStatus===v?'selected':''}>${titleCase(v)}</option>`).join('')}</select>
        <select class="select-input" id="theme-pattern"><option value="all">All patterns</option>${['repeated','mixed','isolated','uncertain'].map(v => `<option value="${v}" ${state.themePattern===v?'selected':''}>${titleCase(v)}</option>`).join('')}</select>
        <button class="ghost-button" data-action="start-merge" ${state.mergeSelection.size < 2 ? 'disabled' : ''}>${icon('merge',15)}Merge ${state.mergeSelection.size || ''}</button>
      </div>
    </div>
    <section class="theme-workspace">
      <aside class="theme-list-panel">
        <div class="panel-header"><h2>${cards.length} themes</h2><p class="card-subtitle">Select two checkboxes to merge</p></div>
        <div class="panel-scroll">
          ${cards.map(card => `<div style="display:grid;grid-template-columns:24px 1fr;align-items:start">
            <label style="padding:15px 0 0 8px"><input type="checkbox" class="merge-check" data-theme-id="${card.theme.id}" ${state.mergeSelection.has(card.theme.id)?'checked':''} /></label>
            <button class="theme-list-item ${selected?.theme.id === card.theme.id ? 'active' : ''}" data-action="select-theme" data-theme-id="${card.theme.id}">
              <span class="theme-list-title">${escapeHtml(card.theme.title)}</span>
              <span class="meta"><span>${card.metrics.feedback_count} feedback</span><span>·</span><span>${Math.round(card.theme.confidence*100)}%</span><span>·</span><span>${titleCase(card.theme.pattern_type)}</span></span>
            </button>
          </div>`).join('') || '<div class="empty-state" style="min-height:260px"><p>No themes match these filters.</p></div>'}
        </div>
      </aside>
      <main class="theme-detail-panel">
        ${selected ? themeDetailMarkup(selected) : '<div class="empty-state"><div><div class="empty-icon">'+icon('layers',26)+'</div><h2>Select a theme</h2><p>Open a theme to inspect its problem statement, deterministic metrics and original evidence.</p></div></div>'}
      </main>
      <aside class="evidence-panel">
        <div class="panel-header"><h2>Source evidence</h2><p class="card-subtitle">Original comments behind this theme</p></div>
        <div class="panel-scroll">
          ${selected ? selected.evidence.map(item => evidenceMarkup(item)).join('') : '<p class="card-subtitle" style="padding:15px">Select a theme to review evidence.</p>'}
        </div>
      </aside>
    </section>`;
}

function themeDetailMarkup(detail) {
  const t = detail.theme, m = detail.metrics;
  const historical = detail.historical_theme;
  return `<div class="detail-content">
    <div class="detail-title-row"><div><div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:9px">${statusBadge(t.status)}<span class="tag">${titleCase(t.pattern_type)}</span><span class="tag">${titleCase(t.historical_relationship)}</span></div><h2>${escapeHtml(t.title)}</h2></div>
      <button class="icon-button" data-action="rename-theme" title="Rename theme">${icon('edit',16)}</button></div>
    <div class="confidence-row"><div class="confidence-track"><div class="confidence-fill" style="width:${t.confidence*100}%"></div></div><strong>${Math.round(t.confidence*100)}% confidence</strong></div>
    <div class="copy-block"><label>AI-assisted summary</label><p>${escapeHtml(t.summary)}</p></div>
    <div class="copy-block"><label>Proposed problem statement</label><p>${escapeHtml(t.problem_statement)}</p></div>
    ${t.uncertainty_reason ? `<div class="copy-block"><label>Uncertainty</label><p>${escapeHtml(t.uncertainty_reason)}</p></div>` : ''}
    <div class="mini-metrics"><div class="mini-metric"><strong>${m.feedback_count}</strong><span>Feedback items</span></div><div class="mini-metric"><strong>${m.unique_feedback_count}</strong><span>Unique comments</span></div><div class="mini-metric"><strong>${m.source_distribution.length}</strong><span>Sources represented</span></div></div>
    ${historical ? `<div class="copy-block"><label>Historical comparison</label><p><strong>${escapeHtml(historical.title)}</strong><br>${escapeHtml(historical.description)}</p></div>` : `<div class="copy-block"><label>Historical comparison</label><p>No sufficiently similar historical theme was found.</p></div>`}
    <div class="detail-actions">
      <button class="secondary-button" data-action="approve-theme" ${t.status === 'approved' ? 'disabled' : ''}>${icon('check',15)}Approve</button>
      <button class="danger-button" data-action="reject-theme" ${t.status === 'rejected' ? 'disabled' : ''}>${icon('x',15)}Reject</button>
      <button class="ghost-button" data-action="edit-theme">${icon('edit',15)}Edit copy</button>
      <button class="ghost-button" data-action="start-split" ${state.splitSelection.size === 0 ? 'disabled' : ''}>${icon('split',15)}Split ${state.splitSelection.size || ''}</button>
    </div>
  </div>`;
}

function evidenceMarkup(item) {
  return `<label class="evidence-card ${item.is_primary_evidence ? 'primary' : ''}"><span class="evidence-check"><input type="checkbox" class="split-check" data-feedback-id="${item.id}" ${state.splitSelection.has(item.id)?'checked':''} /><span><p>${escapeHtml(item.feedback_text_original)}</p><span class="evidence-meta"><span>${escapeHtml(item.source)}</span><span>·</span><span>${escapeHtml(item.user_type)}</span><span>·</span><span>${formatDate(item.feedback_date)}</span>${item.is_primary_evidence?'<span>· Primary citation</span>':''}</span></span></span></label>`;
}

function datasetsView() {
  return `${pageHeader('Datasets and validation.', 'Inspect every upload, accepted row and validation issue before the data enters the synthesis workflow.')}
    ${state.datasets.length ? `<section class="dataset-grid">${state.datasets.map(ds => `<article class="card dataset-card">
      <div><div class="dataset-status"><span class="status-badge ${ds.status === 'ready' ? 'approved' : 'rejected'}">${titleCase(ds.status)}</span><span class="card-subtitle">${formatDate(ds.created_at)}</span></div><h2 style="margin-top:18px">${escapeHtml(ds.file_name)}</h2><p class="card-subtitle">${escapeHtml(Object.entries(ds.column_mapping || {}).map(([k,v]) => `${k}→${v}`).slice(0,3).join(' · '))}</p></div>
      <div class="validation-counts"><div class="validation-count"><strong>${ds.total_rows}</strong><span>Total</span></div><div class="validation-count"><strong>${ds.valid_rows}</strong><span>Valid</span></div><div class="validation-count"><strong>${ds.invalid_rows}</strong><span>Invalid</span></div></div>
      <button class="ghost-button" data-action="select-dataset" data-dataset-id="${ds.id}">${icon('arrow',15)}Open dataset</button>
    </article>`).join('')}</section>` : emptyState()}`;
}

function reportsView() {
  const approved = state.themeCards.filter(c => c.theme.status === 'approved').length;
  return `${pageHeader('Reviewed synthesis reports.', 'Reports are immutable snapshots: later edits never rewrite what a reviewer previously approved.', 'Create report')}
    <div class="toolbar"><p class="subtitle">${approved} approved themes are currently eligible for the next report.</p><button class="secondary-button" data-action="save-report" ${!state.run || approved === 0 ? 'disabled' : ''}>${icon('report',15)}Save reviewed report</button></div>
    ${state.reports.length ? `<section class="report-grid">${state.reports.map(report => `<article class="card report-card"><div><span class="status-badge approved">Saved snapshot</span><h2 style="margin-top:18px">${escapeHtml(report.title)}</h2><p class="card-subtitle">Version ${report.version} · ${formatDate(report.created_at)} at ${formatTime(report.created_at)}</p></div><div><p class="card-subtitle">Created by ${escapeHtml(report.created_by)}</p><button class="ghost-button" data-action="open-report" data-report-id="${report.id}">${icon('external',15)}Inspect snapshot</button></div></article>`).join('')}</section>` : `<section class="empty-state"><div><div class="empty-icon">${icon('report',26)}</div><h2>No reports saved yet</h2><p>Approve selected themes, then create an immutable report containing metrics and cited source feedback.</p></div></section>`}`;
}

function activityView() {
  return `${pageHeader('Workflow activity.', 'Trace ingestion, clustering, synthesis, validation and reviewer decisions through structured events and request IDs.')}
    ${state.logs.length ? `<section class="card"><div class="card-header"><div><h2>${state.logs.length} workflow events</h2><p class="card-subtitle">Run ${escapeHtml(state.run?.id?.slice(0,8) || '—')}</p></div></div><div class="log-list">${state.logs.map(log => `<div class="log-row"><span class="log-time">${formatDate(log.created_at)} ${formatTime(log.created_at)}</span><span><span class="log-event">${escapeHtml(log.event_type)}</span><br><span class="card-subtitle">${escapeHtml(log.step || 'system')} · ${escapeHtml(log.request_id || 'no request id')}</span></span><span class="log-duration">${log.duration_ms == null ? '—' : `${log.duration_ms} ms`}</span></div>`).join('')}</div></section>` : `<section class="empty-state"><div><div class="empty-icon">${icon('activity',26)}</div><h2>No workflow events yet</h2><p>Events appear after an analysis run starts.</p></div></section>`}`;
}

function content() {
  if (state.loading) return `<div class="page-header"><div><div class="skeleton" style="width:180px;height:13px;margin-bottom:12px"></div><div class="skeleton" style="width:min(520px,80vw);height:58px;margin-bottom:12px"></div><div class="skeleton" style="width:min(650px,80vw);height:20px"></div></div></div><div class="dashboard-grid"><div class="card skeleton" style="height:260px"></div><div class="card skeleton" style="height:260px"></div><div class="card skeleton" style="height:540px"></div></div>`;
  if (state.error && !state.health) return `<section class="empty-state"><div><div class="empty-icon">${icon('x',26)}</div><h2>Engine could not be reached</h2><p>${escapeHtml(state.error)}</p><div class="empty-actions"><button class="primary-button" data-action="refresh">Retry connection</button></div></div></section>`;
  if (state.view === 'themes') return themesView();
  if (state.view === 'datasets') return datasetsView();
  if (state.view === 'reports') return reportsView();
  if (state.view === 'activity') return activityView();
  return overview();
}

function render() {
  document.getElementById('app').innerHTML = `<main class="app-frame">${nav()}${content()}<footer class="footer-note"><span>AI proposes interpretations. Deterministic code owns counts and distributions.</span><span>${state.health ? `Engine ${escapeHtml(state.health.version)} · ${escapeHtml(state.health.embedding_provider)} embeddings` : 'Connection unavailable'}</span></footer></main>`;
  bindInputs();
}

async function loadWorkspace(preferredProjectId = null) {
  state.loading = true; state.error = null; render();
  try {
    state.health = await api('/health');
    state.projects = await api('/projects');
    state.project = state.projects.find(p => p.id === preferredProjectId) || state.projects[0] || null;
    state.datasets = state.project ? await api(`/projects/${state.project.id}/datasets`) : [];
    state.dataset = state.datasets[0] || null;
    state.runs = state.dataset ? await api(`/datasets/${state.dataset.id}/analysis-runs`) : [];
    state.run = state.runs.find(r => r.status === 'ready_for_review') || state.runs[0] || null;
    if (state.run) {
      const [summary, cards, logs] = await Promise.all([
        api(`/analysis-runs/${state.run.id}/summary`),
        api(`/analysis-runs/${state.run.id}/theme-cards`),
        api(`/analysis-runs/${state.run.id}/logs`),
      ]);
      state.summary = summary;
      state.themeCards = cards;
      state.logs = logs;
      if (cards.length) await selectTheme(cards[0].theme.id, false);
    } else {
      state.summary = null; state.themeCards = []; state.logs = []; state.selectedTheme = null;
    }
    state.reports = state.project ? await api(`/projects/${state.project.id}/reports`) : [];
  } catch (error) {
    state.error = error.message;
    state.health = null;
  } finally {
    state.loading = false;
    render();
  }
}

async function selectTheme(themeId, shouldRender = true) {
  try {
    state.selectedTheme = await api(`/themes/${themeId}`);
    state.splitSelection.clear();
    if (shouldRender) render();
  } catch (error) { toast(error.message, 'error'); }
}

function bindInputs() {
  const search = document.getElementById('theme-search');
  search?.addEventListener('input', (event) => { state.themeSearch = event.target.value; render(); const next = document.getElementById('theme-search'); next?.focus(); next?.setSelectionRange(state.themeSearch.length, state.themeSearch.length); });
  document.getElementById('theme-status')?.addEventListener('change', (event) => { state.themeStatus = event.target.value; render(); });
  document.getElementById('theme-pattern')?.addEventListener('change', (event) => { state.themePattern = event.target.value; render(); });
  document.querySelectorAll('.merge-check').forEach(input => input.addEventListener('change', event => {
    const id = event.target.dataset.themeId;
    event.target.checked ? state.mergeSelection.add(id) : state.mergeSelection.delete(id);
    render();
  }));
  document.querySelectorAll('.split-check').forEach(input => input.addEventListener('change', event => {
    const id = event.target.dataset.feedbackId;
    event.target.checked ? state.splitSelection.add(id) : state.splitSelection.delete(id);
    render();
  }));
}

function modal({ title, subtitle = '', body, footer = '', large = false, onMount }) {
  const root = document.getElementById('modal-root');
  root.innerHTML = `<div class="modal-backdrop" data-action="close-modal"><section class="modal ${large ? 'large' : ''}" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}" onclick="event.stopPropagation()"><header class="modal-header"><div><h2>${escapeHtml(title)}</h2>${subtitle ? `<p class="subtitle">${escapeHtml(subtitle)}</p>` : ''}</div><button class="modal-close" data-action="close-modal">${icon('x',17)}</button></header>${body}${footer}</section></div>`;
  onMount?.(root);
}
function closeModal() { document.getElementById('modal-root').innerHTML = ''; }

function importModal() {
  modal({
    title: 'Import product feedback',
    subtitle: 'Required fields: feedback text, source, user type, product area and date. Rating is optional.',
    body: `<form id="import-form" class="form-grid">
      <div class="form-field"><label>Project name</label><input id="project-name" class="text-input" value="${escapeHtml(state.project?.name || 'Customer feedback review')}" required minlength="2" /></div>
      <label class="dropzone" id="dropzone"><input id="csv-file" type="file" accept=".csv,text/csv" /><span><span class="dropzone-icon">${icon('upload',22)}</span><strong id="file-label">Choose a CSV file</strong><span class="form-hint" style="display:block">or drag and drop it here</span></span></label>
      <div id="import-error"></div>
      <div class="form-hint">No public or shared API keys are used. Provider credentials stay only in the backend environment.</div>
    </form>`,
    footer: `<footer class="modal-footer"><button class="ghost-button" data-action="use-sample">Use included real sample</button><button class="primary-button" id="submit-import" type="submit" form="import-form">${icon('spark',15)}Validate and analyse</button></footer>`,
    onMount: () => {
      const input = document.getElementById('csv-file');
      const drop = document.getElementById('dropzone');
      input.addEventListener('change', () => { document.getElementById('file-label').textContent = input.files[0]?.name || 'Choose a CSV file'; });
      ['dragenter','dragover'].forEach(type => drop.addEventListener(type, e => { e.preventDefault(); drop.classList.add('dragging'); }));
      ['dragleave','drop'].forEach(type => drop.addEventListener(type, e => { e.preventDefault(); drop.classList.remove('dragging'); }));
      drop.addEventListener('drop', e => { if (e.dataTransfer.files[0]) { input.files = e.dataTransfer.files; document.getElementById('file-label').textContent = input.files[0].name; } });
      document.getElementById('import-form').addEventListener('submit', async event => {
        event.preventDefault();
        const file = input.files[0];
        if (!file) { document.getElementById('import-error').innerHTML = '<div class="form-error">Select a CSV file before continuing.</div>'; return; }
        await runImport(file, document.getElementById('project-name').value.trim());
      });
    },
  });
}

async function runImport(file, projectName) {
  closeModal();
  showBusy('Creating analysis workspace', 'Preparing the project and validating the uploaded schema.');
  try {
    let project = state.project;
    if (!project || project.name !== projectName) project = await api('/projects', { method: 'POST', body: JSON.stringify({ name: projectName, description: 'Evidence-grounded product feedback synthesis.' }) });
    updateBusy('Validating every row', 'Normalising fields, masking sensitive values and identifying duplicate comments.');
    const form = new FormData(); form.append('file', file);
    const dataset = await api(`/projects/${project.id}/datasets`, { method: 'POST', body: form });
    updateBusy('Discovering recurring problems', `Analysing ${dataset.valid_rows} validated feedback items and grounding each theme in source IDs.`);
    await api(`/datasets/${dataset.id}/analysis-runs`, { method: 'POST', body: JSON.stringify({}) });
    updateBusy('Preparing the review workspace', 'Calculating deterministic distributions and loading source evidence.');
    await loadWorkspace(project.id);
    state.view = 'overview';
    toast('Analysis is ready for human review.');
  } catch (error) {
    toast(error.message, 'error');
  } finally { hideBusy(); render(); }
}

async function useSample() {
  closeModal();
  try {
    showBusy('Loading the real-world sample', 'Fetching 250 public CFPB complaint narratives included with the project.');
    const response = await fetch('/app/cfpb_feedback_sample.csv');
    if (!response.ok) throw new Error('The included sample file could not be loaded.');
    const blob = await response.blob();
    const file = new File([blob], `cfpb-feedback-${Date.now()}.csv`, { type: 'text/csv' });
    await runImport(file, `CFPB feedback review ${new Date().toISOString().replace('T', ' ').slice(0, 19)}`);
  } catch (error) { hideBusy(); toast(error.message, 'error'); }
}

function settingsModal() {
  const providers = state.health?.configured_llm_providers || [];
  modal({ title: 'AI provider configuration', subtitle: 'The engine supports legitimate free or local options without exposing secrets to the browser.', body: `<div class="form-grid">
    <div class="copy-block"><label>Configured providers</label><p>${providers.map(titleCase).join(', ') || 'Deterministic fallback only'}</p></div>
    <div class="copy-block"><label>Recommended free hosted path</label><p><strong>GitHub Models</strong> with a fine-grained personal access token limited to <code>models:read</code>. Keep the token in the backend environment; never commit it.</p></div>
    <div class="copy-block"><label>Fully local path</label><p><strong>Ollama</strong> can run synthesis and embeddings on your machine with no external key. TF-IDF remains the zero-cost deterministic embedding fallback.</p></div>
    <div class="copy-block"><label>Current engine</label><p>Synthesis: ${escapeHtml(state.health?.synthesis_provider || 'unknown')}<br>Embeddings: ${escapeHtml(state.health?.embedding_provider || 'unknown')}</p></div>
  </div>`, footer: `<footer class="modal-footer"><button class="primary-button" data-action="close-modal">Done</button></footer>` });
}

function renameModal() {
  const theme = state.selectedTheme?.theme; if (!theme) return;
  modal({ title: 'Rename theme', subtitle: 'The original AI title remains in the audit history.', body: `<form id="rename-form"><div class="form-field"><label>Theme title</label><input id="rename-value" class="text-input" value="${escapeHtml(theme.title)}" minlength="2" maxlength="240" required /></div></form>`, footer: `<footer class="modal-footer"><button class="ghost-button" data-action="close-modal">Cancel</button><button class="primary-button" form="rename-form">Save title</button></footer>`, onMount: () => document.getElementById('rename-form').addEventListener('submit', async e => { e.preventDefault(); await mutateTheme(`/themes/${theme.id}/rename`, 'PATCH', { title: document.getElementById('rename-value').value.trim() }, 'Theme renamed.'); closeModal(); }) });
}

function editModal() {
  const theme = state.selectedTheme?.theme; if (!theme) return;
  modal({ title: 'Edit reviewed copy', subtitle: 'Memberships and deterministic metrics will not change.', body: `<form id="edit-form" class="form-grid"><div class="form-field"><label>Summary</label><textarea id="edit-summary" class="textarea-input" required>${escapeHtml(theme.summary)}</textarea></div><div class="form-field"><label>Problem statement</label><textarea id="edit-problem" class="textarea-input" required>${escapeHtml(theme.problem_statement)}</textarea></div></form>`, footer: `<footer class="modal-footer"><button class="ghost-button" data-action="close-modal">Cancel</button><button class="primary-button" form="edit-form">Save changes</button></footer>`, onMount: () => document.getElementById('edit-form').addEventListener('submit', async e => { e.preventDefault(); await mutateTheme(`/themes/${theme.id}`, 'PATCH', { summary: document.getElementById('edit-summary').value.trim(), problem_statement: document.getElementById('edit-problem').value.trim() }, 'Theme copy updated.'); closeModal(); }) });
}

function rejectModal() {
  const theme = state.selectedTheme?.theme; if (!theme) return;
  modal({ title: 'Reject theme', subtitle: 'Rejected themes stay in the audit trail but are excluded from reports.', body: `<form id="reject-form"><div class="form-field"><label>Reason</label><select id="reject-reason" class="select-input" style="width:100%"><option>Incorrect grouping</option><option>Insufficient evidence</option><option>Duplicate theme</option><option>Irrelevant feedback</option><option>Not a user problem</option></select></div></form>`, footer: `<footer class="modal-footer"><button class="ghost-button" data-action="close-modal">Cancel</button><button class="danger-button" form="reject-form">Reject theme</button></footer>`, onMount: () => document.getElementById('reject-form').addEventListener('submit', async e => { e.preventDefault(); await mutateTheme(`/themes/${theme.id}/reject`, 'POST', { reason: document.getElementById('reject-reason').value }, 'Theme rejected.'); closeModal(); }) });
}

function mergeModal() {
  const selected = state.themeCards.filter(card => state.mergeSelection.has(card.theme.id));
  if (selected.length < 2) return;
  modal({ title: `Merge ${selected.length} themes`, subtitle: 'All feedback memberships are combined transactionally; duplicate links are removed.', body: `<form id="merge-form" class="form-grid"><div class="copy-block"><label>Selected themes</label><p>${selected.map(c => escapeHtml(c.theme.title)).join('<br>')}</p></div><div class="form-field"><label>New title</label><input id="merge-title" class="text-input" value="${escapeHtml(selected[0].theme.title)}" required /></div><div class="form-field"><label>Summary</label><textarea id="merge-summary" class="textarea-input" required>${escapeHtml(selected.map(c=>c.theme.summary).join(' '))}</textarea></div><div class="form-field"><label>Problem statement</label><textarea id="merge-problem" class="textarea-input" required>${escapeHtml(selected[0].theme.problem_statement)}</textarea></div></form>`, footer: `<footer class="modal-footer"><button class="ghost-button" data-action="close-modal">Cancel</button><button class="primary-button" form="merge-form">${icon('merge',15)}Merge themes</button></footer>`, onMount: () => document.getElementById('merge-form').addEventListener('submit', async e => { e.preventDefault(); showBusy('Merging themes', 'Combining memberships and recalculating deterministic metrics.'); try { const merged = await api('/themes/merge', { method:'POST', body:JSON.stringify({ theme_ids:[...state.mergeSelection], title:document.getElementById('merge-title').value.trim(), summary:document.getElementById('merge-summary').value.trim(), problem_statement:document.getElementById('merge-problem').value.trim() }) }); state.mergeSelection.clear(); closeModal(); await refreshRunData(); await selectTheme(merged.id); toast('Themes merged successfully.'); } catch(error){ toast(error.message,'error'); } finally { hideBusy(); } }) });
}

function splitModal() {
  const theme = state.selectedTheme?.theme; if (!theme || !state.splitSelection.size) return;
  modal({ title: `Split ${state.splitSelection.size} feedback items`, subtitle: 'Selected evidence moves into a new theme; no feedback is deleted.', body: `<form id="split-form" class="form-grid"><div class="form-field"><label>New theme title</label><input id="split-title" class="text-input" required placeholder="Describe the distinct problem" /></div><div class="form-field"><label>Summary</label><textarea id="split-summary" class="textarea-input" required placeholder="Summarise the selected feedback only"></textarea></div><div class="form-field"><label>Problem statement</label><textarea id="split-problem" class="textarea-input" required placeholder="Users cannot..."></textarea></div></form>`, footer: `<footer class="modal-footer"><button class="ghost-button" data-action="close-modal">Cancel</button><button class="primary-button" form="split-form">${icon('split',15)}Create split theme</button></footer>`, onMount: () => document.getElementById('split-form').addEventListener('submit', async e => { e.preventDefault(); showBusy('Splitting theme', 'Moving selected evidence and preserving both audit histories.'); try { const created = await api(`/themes/${theme.id}/split`, { method:'POST', body:JSON.stringify({ feedback_item_ids:[...state.splitSelection], new_title:document.getElementById('split-title').value.trim(), new_summary:document.getElementById('split-summary').value.trim(), new_problem_statement:document.getElementById('split-problem').value.trim() }) }); state.splitSelection.clear(); closeModal(); await refreshRunData(); await selectTheme(created.id); toast('Theme split created.'); } catch(error){ toast(error.message,'error'); } finally { hideBusy(); } }) });
}

async function mutateTheme(path, method, body, success) {
  if (!state.selectedTheme) return;
  showBusy('Updating theme', 'Saving the reviewer decision and refreshing deterministic metrics.');
  try {
    const updated = await api(path, { method, body: JSON.stringify(body || {}) });
    await refreshRunData(); await selectTheme(updated.id); toast(success);
  } catch (error) { toast(error.message, 'error'); }
  finally { hideBusy(); }
}

async function refreshRunData() {
  if (!state.run) return;
  const [summary, cards, logs] = await Promise.all([api(`/analysis-runs/${state.run.id}/summary`), api(`/analysis-runs/${state.run.id}/theme-cards`), api(`/analysis-runs/${state.run.id}/logs`)]);
  state.summary = summary; state.themeCards = cards; state.logs = logs;
}

function saveReportModal() {
  if (!state.run) return;
  modal({ title: 'Save reviewed synthesis', subtitle: 'This creates an immutable snapshot of approved themes, metrics and evidence.', body: `<form id="report-form"><div class="form-field"><label>Report title</label><input id="report-title" class="text-input" value="Reviewed feedback synthesis — ${new Date().toLocaleDateString('en-GB')}" required /></div></form>`, footer: `<footer class="modal-footer"><button class="ghost-button" data-action="close-modal">Cancel</button><button class="primary-button" form="report-form">Save snapshot</button></footer>`, onMount: () => document.getElementById('report-form').addEventListener('submit', async e => { e.preventDefault(); showBusy('Saving report', 'Freezing approved themes and all supporting evidence into a versioned snapshot.'); try { await api(`/analysis-runs/${state.run.id}/reports`, { method:'POST', body:JSON.stringify({title:document.getElementById('report-title').value.trim()}) }); closeModal(); state.reports = await api(`/projects/${state.project.id}/reports`); render(); toast('Reviewed report saved.'); } catch(error){ toast(error.message,'error'); } finally { hideBusy(); } }) });
}

async function openReport(id) {
  try {
    const detail = await api(`/reports/${id}`);
    modal({ title: detail.report.title, subtitle: `Version ${detail.report.version} · ${detail.themes.length} approved themes`, large: true, body: `<div class="form-grid">${detail.themes.map(theme => `<div class="copy-block"><label>${escapeHtml(theme.pattern_type)} · ${theme.metrics_json.feedback_count || 0} feedback</label><h3>${escapeHtml(theme.theme_title)}</h3><p>${escapeHtml(theme.problem_statement)}</p></div>`).join('')}</div>`, footer: `<footer class="modal-footer"><button class="primary-button" data-action="close-modal">Close</button></footer>` });
  } catch(error) { toast(error.message,'error'); }
}

document.addEventListener('click', async event => {
  const target = event.target.closest('[data-action]');
  if (!target) return;
  const action = target.dataset.action;
  if (action === 'nav') { state.view = target.dataset.view; if (state.view === 'themes' && !state.selectedTheme && state.themeCards[0]) await selectTheme(state.themeCards[0].theme.id, false); render(); }
  else if (action === 'refresh') await loadWorkspace(state.project?.id);
  else if (action === 'open-import') importModal();
  else if (action === 'use-sample') await useSample();
  else if (action === 'open-settings') settingsModal();
  else if (action === 'close-modal') closeModal();
  else if (action === 'open-theme' || action === 'select-theme') { state.view = 'themes'; await selectTheme(target.dataset.themeId); }
  else if (action === 'approve-theme') await mutateTheme(`/themes/${state.selectedTheme.theme.id}/approve`, 'POST', {}, 'Theme approved.');
  else if (action === 'reject-theme') rejectModal();
  else if (action === 'rename-theme') renameModal();
  else if (action === 'edit-theme') editModal();
  else if (action === 'start-merge') mergeModal();
  else if (action === 'start-split') splitModal();
  else if (action === 'save-report') saveReportModal();
  else if (action === 'open-report') await openReport(target.dataset.reportId);
  else if (action === 'select-dataset') { state.dataset = state.datasets.find(d => d.id === target.dataset.datasetId); state.view = 'overview'; await loadWorkspace(state.project.id); }
});

if (location.protocol === 'file:' || new URLSearchParams(location.search).get('preview') === '1') { loadPreviewData(); render(); } else { loadWorkspace(); }
