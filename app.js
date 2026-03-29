import { supabase } from './supabase.js'

// ============================================================
// AUTHENTICATION LOGIC
// ============================================================

// REGISTER
async function register(email, password, name) {
  const { data, error } = await supabase.auth.signUp({ email, password })
  if (!error && data.user) {
    await supabase.from('profiles').insert({ id: data.user.id, name })
  }
  return { data, error }
}

// LOGIN
async function login(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  return { data, error }
}

// LOGOUT
async function logout() {
  await supabase.auth.signOut()
  window.location.href = 'index.html'
}

// CHECK SESSION
try {
  const { data: { session } } = await supabase.auth.getSession()
  const isDashboard = window.location.pathname.includes('dashboard.html');
  if (!session && isDashboard) {
    window.location.href = 'index.html';
  } else if (session && (window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/'))) {
    window.location.href = 'dashboard.html';
  }
} catch (e) {
  console.error("Supabase session check failed (likely needs URL configuration):", e);
}

const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const loginView = document.getElementById('login-view');
const registerView = document.getElementById('register-view');

// Toggle between Login and Register views
function toggleAuth(view) {
  if (!loginView || !registerView) return;

  if (view === 'register') {
    loginView.classList.add('hidden-auth');
    registerView.classList.remove('hidden-auth');
  } else {
    registerView.classList.add('hidden-auth');
    loginView.classList.remove('hidden-auth');
  }
}
window.toggleAuth = toggleAuth; // Expose for inline HTML handler

// Handle Form Submissions (Mock Auth -> Real Auth)
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const pw = document.getElementById('login-password').value;
    
    try {
      const { data, error } = await login(email, pw);
      if (error) {
        alert("Login failed: " + error.message);
        return;
      }
      window.location.href = 'dashboard.html';
    } catch (err) {
      console.error(err);
      alert("System error. Have you configured supabase.js? " + err.message);
    }
  });
}

if (registerForm) {
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const pw = document.getElementById('reg-password').value;

    try {
      const { data, error } = await register(email, pw, name);
      if (error) {
        alert("Registration failed: " + error.message);
        return;
      }
      window.location.href = 'dashboard.html';
    } catch (err) {
      console.error(err);
      alert("System error. Have you configured supabase.js? " + err.message);
    }
  });
}

// ============================================================
// DASHBOARD LOGIC
// ============================================================

// --- User Info Init ---
async function initDashboard() {
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      const { data: profile } = await supabase.from('profiles').select('name').eq('id', user.id).single();
      const displayName = profile?.name || user.email;
      
      const navUser = document.getElementById('navbar-username');
      const sideUser = document.getElementById('sidebar-username');
      if (navUser) navUser.textContent = displayName;
      if (sideUser) sideUser.textContent = displayName;
    }
  } catch (e) {
    console.error("Dashboard user init failed:", e);
  }
}

window.logout = logout; // Expose for inline HTML handler

if (window.location.pathname.includes('dashboard.html')) {
  initDashboard();
}

// ============================================================
// FACE SCANNER & ML MOCK
// ============================================================
const videoFeed = document.getElementById('video-feed');
const scannerWrapper = document.getElementById('scanner-wrapper');
const scanBtn = document.getElementById('scan-btn');
const resultsPanel = document.getElementById('results-panel');
let mediaStream = null;

// Start Webcam
async function initCamera() {
  if (!videoFeed) return;
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
    videoFeed.srcObject = mediaStream;
  } catch (err) {
    console.error("Camera access denied:", err);
    // show fallback
  }
}

if (videoFeed) {
  initCamera();
}

// ------------------------------------------------------------
// ML MODEL INTEGRATION — CONNECT HERE
// ------------------------------------------------------------

function dataURLtoFile(dataurl, filename) {
  var arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1],
      bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n);
  while(n--){
      u8arr[n] = bstr.charCodeAt(n);
  }
  return new File([u8arr], filename, {type:mime});
}

async function saveScan(imageFile, mlResult) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Not logged in' }

  // 1. Upload image to storage
  const fileName = `${user.id}/${Date.now()}.jpg`
  const { data: uploadData, error: uploadError } = await supabase.storage
    .from('scan-images')
    .upload(fileName, imageFile)

  if (uploadError) return { error: uploadError }

  const imageUrl = supabase.storage
    .from('scan-images')
    .getPublicUrl(fileName).data.publicUrl

  // 2. Save scan result to DB
  const { data, error } = await supabase.from('scans').insert({
    user_id: user.id,
    condition: mlResult.condition,
    severity: mlResult.severity,
    confidence: mlResult.confidence,
    image_url: imageUrl
  })

  return { data, error }
}

