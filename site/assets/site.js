(function () {
  'use strict';
  const config = window.MALHAEBOM_CONFIG || {};
  const themeKey = 'malhaebom-intro-theme';
  const root = document.documentElement;
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const themeControls = Array.from(document.querySelectorAll('[data-theme-toggle]'));
  let currentTheme = 'system';

  try {
    const saved = localStorage.getItem(themeKey);
    if (['light','dark','system'].includes(saved)) currentTheme = saved;
  } catch (_e) {}

  function updateTheme() {
    const actual = currentTheme === 'system' ? (mediaQuery.matches ? 'dark' : 'light') : currentTheme;
    root.dataset.theme = actual;
    root.dataset.themePreference = currentTheme;
    themeControls.forEach(el => {
      const labels = { light: '밝은 테마', dark: '어두운 테마', system: '시스템 테마' };
      el.setAttribute('aria-label', `현재 ${labels[currentTheme]}. 클릭하여 테마 변경`);
      el.setAttribute('title', `테마: ${labels[currentTheme]}`);
      const status = el.querySelector('[data-theme-label]');
      if (status) status.textContent = { light: '라이트', dark: '다크', system: '시스템' }[currentTheme];
    });
  }
  updateTheme();
  themeControls.forEach(el => el.addEventListener('click', () => {
    const values = ['system','light','dark'];
    currentTheme = values[(values.indexOf(currentTheme)+1)%values.length];
    try { localStorage.setItem(themeKey,currentTheme); } catch (_e) {}
    updateTheme();
  }));
  if (mediaQuery.addEventListener) mediaQuery.addEventListener('change', updateTheme);

  const menuToggle = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-main-nav]');
  if (menuToggle && nav) {
    menuToggle.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      menuToggle.setAttribute('aria-expanded', String(open));
      menuToggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
    });
    nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
      nav.classList.remove('is-open');
      menuToggle.setAttribute('aria-expanded','false');
    }));
  }

  const dialog = document.querySelector('[data-link-dialog]');
  const openDialog = () => {
    if (dialog && typeof dialog.showModal === 'function') dialog.showModal();
    else alert('실제 서비스 링크를 연결하기 전입니다. 배포 담당자에게 서비스 URL 등록을 요청해 주세요.');
  };
  document.querySelectorAll('[data-service-link]').forEach(el => {
    if (config.serviceUrl && /^https?:\/\//i.test(config.serviceUrl)) {
      el.setAttribute('href',config.serviceUrl);
      el.setAttribute('target','_blank');
      el.setAttribute('rel','noopener noreferrer');
    } else {
      el.setAttribute('href','#start');
      el.addEventListener('click', event => {
        event.preventDefault();
        openDialog();
      });
    }
  });
  if (dialog) {
    dialog.querySelectorAll('[data-close-dialog]').forEach(b => b.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  }
  document.querySelectorAll('[data-repo-link]').forEach(el => {
    if (config.projectRepoUrl && /^https?:\/\//i.test(config.projectRepoUrl)) {
      el.href = config.projectRepoUrl;
      el.target = '_blank';
      el.rel = 'noopener noreferrer';
    } else {
      el.hidden = true;
    }
  });

  // Reveal effects are optional and disabled for reduced motion preferences.
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const targets = document.querySelectorAll('.reveal');
    document.documentElement.classList.add('motion-ready');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.09, rootMargin: '0px 0px -32px 0px' });
    targets.forEach(el => observer.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in-view'));
  }

  // Header state and scroll-to-top affordance.
  const header = document.querySelector('.site-header');
  const toTop = document.querySelector('[data-back-to-top]');
  const onScroll = () => {
    if (header) header.classList.toggle('is-scrolled', window.scrollY > 12);
    if (toTop) toTop.classList.toggle('is-visible', window.scrollY > 650);
  };
  window.addEventListener('scroll', onScroll, {passive:true});
  onScroll();
  if (toTop) toTop.addEventListener('click', () => window.scrollTo({top:0,behavior:'smooth'}));
})();
