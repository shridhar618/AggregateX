/* Isolated legacy processing engines. Every request still passes session auth. */
(() => {
  const params = new URLSearchParams(location.search);
  const id = params.get('case');
  if (/^[a-f0-9]{32}$/.test(id)) localStorage.setItem('witnesstrace-case', id);
  const originalFetch = window.fetch.bind(window);
  const path = value => typeof value === 'string' && /^\/(api|images|static)\//.test(value) ? '/wt-api' + value : value;
  const translate = value => {
    if (typeof value === 'string') return path(value);
    if (Array.isArray(value)) return value.map(translate);
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k,v]) => [k,translate(v)]));
    return value;
  };
  window.fetch = async (input, options) => {
    const response = await originalFetch(path(input), options);
    if (response.headers.get('content-type')?.includes('application/json')) {
      const json = response.json.bind(response);
      response.json = async () => translate(await json());
    }
    if (options?.method && options.method !== 'GET' && response.ok) parent.postMessage({type:'witness-saved',caseId:id}, location.origin);
    return response;
  };
  addEventListener('DOMContentLoaded', () => {
    document.documentElement.dataset.tool = params.get('tool') || 'sketch';
    const syncTheme = () => { document.documentElement.dataset.theme = parent.document.documentElement.dataset.theme || params.get('theme') || 'dark'; };
    syncTheme();
    const themeObserver = new MutationObserver(syncTheme);
    themeObserver.observe(parent.document.documentElement, {attributes:true, attributeFilter:['data-theme']});
    addEventListener('pagehide', () => themeObserver.disconnect(), {once:true});
    const originalSelectTab = window.selectTab;
    window.selectTab = (name, focus) => {
      if (document.documentElement.dataset.tool !== 'multiview' && ['sketch', 'enhance'].includes(name)) document.documentElement.dataset.tool = name;
      originalSelectTab(name, focus);
      if (name === 'enhance') document.querySelector('.enhance-preview-detail').open = true;
    };
    const observer = new MutationObserver(() => {
      const target = document.getElementById('case-select');
      if (target?.value === id && !document.getElementById('save-case').disabled) {
        document.querySelector('[data-tab="' + (params.get('tool') === 'enhance' ? 'enhance' : 'sketch') + '"]')?.click();
        if (params.get('tool') === 'multiview') { document.getElementById('multiview-section').open = true; }
        observer.disconnect();
      }
    });
    observer.observe(document.body, {subtree:true,attributes:true,childList:true});
  });
})();
