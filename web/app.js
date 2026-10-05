// ==========================================================================
// KAIROS CLIENT APPLICATION SCRIPT
// ==========================================================================

const API_BASE = window.location.origin;

// Application State
let activeTab = 'tab-overview';
let liveStatus = null;
let todayStats = null;
let allRules = [];
let allCategories = [];
let weeklyTrends = [];
let recentInterventions = [];
let timerInterval = null;
let currentDeviceFilter = 'all';

// DOM Elements
const dom = {
  headerApp: document.getElementById('header-active-app'),
  headerTitle: document.getElementById('header-active-title'),
  topbarTimer: document.getElementById('topbar-timer-text'),
  mobileTimerDigits: document.getElementById('mobile-timer-digits'),
  sidebar: document.getElementById('app-sidebar'),
  sidebarBackdrop: document.getElementById('sidebar-backdrop'),
  btnMobileMenu: document.getElementById('btn-mobile-menu'),
  btnRefresh: document.getElementById('btn-refresh-data'),
  toastContainer: document.getElementById('toast-container'),
  selectDeviceFilter: document.getElementById('select-device-filter'),
  displayLanUrl: document.getElementById('display-lan-url'),
  btnCopyLanUrl: document.getElementById('btn-copy-lan-url'),
  devicesListContainer: document.getElementById('devices-list-container'),
  btnOpenSyncModal: document.getElementById('btn-open-sync-modal'),
  syncModal: document.getElementById('sync-modal'),
  btnCloseSyncModal: document.getElementById('btn-close-sync-modal'),
  btnCancelSync: document.getElementById('btn-cancel-sync'),
  btnStartSync: document.getElementById('btn-start-sync'),
  syncServerInput: document.getElementById('sync-server-input'),
  syncPendingEvents: document.getElementById('sync-pending-events'),
  syncPendingBadge: document.getElementById('sync-pending-badge'),
  syncLastTime: document.getElementById('sync-last-time'),

  // Metrics
  valTotalTime: document.getElementById('val-total-time'),
  valActiveTime: document.getElementById('val-active-time'),
  valIdleTime: document.getElementById('val-idle-time'),
  barTotalTime: document.getElementById('bar-total-time'),
  valFocusScore: document.getElementById('val-focus-score'),
  badgeFocusLevel: document.getElementById('badge-focus-level'),
  valProdTime: document.getElementById('val-prod-time'),
  valDistTime: document.getElementById('val-dist-time'),
  barFocusScore: document.getElementById('bar-focus-score'),
  valPomoCount: document.getElementById('val-pomo-count'),
  badgePomoStatus: document.getElementById('badge-pomo-status'),
  valPomoPhase: document.getElementById('val-pomo-phase'),
  valPomoRemain: document.getElementById('val-pomo-remain'),
  barPomo: document.getElementById('bar-pomo'),
  valInterventionsCount: document.getElementById('val-interventions-count'),
  valActiveRulesCount: document.getElementById('val-active-rules-count'),
  valSnoozeStatus: document.getElementById('val-snooze-status'),
  barInterventions: document.getElementById('bar-interventions'),

  // Leaderboard & Visuals
  appsTableBody: document.getElementById('apps-table-body'),
  productivityStackedBar: document.getElementById('productivity-stacked-bar'),
  pctProd: document.getElementById('pct-prod'),
  pctNeut: document.getElementById('pct-neut'),
  pctDist: document.getElementById('pct-dist'),
  categoryBarsList: document.getElementById('category-bars-list'),
  tagsCloudContainer: document.getElementById('tags-cloud-container'),
  timelineHistogramWrap: document.getElementById('timeline-histogram-wrap'),

  // Pomodoro
  clockModeLabel: document.getElementById('clock-mode-label'),
  clockDigits: document.getElementById('clock-digits'),
  clockSubLabel: document.getElementById('clock-sub-label'),
  pomoSvgIndicator: document.getElementById('pomo-svg-indicator'),
  btnPomoToggle: document.getElementById('btn-pomo-toggle'),
  btnPomoReset: document.getElementById('btn-pomo-reset'),
  btnPomoSkip: document.getElementById('btn-pomo-skip'),
  toggleStrictFocus: document.getElementById('toggle-strict-focus'),

  // Rules & Modal
  rulesTableBody: document.getElementById('rules-table-body'),
  ruleSearchInput: document.getElementById('rule-search-input'),
  btnOpenRuleModal: document.getElementById('btn-open-rule-modal'),
  btnQuickAddRule: document.getElementById('btn-quick-add-rule'),
  ruleModal: document.getElementById('rule-modal'),
  btnCloseModal: document.getElementById('btn-close-modal'),
  btnCancelModal: document.getElementById('btn-cancel-modal'),
  ruleForm: document.getElementById('rule-form'),
  formRuleType: document.getElementById('form-rule-type'),
  formRulePattern: document.getElementById('form-rule-pattern'),
  formRuleCategory: document.getElementById('form-rule-category'),
  formRuleScore: document.getElementById('form-rule-score'),
  formRuleTags: document.getElementById('form-rule-tags'),
  formRuleLimit: document.getElementById('form-rule-limit'),
  formRuleAction: document.getElementById('form-rule-action'),

  // Categories Manager & Modal
  categoriesGrid: document.getElementById('categories-grid-container'),
  btnOpenCategoryModal: document.getElementById('btn-open-category-modal'),
  categoryModal: document.getElementById('category-modal'),
  btnCloseCatModal: document.getElementById('btn-close-cat-modal'),
  btnCancelCatModal: document.getElementById('btn-cancel-cat-modal'),
  categoryForm: document.getElementById('category-form'),
  formCatId: document.getElementById('form-cat-id'),
  formCatName: document.getElementById('form-cat-name'),
  formCatDisplay: document.getElementById('form-cat-display'),
  formCatColor: document.getElementById('form-cat-color'),
  formCatColorHex: document.getElementById('form-cat-color-hex'),
  formCatIcon: document.getElementById('form-cat-icon'),
  formCatScore: document.getElementById('form-cat-score'),
  catModalTitle: document.getElementById('cat-modal-title'),

  // Trends & Interventions
  weeklyCardsContainer: document.getElementById('weekly-cards-container'),
  interventionsListContainer: document.getElementById('interventions-list-container')
};

