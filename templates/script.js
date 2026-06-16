// --- State ---
let currentPage = 'dashboard';
let currentAuthMode = 'login';
let sessionUser = null;
let activeDoctorPatientId = null;
let allPatientReadings = {};

const PLT = {responsive:true, displayModeBar:false};
const DARK_BASE = {
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  xaxis:{gridcolor:'rgba(48,54,61,0.6)', showgrid:true},
  yaxis:{gridcolor:'rgba(48,54,61,0.6)', showgrid:true}
};

function getDARKLayout(extra = {}) {
  const isMobile = window.innerWidth < 768;
  return {
    ...DARK_BASE,
    font: { color: '#8b949e', size: isMobile ? 8.5 : 10.5 },
    margin: isMobile 
      ? { t: 10, r: 8, b: 24, l: 32 } 
      : { t: 10, r: 15, b: 30, l: 45 },
    ...extra
  };
}

// --- Authentication Session Loops ---
async function checkAuthSession() {
  try {
    const res = await fetch('/api/auth/session').then(r => r.json());
    const container = document.getElementById('session-container');
    const doctorBtn = document.getElementById('btn-nav-doctor');

    if (res.authenticated && res.user) {
      sessionUser = res;
      let displayName = res.user.email;
      if (res.user.role === 'PATIENT' && res.patient) {
        displayName = res.patient.name || res.patient.patient_id;
      } else if (res.user.role === 'DOCTOR' && res.doctor) {
        displayName = 'Dr. ' + res.doctor.name;
      }

      document.getElementById('welcome-text').textContent = '👋 Welcome, ' + displayName;

      container.innerHTML = `
        <div class="session-user" title="${res.user.email}">${displayName}</div>
        <div class="session-role">${res.user.role}</div>
        <button class="btn btn-danger btn-sm" style="width:100%; padding:4px 8px; font-size:0.75rem; margin-top:8px" onclick="logout()">🚪 Log Out</button>
      `;

      if (res.user.role === 'PATIENT') {
        document.getElementById('btn-nav-profile').style.display = '';
        document.getElementById('btn-nav-health-history').style.display = '';
      } else {
        document.getElementById('btn-nav-profile').style.display = 'none';
        document.getElementById('btn-nav-health-history').style.display = 'none';
      }
      if (res.user.role === 'DOCTOR') {
        doctorBtn.style.display = 'block';
      } else {
        doctorBtn.style.display = 'none';
      }
    } else {
      sessionUser = null;
      doctorBtn.style.display = 'none';
      document.getElementById('btn-nav-profile').style.display = 'none';
      document.getElementById('btn-nav-health-history').style.display = 'none';
      document.getElementById('welcome-text').textContent = '🌐 Welcome to Medicare IoT Platform';
      container.innerHTML = `
        <div class="session-user">Guest Session</div>
        <div style="display:flex;gap:8px;margin-top:8px">
          <button class="btn btn-primary btn-sm" style="flex:1;padding:4px 8px;font-size:0.72rem;font-weight:600" onclick="openAuthModal('login')">🔑 Log In</button>
          <button class="btn btn-danger btn-sm" style="flex:1;padding:4px 8px;font-size:0.72rem;font-weight:600;background:rgba(88,166,255,0.1);border-color:rgba(88,166,255,0.2);color:var(--accent)" onclick="openAuthModal('signup')">📝 Register</button>
        </div>
      `;
    }
  } catch (e) { console.error('Session sync error:', e); }
}

function openAuthModal(mode) {
  currentAuthMode = mode;
  document.getElementById('auth-modal').style.display = 'flex';
  document.getElementById('auth-error-msg').style.display = 'none';
  toggleAuthModeUI(mode);
}

function closeAuthModal(event) {
  document.getElementById('auth-modal').style.display = 'none';
}

function toggleAuthMode(e) {
  e.preventDefault();
  currentAuthMode = currentAuthMode === 'login' ? 'signup' : 'login';
  toggleAuthModeUI(currentAuthMode);
}

function toggleAuthModeUI(mode) {
  const isSignup = mode === 'signup';
  document.getElementById('auth-title').textContent = isSignup ? '📝 Create Account' : '🔑 Log In';
  document.getElementById('auth-fields-signup').style.display = isSignup ? 'block' : 'none';
  document.getElementById('auth-toggle-prompt').textContent = isSignup ? 'Already registered?' : "Don't have an account?";
  document.getElementById('auth-toggle-link').textContent = isSignup ? 'Log In' : 'Sign Up';
  document.getElementById('auth-submit-btn').textContent = isSignup ? 'Register & Initialize' : 'Sign In';
}

async function submitAuth() {
  const email = document.getElementById('auth-email').value;
  const password = document.getElementById('auth-password').value;
  const errorMsg = document.getElementById('auth-error-msg');
  
  if (!email || !password) {
    errorMsg.textContent = 'Please fill out email and password.';
    errorMsg.style.display = 'block';
    return;
  }

  let payload = { email, password };
  let endpoint = '/api/auth/login';

  if (currentAuthMode === 'signup') {
    payload.role = document.getElementById('auth-role').value;
    payload.name = document.getElementById('auth-name').value || 'New User';
    payload.age = parseInt(document.getElementById('auth-age').value) || 35;
    payload.gender = document.getElementById('auth-gender').value || 'Other';
    endpoint = '/api/auth/signup';
  }

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    if (res.error) {
      errorMsg.textContent = res.error;
      errorMsg.style.display = 'block';
    } else {
      document.getElementById('auth-modal').style.display = 'none';
      if (currentAuthMode === 'signup') {
        alert('Registration complete! Please log in with your credentials.');
        openAuthModal('login');
      } else {
        await checkAuthSession();
        loadDashboard();
      }
    }
  } catch (e) {
    errorMsg.textContent = 'Server connection failed.';
    errorMsg.style.display = 'block';
  }
}

