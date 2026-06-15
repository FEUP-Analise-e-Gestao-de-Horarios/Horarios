import { Fragment, useLayoutEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useProjectRoom } from "@/api/hooks/project/room";
import { useProjectTeacher } from "@/api/hooks/project/teacher";
import HoverTooltip from "./HoverTooltip";
import MarqueeText from "./MarqueeText";
import MiniAvailabilityGrid from "./MiniAvailabilityGrid";

type Teacher = { id: string; acronym: string; name: string };

function Shell({ title, body }: { title: string; body: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="font-semibold whitespace-nowrap">{title}</p>
      {body}
    </div>
  );
}

/** Tooltip body for a docente: full name + their availability grid (#4). */
export function TeacherAvailability({
  teacherId,
  name,
  fill,
}: {
  teacherId: string;
  name: string;
  fill?: boolean;
}) {
  const { projectId } = useParams<{ projectId: string }>();
  const { data, isPending } = useProjectTeacher(projectId ?? "", teacherId);
  return (
    <Shell
      title={name}
      body={
        isPending ? (
          <p className="text-[#6b6375]">A carregar…</p>
        ) : (
          <MiniAvailabilityGrid redBlocks={data?.red_blocks ?? []} fill={fill} />
        )
      }
    />
  );
}

/** Tooltip body for a sala: name + its availability grid (#4). */
export function RoomAvailability({
  roomId,
  name,
  fill,
}: {
  roomId: string;
  name: string;
  fill?: boolean;
}) {
  const { projectId } = useParams<{ projectId: string }>();
  const { data, isPending } = useProjectRoom(projectId ?? "", roomId);
  return (
    <Shell
      title={name}
      body={
        isPending ? (
          <p className="text-[#6b6375]">A carregar…</p>
        ) : (
          <MiniAvailabilityGrid redBlocks={data?.red_blocks ?? []} fill={fill} />
        )
      }
    />
  );
}

/**
 * Renders the event's docente acronym(s) with hover availability (#4). With a
 * single docente, or when each acronym fits, every name is its own hover target
 * (so the right grid shows per name). When the names overflow (marquee), they
 * can't be hovered individually, so one tooltip shows every grid side by side.
 */
export function TeacherHoverNames({
  teachers,
  className,
}: {
  teachers: Teacher[];
  className?: string;
}) {
  const measureRef = useRef<HTMLDivElement>(null);
  const [overflow, setOverflow] = useState(false);
  const joined = teachers.map((teacher) => teacher.acronym).join(", ");

  useLayoutEffect(() => {
    const el = measureRef.current;
    if (!el) return;
    const check = () => setOverflow(el.scrollWidth - el.clientWidth > 1);
    check();
    const observer = new ResizeObserver(check);
    observer.observe(el);
    return () => observer.disconnect();
  }, [joined]);

  const single = teachers[0];
  if (teachers.length <= 1) {
    if (!single) return null;
    return (
      <HoverTooltip
        className={className}
        content={<TeacherAvailability teacherId={single.id} name={single.name} fill />}
      >
        <MarqueeText className="opacity-80">{single.acronym}</MarqueeText>
      </HoverTooltip>
    );
  }

  if (overflow) {
    return (
      <HoverTooltip
        className={className}
        content={
          <div className="flex gap-3">
            {teachers.map((teacher) => (
              <TeacherAvailability key={teacher.id} teacherId={teacher.id} name={teacher.name} />
            ))}
          </div>
        }
      >
        <MarqueeText className="opacity-80">{joined}</MarqueeText>
      </HoverTooltip>
    );
  }

  return (
    <div
      ref={measureRef}
      className={`flex overflow-hidden whitespace-nowrap opacity-80 ${className ?? ""}`}
    >
      {teachers.map((teacher, index) => (
        <Fragment key={teacher.id}>
          <HoverTooltip
            content={<TeacherAvailability teacherId={teacher.id} name={teacher.name} fill />}
          >
            <span className="hover:underline">{teacher.acronym}</span>
          </HoverTooltip>
          {index < teachers.length - 1 ? <span>,&nbsp;</span> : null}
        </Fragment>
      ))}
    </div>
  );
}
