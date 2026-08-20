import type { Config, Context } from "@netlify/functions";

/**
 * Proxy dynamic requests to the Django backend (Gunicorn on Render/Railway/etc.).
 * Static assets under /static/ are served from the publish directory first
 * when preferStatic is enabled.
 */
export default async (req: Request, _context: Context) => {
  const backend = process.env.DJANGO_BACKEND_URL?.replace(/\/$/, "");
  if (!backend) {
    return new Response(
      [
        "Lumina Atelier — Django backend not configured.",
        "",
        "Netlify serves static files and proxies dynamic pages to a Django server.",
        "1. Deploy this repo with the included Dockerfile (see render.yaml).",
        "2. In Netlify → Site settings → Environment variables, set:",
        "   DJANGO_BACKEND_URL = https://your-backend.onrender.com",
        "   (scope: Functions)",
        "3. Redeploy this site.",
      ].join("\n"),
      {
        status: 503,
        headers: { "content-type": "text/plain; charset=utf-8" },
      },
    );
  }

  const incoming = new URL(req.url);
  const target = new URL(incoming.pathname + incoming.search, backend);
  const backendHost = new URL(backend).host;

  const headers = new Headers(req.headers);
  headers.set("X-Forwarded-Proto", incoming.protocol.replace(":", "") || "https");
  headers.set("X-Forwarded-Host", incoming.host);
  headers.set("Host", backendHost);

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const upstream = await fetch(target.toString(), init);

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
};

export const config: Config = {
  path: "/*",
  preferStatic: true,
};