async function logout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  await checkAuthSession();
  nav('dashboard');
}

// --- Sidebar Hamburger Toggle ---
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const ov = document.getElementById('sidebar-overlay');
  const isOpen = sb.classList.contains('open');
  sb.classList.toggle('open', !isOpen);
  ov.classList.toggle('show', !isOpen);
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('show');
}
// Resize and relayout all Plotly charts dynamically on window resize / orientation change
window.addEventListener('resize', () => {
  document.querySelectorAll('.js-plotly-plot').forEach(el => {
    try {
      const isMobile = window.innerWidth < 768;
      const extra = {};
      if (el.id === 'ch-gauge') {
        extra.height = 220;
        extra.margin = isMobile ? {t:25,r:10,b:10,l:10} : {t:30,r:20,b:20,l:20};
      } else if (el.id === 'ch-pred' || el.id === 'ch-feat') {
        extra.height = 280;
        if (el.id === 'ch-pred') extra.yaxis = {title:'Count'};
        else extra.xaxis = {title:'Count'};
      } else {
        extra.height = 180;
      }
      Plotly.relayout(el, getDARKLayout(extra));
      Plotly.Plots.resize(el);
    } catch(e) {}
  });
});

// --- Navigation ---
function nav(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-nav-' + page).classList.add('active');
  
  closeSidebar(); // Auto-close drawer on mobile navigation selection
  
  if (page === 'dashboard') loadDashboard();
  else if (page === 'profile') loadProfile();
  else if (page === 'health-history') loadHealthHistory();
  else if (page === 'doctor') loadDoctorWorkspace();
}

