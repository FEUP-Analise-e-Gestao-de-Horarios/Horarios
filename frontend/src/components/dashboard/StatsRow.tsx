import {
  BookOpen,
  CalendarDays,
  Clock,
  DoorOpen,
  GraduationCap,
  Users,
  UserCheck,
} from "lucide-react";
import StatCard from "./StatCard";
import type { ProjectStats } from "@/types/dashboard";

interface StatsRowProps {
  stats: ProjectStats;
  processing: boolean;
}

const STAT_CARDS = [
  {
    key: "degrees" as const,
    label: "Cursos",
    icon: GraduationCap,
    color: "bg-violet-100 text-violet-700",
  },
  { key: "years" as const, label: "Anos", icon: CalendarDays, color: "bg-blue-100 text-blue-700" },
  {
    key: "subjects" as const,
    label: "Unidades Curriculares",
    icon: BookOpen,
    color: "bg-emerald-100 text-emerald-700",
  },
  { key: "classes" as const, label: "Turmas", icon: Users, color: "bg-teal-100 text-teal-700" },
  {
    key: "teachers" as const,
    label: "Docentes",
    icon: UserCheck,
    color: "bg-orange-100 text-orange-700",
  },
  { key: "rooms" as const, label: "Salas", icon: DoorOpen, color: "bg-yellow-100 text-yellow-700" },
  { key: "sessions" as const, label: "Aulas", icon: Clock, color: "bg-red-100 text-[#8c2d19]" },
] as const;

export default function StatsRow({ stats, processing }: StatsRowProps) {
  return (
    <div className="flex flex-wrap gap-3">
      {STAT_CARDS.map(({ key, label, icon, color }) => (
        <StatCard
          key={key}
          label={label}
          value={stats[key]}
          icon={icon}
          color={color}
          processing={processing}
        />
      ))}
    </div>
  );
}
