// FindIt — campus selection logic
// On the homepage, the quick campus dropdown stores the choice.
// On the report forms, that stored choice pre-fills the campus dropdown.

document.addEventListener('DOMContentLoaded', () => {
  const stored = localStorage.getItem('findit_campus');

  const quickSelect = document.getElementById('campusQuickSelect');
  if (quickSelect) {
    if (stored) quickSelect.value = stored;
    quickSelect.addEventListener('change', () => {
      localStorage.setItem('findit_campus', quickSelect.value);
    });
  }

  const formSelect = document.getElementById('campus');
  if (formSelect && stored) {
    formSelect.value = stored;
  }
});

// FindIt — signup & login now talk to a JSON API (see backend/app.py),
// so these two forms are intercepted and sent as fetch() calls instead
// of a normal browser form submission. Report forms are left as plain
// multipart submissions since they include a photo file.

document.addEventListener('DOMContentLoaded', () => {
  const signupForm = document.querySelector('form[action="/api/signup"]');
  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const password = signupForm.password.value;
      const confirmPassword = signupForm.confirm_password.value;

      if (password !== confirmPassword) {
        alert('Passwords do not match.');
        return;
      }

      const payload = {
        name: signupForm.name.value,
        email: signupForm.email.value,
        phone: signupForm.phone.value,
        university_id: signupForm.university_id.value,
        campus: signupForm.campus.value,
        password: password
      };

      try {
        const res = await fetch('/api/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
          window.location.href = '/login';
        } else {
          alert(data.error || 'Signup failed. Please try again.');
        }
      } catch (err) {
        alert('Could not reach the server. Is the backend running?');
      }
    });
  }

  const loginForm = document.querySelector('form[action="/api/login"]');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        email: loginForm.email.value,
        password: loginForm.password.value
      };

      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
          window.location.href = '/';
        } else {
          alert(data.error || 'Invalid email or password.');
        }
      } catch (err) {
        alert('Could not reach the server. Is the backend running?');
      }
    });
  }
});

// FindIt — show which photo was selected, so the user gets clear
// confirmation before submitting (backend already saves it fine).

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.file-drop input[type="file"]').forEach((input) => {
    input.addEventListener('change', () => {
      const drop = input.closest('.file-drop');
      const title = drop.querySelector('.file-drop-title');
      const desc = drop.querySelector('.file-drop-desc');

      if (input.files && input.files.length > 0) {
        drop.classList.add('has-file');
        if (title) title.textContent = `Selected: ${input.files[0].name}`;
        if (desc) desc.textContent = 'Click to choose a different photo';
      } else {
        drop.classList.remove('has-file');
        if (title) title.textContent = 'Click to upload';
        if (desc) desc.textContent = drop.dataset.defaultDesc || '';
      }
    });
  });
});

// FindIt — Browse Items page: fetch /api/items and render cards,
// re-fetching whenever a filter dropdown changes.

const CATEGORY_ICON_PATHS = {
  'Electronics': '<rect x="7" y="2" width="10" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18"/>',
  'Bag / Backpack': '<path d="M6 8a6 6 0 0 1 12 0v11a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/><rect x="9" y="12" width="6" height="4" rx="1"/>',
  'ID / Cards': '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="11" r="2"/><path d="M6 16c.5-1.5 1.8-2 3-2s2.5.5 3 2"/><line x1="14" y1="9" x2="18" y2="9"/><line x1="14" y1="13" x2="18" y2="13"/>',
  'Keys': '<circle cx="8" cy="8" r="4"/><path d="M10.8 10.8 20 20"/><path d="M16 16l3 3"/><path d="M13.5 13.5l2.5 2.5"/>',
  'Water Bottle': '<path d="M9 2h6"/><path d="M10 2v3.5L8 8v12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V8l-2-2.5V2"/>',
  'Clothing': '<path d="M8 4 4 7l2 3 2-1.5V20h8V8.5L18 10l2-3-4-3-2 2h-4Z"/>',
  'Other': '<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>'
};