// --- Dashboard ---
async function loadDashboard() {
  try {
    let historyUrl = '/api/sensor-history?limit=50';
    let latestUrl  = '/api/latest-data';
    let predUrl    = '/api/latest-prediction';
    let alertsUrl  = '/api/alerts?limit=10';
    let stabilityUrl = '/api/stability-status';

    if (sessionUser && sessionUser.user.role === 'PATIENT' && sessionUser.patient) {
      const pid = sessionUser.patient.patient_id;
      predUrl    += '?patient_id=' + pid;
      stabilityUrl += '?patient_id=' + pid;
    }

    const [latRes, histRes, predRes, alertRes, stabRes] = await Promise.all([
      fetch(latestUrl).then(r => r.json()).catch(() => ({})),
      fetch(historyUrl).then(r => r.json()).catch(() => ({readings:[]})),
      fetch(predUrl).then(r => r.json()).catch(() => ({})),
      fetch(alertsUrl).then(r => r.json()).catch(() => ({alerts:[]})),
      fetch(stabilityUrl).then(r => r.json()).catch(() => ({}))
    ]);

    // ── Hardware connection status ────────────────────────────────
    const isLive = latRes.is_live === true;
    const hwStatus = document.getElementById('hw-status');
    if (hwStatus) {
      if (isLive) {
        hwStatus.textContent = '🟢 ESP32 Live';
        hwStatus.style.color = 'var(--green)';
      } else {
        const ago = latRes.seconds_ago;
        const label = ago != null ? ` (${ago > 3600 ? Math.floor(ago/3600)+'h' : ago > 60 ? Math.floor(ago/60)+'m' : ago+'s'} ago)` : '';
        hwStatus.textContent = '🔴 ESP32 Offline' + label;
        hwStatus.style.color = 'var(--red)';
      }
    }

    document.getElementById('last-updated').textContent =
      isLive ? 'Last updated: ' + new Date().toLocaleTimeString()
             : 'Waiting for ESP32 wearable data...';

    // ── STABILITY STATUS ──────────────────────────────────────────
    const stabilityEl = document.getElementById('stability-status');
    if (stabRes && stabRes.stability_status) {
      stabilityEl.style.display = '';
      if (stabRes.stability_status === 'Stable') {
        stabilityEl.textContent = '🟢 Monitoring Active';
        stabilityEl.style.background = 'rgba(63,185,80,0.12)';
        stabilityEl.style.color = 'var(--green)';
      } else {
        stabilityEl.textContent = '🟡 Movement Detected – Accuracy May Be Reduced';
        stabilityEl.style.background = 'rgba(210,153,34,0.12)';
        stabilityEl.style.color = 'var(--yellow)';
      }
    } else {
      stabilityEl.style.display = 'none';
    }

    // ── Check for unlinked device readings (show even offline) ────
    const claimBtn = document.getElementById('btn-claim');
    if (claimBtn) {
      if (latRes.reading && !latRes.reading.patient_id && sessionUser && sessionUser.user.role === 'PATIENT') {
        claimBtn.style.display = '';
      } else {
        claimBtn.style.display = 'none';
      }
    }

    // ── OFFLINE / STALE STATE ────────────────────────────────────
    if (!isLive) {
      if (!latRes.reading) {
        // Truly no data at all — show empty cards
        ['bpm','spo2','temp'].forEach(id => {
          document.getElementById('v-' + id).textContent = '--';
          const badge = document.getElementById('b-' + id);
          badge.textContent = 'Offline';
          badge.className = 'card-badge';
          badge.style.background = 'rgba(139,148,158,0.15)';
          badge.style.color = 'var(--muted)';
          const card = document.getElementById('card-' + id);
          if (card) card.classList.remove('card-danger','card-warning');
        });
        document.getElementById('v-risk').textContent = '--';
        document.getElementById('b-risk').textContent = 'No Data';
        document.getElementById('b-risk').className = 'card-badge';
        document.getElementById('v-recommendation').textContent =
          '📡 Waiting for ESP32 wearable — connect the device and ensure it is on the same WiFi network as this PC.';

        ['ch-bpm','ch-spo2','ch-temp'].forEach(id => {
          Plotly.newPlot(id, [], getDARKLayout({height:180,
            annotations:[{text:'No hardware data',showarrow:false,
              font:{color:'#8b949e',size:13},xref:'paper',yref:'paper',x:0.5,y:0.5}]
          }), PLT);
        });
        Plotly.newPlot('ch-gauge', [{
          type:'indicator', mode:'gauge+number', value: 0,
          title:{text:'No Data', font:{color:'#8b949e',size:13}},
          gauge:{axis:{range:[0,100]}, bar:{color:'#30363d'},
            steps:[{range:[0,100],color:'rgba(48,54,61,0.3)'}]}
        }], getDARKLayout({height:220, margin:{t:30,r:20,b:20,l:20}}), PLT);

        document.getElementById('tbl-latest').innerHTML =
          '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:20px">' +
          '📡 No ESP32 data — connect the wearable device to see live readings</td></tr>';

        document.getElementById('alert-banner').innerHTML = '';
        document.getElementById('stability-status').style.display = 'none';
        document.getElementById('fall-badge').style.display = 'none';
        return;
      }
      // Have stale data — still render it below, just marked as offline
    }

    // ── RENDER READING DATA (live or stale) ──────────────────────
    if (latRes.reading) {
      const r = latRes.reading;
      const bpmDanger  = r.heart_rate < 50 || r.heart_rate > 110;
      const bpmWarn    = !bpmDanger && (r.heart_rate < 60 || r.heart_rate > 100);
      const spo2Danger = r.spo2 < 92;
      const spo2Warn   = !spo2Danger && r.spo2 < 95;
      const tempDanger = r.temperature < 35.5 || r.temperature > 38.5;
      const tempWarn   = !tempDanger && (r.temperature < 36.1 || r.temperature > 37.5);

      // Reset any leftover offline styles
      ['bpm','spo2','temp'].forEach(id => {
        const badge = document.getElementById('b-' + id);
        badge.style.background = '';
        badge.style.color = '';
      });

      setCard('bpm',  r.heart_rate  != null ? (+r.heart_rate).toFixed(0)  : '--', bpmDanger,  bpmWarn, !isLive ? 'Stale' : null);
      setCard('spo2', r.spo2        != null ? (+r.spo2).toFixed(1)        : '--', spo2Danger, spo2Warn, !isLive ? 'Stale' : null);
      setCard('temp', r.temperature != null ? (+r.temperature).toFixed(1) : '--', tempDanger, tempWarn, !isLive ? 'Stale' : null);

      const fallBadge = document.getElementById('fall-badge');
      if (r.fall_detected) {
        fallBadge.style.display = '';
        ['card-bpm','card-spo2','card-temp','card-risk'].forEach(id => {
          const c = document.getElementById(id);
          if (c) c.classList.add('card-danger');
        });
      } else {
        fallBadge.style.display = 'none';
      }
    }

    if (predRes.prediction) {
      const p = predRes.prediction;
      const score = +(p.risk_score || 0);
      document.getElementById('v-risk').textContent = score.toFixed(0);
      document.getElementById('b-risk').textContent = p.risk_level || 'Low';
      document.getElementById('b-risk').className = 'card-badge ' +
        (p.risk_level === 'Low' ? 'badge-ok' : p.risk_level === 'Medium' ? 'badge-warning' : 'badge-danger');
      const riskCard = document.getElementById('card-risk');
      if (riskCard) {
        riskCard.classList.remove('card-danger','card-warning');
        if (p.risk_level === 'High' || p.risk_level === 'Critical') riskCard.classList.add('card-danger');
        else if (p.risk_level === 'Medium') riskCard.classList.add('card-warning');
      }
      document.getElementById('v-recommendation').textContent = p.recommendation || 'No active advice.';

      Plotly.newPlot('ch-gauge', [{
        type:'indicator', mode:'gauge+number', value: score,
        title:{text:(p.risk_level||'Low')+' Risk', font:{color:'#8b949e',size:window.innerWidth<768?10:13}},
        gauge:{axis:{range:[0,100]}, bar:{color:'#58a6ff'},
          steps:[{range:[0,25],color:'rgba(63,185,80,0.25)'},
                 {range:[25,50],color:'rgba(210,153,34,0.25)'},
                 {range:[50,100],color:'rgba(248,81,73,0.25)'}]}
      }], getDARKLayout({height:220, margin:window.innerWidth<768?{t:25,r:10,b:10,l:10}:{t:30,r:20,b:20,l:20}}), PLT);

      setTimeout(() => { const gd = document.getElementById('ch-gauge'); if(gd) Plotly.Plots.resize(gd); }, 50);
    }

    renderAlertBanner(alertRes.alerts || []);

    // Only show readings from the last 5 minutes in charts (fresh ESP32 data)
    const cutoff = Date.now() - 5 * 60 * 1000;
    function parseTime(ts) {
      if (!ts) return null;
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(ts)) ts += 'Z';
      return new Date(ts).getTime();
    }
    const readings = (histRes.readings || [])
      .filter(r => parseTime(r.timestamp) > cutoff)
      .reverse();

    const ts = readings.map(r => {
      const t = r.timestamp || '';
      return t.substring(11,19);
    });
    trendChart('ch-bpm',  ts, readings.map(r => r.heart_rate),  '#f85149', 'Heart Rate (bpm)');
    trendChart('ch-spo2', ts, readings.map(r => r.spo2),        '#58a6ff', 'SpO2 (%)');
    trendChart('ch-temp', ts, readings.map(r => r.temperature), '#f39c12', 'Temp (°C)');

    const tbody = document.getElementById('tbl-latest');
    if (!readings.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--muted)">Waiting for first live reading...</td></tr>';
    } else {
      tbody.innerHTML = readings.slice(-10).reverse().map(r => {
        const risk = predRes.prediction ? (+predRes.prediction.risk_score).toFixed(0) : '--';
        return '<tr>' +
          '<td>' + (r.heart_rate  != null ? (+r.heart_rate).toFixed(0)  : '--') + '</td>' +
          '<td>' + (r.spo2        != null ? (+r.spo2).toFixed(1)        : '--') + '</td>' +
          '<td>' + (r.temperature != null ? (+r.temperature).toFixed(1) : '--') + '</td>' +
          '<td>' + risk + '</td>' +
          '<td>' + (r.fall_detected ? '💥 FALL' : 'Normal') + '</td></tr>';
      }).join('');
    }

  } catch(e) { console.error('Dashboard error:', e); }
}

