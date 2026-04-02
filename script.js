document.addEventListener('DOMContentLoaded', () => {

  /* ── Splash screen ── */
  const splash  = document.getElementById('splash');
  const mainApp = document.getElementById('mainApp');

  setTimeout(() => {
    splash.classList.add('fade-out');
    setTimeout(() => {
      splash.style.display = 'none';
      mainApp.classList.remove('hidden');
    }, 650);
  }, 1800);

  /* ── Theme toggle ── */
  const themeToggle = document.getElementById('themeToggle');
  const themeIcon   = document.getElementById('themeIcon');

  const logoLight = 'assets/logo_light.png';
  const logoDark  = 'assets/logo_dark.png';

  const logoImages = () => document.querySelectorAll(
    '#splashLogo, #sidebarLogo, #editProfileImg, #widgetLogo'
  );

  let isDark = false;

  themeToggle.addEventListener('click', () => {
    isDark = !isDark;
    document.body.classList.toggle('dark', isDark);
    themeIcon.textContent = isDark ? '☀' : '☾';

    const src = isDark ? logoDark : logoLight;
    logoImages().forEach(img => { if (img) img.src = src; });
  });

});

/* ── Page navigation ── */
function navigate(page) {
  // hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

  // show target
  const target = document.getElementById('page-' + page);
  if (target) target.classList.add('active');

  // mark current page in sidebar (greyed out)
  document.querySelectorAll('.nav-link, .help-link').forEach(link => {
    link.classList.remove('current-page');
    if (link.dataset.page === page) link.classList.add('current-page');
  });

  // scroll content to top
  const content = document.querySelector('.content');
  if (content) content.scrollTop = 0;
}

/* ── Tab switching ── */
function switchTab(btn, tabId) {
  const page = btn.closest('.page');

  page.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  page.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

  btn.classList.add('active');
  const pane = document.getElementById('tab-' + tabId);
  if (pane) pane.classList.add('active');
}