// Utilities
function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0m';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (hrs > 0) return `${hrs}h ${mins.toString().padStart(2, '0')}m`;
  return `${mins}m`;
}

function formatMinutes(seconds) {
  const m = Math.round(seconds / 60);
  return `${m}m`;
}

function formatClock(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>⏳</span><span>${message}</span>`;
  dom.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// --------------------------------------------------------------------------
// Navigation & Mobile Drawer
// --------------------------------------------------------------------------
function toggleSidebar(open) {
  if (!dom.sidebar) return;
  const isOpen = open !== undefined ? open : !dom.sidebar.classList.contains('open');
  dom.sidebar.classList.toggle('open', isOpen);
  if (dom.sidebarBackdrop) {
    dom.sidebarBackdrop.classList.toggle('active', isOpen);
  }
}

if (dom.btnMobileMenu) {
  dom.btnMobileMenu.addEventListener('click', () => toggleSidebar());
}

if (dom.sidebarBackdrop) {
  dom.sidebarBackdrop.addEventListener('click', () => toggleSidebar(false));
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    
    btn.classList.add('active');
    activeTab = btn.getAttribute('data-tab');
    const panel = document.getElementById(activeTab);
    if (panel) panel.classList.add('active');

    // Close mobile drawer if open
    toggleSidebar(false);

    // Trigger tab-specific refresh
    if (activeTab === 'tab-rules') {
      loadRules();
      loadCategories();
    }
    if (activeTab === 'tab-devices') loadNetworkAndDevices();
    if (activeTab === 'tab-trends') {
      loadWeeklyTrends();
      loadRecentInterventions();
    }
  });
});

// --------------------------------------------------------------------------
// Live Data Fetching
// --------------------------------------------------------------------------
async function fetchLiveStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    if (!res.ok) return;
    liveStatus = await res.json();
    renderLiveStatus();
  } catch (err) {
    console.error('Error fetching live status:', err);
  }
}

async function fetchTodayStats() {
  try {
    const url = currentDeviceFilter !== 'all' 
      ? `${API_BASE}/api/stats/today?device_type=${currentDeviceFilter}`
      : `${API_BASE}/api/stats/today`;
    const res = await fetch(url);
    if (!res.ok) return;
    todayStats = await res.json();
    renderTodayStats();
  } catch (err) {
    console.error('Error fetching today stats:', err);
  }
}

function renderLiveStatus() {
  if (!liveStatus) return;

  // Active foreground window
  const active = liveStatus.active_window || {};
  dom.headerApp.textContent = active.app_name || '系統待命中';
  dom.headerTitle.textContent = active.title || '';

  // Pomodoro status
  const pomo = liveStatus.pomodoro || {};
  const remainClock = formatClock(pomo.remaining_seconds || 0);
  dom.topbarTimer.textContent = remainClock;
  if (dom.mobileTimerDigits) dom.mobileTimerDigits.textContent = remainClock;
  dom.clockDigits.textContent = remainClock;
  dom.clockModeLabel.textContent = (pomo.mode || 'IDLE').toUpperCase();
  dom.clockSubLabel.textContent = `今日已完成 ${pomo.focus_count_today || 0} 個番茄`;
  dom.btnPomoToggle.textContent = pomo.is_running ? '暫停' : '開始專注';
  dom.btnPomoToggle.className = pomo.is_running ? 'btn btn-secondary btn-lg' : 'btn btn-primary btn-lg';

  // SVG Progress Ring calculation
  // Radius = 120, circumference = 2 * PI * 120 = 753.98
  const circumference = 753.98;
  const progressRatio = pomo.duration_seconds > 0 
    ? (pomo.duration_seconds - pomo.remaining_seconds) / pomo.duration_seconds 
    : 0;
  const offset = circumference * (1 - progressRatio);
  dom.pomoSvgIndicator.style.strokeDashoffset = offset;

  // Metrics quick sync
  dom.valPomoCount.innerHTML = `${pomo.focus_count_today || 0} <span class="unit">顆完成</span>`;
  dom.badgePomoStatus.textContent = pomo.is_running ? '專注中' : (pomo.mode === 'idle' ? '待命' : '暫停');
  dom.valPomoRemain.textContent = `剩餘 ${remainClock}`;
  dom.barPomo.style.width = `${Math.min(100, Math.round(progressRatio * 100))}%`;
}

function renderTodayStats() {
  if (!todayStats) return;

  const totalSec = todayStats.total_active_sec || 0;
  const idleSec = todayStats.total_idle_sec || 0;
  const focusScore = todayStats.focus_score || 50;
  const prod = todayStats.productivity || { productive: 0, neutral: 0, distracting: 0 };

  // Metric Cards
  dom.valTotalTime.textContent = formatDuration(totalSec);
  dom.valActiveTime.textContent = formatDuration(totalSec);
  dom.valIdleTime.textContent = formatDuration(idleSec);
  // Target: 8 hours = 28800 seconds
  const totalPct = Math.min(100, Math.round((totalSec / 28800) * 100));
  dom.barTotalTime.style.width = `${totalPct}%`;

  dom.valFocusScore.innerHTML = `${focusScore.toFixed(1)}<span class="unit">分</span>`;
  dom.barFocusScore.style.width = `${focusScore}%`;
  dom.valProdTime.textContent = formatMinutes(prod.productive);
  dom.valDistTime.textContent = formatMinutes(prod.distracting);

  if (focusScore >= 75) {
    dom.badgeFocusLevel.textContent = '極佳';
    dom.badgeFocusLevel.className = 'card-badge badge-green';
  } else if (focusScore >= 50) {
    dom.badgeFocusLevel.textContent = '良好';
    dom.badgeFocusLevel.className = 'card-badge badge-cyan';
  } else {
    dom.badgeFocusLevel.textContent = '注意';
    dom.badgeFocusLevel.className = 'card-badge badge-amber';
  }

  // Productivity Stacked Bar
  const totalTracked = (prod.productive + prod.neutral + prod.distracting) || 1;
  const pctP = Math.round((prod.productive / totalTracked) * 100);
  const pctN = Math.round((prod.neutral / totalTracked) * 100);
  const pctD = 100 - pctP - pctN;

  dom.pctProd.textContent = `${pctP}%`;
  dom.pctNeut.textContent = `${pctN}%`;
  dom.pctDist.textContent = `${pctD}%`;

  dom.productivityStackedBar.innerHTML = `
    <div class="bar-segment seg-productive" style="width: ${pctP}%" title="深度生產力: ${formatMinutes(prod.productive)}"></div>
    <div class="bar-segment seg-neutral" style="width: ${pctN}%" title="中性輔助: ${formatMinutes(prod.neutral)}"></div>
    <div class="bar-segment seg-distracting" style="width: ${pctD}%" title="分心娛樂: ${formatMinutes(prod.distracting)}"></div>
  `;

  // Leaderboard Table
  renderLeaderboard(todayStats.top_apps || []);

  // Category Distribution
  renderCategories(todayStats.categories || [], totalSec);

  // Tags Cloud
  renderTags(todayStats.tags || []);

  // 24H Timeline
  renderTimeline(todayStats.hourly_distribution || []);
}

function renderLeaderboard(apps) {
  if (!apps || apps.length === 0) {
    dom.appsTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">今日尚無活躍記錄</td></tr>`;
    return;
  }

  let html = '';
  apps.forEach(app => {
    const iconLetter = (app.app_name || 'A').substring(0, 1).toUpperCase();
    const scoreBadge = getScoreBadge(app.avg_score);
    const categoryBadge = getCategoryBadge(app.category);

    html += `
      <tr>
        <td>
          <div class="app-cell">
            <div class="app-icon-badge">${iconLetter}</div>
            <span class="app-name-text">${escapeHtml(app.app_name)}</span>
          </div>
        </td>
        <td>${categoryBadge}</td>
        <td><strong class="font-mono">${formatDuration(app.total_sec)}</strong></td>
        <td>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div class="progress-bar-wrap" style="width: 60px;">
              <div class="progress-bar-fill fill-cyan" style="width: ${Math.min(100, app.percentage)}%"></div>
            </div>
            <span class="text-sm font-mono text-muted">${app.percentage}%</span>
          </div>
        </td>
        <td>${scoreBadge}</td>
        <td>
          <button class="btn-sm btn-outline" onclick="openRuleModalForApp('${escapeHtml(app.app_name)}', '${escapeHtml(app.category)}')">
            設限
          </button>
        </td>
      </tr>
    `;
  });
  dom.appsTableBody.innerHTML = html;
}