function setCard(id, val, abnormal, warning, staleLabel) {
  document.getElementById('v-' + id).textContent = val;
  const badge = document.getElementById('b-' + id);
  if (staleLabel) {
    badge.textContent = staleLabel;
    badge.className = 'card-badge';
    badge.style.background = 'rgba(139,148,158,0.15)';
    badge.style.color = 'var(--muted)';
  } else {
    badge.textContent = abnormal ? 'Abnormal' : warning ? 'Warning' : 'Normal';
    badge.className = 'card-badge ' + (abnormal ? 'badge-danger' : warning ? 'badge-warning' : 'badge-ok');
  }
  // Apply glowing border to the parent card
  const card = document.getElementById('card-' + id);
  if (card) {
    card.classList.remove('card-danger', 'card-warning');
    if (abnormal) card.classList.add('card-danger');
    else if (warning && !staleLabel) card.classList.add('card-warning');
  }
}

// --- Rich Glassmorphic Alert Banner ---
function renderAlertBanner(alerts) {
  const banner = document.getElementById('alert-banner');
  const active = alerts.filter(a => !a.is_read);
  if (!active.length) { banner.innerHTML = ''; banner.style.display = 'none'; return; }

  const SEVERITY_MAP = {
    CRITICAL:  { cls: 'alert-danger',  icon: '🚨', label: 'Critical Alert' },
    EMERGENCY: { cls: 'alert-danger',  icon: '🆘', label: 'Emergency' },
    HIGH:      { cls: 'alert-danger',  icon: '⚠️', label: 'High Alert' },
    MEDIUM:    { cls: 'alert-warning', icon: '⚡', label: 'Medium Alert' },
  };

  const TYPE_ICON = {
    fall: '💥', ml_risk: '🧠',
    heart_rate: '❤️', spo2: '🫁', temperature: '🌡️',
  };

  function relativeTime(ts) {
    if (!ts) return '';
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(ts)) {
      ts += 'Z';
    }
    const diff = Math.floor((Date.now() - new Date(ts)) / 1000);
    const absDiff = Math.max(0, diff);
    if (absDiff < 60) return absDiff + 's ago';
    if (absDiff < 3600) return Math.floor(absDiff / 60) + 'm ago';
    return Math.floor(absDiff / 3600) + 'h ago';
  }

  // Show relevant alerts (MEDIUM and above)
  const dangerAlerts = active.filter(a => {
    const sev = (a.severity || '').toUpperCase();
    return sev === 'CRITICAL' || sev === 'EMERGENCY' || sev === 'HIGH' || sev === 'MEDIUM';
  });
  if (!dangerAlerts.length) { banner.innerHTML = ''; banner.style.display = 'none'; return; }

  banner.style.display = '';

  function renderAlert(a) {
    const sev = (a.severity || '').toUpperCase();
    const meta = SEVERITY_MAP[sev] || SEVERITY_MAP['CRITICAL'];
    const typeIcon = TYPE_ICON[a.alert_type] || '⚠️';
    const ts = relativeTime(a.timestamp || a.created_at);

    let valueBadge = '';
    if (a.value != null && a.threshold != null && a.alert_type !== 'ml_risk') {
      valueBadge = `<span class="alert-value-badge">${(+a.value).toFixed(1)}</span>`;
    }

    return `
      <div class="alert-card ${meta.cls}" id="alert-card-${a.id}">
        <div class="alert-content">
          <div class="alert-icon-wrapper">${typeIcon}</div>
          <div class="alert-text">
            <div class="alert-title">${meta.icon} ${meta.label}${valueBadge}</div>
            <div class="alert-message">${a.message || ''}</div>
            ${ts ? `<div class="alert-time">${ts}</div>` : ''}
          </div>
        </div>
        <button class="alert-action-btn" onclick="dismissAlert(${a.id})" title="Dismiss">✕</button>
      </div>
    `;
  }

  banner.innerHTML = dangerAlerts.slice(0, 5).map(renderAlert).join('');
}