function categoryIconSvg(category) {
  const path = CATEGORY_ICON_PATHS[category] || CATEGORY_ICON_PATHS['Other'];
  return `<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
}

function timeAgo(dateString) {
  if (!dateString) return '';
  const then = new Date(dateString);
  const seconds = Math.floor((Date.now() - then.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

async function loadItems() {
  const grid = document.getElementById('itemsGrid');
  const status = document.getElementById('itemsStatus');
  if (!grid) return;

  const type = document.getElementById('filterType').value;
  const campus = document.getElementById('filterCampus').value;
  const category = document.getElementById('filterCategory').value;

  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (campus) params.set('campus', campus);
  if (category) params.set('category', category);

  status.textContent = 'Loading items…';
  grid.innerHTML = '';

  try {
    const res = await fetch(`/api/items?${params.toString()}`);
    const items = await res.json();

    if (!Array.isArray(items) || items.length === 0) {
      status.textContent = 'No items match these filters yet.';
      return;
    }

    status.textContent = '';
    items.forEach((item) => {
      const badgeClass = item.type === 'found' ? 'found' : 'lost';
      const badgeLabel = item.type === 'found' ? 'Found' : 'Lost';
      const card = document.createElement('article');
      card.className = 'item-card';
      card.innerHTML = `
        <div class="item-thumb">
          <span class="item-badge ${badgeClass}">${badgeLabel}</span>
          ${categoryIconSvg(item.category)}
        </div>
        <div class="item-body">
          <h4>${item.title}</h4>
          <div class="item-meta"><span>${item.campus || ''}</span><span>${timeAgo(item.created_at)}</span></div>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    status.textContent = 'Could not load items. Is the backend running?';
  }
}

const itemsGridEl = document.getElementById('itemsGrid');
if (itemsGridEl) {
  document.addEventListener('DOMContentLoaded', () => {
    loadItems();
    ['filterType', 'filterCampus', 'filterCategory'].forEach((id) => {
      document.getElementById(id).addEventListener('change', loadItems);
    });
  });
}

// FindIt — Notifications page: fetch /api/my-notifications and render.

const NOTIF_MESSAGES = {
  match_found: { title: 'Possible match found', text: 'Someone reported an item that looks similar to yours. Log in to review it.' },
  reminder: { title: 'Reminder', text: 'You have an open report that might need an update.' }
};

async function loadNotifications() {
  const list = document.getElementById('notifList');
  const status = document.getElementById('notifStatus');
  if (!list) return;

  try {
    const res = await fetch('/api/my-notifications', { credentials: 'same-origin' });

    if (res.status === 401) {
      window.location.href = '/login';
      return;
    }

    const notifications = await res.json();

    if (!Array.isArray(notifications) || notifications.length === 0) {
      status.textContent = "You're all caught up — no notifications yet.";
      return;
    }

    status.textContent = '';
    notifications.forEach((n) => {
      const info = NOTIF_MESSAGES[n.type] || { title: 'Notification', text: 'You have a new update.' };
      const card = document.createElement('div');
      card.className = 'notif-card' + (n.is_read ? '' : ' unread');
      card.innerHTML = `
        <span class="notif-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>
        </span>
        <div class="notif-body">
          <h4>${info.title}</h4>
          <p>${info.text}</p>
          <div class="notif-time">${timeAgo(n.sent_at)}</div>
        </div>
      `;
      list.appendChild(card);
    });
  } catch (err) {
    status.textContent = 'Could not load notifications. Is the backend running?';
  }
}

if (document.getElementById('notifList')) {
  document.addEventListener('DOMContentLoaded', loadNotifications);
}
document.addEventListener("DOMContentLoaded", function() {
    // Sirf navbar ke login button ko target karein
    const loginBtn = document.getElementById("nav-login-btn");
    
    if (loginBtn) {
        fetch('/api/me')
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Not logged in');
        })
        .then(data => {
            // Agar user logged in hai, toh button ko Naam aur Logout se replace kar do
            loginBtn.outerHTML = `
                <div style="display: inline-flex; align-items: center; gap: 15px;">
                    <span style="font-weight: bold; color: #333;">Hi, ${data.name}</span>
                    <a href="#" onclick="logoutUser()" style="color: red; text-decoration: none;">Logout</a>
                </div>
            `;
        })
        .catch(error => {
            // User login nahi hai, as it is chhor do
            console.log("Guest user");
        });
    }
});

// Logout ka function
function logoutUser() {
    fetch('/api/logout', { method: 'POST' })
    .then(() => {
        window.location.href = '/'; // Home page par wapis bhej dein
    });
}