function renderCategories(categories, totalSec) {
  if (!categories || categories.length === 0) {
    dom.categoryBarsList.innerHTML = `<div class="text-muted text-sm">無分類數據</div>`;
    return;
  }

  let html = '';
  categories.slice(0, 6).forEach(cat => {
    const pct = totalSec > 0 ? Math.round((cat.total_sec / totalSec) * 100) : 0;
    const catObj = allCategories.find(c => c.name.toLowerCase() === (cat.category || '').toLowerCase());
    const color = catObj ? catObj.color : '#a855f7';
    const icon = catObj ? catObj.icon : '📁';
    const displayName = catObj ? catObj.display_name : cat.category;

    html += `
      <div class="cat-bar-item">
        <div class="cat-bar-header">
          <span>${icon} ${escapeHtml(displayName)}</span>
          <span class="text-muted font-mono">${formatDuration(cat.total_sec)} (${pct}%)</span>
        </div>
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" style="width: ${pct}%; background-color: ${color}; box-shadow: 0 0 10px ${color}55;"></div>
        </div>
      </div>
    `;
  });
  dom.categoryBarsList.innerHTML = html;
}

function renderTags(tags) {
  if (!tags || tags.length === 0) {
    dom.tagsCloudContainer.innerHTML = `<span class="text-muted text-sm">尚無標籤數據</span>`;
    return;
  }

  let html = '';
  tags.forEach(t => {
    html += `
      <div class="tag-chip">
        <span>#${escapeHtml(t.tag)}</span>
        <strong>${formatMinutes(t.total_sec)}</strong>
      </div>
    `;
  });
  dom.tagsCloudContainer.innerHTML = html;
}

function renderTimeline(hourly) {
  let maxSec = 1;
  hourly.forEach(h => { if (h.seconds > maxSec) maxSec = h.seconds; });

  let html = '';
  hourly.forEach(h => {
    const heightPct = Math.max(3, Math.round((h.seconds / maxSec) * 100));
    const mins = Math.round(h.seconds / 60);
    html += `
      <div class="timeline-col" title="${h.hour}:00 - ${h.hour}:59 (${mins} 分鐘)">
        <div class="timeline-bar" style="height: ${heightPct}%"></div>
        <div class="timeline-hour">${h.hour}</div>
      </div>
    `;
  });
  dom.timelineHistogramWrap.innerHTML = html;
}

