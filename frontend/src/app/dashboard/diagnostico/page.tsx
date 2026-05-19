import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

function decodeJwtPayload(token: string): { dirigente_id?: string | number } | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
  } catch {
    return null;
  }
}

export default function DiagnosticoDispatcher() {
  const token = cookies().get("crece_access_token")?.value;
  const payload = token ? decodeJwtPayload(token) : null;
  const dirigenteId = payload?.dirigente_id;

  if (dirigenteId) {
    redirect(`/dashboard/diagnostico/${dirigenteId}`);
  }
  redirect("/dashboard/dirigentes");
}
