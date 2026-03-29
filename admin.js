import { supabase } from './supabase.js'

// ============================================================
// ADMIN DASHBOARD LOGIC
// ============================================================

// --- Navigation ---
function switchTab(tabId) {
  // Update nav UI
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === tabId)
  })

  // Switch content
  document.querySelectorAll('.admin-section').forEach(sec => sec.classList.remove('active'));
  const target = document.getElementById(`${tabId}-section`)
  if (target) target.classList.add('active', 'fade-in')
}
window.switchTab = switchTab;

// --- Data Population (Fetching from Edge Function) ---
document.addEventListener('DOMContentLoaded', async () => {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) {
    window.location.href = 'index.html';
    return;
  }

  const { data: userResp } = await supabase.auth.getUser()
  const user = userResp?.user
  const { data: profileData } = await supabase.from('profiles').select('role').eq('id', user?.id).single()
  const isAdmin = profileData?.role === 'admin' || user?.email?.includes('admin')
  if (!isAdmin) {
    alert('Restricted admin area. Redirecting to your dashboard.')
    window.location.href = 'dashboard.html'
    return
  }

  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.page))
  })
  switchTab('dashboard')

  try {
    const { data, error } = await supabase.functions.invoke('admin-data');
    if (error) throw error;

    if (data.allUsers) populateUsers(data.allUsers);
    if (data.allScans) populateScans(data.allScans);
    if (data.allScans) populateGallery(data.allScans);
    if (data.allRemedies) populateCommunity(data.allRemedies);
    populateStats(data);
  } catch (err) {
    console.error("Failed to load admin data:", err);
    // fallback to mock for demonstration
    populateStats();
    populateUsers();
    populateScans();
    populateGallery();
    populateCommunity();
  }
});

function populateStats(data) {
  if (data) {
    document.getElementById('stat-users').textContent = data.allUsers?.length || 0;
    document.getElementById('stat-scans').textContent = data.allScans?.length || 0;
    
    if (data.allScans && data.allScans.length > 0) {
      const counts = data.allScans.reduce((acc, scan) => {
        acc[scan.condition] = (acc[scan.condition] || 0) + 1;
        return acc;
      }, {});
      const mostCommon = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
      document.getElementById('stat-condition').textContent = mostCommon;
    } else {
      document.getElementById('stat-condition').textContent = 'N/A';
    }
  } else {
    document.getElementById('stat-users').textContent = '1,248';
    document.getElementById('stat-scans').textContent = '84';
    document.getElementById('stat-condition').textContent = 'Dry Skin';
  }
}

function populateUsers(usersData) {
  const users = usersData || [
    { id: 'U001', name: 'Alice Smith', email: 'alice@example.com', date: '2023-10-12', scans: 5 },
    { id: 'U002', name: 'Bob Jones', email: 'bob@example.com', date: '2023-10-15', scans: 2 },
    { id: 'U003', name: 'Charlie Ray', email: 'charlie@example.com', date: '2023-11-01', scans: 14 }
  ];

  const tbody = document.getElementById('table-users');
  tbody.innerHTML = users.map(u => {
    const isReal = !!usersData;
    const id = isReal ? u.id.substring(0,6) : u.id;
    const date = isReal ? new Date(u.created_at).toLocaleDateString() : u.date;
    const scansCount = isReal ? '?' : u.scans; 

    return `
      <tr class="hover:bg-surface-container-high/30 transition-colors">
        <td class="px-6 py-4 text-on-surface-variant font-mono text-xs">#${id}</td>
        <td class="px-6 py-4 text-primary-fixed-dim font-display text-lg">${u.name || 'Unknown'}</td>
        <td class="px-6 py-4 text-on-surface-variant">${u.email || 'Protected'}</td>
        <td class="px-6 py-4 font-label text-xs uppercase tracking-widest text-on-surface-variant">${date}</td>
        <td class="px-6 py-4 font-label text-xs uppercase tracking-widest text-on-surface-variant">${scansCount}</td>
      </tr>
    `;
  }).join('');
}

