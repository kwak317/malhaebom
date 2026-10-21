(function () {
  'use strict';
  const query = new URLSearchParams(window.location.search);
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  const failed = query.has('error') || fragment.has('error');
  if (!query.has('code') && !fragment.has('access_token') && !failed) return;
  let destination = 'practice';
  try {
    if (sessionStorage.getItem('malhaebom-login-destination') === 'home') destination = 'home';
    sessionStorage.removeItem('malhaebom-login-destination');
  } catch (_error) {}
  const path = destination === 'practice' ? '/app/practice' : failed ? '/app/auth' : '/app/';
  window.location.replace(path + window.location.search + window.location.hash);
})();