function getCategoryBadge(cat) {
  const catObj = allCategories.find(c => c.name.toLowerCase() === (cat || '').toLowerCase());
  if (catObj) {
    const col = catObj.color || '#38bdf8';
    return `<span class="pill-badge" style="background: ${col}18; color: ${col}; border: 1px solid ${col}40;">${catObj.icon || '📁'} ${escapeHtml(catObj.display_name)}</span>`;
  }
  const c = (cat || 'Uncategorized').toLowerCase();
  if (c.includes('dev')) return `<span class="pill-badge pill-dev">💻 開發工作</span>`;
  if (c.includes('comm')) return `<span class="pill-badge pill-comm">💬 通訊聊天</span>`;
  if (c.includes('ent') || c.includes('game')) return `<span class="pill-badge pill-ent">🎬 影音娛樂</span>`;
  if (c.includes('social')) return `<span class="pill-badge pill-social">📱 社群網路</span>`;
  return `<span class="pill-badge pill-neut">📁 ${escapeHtml(cat)}</span>`;
}

function getScoreBadge(score) {
  const s = Math.round(score || 0);
  if (s >= 2) return `<span class="pill-badge pill-dev">深度生產 (+2)</span>`;
  if (s === 1) return `<span class="pill-badge pill-dev">輔助工具 (+1)</span>`;
  if (s === 0) return `<span class="pill-badge pill-neut">中性 (0)</span>`;
  if (s === -1) return `<span class="pill-badge pill-social">分心 (-1)</span>`;
  return `<span class="pill-badge pill-ent">嚴重成癮 (-2)</span>`;
}

function escapeHtml(text) {
  if (!text) return '';
  return text.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// --------------------------------------------------------------------------
// Pomodoro Actions
// --------------------------------------------------------------------------
document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const mode = btn.getAttribute('data-pomo');
    const minutes = parseInt(btn.getAttribute('data-min'), 10);

    try {
      await fetch(`${API_BASE}/api/pomodoro/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, duration_minutes: minutes })
      });
      fetchLiveStatus();
      showToast(`已切換至 ${mode.toUpperCase()} (${minutes} 分鐘)`);
    } catch (err) {
      console.error(err);
    }
  });
});

dom.btnPomoToggle.addEventListener('click', async () => {
  if (!liveStatus || !liveStatus.pomodoro) return;
  const isRunning = liveStatus.pomodoro.is_running;
  const endpoint = isRunning ? '/api/pomodoro/pause' : '/api/pomodoro/resume';
  
  // If it was idle, start default 25m
  if (liveStatus.pomodoro.mode === 'idle') {
    await fetch(`${API_BASE}/api/pomodoro/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'focus', duration_minutes: 25 })
    });
  } else {
    await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
  }
  fetchLiveStatus();
});

dom.btnPomoReset.addEventListener('click', async () => {
  await fetch(`${API_BASE}/api/pomodoro/reset`, { method: 'POST' });
  fetchLiveStatus();
  showToast('番茄鐘已重置');
});

dom.btnPomoSkip.addEventListener('click', async () => {
  await fetch(`${API_BASE}/api/pomodoro/skip`, { method: 'POST' });
  fetchLiveStatus();
  showToast('已跳過當前階段');
});

dom.toggleStrictFocus.addEventListener('change', async () => {
  const res = await fetch(`${API_BASE}/api/pomodoro/toggle-strict`, { method: 'POST' });
  const data = await res.json();
  showToast(data.strict_mode ? '已開啟嚴格專注防繞過！' : '已關閉嚴格模式');
});

// --------------------------------------------------------------------------
// Rules & Limits Management
// --------------------------------------------------------------------------
async function loadRules() {
  try {
    const res = await fetch(`${API_BASE}/api/rules`);
    const data = await res.json();
    allRules = data.rules || [];
    renderRules(allRules);
    dom.valActiveRulesCount.textContent = allRules.filter(r => r.daily_limit_minutes > 0).length;
  } catch (err) {
    console.error(err);
  }
}

function renderRules(rules) {
  if (!rules || rules.length === 0) {
    dom.rulesTableBody.innerHTML = `<tr><td colspan="9" class="text-center text-muted py-4">尚未設定規則</td></tr>`;
    return;
  }

  let html = '';
  rules.forEach(rule => {
    const actionBadge = rule.block_action === 'strict_lock' 
      ? '<span class="pill-badge pill-ent">強制最小化+冷卻</span>'
      : (rule.block_action === 'soft_warn' ? '<span class="pill-badge pill-social">柔性呼吸聲效</span>' : '<span class="text-muted">僅統計</span>');

    const limitText = rule.daily_limit_minutes > 0 
      ? `<strong>${rule.daily_limit_minutes}m</strong> / 天` 
      : '<span class="text-dim">無限制</span>';

    html += `
      <tr>
        <td>
          <input type="checkbox" ${rule.is_enabled ? 'checked' : ''} onchange="toggleRuleEnabled(${rule.id}, this.checked)" />
        </td>
        <td><span class="pill-badge pill-neut">${rule.pattern_type}</span></td>
        <td><strong class="font-mono text-cyan">${escapeHtml(rule.pattern)}</strong></td>
        <td>${escapeHtml(rule.category)}</td>
        <td><span class="text-dim">${escapeHtml(rule.tags || '-')}</span></td>
        <td>${getScoreBadge(rule.productivity_score)}</td>
        <td>${limitText}</td>
        <td>${actionBadge}</td>
        <td>
          <button class="btn-sm btn-outline text-rose" onclick="deleteRule(${rule.id})">刪除</button>
        </td>
      </tr>
    `;
  });
  dom.rulesTableBody.innerHTML = html;
}