async function getUserHistory() {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return []
  
  const { data, error } = await supabase
    .from('scans')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
  return data
}

function startScan() {
  if (!scannerWrapper || !scanBtn) return;

  // Start animation
  scannerWrapper.classList.add('scanning-active');
  scanBtn.disabled = true;
  scanBtn.textContent = 'Scanning...';

  // Capture Frame
  const canvas = document.createElement('canvas');
  canvas.width = videoFeed.videoWidth || 400;
  canvas.height = videoFeed.videoHeight || 500;
  const ctx = canvas.getContext('2d');

  // Mirror canvas draw text
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);

  const frameData = canvas.toDataURL('image/jpeg');

  // Convert data URL to blob
  canvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append('file', blob, 'scan.jpg');

    try {
      // Call the API
      const response = await fetch('http://localhost:8002/predict', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('API call failed');
      }

      const result = await response.json();

      // Transform API result to match expected format
      const mockResult = {
        condition: result.advice.title,
        severity: result.severity || 'Unknown',
        confidence: result.confidence || 85,
        remedies: result.remedies || [
          { title: 'Consult Professional', desc: result.advice.advice }
        ],
        products: result.products || [
          { name: 'Recommended Product', use: 'Personalized care', ingredient: 'Consult specialist' }
        ]
      };

      // Save scan to DB silently
      const file = dataURLtoFile(frameData, `scan_${Date.now()}.jpg`);
      await saveScan(file, mockResult);

      // Process Result
      displayResults(frameData, mockResult);

    } catch (error) {
      console.error('Scan failed:', error);
      // Fallback to mock data
      const fallbackResult = {
        condition: 'Analysis Error',
        severity: 'Unknown',
        confidence: 0,
        remedies: [
          { title: 'Please try again', desc: 'There was an error analyzing your skin.' }
        ],
        products: [
          { name: 'Consult Dermatologist', use: 'Professional advice', ingredient: 'Expert care' }
        ]
      };
      displayResults(frameData, fallbackResult);
    } finally {
      scannerWrapper.classList.remove('scanning-active');
      scanBtn.disabled = false;
      scanBtn.textContent = 'Scan Again';
    }
  }, 'image/jpeg');
}
window.startScan = startScan; // Expose to window

function displayResults(imageData, mockResult) {
  if (!resultsPanel) return;
  
  // Remove Mock ML Data definition as we're passing it from startScan
  // Populate UI
  document.getElementById('result-img').src = imageData;
  document.getElementById('condition-name').textContent = mockResult.condition;
  
  const badge = document.getElementById('severity-badge');
  badge.textContent = `${mockResult.severity} Severity`;
  badge.className = `severity-badge severity-${mockResult.severity.toLowerCase()}`;
  
  document.getElementById('confidence-fill').style.width = '0%';
  setTimeout(() => {
    document.getElementById('confidence-fill').style.width = `${mockResult.confidence}%`;
  }, 300); // trigger animation

  // Populate Remedies
  const remedyList = document.getElementById('remedy-list');
  remedyList.innerHTML = mockResult.remedies.map(r => `
    <div class="bg-surface-container-high/40 p-4 rounded border border-white/5 flex flex-col gap-1">
      <h4 class="text-on-surface font-display text-lg">${r.title}</h4>
      <p class="text-on-surface-variant text-sm">${r.desc}</p>
    </div>
  `).join('');

  // Populate Products
  const productList = document.getElementById('product-list');
  productList.innerHTML = mockResult.products.map(p => `
    <div class="bg-surface-container p-4 rounded border border-white/5 flex flex-col gap-1">
      <h4 class="text-primary-fixed-dim font-display text-lg">${p.name}</h4>
      <p class="text-on-surface-variant font-light text-sm mb-2">${p.use}</p>
      <span class="inline-block text-[10px] font-label tracking-widest uppercase bg-primary/10 text-primary border border-primary/20 px-2 py-1 rounded w-fit">${p.ingredient}</span>
    </div>
  `).join('');

  resultsPanel.classList.remove('hidden');

  // Load Community Suggestions after scan
  loadCommunitySuggestions();
}