async function dismissAlert(id) {
  const card = document.getElementById('alert-card-' + id);
  if (card) { card.style.opacity = '0'; card.style.transform = 'translateX(20px)'; card.style.transition = 'all 0.25s ease'; }
  try {
    await fetch('/api/alerts/' + id + '/read', { method: 'PATCH' });
  } catch(e) {}
  setTimeout(() => { if (card) card.remove(); }, 280);
}

async function injectDemoReading(type) {
  let hr = 72 + Math.floor(Math.random() * 10);
  let spo2 = 97.5 + Math.random() * 2;
  let temp = 36.6 + Math.random() * 0.5;
  let fall = false;

  if (type === 'low_spo2') {
    spo2 = 89.2;
    hr = 104;
  } else if (type === 'fall') {
    fall = true;
    hr = 112;
  }

  // Clip ranges
  spo2 = Math.min(100, Math.max(70, spo2));
  
  try {
    const res = await fetch('/api/sensor-data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        heart_rate: hr,
        spo2: spo2,
        temperature: temp,
        fall_detected: fall
      })
    }).then(r => r.json());

    if (res.status === 'success') {
      loadDashboard();
    } else {
      alert('Error injecting: ' + (res.error || res.status || 'Unknown error'));
    }
  } catch(e) {
    alert('Injection request failed. Make sure your server is running.');
  }
}

function trendChart(el, x, y, color, name) {
  Plotly.newPlot(el, [{x, y, type:'scatter', mode:'lines+markers', name,
    line:{color, width:2}, marker:{size:4, color}}], getDARKLayout({height:180}), PLT);

  // Instantly force-fit plot size to container on load to prevent any layout stretching
  setTimeout(() => {
    const gd = document.getElementById(el);
    if (gd) Plotly.Plots.resize(gd);
  }, 50);
}

// --- Profile ---
async function loadProfile() {
  try {
    const res = await fetch('/api/profile').then(r => r.json());
    if (res.profile) {
      const p = res.profile;
      
      // Update form inputs
      document.getElementById('pf-name').value = p.name || '';
      document.getElementById('pf-age').value = p.age || '';
      document.getElementById('pf-gender').value = p.gender || '';
      document.getElementById('pf-blood').value = p.blood_group || '';
      document.getElementById('pf-emergency').value = p.emergency_contact || '';
      
      const emailVal = (sessionUser && sessionUser.user ? sessionUser.user.email : '') || '';
      document.getElementById('pf-email').value = emailVal;
      
      const docName = p.doctor_name || 'Not Assigned';
      document.getElementById('pf-doctor').value = docName;

      // Update left side summary card details
      document.getElementById('pf-summary-name').textContent = p.name || 'Patient Profile';
      document.getElementById('pf-summary-id').textContent = 'Patient ID: ' + (p.patient_id || '--');
      document.getElementById('pf-stat-blood').textContent = p.blood_group || '--';
      document.getElementById('pf-stat-age').textContent = p.age ? p.age + ' yrs' : '--';
      document.getElementById('pf-stat-gender').textContent = p.gender || '--';
      document.getElementById('pf-summary-email').textContent = emailVal || '--';
      document.getElementById('pf-summary-doctor').textContent = docName;

      // Calculate and display initials for the avatar circle
      const initials = (p.name || 'Patient')
        .split(' ')
        .filter(w => w.length > 0)
        .map(w => w[0])
        .join('')
        .substring(0, 2)
        .toUpperCase();
      document.getElementById('pf-avatar').textContent = initials;
    }
  } catch(e) { console.error('Profile load error:', e); }
}

async function saveProfile() {
  const msg = document.getElementById('pf-msg');
  msg.style.display = 'none';
  try {
    const res = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('pf-name').value,
        age: document.getElementById('pf-age').value,
        gender: document.getElementById('pf-gender').value,
        blood_group: document.getElementById('pf-blood').value,
        emergency_contact: document.getElementById('pf-emergency').value,
      })
    }).then(r => r.json());
    if (res.success) {
      msg.innerHTML = '✨ Profile updated successfully!';
      msg.style.display = 'block';
      msg.style.background = 'rgba(63, 185, 80, 0.1)';
      msg.style.borderColor = 'rgba(63, 185, 80, 0.3)';
      msg.style.color = 'var(--green)';
      msg.style.boxShadow = '0 0 10px rgba(63, 185, 80, 0.2)';
      
      // Reload profile to update summary card dynamically
      await loadProfile();
    } else {
      msg.innerHTML = '⚠️ ' + (res.error || 'Failed to save details');
      msg.style.display = 'block';
      msg.style.background = 'rgba(248, 81, 73, 0.1)';
      msg.style.borderColor = 'rgba(248, 81, 73, 0.3)';
      msg.style.color = 'var(--red)';
      msg.style.boxShadow = '0 0 10px rgba(248, 81, 73, 0.2)';
    }
  } catch(e) {
    msg.innerHTML = '⚠️ Connection or Server Error';
    msg.style.display = 'block';
    msg.style.background = 'rgba(248, 81, 73, 0.1)';
    msg.style.borderColor = 'rgba(248, 81, 73, 0.3)';
    msg.style.color = 'var(--red)';
    msg.style.boxShadow = '0 0 10px rgba(248, 81, 73, 0.2)';
  }
}

