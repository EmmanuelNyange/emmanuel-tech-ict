window.API_BASE_URL = window.API_BASE_URL || (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" ? "" : "https://YOUR-RENDER-APP.onrender.com");
window.getApiUrl = function (path) {
  const base = String(window.API_BASE_URL || "").replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
};
