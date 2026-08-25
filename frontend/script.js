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