// ============================================================
// COMMUNITY SUGGESTIONS
// ============================================================
function loadCommunitySuggestions() {
  const commList = document.getElementById('community-list');
  if (!commList) return;

  // [DATABASE READ — LEAVE EMPTY]
  // ... fetch community remedies ...

  const mockCommunity = [
    { condition: 'Eczema', remedy: 'Shea Butter & Zinc Oxide', count: 142 },
    { condition: 'Mild Rash', remedy: 'Hydrocortisone 1%', count: 89 },
    { condition: 'Dry Skin', remedy: 'Squalane Oil Nightly', count: 215 }
  ];

  commList.innerHTML = mockCommunity.map(item => `
    <div class="remedy-card">
      <div>
        <span class="skin-tag" style="background:var(--color-accent); margin-bottom:0.5rem;">${item.condition}</span>
        <p style="font-weight: 500;">${item.remedy}</p>
      </div>
      <div class="text-sm text-muted flex items-center gap-1">
        <span>👍</span> Helped ${item.count} users
      </div>
    </div>
  `).join('');
}

// ============================================================
// CHATBOT LOGIC
// ============================================================
let isChatOpen = false;
function toggleChatbot() {
  const panel = document.getElementById('chatbot-panel');
  if (!panel) return;
  
  isChatOpen = !isChatOpen;
  if (isChatOpen) {
    panel.classList.add('active');
  } else {
    panel.classList.remove('active');
  }
}

const botResponses = {
  'What skin type do I have?': 'Based on your profile, you have Combination Skin. This means some areas (like your T-zone) may be oily, while cheeks might be dry.',
  'Is my rash serious?': 'I can only provide general guidance. If your rash is spreading rapidly, painful, or accompanied by a fever, please consult a doctor immediately.',
  'What ingredients should I avoid?': 'For eczema or sensitive skin, avoid artificial fragrances, strong exfoliants (like high % AHA/BHA), and drying alcohols.',
  'How often should I moisturize?': 'Twice daily is standard. However, for conditions like eczema, moisturize immediately after bathing while skin is still damp.',
  'When should I see a doctor?': 'See a doctor if symptoms persist longer than 2 weeks, worsen suddenly, or if over-the-counter methods show no improvement.',
  'What does my scan result mean?': 'Your scan detected potential signs of a skin condition. The confidence score shows how certain our AI is. Please review the suggested products and consult an expert if needed.'
};

function askQuestion(question) {
  const chatBody = document.getElementById('chat-body');
  if (!chatBody) return;

  // Add User message
  const userMsg = document.createElement('div');
  userMsg.className = 'chat-msg msg-user animate-slide-up';
  userMsg.textContent = question;
  chatBody.appendChild(userMsg);

  // Scroll
  chatBody.scrollTop = chatBody.scrollHeight;

  // Add typing indicator
  const typing = document.createElement('div');
  typing.className = 'chat-msg msg-bot typing-indicator';
  typing.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
  chatBody.appendChild(typing);
  chatBody.scrollTop = chatBody.scrollHeight;

  // Call API for bot response
  fetch('http://localhost:8002/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: question })
  })
  .then(response => response.json())
  .then(data => {
    chatBody.removeChild(typing);

    const botMsg = document.createElement('div');
    botMsg.className = 'chat-msg msg-bot animate-slide-up';
    botMsg.textContent = data.response || "I'm still learning and don't know the answer to that yet!";
    chatBody.appendChild(botMsg);

    chatBody.scrollTop = chatBody.scrollHeight;
  })
  .catch(error => {
    console.error('Chat API error:', error);
    chatBody.removeChild(typing);

    const botMsg = document.createElement('div');
    botMsg.className = 'chat-msg msg-bot animate-slide-up';
    botMsg.textContent = "Sorry, I'm having trouble connecting right now. Please try again later.";
    chatBody.appendChild(botMsg);

    chatBody.scrollTop = chatBody.scrollHeight;
  });
}

// ============================================================
// ACTIONS
// ============================================================
function bookDoctor() {
  // [BOOKING API — LEAVE EMPTY]
  alert("Booking interface would open here. API Connection placeholder.");
}
window.bookDoctor = bookDoctor;
window.toggleChatbot = toggleChatbot;
window.askQuestion = askQuestion;

