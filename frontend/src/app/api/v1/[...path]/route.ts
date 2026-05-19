import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
]);

function copyHeaders(src: Headers): Headers {
  const out = new Headers();
  src.forEach((v, k) => {
    if (!HOP_BY_HOP.has(k.toLowerCase())) out.set(k, v);
  });
  return out;
}

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const backend = process.env.BACKEND_TUNNEL_URL ?? "";
  if (!backend) {
    return new Response(JSON.stringify({ detail: "BACKEND_TUNNEL_URL not configured" }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }
  const url = new URL(req.url);
  const target = `${backend.replace(/\/+$/, "")}/api/v1/${path.join("/")}${url.search}`;
  const fwdHeaders = copyHeaders(req.headers);
  // ngrok free tier intercepts browser-like requests and returns an HTML
  // interstitial. This header tells ngrok to pass through. Harmless when the
  // backend tunnel is not ngrok.
  fwdHeaders.set("ngrok-skip-browser-warning", "1");
  const init: RequestInit = {
    method: req.method,
    headers: fwdHeaders,
    // Follow redirects server-side. FastAPI responde 307/308 cuando el path
    // difiere por trailing slash y el Location es absoluto al backend
    // (trycloudflare). Si el browser lo siguiera, sale del mismo origen,
    // pierde el JWT (auth Bearer en JS) y dispara bounce a /login.
    redirect: "follow",
  };
  if (!["GET", "HEAD"].includes(req.method)) {
    init.body = await req.arrayBuffer();
  }
  const upstream = await fetch(target, init);
  const headers = copyHeaders(upstream.headers);
  headers.delete("content-length");
  headers.delete("content-encoding");
  const body = await upstream.arrayBuffer();
  return new Response(body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await ctx.params).path);
}
export async function PUT(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await ctx.params).path);
}
export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await ctx.params).path);
}
export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await ctx.params).path);
}
export async function OPTIONS(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await ctx.params).path);
}
