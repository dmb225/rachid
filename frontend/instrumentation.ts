import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "rachid-frontend",
  });
}
