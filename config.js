window.API_BASE_URL = window.API_BASE_URL || "";
window.getApiUrl = function (path) {
  const base = String(window.API_BASE_URL || "").replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
};