// --- Health History ---
async function loadHealthHistory() {
  try {
    const res = await fetch('/api/health-history?limit=100').then(r => r.json());
    const readings = res.readings || [];
    document.getElementById('hh-loading').style.display = 'none';
    document.getElementById('hh-content').style.display = '';

    if (!readings.length) {
      ['hh-hr','hh-spo2','hh-temp','hh-fall'].forEach(id =>
        document.getElementById(id).innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--muted)">No records yet</td></tr>');
      return;
    }

    function fmt(ts) {
      if (!ts) return '--';
      const d = new Date(ts + 'Z');
      return d.toLocaleString();
    }
    function statusHR(v) { return v < 60 || v > 100 ? '⚠️' : '✅'; }
    function statusSPO2(v) { return v < 95 ? '⚠️' : '✅'; }
    function statusTEMP(v) { return v < 36.1 || v > 37.5 ? '⚠️' : '✅'; }

    document.getElementById('hh-hr').innerHTML = readings.map(r =>
      '<tr><td>'+fmt(r.timestamp)+'</td><td>'+(r.heart_rate!=null?(+r.heart_rate).toFixed(0):'--')+'</td><td>'+statusHR(r.heart_rate)+'</td></tr>'
    ).join('');

    document.getElementById('hh-spo2').innerHTML = readings.map(r =>
      '<tr><td>'+fmt(r.timestamp)+'</td><td>'+(r.spo2!=null?(+r.spo2).toFixed(1):'--')+'</td><td>'+statusSPO2(r.spo2)+'</td></tr>'
    ).join('');

    document.getElementById('hh-temp').innerHTML = readings.map(r =>
      '<tr><td>'+fmt(r.timestamp)+'</td><td>'+(r.temperature!=null?(+r.temperature).toFixed(1):'--')+'</td><td>'+statusTEMP(r.temperature)+'</td></tr>'
    ).join('');

    document.getElementById('hh-fall').innerHTML = readings.map(r =>
      '<tr><td>'+fmt(r.timestamp)+'</td><td>'+(r.fall_detected?'💥 Yes':'No')+'</td></tr>'
    ).join('');

    // Store for PDF export
    window._pdfReadings = readings;
  } catch(e) {
    document.getElementById('hh-loading').textContent = '❌ Failed to load health history';
    console.error('Health history error:', e);
  }
}

