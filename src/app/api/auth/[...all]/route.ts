import { toNextJsHandler } from "better-auth/next-js";
import { auth } from "@/lib/auth/server";
import { conCookieSecure } from "@/lib/auth/cookie-secure";

const gestori = toNextJsHandler(auth);

export async function GET(request: Request) {
  return conCookieSecure(request, await gestori.GET(request));
}

export async function POST(request: Request) {
  return conCookieSecure(request, await gestori.POST(request));
}
