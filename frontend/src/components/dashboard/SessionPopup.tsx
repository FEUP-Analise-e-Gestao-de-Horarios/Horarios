import { useEffect } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";
import { ROUTES } from "@/routes";
import type { SessionResponse } from "@/types/project/sessions";
import { buildPath } from "@/utils/routes";

const WEEKDAY_LABELS: Record<string, string> = {
  monday: "Segunda",
  tuesday: "Terça",
  wednesday: "Quarta",
  thursday: "Quinta",
  friday: "Sexta",
  saturday: "Sábado",
};

function hhmmLabel(hhmm: number): string {
  const h = Math.floor(hhmm / 100);
  const m = hhmm % 100;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

function durationLabel(durationSlots: number): string {
  const minutes = durationSlots * 30;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}min`;
  if (m === 0) return `${h}h`;
  return `${h}h${m}`;
}

function endTime(start: number, duration: number): number {
  const startMin = Math.floor(start / 100) * 60 + (start % 100);
  const endMin = startMin + duration * 30;
  const h = Math.floor(endMin / 60);
  const m = endMin % 60;
  return h * 100 + m;
}

interface SessionPopupProps {
  session: SessionResponse;
  projectId: string;
  currentRoomId?: string;
  currentTeacherId?: string;
  currentSubjectId?: string;
  currentClassId?: string;
  onClose: () => void;
}

export default function SessionPopup({
  session,
  projectId,
  currentRoomId,
  currentTeacherId,
  currentSubjectId,
  currentClassId,
  onClose,
}: SessionPopupProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const roomsToShow = currentRoomId
    ? session.rooms.filter((r) => r.id !== currentRoomId)
    : session.rooms;
  const roomsSectionTitle = currentRoomId ? "Outras salas" : "Salas";

  const teachersToShow = currentTeacherId
    ? session.teachers.filter((t) => t.id !== currentTeacherId)
    : session.teachers;
  const teachersSectionTitle = currentTeacherId ? "Outros docentes" : "Docentes";

  const subjectsToShow = currentSubjectId
    ? session.subjects.filter((s) => s.id !== currentSubjectId)
    : session.subjects;
  const subjectsSectionTitle = currentSubjectId
    ? "Outras unidades curriculares"
    : "Unidades curriculares";

  const classesToShow = currentClassId
    ? session.classes.filter((c) => c.id !== currentClassId)
    : session.classes;
  const classesSectionTitle = currentClassId ? "Outras turmas" : "Turmas";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Fechar"
        onClick={onClose}
        className="absolute inset-0 bg-black/40 cursor-default"
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative bg-white rounded-lg border border-[#e5e4e7] shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto"
      >
        <div className="px-6 py-4 border-b border-[#e5e4e7] flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 data-copy-id={session.id} className="text-lg font-bold text-[#08060d] truncate">
              {session.subjects.map((s) => s.acronym).join(", ") || "—"}
            </h2>
            <div className="mt-1 text-sm text-[#6b6375]">
              {session.type} · {WEEKDAY_LABELS[session.weekday] ?? session.weekday} ·{" "}
              {hhmmLabel(session.start_time)} –{" "}
              {hhmmLabel(endTime(session.start_time, session.duration))} (
              {durationLabel(session.duration)})
            </div>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 text-[#6b6375] hover:text-[#08060d] transition-colors"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-6 flex flex-col gap-7 text-sm">
          {subjectsToShow.length > 0 && (
            <Section title={subjectsSectionTitle}>
              <ul className="flex flex-col gap-0.5">
                {subjectsToShow.map((s) => (
                  <li key={s.id}>
                    <Link
                      to={buildPath(ROUTES.SUBJECT_DETAIL, { projectId, subjectId: s.id })}
                      data-copy-id={s.id}
                      className="flex items-baseline justify-between gap-3 -mx-2 px-2 py-0.5 rounded hover:bg-[#f9f7f4] transition-colors"
                    >
                      <span className="font-medium text-[#08060d] truncate">{s.name}</span>
                      <span className="shrink-0 text-xs text-[#6b6375]">{s.code}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {classesToShow.length > 0 && (
            <Section title={classesSectionTitle}>
              <div className="flex flex-wrap gap-1.5">
                {classesToShow.map((c) => (
                  <Link
                    key={c.id}
                    to={buildPath(ROUTES.CLASS_DETAIL, { projectId, classId: c.id })}
                    data-copy-id={c.id}
                    className="inline-flex items-center rounded-md bg-[#f9f7f4] border border-[#e5e4e7] px-2 py-0.5 text-xs font-medium text-[#08060d] hover:bg-[#f0eeeb] hover:border-[#d9d6db] transition-colors"
                  >
                    {c.code}
                  </Link>
                ))}
              </div>
            </Section>
          )}

          {teachersToShow.length > 0 && (
            <Section title={teachersSectionTitle}>
              <ul className="flex flex-col gap-0.5">
                {teachersToShow.map((t) => (
                  <li key={t.id}>
                    <Link
                      to={buildPath(ROUTES.TEACHER_DETAIL, { projectId, teacherId: t.id })}
                      data-copy-id={t.id}
                      className="flex items-baseline justify-between gap-3 -mx-2 px-2 py-0.5 rounded hover:bg-[#f9f7f4] transition-colors"
                    >
                      <span className="text-[#08060d] truncate">{t.name}</span>
                      <span className="shrink-0 text-xs text-[#6b6375]">{t.acronym}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {roomsToShow.length > 0 && (
            <Section title={roomsSectionTitle}>
              <div className="flex flex-wrap gap-1.5">
                {roomsToShow.map((r) => (
                  <Link
                    key={r.id}
                    to={buildPath(ROUTES.ROOM_DETAIL, { projectId, roomId: r.id })}
                    data-copy-id={r.id}
                    className="inline-flex items-center rounded-md bg-[#f9f7f4] border border-[#e5e4e7] px-2 py-0.5 text-xs font-medium text-[#08060d] hover:bg-[#f0eeeb] hover:border-[#d9d6db] transition-colors"
                  >
                    {r.name}
                  </Link>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-[#6b6375] mb-2">
        {title}
      </div>
      {children}
    </div>
  );
}