window.toggleRuleEnabled = async function(id, enabled) {
  const rule = allRules.find(r => r.id === id);
  if (!rule) return;
  await fetch(`${API_BASE}/api/rules/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category: rule.category,
      tags: rule.tags,
      productivity_score: rule.productivity_score,
      daily_limit_minutes: rule.daily_limit_minutes,
      block_action: rule.block_action,
      is_enabled: enabled ? 1 : 0
    })
  });
  showToast(enabled ? '規則已啟用' : '規則已停用');
};

window.deleteRule = async function(id) {
  if (!confirm('確定要刪除這條規則嗎？')) return;
  await fetch(`${API_BASE}/api/rules/${id}`, { method: 'DELETE' });
  loadRules();
  showToast('規則已刪除');
};

// Modal handlers
dom.btnOpenRuleModal.addEventListener('click', () => {
  dom.ruleForm.reset();
  dom.ruleModal.classList.add('active');
});

dom.btnCloseModal.addEventListener('click', () => dom.ruleModal.classList.remove('active'));
dom.btnCancelModal.addEventListener('click', () => dom.ruleModal.classList.remove('active'));

window.openRuleModalForApp = function(appName, category) {
  dom.ruleForm.reset();
  dom.formRuleType.value = 'app';
  dom.formRulePattern.value = appName;
  if (category) dom.formRuleCategory.value = category;
  dom.formRuleLimit.value = 30;
  dom.formRuleAction.value = 'strict_lock';
  dom.ruleModal.classList.add('active');
};

dom.btnQuickAddRule.addEventListener('click', () => {
  if (!liveStatus || !liveStatus.active_window) return;
  const current = liveStatus.active_window;
  openRuleModalForApp(current.app_name, current.category);
});

dom.ruleForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    pattern_type: dom.formRuleType.value,
    pattern: dom.formRulePattern.value.trim(),
    category: dom.formRuleCategory.value,
    tags: dom.formRuleTags.value.trim(),
    productivity_score: parseInt(dom.formRuleScore.value, 10),
    daily_limit_minutes: parseInt(dom.formRuleLimit.value, 10) || 0,
    block_action: dom.formRuleAction.value
  };

  try {
    const res = await fetch(`${API_BASE}/api/rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      dom.ruleModal.classList.remove('active');
      loadRules();
      fetchTodayStats();
      showToast('防護規則已成功建立！');
    }
  } catch (err) {
    console.error(err);
  }
});

// Search & Filter
dom.ruleSearchInput.addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase();
  const filtered = allRules.filter(r => 
    r.pattern.toLowerCase().includes(query) || 
    r.category.toLowerCase().includes(query) || 
    (r.tags && r.tags.toLowerCase().includes(query))
  );
  renderRules(filtered);
});

document.querySelectorAll('.filter-chips .chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.filter-chips .chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    const filter = chip.getAttribute('data-filter');
    if (filter === 'all') renderRules(allRules);
    else if (filter === 'limit') renderRules(allRules.filter(r => r.daily_limit_minutes > 0));
    else if (filter === 'strict') renderRules(allRules.filter(r => r.block_action === 'strict_lock'));
    else if (filter === 'warn') renderRules(allRules.filter(r => r.block_action === 'soft_warn'));
  });
});

// --------------------------------------------------------------------------
// Custom Categories Manager
// --------------------------------------------------------------------------
async function loadCategories() {
  try {
    const res = await fetch(`${API_BASE}/api/categories`);
    if (!res.ok) return;
    const data = await res.json();
    allCategories = data.categories || [];
    renderCategoriesManager(allCategories);
    renderCategoryDropdown(allCategories);
  } catch (err) {
    console.error('Error loading categories:', err);
  }
}

function renderCategoriesManager(categories) {
  if (!dom.categoriesGrid) return;
  if (!categories || categories.length === 0) {
    dom.categoriesGrid.innerHTML = `<div class="text-muted text-sm py-3">尚無自訂分類</div>`;
    return;
  }

  let html = '';
  categories.forEach(cat => {
    const isSystem = cat.is_system === 1;
    const systemBadge = isSystem 
      ? '<span class="pill-badge pill-neut" style="font-size: 0.7rem; padding: 2px 6px;">系統預設</span>'
      : '<span class="pill-badge pill-comm" style="font-size: 0.7rem; padding: 2px 6px;">使用者自訂</span>';
    
    const scoreBadge = getScoreBadge(cat.default_score);
    const colorHex = cat.color || '#38bdf8';
    const icon = cat.icon || '📁';

    html += `
      <div class="category-card" style="border-left: 3px solid ${colorHex};">
        <div class="category-card-top">
          <div class="category-badge-group">
            <div class="category-icon-box" style="border-color: ${colorHex}55; background: ${colorHex}15; color: ${colorHex};">
              ${icon}
            </div>
            <div class="category-titles">
              <span class="category-name-display">
                ${escapeHtml(cat.display_name)}
                ${systemBadge}
              </span>
              <span class="category-name-key">${escapeHtml(cat.name)}</span>
            </div>
          </div>
        </div>

        <div class="category-card-bottom">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="color-indicator-dot" style="background-color: ${colorHex};" title="${colorHex}"></span>
            ${scoreBadge}
          </div>
          <div class="category-card-actions">
            <button class="btn-sm btn-outline" onclick="openEditCategoryModal(${cat.id})">
              編輯
            </button>
            ${!isSystem ? `<button class="btn-sm btn-outline text-rose" onclick="deleteCategory(${cat.id})">刪除</button>` : ''}
          </div>
        </div>
      </div>
    `;
  });
  dom.categoriesGrid.innerHTML = html;
}

