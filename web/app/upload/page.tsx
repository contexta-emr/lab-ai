import { redirect } from "next/navigation";

/** Uploading lives on Home now. Old links and bookmarks land there. */
export default function UploadPage() {
  redirect("/");
}