// ============================================================
// ANIMATIONS (GSAP)
// ============================================================

// Dashboard entrance animations
function initDashboardAnimations() {
  // Sidebar slides in from left
  gsap.from('#left-sidebar', {
    x: -300, opacity: 0, duration: 0.8,
    ease: 'power3.out', delay: 0.2
  });

  // Right sidebar slides in from right
  gsap.from('#right-sidebar', {
    x: 300, opacity: 0, duration: 0.8,
    ease: 'power3.out', delay: 0.3
  });

  // Nav slides down
  gsap.from('#top-nav', {
    y: -80, opacity: 0, duration: 0.6,
    ease: 'power3.out'
  });

  // Main content fades up
  gsap.from('#main-content', {
    y: 40, opacity: 0, duration: 0.8,
    ease: 'power3.out', delay: 0.4
  });

  // Doctor cards stagger in
  gsap.from('.doctor-card', {
    y: 30, opacity: 0, duration: 0.5,
    stagger: 0.12, ease: 'power2.out', delay: 0.6
  });

  // Nav items stagger in
  gsap.from('.nav-item', {
    x: -20, opacity: 0, duration: 0.4,
    stagger: 0.08, ease: 'power2.out', delay: 0.5
  });
}

// Scan button hover animation
if (scanBtn) {
  scanBtn.addEventListener('mouseenter', () => {
    gsap.to('.btn-rings span', {
      scale: 3, opacity: 0, duration: 1,
      stagger: 0.2, ease: 'power2.out'
    });
  });
}

// Enhanced start scan animation
function startScan() {
  if (!scannerWrapper || !scanBtn) return;

  // Start animation
  scannerWrapper.classList.add('scanning-active');
  scanBtn.disabled = true;
  scanBtn.textContent = 'Scanning...';

  // GSAP animations
  gsap.to('#scanner-frame', {
    boxShadow: '0 0 60px rgba(196,168,130,0.4)',
    duration: 0.5
  });
  gsap.to('.corner-bracket', {
    borderColor: '#F5E6D3',
    duration: 0.3,
    stagger: 0.05
  });

  // Capture Frame
  const canvas = document.createElement('canvas');
  canvas.width = videoFeed.videoWidth || 400;
  canvas.height = videoFeed.videoHeight || 500;
  const ctx = canvas.getContext('2d');

  // Mirror canvas draw text
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);

  const frameData = canvas.toDataURL('image/jpeg');

  // Simulate API delay
  setTimeout(async () => {
    scannerWrapper.classList.remove('scanning-active');
    scanBtn.disabled = false;
    scanBtn.textContent = 'Scan Again';

    // Mock ML Data (to simulate the API output)
    const mockResult = {
      condition: 'Mild Eczema',
      severity: 'Medium',
      confidence: 87, // percentage
      remedies: [
        { title: 'Oatmeal Bath', desc: 'Soothes inflammation and itching.' },
        { title: 'Cold Compress', desc: 'Reduces redness temporarily.' },
        { title: 'Aloe Vera', desc: 'Applies cooling hydration.' }
      ],
      products: [
        { name: 'Ceramide Rich Cream', use: 'Barrier repair', ingredient: 'Ceramides' },
        { name: 'Gentle Hydrating Cleanser', use: 'Daily wash', ingredient: 'Hyaluronic Acid' },
        { name: 'Colloidal Oatmeal Lotion', use: 'Itch relief', ingredient: 'Oat Extract' }
      ]
    };

    // Save scan to DB silently
    const file = dataURLtoFile(frameData, `scan_${Date.now()}.jpg`);
    await saveScan(file, mockResult);

    // Process Mock Result
    displayResults(frameData, mockResult);
  }, 2500);
}

// ============================================================
// AUTH PANEL FUNCTIONS
// ============================================================

// Auth panel functionality
let isSignUp = false;