function renderCategoryDropdown(categories) {
  if (!dom.formRuleCategory) return;
  const currentVal = dom.formRuleCategory.value;
  let html = '';
  categories.forEach(cat => {
    html += `<option value="${escapeHtml(cat.name)}">${cat.icon || '📁'} ${escapeHtml(cat.display_name)} (${escapeHtml(cat.name)})</option>`;
  });
  dom.formRuleCategory.innerHTML = html;
  if (currentVal && categories.some(c => c.name === currentVal)) {
    dom.formRuleCategory.value = currentVal;
  }
}

// Category Modal Handlers
if (dom.btnOpenCategoryModal) {
  dom.btnOpenCategoryModal.addEventListener('click', () => {
    if (dom.categoryForm) dom.categoryForm.reset();
    if (dom.formCatId) dom.formCatId.value = '';
    if (dom.formCatName) {
      dom.formCatName.value = '';
      dom.formCatName.disabled = false;
    }
    if (dom.formCatDisplay) dom.formCatDisplay.value = '';
    if (dom.formCatColor) dom.formCatColor.value = '#38bdf8';
    if (dom.formCatColorHex) dom.formCatColorHex.value = '#38bdf8';
    if (dom.formCatIcon) dom.formCatIcon.value = '🚀';
    if (dom.formCatScore) dom.formCatScore.value = '1';
    if (dom.catModalTitle) dom.catModalTitle.textContent = '新增自訂分類';
    if (dom.categoryModal) dom.categoryModal.classList.add('active');
  });
}

if (dom.btnCloseCatModal) {
  dom.btnCloseCatModal.addEventListener('click', () => {
    if (dom.categoryModal) dom.categoryModal.classList.remove('active');
  });
}

if (dom.btnCancelCatModal) {
  dom.btnCancelCatModal.addEventListener('click', () => {
    if (dom.categoryModal) dom.categoryModal.classList.remove('active');
  });
}

// Sync color picker and hex
if (dom.formCatColor && dom.formCatColorHex) {
  dom.formCatColor.addEventListener('input', (e) => {
    dom.formCatColorHex.value = e.target.value;
  });
  dom.formCatColorHex.addEventListener('input', (e) => {
    if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) {
      dom.formCatColor.value = e.target.value;
    }
  });
}

window.selectEmoji = function(emoji) {
  if (dom.formCatIcon) {
    dom.formCatIcon.value = emoji;
  }
};

window.openEditCategoryModal = function(catId) {
  const cat = allCategories.find(c => c.id === catId);
  if (!cat) return;

  if (dom.formCatId) dom.formCatId.value = cat.id;
  if (dom.formCatName) {
    dom.formCatName.value = cat.name;
    dom.formCatName.disabled = (cat.is_system === 1);
  }
  if (dom.formCatDisplay) dom.formCatDisplay.value = cat.display_name;
  if (dom.formCatColor) dom.formCatColor.value = cat.color || '#38bdf8';
  if (dom.formCatColorHex) dom.formCatColorHex.value = cat.color || '#38bdf8';
  if (dom.formCatIcon) dom.formCatIcon.value = cat.icon || '📁';
  if (dom.formCatScore) dom.formCatScore.value = cat.default_score !== undefined ? cat.default_score.toString() : '0';
  if (dom.catModalTitle) dom.catModalTitle.textContent = `編輯分類：${cat.display_name}`;
  if (dom.categoryModal) dom.categoryModal.classList.add('active');
};

window.deleteCategory = async function(catId) {
  const cat = allCategories.find(c => c.id === catId);
  if (!cat) return;
  if (!confirm(`確定要刪除自訂分類「${cat.display_name}」嗎？\n已套用此分類的規則將自動調整為「未分類 (Uncategorized)」。`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/categories/${catId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast(`已成功刪除分類「${cat.display_name}」`);
      loadCategories();
      loadRules();
      fetchTodayStats();
    } else {
      const err = await res.json();
      alert(`刪除失敗：${err.detail || '未知錯誤'}`);
    }
  } catch (err) {
    console.error(err);
    alert('無法連線至後端伺服器');
  }
};

if (dom.categoryForm) {
  dom.categoryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const catId = dom.formCatId.value;
    const isEdit = !!catId;

    const payload = {
      name: dom.formCatName.value.trim(),
      display_name: dom.formCatDisplay.value.trim(),
      color: dom.formCatColorHex.value.trim() || dom.formCatColor.value,
      icon: dom.formCatIcon.value.trim() || '📁',
      default_score: parseInt(dom.formCatScore.value, 10) || 0
    };

    try {
      const url = isEdit ? `${API_BASE}/api/categories/${catId}` : `${API_BASE}/api/categories`;
      const method = isEdit ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        if (dom.categoryModal) dom.categoryModal.classList.remove('active');
        showToast(isEdit ? `分類「${payload.display_name}」已更新！` : `自訂分類「${payload.display_name}」建立成功！`);
        loadCategories();
        loadRules();
        fetchTodayStats();
      } else {
        const err = await res.json();
        alert(`儲存失敗：${err.detail || '請確認分類代碼是否已重複！'}`);
      }
    } catch (err) {
      console.error(err);
      alert('無法連線至伺服器儲存分類');
    }
  });
}

