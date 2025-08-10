import { useParams } from "react-router-dom";
import Dashboard from "@/components/dashboard";

export default function DashboardPage() {
  const { pageId } = useParams();
  if (!pageId) return <div>Loading...</div>;

  return <Dashboard pageId={pageId} />;
}