async function downloadPDF() {
  const readings = window._pdfReadings;
  if (!readings || !readings.length) {
    alert('No health records to export. Load the Health History page first.');
    return;
  }

  function fmt(ts) {
    if (!ts) return '--';
    const d = new Date(ts + 'Z');
    const y = d.getFullYear();
    const mo = String(d.getMonth()+1).padStart(2,'0');
    const da = String(d.getDate()).padStart(2,'0');
    const h = String(d.getHours()).padStart(2,'0');
    const mi = String(d.getMinutes()).padStart(2,'0');
    return y+'-'+mo+'-'+da+' '+h+':'+mi;
  }
  function statusHR(v) { return v < 60 || v > 100 ? 'Abnormal' : 'Normal'; }
  function statusSPO2(v) { return v < 95 ? 'Low' : 'Normal'; }
  function statusTEMP(v) { return v < 36.1 || v > 37.5 ? 'Abnormal' : 'Normal'; }
  function rowClass(i) { return i % 2 === 0 ? 'background:#f9f9f9' : ''; }

  const name = document.getElementById('pf-name').value || 'Unknown';
  document.getElementById('pdf-patient-name').textContent = name;
  document.getElementById('pdf-date').textContent = new Date().toLocaleString();

  const total = readings.length;
  document.getElementById('pdf-total').textContent = total;
  const firstTs = readings[total-1] && readings[total-1].timestamp ? fmt(readings[total-1].timestamp) : '--';
  const lastTs = readings[0] && readings[0].timestamp ? fmt(readings[0].timestamp) : '--';
  document.getElementById('pdf-period').textContent = firstTs + '  to  ' + lastTs;

  const B = '1px solid #ddd';

  document.getElementById('pdf-hr').innerHTML = readings.map((r,i) =>
    '<tr style="'+rowClass(i)+'">' +
      '<td style="padding:6px 10px;border:'+B+'">'+fmt(r.timestamp)+'</td>' +
      '<td style="padding:6px 10px;border:'+B+';text-align:center;font-weight:600">'+(r.heart_rate!=null?(+r.heart_rate).toFixed(0):'--')+'</td>' +
      '<td style="padding:6px 10px;border:'+B+';text-align:center;color:'+(r.heart_rate!=null&&(r.heart_rate<60||r.heart_rate>100)?'#d93025':'#188038')+'">'+statusHR(r.heart_rate)+'</td>' +
    '</tr>'
  ).join('');

  document.getElementById('pdf-spo2').innerHTML = readings.map((r,i) =>
    '<tr style="'+rowClass(i)+'">' +
      '<td style="padding:6px 10px;border:'+B+'">'+fmt(r.timestamp)+'</td>' +
      '<td style="padding:6px 10px;border:'+B+';text-align:center;font-weight:600">'+(r.spo2!=null?(+r.spo2).toFixed(1):'--')+'</td>' +
      '<td style="padding:6px 10px;border:'+B+';text-align:center;color:'+(r.spo2!=null&&r.spo2<95?'#d93025':'#188038')+'">'+statusSPO2(r.spo2)+'</td>' +
    '</tr>'
  ).join('');

  document.getElementById('pdf-temp').innerHTML = readings.map((r,i) =>
    '<tr style="'+rowClass(i)+'">' +
      '<td style="padding:6px 10px;border:'+B+'">'+fmt(r.timestamp)+'</td>' +
      '<td style="padding:6px 10px;border:'+B+';text-align:center;font-weight:600">'+(r.temperature!=null?(+r.temperature).toFixed(1):'--')+'</td>' +
      '<td style="padding:6px 10px;border:'+B+';text-align:center;color:'+(r.temperature!=null&&(r.temperature<36.1||r.temperature>37.5)?'#d93025':'#188038')+'">'+statusTEMP(r.temperature)+'</td>' +
    '</tr>'
  ).join('');

  document.getElementById('pdf-fall').innerHTML = readings.map((r,i) =>
    '<tr style="'+rowClass(i)+'">' +
      '<td style="padding:6px 10px;border:'+B+'">'+fmt(r.timestamp)+'</td>' +
      '<td style="padding:6px 10px;border:'+B+';text-align:center;font-weight:600;color:'+(r.fall_detected?'#d93025':'#188038')+'">'+(r.fall_detected?'Yes':'No')+'</td>' +
    '</tr>'
  ).join('');

  const el = document.getElementById('pdf-report');
  const orig = el.style.cssText;
  el.style.position = 'fixed';
  el.style.left = '0';
  el.style.top = '0';
  el.style.width = '800px';
  el.style.zIndex = '-1';
  el.style.opacity = '0';
  el.style.display = 'block';
  el.style.background = '#fff';

  await new Promise(r => setTimeout(r, 100));

  const opt = {
    margin: [6, 6, 6, 6],
    filename: 'Health_Report_'+new Date().toISOString().slice(0,10)+'.pdf',
    image: { type: 'jpeg', quality: 0.95 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
  };
  try {
    await html2pdf().set(opt).from(el).save();
  } catch(e) {
    console.error('PDF error:', e);
    alert('PDF generation failed. Check console for details.');
  } finally {
    el.style.cssText = orig;
  }
}



// --- Doctor Workspace ---
async function loadDoctorWorkspace() {
  try {
    const histRes = await fetch('/api/sensor-history?limit=100').then(r => r.json()).catch(() => ({readings:[]}));
    const readings = histRes.readings || [];

    // Group readings by patient/device
    let groups = {};
    readings.forEach(r => {
      const pid = r.patient_id || 'ESP32_Device';
      if (!groups[pid]) groups[pid] = [];
      groups[pid].push(r);
    });

    allPatientReadings = groups;
    const tbody = document.getElementById('doc-patient-tbody');
    
    if (Object.keys(groups).length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--muted)">No active sensor streams detected in system logs.</td></tr>';
      return;
    }

    tbody.innerHTML = Object.keys(groups).map(pid => {
      const list = groups[pid];
      const latest = list[0];
      const selectedClass = pid === activeDoctorPatientId ? 'selected' : '';
      
      const hr = latest.heart_rate != null ? (+latest.heart_rate).toFixed(0) : '--';
      const spo2 = latest.spo2 != null ? (+latest.spo2).toFixed(1) : '--';
      const temp = latest.temperature != null ? (+latest.temperature).toFixed(1) : '--';

      const isAbnormal = latest.heart_rate < 60 || latest.heart_rate > 100 || latest.spo2 < 95;
      const statusText = latest.fall_detected ? '💥 FALL DETECTED' : isAbnormal ? '⚠️ Unstable Vitals' : '💚 Stable';
      const statusStyle = latest.fall_detected || isAbnormal ? 'color:var(--red); font-weight:600' : 'color:var(--green)';

      return `
        <tr class="patient-row ${selectedClass}" onclick="selectDoctorPatient('${pid}')">
          <td><strong>${pid}</strong></td>
          <td>${hr} bpm</td>
          <td>${spo2} %</td>
          <td>${temp} °C</td>
          <td style="${statusStyle}">${statusText}</td>
        </tr>
      `;
    }).join('');

    if (activeDoctorPatientId) {
      loadDoctorDiagnostic(activeDoctorPatientId);
    }
  } catch (e) { console.error('Doctor panel load error:', e); }
}