// --------------------------------------------------------------------------
// Trends & Interventions
// --------------------------------------------------------------------------
async function loadWeeklyTrends() {
  try {
    const res = await fetch(`${API_BASE}/api/stats/weekly`);
    const data = await res.json();
    weeklyTrends = data.trends || [];
    renderWeeklyTrends(weeklyTrends);
  } catch (err) {
    console.error(err);
  }
}

function renderWeeklyTrends(trends) {
  if (!trends || trends.length === 0) {
    dom.weeklyCardsContainer.innerHTML = `<div class="text-muted text-sm col-span-7">尚無過去一週歷史記錄</div>`;
    return;
  }

  let html = '';
  trends.forEach(day => {
    html += `
      <div class="weekly-day-card">
        <div class="day-name">${day.date.substring(5)}</div>
        <div class="day-time">${formatDuration(day.total_sec)}</div>
        <div class="day-score">專注分: ${day.avg_score}</div>
      </div>
    `;
  });
  dom.weeklyCardsContainer.innerHTML = html;
}

async function loadRecentInterventions() {
  try {
    const res = await fetch(`${API_BASE}/api/interventions/recent`);
    const data = await res.json();
    recentInterventions = data.interventions || [];
    renderInterventions(recentInterventions);
  } catch (err) {
    console.error(err);
  }
}

function renderInterventions(logs) {
  if (!logs || logs.length === 0) {
    dom.interventionsListContainer.innerHTML = `<div class="text-muted text-sm">今日無攔截或超時紀錄</div>`;
    dom.valInterventionsCount.innerHTML = `0 <span class="unit">次</span>`;
    return;
  }

  dom.valInterventionsCount.innerHTML = `${logs.length} <span class="unit">次</span>`;
  let html = '';
  logs.forEach(log => {
    let badge = `<span class="intervention-badge badge-strict">強制冷卻</span>`;
    if (log.action_taken === 'soft_warn') badge = `<span class="intervention-badge badge-soft">柔性提醒</span>`;
    if (log.action_taken === 'snooze_5m') badge = `<span class="intervention-badge badge-snooze">延長5分鐘</span>`;

    html += `
      <div class="intervention-item">
        <div>
          <strong class="font-mono text-cyan">${escapeHtml(log.app_name)}</strong>
          <span class="text-dim text-sm ml-2">${escapeHtml(log.reason)}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          ${badge}
          <span class="text-dim text-sm font-mono">${log.timestamp.substring(11, 19)}</span>
        </div>
      </div>
    `;
  });
  dom.interventionsListContainer.innerHTML = html;
}

// --------------------------------------------------------------------------
// Cross-Platform Devices & Network
// --------------------------------------------------------------------------
async function loadNetworkAndDevices() {
  try {
    const resNet = await fetch(`${API_BASE}/api/network/lan-ip`);
    if (resNet.ok) {
      const net = await resNet.json();
      if (dom.displayLanUrl) dom.displayLanUrl.textContent = net.url;
    }

    const resDev = await fetch(`${API_BASE}/api/devices`);
    if (resDev.ok) {
      const data = await resDev.json();
      renderDevices(data.devices || []);
    }
  } catch (err) {
    console.error('Error loading devices:', err);
  }
}

function renderDevices(devices) {
  if (!dom.devicesListContainer) return;
  if (!devices || devices.length === 0) {
    dom.devicesListContainer.innerHTML = `<div class="text-muted text-sm">尚未有跨平台客戶端連線</div>`;
    return;
  }

  let html = '';
  devices.forEach(dev => {
    let icon = '💻';
    let badgeClass = 'pill-dev';
    if (dev.device_type === 'android') { icon = '📱'; badgeClass = 'pill-comm'; }
    if (dev.device_type === 'ipad' || dev.device_type === 'ios') { icon = '📋'; badgeClass = 'pill-social'; }

    html += `
      <div class="device-item">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span>${icon}</span>
          <div>
            <strong>${escapeHtml(dev.device_name)}</strong>
            <span class="text-dim text-sm font-mono ml-2">(${dev.device_id})</span>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="pill-badge ${badgeClass}">${dev.device_type.toUpperCase()}</span>
          <span class="text-dim text-sm font-mono">${(dev.last_seen || '').substring(11, 19)}</span>
        </div>
      </div>
    `;
  });
  dom.devicesListContainer.innerHTML = html;
}

// --------------------------------------------------------------------------
// Local-First Offline Storage & Synchronization Engine
// --------------------------------------------------------------------------
function getDeviceType() {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes('ipad') || (ua.includes('macintosh') && 'ontouchend' in document)) return 'ipad';
  if (ua.includes('android')) return 'android';
  return 'windows';
}

function getDeviceId() {
  let id = localStorage.getItem('kairos_device_id');
  if (!id) {
    id = getDeviceType() + '-' + Math.random().toString(36).substring(2, 8);
    localStorage.setItem('kairos_device_id', id);
  }
  return id;
}

function getDeviceName() {
  const t = getDeviceType();
  if (t === 'ipad') return '我的 iPad';
  if (t === 'android') return '我的 Android 手機';
  return '個人電腦 (Web)';
}

const LocalStore = {
  getEvents() {
    try { return JSON.parse(localStorage.getItem('kairos_offline_events') || '[]'); } catch (e) { return []; }
  },
  addEvent(ev) {
    const list = this.getEvents();
    list.push(ev);
    localStorage.setItem('kairos_offline_events', JSON.stringify(list));
    updateSyncBadge();
  },
  clearEvents() {
    localStorage.removeItem('kairos_offline_events');
    updateSyncBadge();
  },
  getPomodoros() {
    try { return JSON.parse(localStorage.getItem('kairos_offline_pomodoros') || '[]'); } catch (e) { return []; }
  },
  addPomodoro(p) {
    const list = this.getPomodoros();
    list.push(p);
    localStorage.setItem('kairos_offline_pomodoros', JSON.stringify(list));
    updateSyncBadge();
  },
  clearPomodoros() {
    localStorage.removeItem('kairos_offline_pomodoros');
    updateSyncBadge();
  },
  getLastSync() {
    return localStorage.getItem('kairos_last_sync_time') || '尚未同步';
  },
  setLastSync(str) {
    localStorage.setItem('kairos_last_sync_time', str);
  },
  getServerUrl() {
    return localStorage.getItem('kairos_sync_server_url') || window.location.origin;
  },
  setServerUrl(url) {
    localStorage.setItem('kairos_sync_server_url', url);
  }
};