function toggleAuthMode() {
  isSignUp = !isSignUp;
  const formTitle = document.getElementById('auth-form-title');
  const formSubtitle = document.getElementById('auth-form-subtitle');
  const nameGroup = document.getElementById('name-group');
  const submitBtn = document.getElementById('auth-submit-btn');
  const toggleText = document.getElementById('auth-toggle-text');
  const toggleLink = document.getElementById('auth-toggle-link');

  if (isSignUp) {
    formTitle.textContent = 'Create Account';
    formSubtitle.textContent = 'Join thousands discovering their best skin';
    nameGroup.style.display = 'block';
    submitBtn.querySelector('.btn-text').textContent = 'Create Account';
    toggleText.innerHTML = 'Already have an account? <a href="#" id="auth-toggle-link">Sign in</a>';
  } else {
    formTitle.textContent = 'Sign In';
    formSubtitle.textContent = 'Enter your credentials to continue';
    nameGroup.style.display = 'none';
    submitBtn.querySelector('.btn-text').textContent = 'Sign In';
    toggleText.innerHTML = 'Don\'t have an account? <a href="#" id="auth-toggle-link">Create one</a>';
  }

  // Reattach event listener
  document.getElementById('auth-toggle-link').addEventListener('click', (e) => {
    e.preventDefault();
    toggleAuthMode();
  });
}

async function handleAuthSubmit(e) {
  e.preventDefault();

  const email = document.getElementById('auth-email').value;
  const password = document.getElementById('auth-password').value;
  const name = document.getElementById('auth-name').value;
  const submitBtn = document.getElementById('auth-submit-btn');
  const btnText = submitBtn.querySelector('.btn-text');
  const spinner = submitBtn.querySelector('.btn-spinner');
  const messageDiv = document.getElementById('auth-message');

  // Show loading state
  submitBtn.disabled = true;
  btnText.style.display = 'none';
  spinner.style.display = 'block';
  messageDiv.textContent = '';

  try {
    let result;
    if (isSignUp) {
      result = await register(email, password, name);
    } else {
      result = await login(email, password);
    }

    if (result.error) {
      throw result.error;
    }

    // Success - redirect to dashboard
    messageDiv.textContent = 'Success! Redirecting...';
    messageDiv.className = 'auth-message success';
    setTimeout(() => {
      window.location.href = 'dashboard.html';
    }, 1000);

  } catch (error) {
    messageDiv.textContent = error.message || 'An error occurred';
    messageDiv.className = 'auth-message error';
  } finally {
    // Reset loading state
    submitBtn.disabled = false;
    btnText.style.display = 'block';
    spinner.style.display = 'none';
  }
}

// Initialize auth panel
function initAuthPanel() {
  const toggleLink = document.getElementById('auth-toggle-link');
  const authForm = document.getElementById('auth-form');

  if (toggleLink) {
    toggleLink.addEventListener('click', (e) => {
      e.preventDefault();
      toggleAuthMode();
    });
  }

  if (authForm) {
    authForm.addEventListener('submit', handleAuthSubmit);
  }
}