function selectDoctorPatient(pid) {
  activeDoctorPatientId = pid;
  document.querySelectorAll('.patient-row').forEach(row => {
    row.classList.remove('selected');
  });
  event.currentTarget.classList.add('selected');
  loadDoctorDiagnostic(pid);
}

async function loadDoctorDiagnostic(pid) {
  try {
    const [predRes, alertRes] = await Promise.all([
      fetch('/api/latest-prediction?patient_id=' + pid).then(r => r.json()).catch(() => ({})),
      fetch('/api/alerts?limit=5&patient_id=' + pid).then(r => r.json()).catch(() => ({alerts:[]}))
    ]);

    document.getElementById('doc-diagnostic-no-selection').style.display = 'none';
    document.getElementById('doc-diagnostic-card').style.display = 'block';

    const p = predRes.prediction;
    if (!p) {
      document.getElementById('doc-active-patient-name').textContent = `Diagnostics for ${pid}`;
      document.getElementById('doc-v-hr').textContent = '--';
      document.getElementById('doc-v-spo2').textContent = '--';
      document.getElementById('doc-v-temp').textContent = '--';
      document.getElementById('doc-v-risk').textContent = '--';
      document.getElementById('doc-v-anomaly').textContent = 'No Prediction';
      document.getElementById('doc-active-recommendation').textContent = 'Start the simulator to stream predictions.';
      updateShapUI({heart_rate:0, spo2:0, temperature:0, fall_detected:0});
      return;
    }

    document.getElementById('doc-active-patient-name').textContent = `Diagnostics: Patient ${pid}`;
    document.getElementById('doc-v-hr').textContent = (p.heart_rate != null ? (+p.heart_rate).toFixed(0) : '--') + ' bpm';
    document.getElementById('doc-v-spo2').textContent = (p.spo2 != null ? (+p.spo2).toFixed(1) : '--') + ' %';
    document.getElementById('doc-v-temp').textContent = (p.temperature != null ? (+p.temperature).toFixed(1) : '--') + ' °C';
    
    const scoreVal = +(p.risk_score || 0);
    const riskBox = document.getElementById('doc-v-risk');
    riskBox.textContent = scoreVal.toFixed(0) + '%';
    riskBox.style.color = p.risk_level === 'Low' ? 'var(--green)' : p.risk_level === 'Medium' ? 'var(--yellow)' : 'var(--red)';

    const anomalyBox = document.getElementById('doc-v-anomaly');
    const isAnomaly = p.anomaly_status ? p.anomaly_status.is_anomaly : false;
    anomalyBox.textContent = isAnomaly ? '⚠️ Outlier' : '💚 Regular';
    anomalyBox.style.color = isAnomaly ? 'var(--red)' : 'var(--green)';

    document.getElementById('doc-active-recommendation').textContent = p.recommendation || 'Vitals are stable. Standard outpatient observation recommended.';

    // Explainability Attribution
    let shap = p.explanation;
    if (typeof shap === 'string') {
      try { shap = JSON.parse(shap); } catch(e){}
    }
    const contributions = shap ? shap.contributions : null;
    
    if (contributions) {
      updateShapUI(contributions);
    } else {
      updateShapUI({heart_rate:33, spo2:33, temperature:33, fall_detected:0});
    }

  } catch(e) { console.error('Load diagnostics error:', e); }
}

function updateShapUI(contrib) {
  const hr = contrib.heart_rate || 0;
  const spo2 = contrib.spo2 || 0;
  const temp = contrib.temperature || 0;
  const fall = contrib.fall_detected || 0;

  document.getElementById('shap-pct-hr').textContent = hr.toFixed(1) + '%';
  document.getElementById('shap-bar-hr').style.width = hr + '%';

  document.getElementById('shap-pct-spo2').textContent = spo2.toFixed(1) + '%';
  document.getElementById('shap-bar-spo2').style.width = spo2 + '%';

  document.getElementById('shap-pct-temp').textContent = temp.toFixed(1) + '%';
  document.getElementById('shap-bar-temp').style.width = temp + '%';

  document.getElementById('shap-pct-fall').textContent = fall.toFixed(1) + '%';
  document.getElementById('shap-bar-fall').style.width = fall + '%';
}

// --- Alerts ---
async function clearAlerts() {
  await fetch('/api/alerts/read-all',{method:'PATCH'});
  loadDashboard();
}

// --- Claim unassigned readings ---
async function claimReadings() {
  try {
    const res = await fetch('/api/claim-readings', { method: 'POST' }).then(r => r.json());
    if (res.success) {
      alert('✅ Linked ' + res.claimed + ' readings to your account!');
      loadDashboard();
    } else {
      alert('❌ ' + (res.error || 'Failed to link'));
    }
  } catch(e) {
    alert('❌ Server error');
  }
}

// --- Boot splash hide ---
function hideBootSplash() {
  const splash = document.getElementById('boot-splash');
  if (splash) splash.classList.add('hidden');
}

window.addEventListener('message', function onBootMsg(e) {
  if (e.data === 'bootComplete') {
    window.removeEventListener('message', onBootMsg);
    setTimeout(hideBootSplash, 400);
  }
});

// --- Init ---
checkAuthSession();
loadDashboard();
setInterval(function(){ 
  if(currentPage==='dashboard') loadDashboard(); 
  else if (currentPage === 'doctor') loadDoctorWorkspace();
}, 2000);