function updateSyncBadge() {
  const evCount = LocalStore.getEvents().length;
  const pomoCount = LocalStore.getPomodoros().length;
  const totalPending = evCount + pomoCount;

  if (dom.syncPendingBadge) {
    if (totalPending > 0) {
      dom.syncPendingBadge.style.display = 'inline-block';
      dom.syncPendingBadge.textContent = totalPending;
    } else {
      dom.syncPendingBadge.style.display = 'none';
    }
  }

  if (dom.syncPendingEvents) {
    dom.syncPendingEvents.textContent = `${evCount} 筆事件 / ${pomoCount} 顆番茄`;
  }
  if (dom.syncLastTime) {
    dom.syncLastTime.textContent = LocalStore.getLastSync();
  }
}

async function triggerSync() {
  const serverUrl = (dom.syncServerInput.value.trim() || LocalStore.getServerUrl()).replace(/\/$/, '');
  LocalStore.setServerUrl(serverUrl);

  const pendingEvents = LocalStore.getEvents();
  const pendingPomodoros = LocalStore.getPomodoros();

  dom.btnStartSync.disabled = true;
  dom.btnStartSync.textContent = '雙向同步傳輸中...';

  try {
    // 1. Push pending records to PC Server
    const pushRes = await fetch(`${serverUrl}/api/sync/push`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: getDeviceId(),
        device_name: getDeviceName(),
        device_type: getDeviceType(),
        events: pendingEvents,
        pomodoros: pendingPomodoros
      })
    });

    if (!pushRes.ok) throw new Error('連線主機失敗');
    const pushData = await pushRes.json();

    // 2. Pull server latest rules and statistics
    const pullRes = await fetch(`${serverUrl}/api/sync/pull`);
    if (pullRes.ok) {
      const pullData = await pullRes.json();
      if (pullData.rules) {
        allRules = pullData.rules;
        renderRules(allRules);
      }
    }

    // 3. Clear pending queue & record timestamp
    LocalStore.clearEvents();
    LocalStore.clearPomodoros();
    const nowStr = new Date().toLocaleTimeString('zh-TW', { hour12: false });
    LocalStore.setLastSync(`今日 ${nowStr}`);

    if (dom.syncModal) dom.syncModal.classList.remove('active');
    showToast(`🎉 同步完成！已合併 ${pushData.inserted_count || 0} 筆記錄至電腦！`);
    fetchTodayStats();
    loadNetworkAndDevices();
  } catch (err) {
    console.error(err);
    alert(`同步失敗：無法連線至 ${serverUrl}。\n請確保電腦已啟動 run_kairos.bat，且兩台設備連上同一個 Wi-Fi 網路！`);
  } finally {
    dom.btnStartSync.disabled = false;
    dom.btnStartSync.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
      立即開始雙向同步
    `;
  }
}

// --------------------------------------------------------------------------
// Initialization & Polling Loop
// --------------------------------------------------------------------------
function init() {
  // Register Service Worker for PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  fetchLiveStatus();
  fetchTodayStats();
  loadCategories();
  loadRules();
  loadNetworkAndDevices();
  updateSyncBadge();

  // Periodic Polling: Every 1.5 seconds for live status, 10s for stats
  setInterval(fetchLiveStatus, 1500);
  setInterval(fetchTodayStats, 10000);

  dom.btnRefresh.addEventListener('click', () => {
    fetchLiveStatus();
    fetchTodayStats();
    showToast('已更新今日統計數據');
  });

  if (dom.selectDeviceFilter) {
    dom.selectDeviceFilter.addEventListener('change', (e) => {
      currentDeviceFilter = e.target.value;
      fetchTodayStats();
      showToast(`已切換統計視角：${e.target.options[e.target.selectedIndex].text}`);
    });
  }

  if (dom.btnCopyLanUrl) {
    dom.btnCopyLanUrl.addEventListener('click', () => {
      if (dom.displayLanUrl && dom.displayLanUrl.textContent) {
        navigator.clipboard.writeText(dom.displayLanUrl.textContent);
        showToast('連線網址已複製至剪貼簿！');
      }
    });
  }

  // Sync Modal bindings
  if (dom.btnOpenSyncModal) {
    dom.btnOpenSyncModal.addEventListener('click', () => {
      if (dom.syncServerInput) {
        dom.syncServerInput.value = LocalStore.getServerUrl();
      }
      updateSyncBadge();
      if (dom.syncModal) dom.syncModal.classList.add('active');
    });
  }

  if (dom.btnCloseSyncModal) {
    dom.btnCloseSyncModal.addEventListener('click', () => {
      if (dom.syncModal) dom.syncModal.classList.remove('active');
    });
  }

  if (dom.btnCancelSync) {
    dom.btnCancelSync.addEventListener('click', () => {
      if (dom.syncModal) dom.syncModal.classList.remove('active');
    });
  }

  if (dom.btnStartSync) {
    dom.btnStartSync.addEventListener('click', triggerSync);
  }
}

window.addEventListener('DOMContentLoaded', init);
