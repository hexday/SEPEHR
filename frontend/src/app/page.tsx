// SEPEHR — Root redirect to home or login
import { redirect } from "next/navigation";
export default function RootPage() {
  redirect("/home");
}