function populateScans(scansData) {
  const scans = scansData || [
    { id: 'S892', user: 'Alice Smith', date: '2023-11-10 14:30', condition: 'Eczema', confidence: 89 },
    { id: 'S893', user: 'Bob Jones', date: '2023-11-10 15:15', condition: 'Clear', confidence: 95 },
    { id: 'S894', user: 'Charlie Ray', date: '2023-11-11 09:20', condition: 'Acne', confidence: 78 }
  ];

  const tbody = document.getElementById('table-scans');
  tbody.innerHTML = scans.map(s => {
    const isReal = !!scansData;
    const id = isReal ? s.id.toString().substring(0,6) : s.id;
    const userStr = isReal ? (s.profiles?.name || s.user_id?.substring(0,6) || 'Unknown') : s.user;
    const date = isReal ? new Date(s.created_at).toLocaleString() : s.date;
    
    return `
      <tr class="hover:bg-surface-container-high/30 transition-colors">
        <td class="px-6 py-4 text-on-surface-variant font-mono text-xs">#${id}</td>
        <td class="px-6 py-4 text-on-surface">${userStr}</td>
        <td class="px-6 py-4 font-label text-xs uppercase tracking-widest text-on-surface-variant">${date}</td>
        <td class="px-6 py-4"><span class="bg-primary/10 border border-primary/30 text-primary text-[10px] font-label uppercase tracking-widest px-2 py-1 rounded inline-block">${s.condition}</span></td>
        <td class="px-6 py-4 font-label text-xs uppercase tracking-widest text-on-surface-variant">${Math.round(s.confidence)}%</td>
      </tr>
    `;
  }).join('');
}

function populateGallery(scansData) {
  const grid = document.getElementById('grid-gallery');
  let html = '';

  if (scansData && scansData.length > 0) {
    const scansWithImages = scansData.filter(s => s.image_url);
    if (scansWithImages.length === 0) {
      grid.innerHTML = '<p class="text-sm text-muted" style="grid-column: 1/-1;">No images available.</p>';
      return;
    }
    html = scansWithImages.map((s, i) => `
      <div class="aspect-square rounded-lg overflow-hidden border border-white/5 bg-surface-container hover:border-primary/50 transition-colors relative group">
        <img src="${s.image_url}" alt="Scan" class="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
      </div>
    `).join('');
  } else {
    for (let i = 0; i < 12; i++) {
      html += `
        <div class="aspect-square rounded-lg border border-white/5 bg-surface-container-high/20 flex flex-col items-center justify-center border-dashed">
            <span class="material-symbols-outlined text-outline/50 mb-2">image</span>
            <span class="text-[10px] font-label uppercase tracking-widest text-on-surface-variant/50">Img ${i+1}</span>
        </div>
      `;
    }
  }
  grid.innerHTML = html;
}

function populateCommunity(commData) {
  const comm = commData || [
    { id: 'C01', condition: 'Eczema', remedy: 'Shea Butter & Zinc Oxide', count: 142 },
    { id: 'C02', condition: 'Mild Rash', remedy: 'Hydrocortisone 1%', count: 89 },
    { id: 'C03', condition: 'Dry Skin', remedy: 'Squalane Oil Nightly', count: 215 },
  ];

  const tbody = document.getElementById('table-community');
  tbody.innerHTML = comm.map(c => {
    const isReal = !!commData;
    const id = isReal ? c.id?.toString().substring(0,6) : c.id;
    return `
      <tr class="hover:bg-surface-container-high/30 transition-colors">
        <td class="px-6 py-4 text-on-surface-variant font-mono text-xs">#${id}</td>
        <td class="px-6 py-4 text-primary-fixed-dim font-display text-lg">${c.condition}</td>
        <td class="px-6 py-4 text-on-surface">${c.remedy}</td>
        <td class="px-6 py-4 font-label text-xs uppercase tracking-widest text-on-surface-variant">${c.helpful_count || c.count || 0}</td>
        <td class="px-6 py-4 flex gap-4">
          <button class="text-[10px] font-label uppercase tracking-widest text-on-surface hover:text-primary transition-colors" onclick="alert('Edit action')">Edit</button>
          <button class="text-[10px] font-label uppercase tracking-widest text-error hover:text-error/80 transition-colors" onclick="alert('Delete action')">Delete</button>
        </td>
      </tr>
    `;
  }).join('');
}
