import { DashboardOverview } from "@/components/dashboard/dashboard-overview";
import { AppFrame } from "@/components/layout/app-frame";

export default function Home() {
  return (
    <AppFrame currentPath="/">
      <DashboardOverview />
    </AppFrame>
  );
}
