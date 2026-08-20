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