// Enhanced results display with animation
function displayResults(imageData, mockResult) {
  if (!resultsPanel) return;

// ============================================================
// HERO ANIMATIONS
// ============================================================

// Register GSAP plugins
gsap.registerPlugin(TextPlugin);

// Hero animation sequence
function playHeroAnimation() {
  const tl = gsap.timeline({ delay: 0.5 });

  // Navbar fade in
  tl.to('#site-nav', { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' });

  // Badge animation
  tl.to('#anim-badge', { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out' }, '-=0.4');

  // Heading animation
  tl.to('#hero-heading', { opacity: 1, y: 0, duration: 0.9, ease: 'power3.out' }, '-=0.5');

  // Description animation
  tl.to('#hero-desc', { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out' }, '-=0.6');

  // CTA block animation
  tl.to('#hero-cta-block', { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out' }, '-=0.5');

  // OR divider and signin link
  tl.to('#anim-or', { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }, '-=0.3');
  tl.to('#anim-signin', { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }, '-=0.3');

  // Finger animation sequence
  tl.to('#finger', {
    x: '60vw',
    y: '20vh',
    rotation: 15,
    duration: 1.5,
    ease: 'power2.inOut'
  }, '-=0.5');

  // Text animation on finger
  tl.to('#finger-text', {
    text: "Tap to scan your skin",
    duration: 1.2,
    ease: 'power2.out'
  }, '-=1.0');

  // Pulse effect on finger
  tl.to('#finger', {
    scale: 1.1,
    duration: 0.3,
    yoyo: true,
    repeat: 3,
    ease: 'power2.inOut'
  }, '-=0.8');

  return tl;
}

// Enter app function
function enterApp() {
  const tl = gsap.timeline();

  // Hide hero elements
  tl.to(['#hero-content', '#finger', '#finger-text'], {
    opacity: 0,
    y: -50,
    duration: 0.8,
    ease: 'power3.in'
  });

  // Show auth panel
  tl.to('#auth-panel', {
    opacity: 1,
    y: 0,
    duration: 1.0,
    ease: 'power3.out'
  }, '-=0.3');

  return tl;
}

// Initialize hero animations on index.html
if (window.location.pathname.includes('index.html') || window.location.pathname.endsWith('/')) {
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize particles
    initParticles();

    // Initialize auth panel
    initAuthPanel();

    // Start hero animation
    playHeroAnimation();

    // Add click handler for CTA button
    const ctaBtn = document.querySelector('.cta-btn');
    if (ctaBtn) {
      ctaBtn.addEventListener('click', enterApp);
    }

    // Add click handler for signin link
    const signinLink = document.querySelector('.signin-link a');
    if (signinLink) {
      signinLink.addEventListener('click', enterApp);
    }
  });
}

  // Populate UI
  document.getElementById('result-img').src = imageData;
  document.getElementById('condition-name').textContent = mockResult.condition;

  const badge = document.getElementById('severity-badge');
  badge.textContent = `${mockResult.severity} Severity`;
  badge.className = `severity-badge severity-${mockResult.severity.toLowerCase()}`;

  document.getElementById('confidence-fill').style.width = '0%';
  setTimeout(() => {
    document.getElementById('confidence-fill').style.width = `${mockResult.confidence}%`;
  }, 300); // trigger animation

  // Populate Remedies
  const remedyList = document.getElementById('remedy-list');
  remedyList.innerHTML = mockResult.remedies.map(r => `
    <div class="bg-surface-container-high/40 p-4 rounded border border-white/5 flex flex-col gap-1">
      <h4 class="text-on-surface font-display text-lg">${r.title}</h4>
      <p class="text-on-surface-variant text-sm">${r.desc}</p>
    </div>
  `).join('');

  // Populate Products
  const productList = document.getElementById('product-list');
  productList.innerHTML = mockResult.products.map(p => `
    <div class="bg-surface-container p-4 rounded border border-white/5 flex flex-col gap-1">
      <h4 class="text-primary-fixed-dim font-display text-lg">${p.name}</h4>
      <p class="text-on-surface-variant font-light text-sm mb-2">${p.use}</p>
      <span class="inline-block text-[10px] font-label tracking-widest uppercase bg-primary/10 text-primary border border-primary/20 px-2 py-1 rounded w-fit">${p.ingredient}</span>
    </div>
  `).join('');

  // Animate results panel in
  resultsPanel.style.display = 'block';
  gsap.from(resultsPanel, {
    y: 60, opacity: 0, duration: 0.8,
    ease: 'back.out(1.7)'
  });

  // Load Community Suggestions after scan
  loadCommunitySuggestions();
}

// Initialize animations on dashboard load
if (window.location.pathname.includes('dashboard.html')) {
  // Wait for DOM to be ready
  document.addEventListener('DOMContentLoaded', () => {
    initDashboardAnimations();
  });
}

// Initial calls
if (window.location.pathname.includes('dashboard.html')) {
  getUserHistory().then(data => {
    const historyContainer = document.getElementById('scan-history');
    if (!historyContainer) return;
    
    if (!data || data.length === 0) {
      historyContainer.innerHTML = '<p class="text-center italic opacity-50 py-4">No scanning rituals recorded yet.</p>';
      return;
    }

    historyContainer.innerHTML = data.map(scan => {
      const date = new Date(scan.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      return `
        <div class="flex items-center gap-4 bg-surface-container p-4 rounded border border-white/5">
          <img src="${scan.image_url}" class="w-12 h-12 object-cover rounded opacity-80 border border-primary/20" />
          <div class="flex-1">
            <h5 class="font-display text-lg text-primary-fixed-dim">${scan.condition || 'General Analysis'}</h5>
            <p class="text-[10px] font-label tracking-widest uppercase text-on-surface-variant">${date}</p>
          </div>
          <span class="text-xs font-label uppercase px-2 py-1 bg-surface rounded text-primary border border-primary/30">${scan.confidence}% Match</span>
        </div>
      `;
    }).join('');
  });
}
