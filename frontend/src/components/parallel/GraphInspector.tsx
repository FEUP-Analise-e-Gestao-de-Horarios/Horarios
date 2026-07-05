import { useMemo } from "react";
import type { ReactNode } from "react";
import type {
  ParallelBlockNode,
  ParallelCandidateEdge,
  ParallelCandidateGraph,
  UUID,
} from "@/types/parallelSessions";
import { sessionTimeRange } from "./parallelDisplay";
import { formatWeek, weekGrid, weekSpanLabel } from "./parallelWeeks";

/** What the pointer is over in the graph, driving the inspector card. */
export type HoverTarget = { kind: "node"; id: UUID } | { kind: "edge"; index: number };

interface GraphInspectorProps {
  graph: ParallelCandidateGraph;
  nodeById: Map<UUID, ParallelBlockNode>;
  hovered: HoverTarget | null;
  /** Blocks currently selected to form a new group. */
  selected: Set<UUID>;
  /** Blocks already assigned to a group — locked. */
  assigned: Set<UUID>;
  /** Selection frontier (selected nodes + their neighbours); null = no selection. */
  active: Set<UUID> | null;
  sessionTypeStyle: (type: string) => { bg: string; text: string };
}

function nodeCodes(node: ParallelBlockNode): string {
  return node.classes.map((c) => c.code).join(" ");
}

function plural(n: number, singular: string, pluralWord: string): string {
  return `${n} ${n === 1 ? singular : pluralWord}`;
}

function Card({ children }: { children: ReactNode }) {
  return (
    <div className="pointer-events-none flex w-[280px] flex-col gap-1.5 rounded-xl border border-[#e8e8e8] bg-white/95 px-3 py-2.5 shadow-md backdrop-blur">
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <span className="text-[9px] font-semibold uppercase tracking-wide text-[#999]">{children}</span>
  );
}

/**
 * One square per teaching week of the candidate, with the `marked` weeks
 * filled — makes collision patterns (weekly, biweekly, sparse) legible at a
 * glance, where a plain date range would hide them.
 */
function WeekStrip({ grid, marked }: { grid: string[]; marked: Set<string> }) {
  if (grid.length === 0) return null;
  return (
    <div className="flex items-center gap-1.5">
      <span className="shrink-0 text-[9px] tabular-nums text-[#999]">{formatWeek(grid[0]!)}</span>
      <div className="flex flex-1 flex-wrap items-center gap-[3px]">
        {grid.map((week) => (
          <span
            key={week}
            className={`h-[7px] w-[7px] rounded-[2px] ${marked.has(week) ? "bg-amber-400" : "bg-[#e8e8e8]"}`}
          />
        ))}
      </div>
      <span className="shrink-0 text-[9px] tabular-nums text-[#999]">
        {formatWeek(grid[grid.length - 1]!)}
      </span>
    </div>
  );
}

/** A block's classes grouped by degree/year, so multi-degree blocks read clearly. */
function ClassesByYear({
  node,
  yearLabelById,
}: {
  node: ParallelBlockNode;
  yearLabelById: Map<UUID, string>;
}) {
  const byYear = new Map<string, string[]>();
  for (const c of node.classes) {
    const label = yearLabelById.get(c.year_id) ?? "—";
    const codes = byYear.get(label);
    if (codes) codes.push(c.code);
    else byYear.set(label, [c.code]);
  }
  return (
    <div className="flex flex-col gap-0.5">
      {[...byYear].map(([label, codes]) => (
        <div key={label} className="flex items-baseline justify-between gap-2">
          <span className="shrink-0 text-[10px] text-[#999]">{label}</span>
          <span className="text-right text-[11px] font-bold tabular-nums text-[#333]">
            {codes.join(" ")}
          </span>
        </div>
      ))}
    </div>
  );
}

function NodeInfo({
  node,
  graph,
  selected,
  assigned,
  active,
  grid,
  yearLabelById,
  nodeById,
  sessionTypeStyle,
}: {
  node: ParallelBlockNode;
  graph: ParallelCandidateGraph;
  selected: Set<UUID>;
  assigned: Set<UUID>;
  active: Set<UUID> | null;
  grid: string[];
  yearLabelById: Map<UUID, string>;
  nodeById: Map<UUID, ParallelBlockNode>;
  sessionTypeStyle: (type: string) => { bg: string; text: string };
}) {
  const id = node.original_block_id;
  const isAssigned = assigned.has(id);
  const isSelected = selected.has(id);
  const canJoin = !isAssigned && !isSelected && active !== null && active.has(id);
  const isDimmed = !isSelected && active !== null && !active.has(id);
  const typeStyle = sessionTypeStyle(node.session.type);

  // Direct overlaps with the current selection — why (and where) this node can join.
  const connections = canJoin
    ? graph.edges
        .filter(
          (e) =>
            (e.source === id && selected.has(e.target)) ||
            (e.target === id && selected.has(e.source)),
        )
        .map((e) => ({
          other: nodeById.get(e.source === id ? e.target : e.source),
          weeks: e.weeks,
        }))
    : [];
  const sharedWeeks = new Set(connections.flatMap((c) => c.weeks));

  return (
    <Card>
      <div className="flex items-center gap-2">
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${typeStyle.bg} ${typeStyle.text}`}
        >
          {node.session.type}
        </span>
        <span className="text-[11px] font-bold tabular-nums text-[#333]">
          {sessionTimeRange(node.session)}
        </span>
        <span className="ml-auto text-[10px] tabular-nums text-[#999]">
          {weekSpanLabel(node.first_week, node.last_week)}
        </span>
      </div>
      <ClassesByYear node={node} yearLabelById={yearLabelById} />
      {isAssigned && (
        <p className="text-[10px] font-medium text-gray-500">
          Já pertence a um grupo, clica para o ver.
        </p>
      )}
      {isSelected && (
        <p className="text-[10px] font-medium text-amber-600">Selecionado, clica para retirar.</p>
      )}
      {isDimmed && !isAssigned && (
        <p className="text-[10px] font-medium text-gray-500">
          Sem sobreposição com a seleção, não pode juntar-se ao grupo.
        </p>
      )}
      {connections.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-[#f0f0f0] pt-1.5">
          <SectionLabel>Sobrepõe-se com a seleção</SectionLabel>
          {connections.map(
            (c) =>
              c.other && (
                <div
                  key={c.other.original_block_id}
                  className="flex items-baseline justify-between gap-2"
                >
                  <span className="truncate text-[11px] font-semibold tabular-nums text-[#333]">
                    {nodeCodes(c.other)}
                  </span>
                  <span className="shrink-0 text-[10px] tabular-nums text-[#999]">
                    {plural(c.weeks.length, "semana", "semanas")}
                  </span>
                </div>
              ),
          )}
          <WeekStrip grid={grid} marked={sharedWeeks} />
        </div>
      )}
    </Card>
  );
}

function EdgeInfo({
  edge,
  nodeById,
  grid,
  sessionTypeStyle,
}: {
  edge: ParallelCandidateEdge;
  nodeById: Map<UUID, ParallelBlockNode>;
  grid: string[];
  sessionTypeStyle: (type: string) => { bg: string; text: string };
}) {
  const endpoints = [nodeById.get(edge.source), nodeById.get(edge.target)];
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-2">
        <SectionLabel>Sobreposição</SectionLabel>
        <span className="text-[10px] font-bold tabular-nums text-amber-600">
          {plural(edge.weeks.length, "semana", "semanas")}
        </span>
      </div>
      {endpoints.map((node) => {
        if (!node) return null;
        const typeStyle = sessionTypeStyle(node.session.type);
        return (
          <div key={node.original_block_id} className="flex items-center gap-1.5">
            <span
              className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${typeStyle.bg} ${typeStyle.text}`}
            >
              {node.session.type}
            </span>
            <span className="truncate text-[11px] font-bold tabular-nums text-[#333]">
              {nodeCodes(node)}
            </span>
          </div>
        );
      })}
      <WeekStrip grid={grid} marked={new Set(edge.weeks)} />
    </Card>
  );
}

function SelectionInfo({
  graph,
  selected,
  grid,
  yearLabelById,
}: {
  graph: ParallelCandidateGraph;
  selected: Set<UUID>;
  grid: string[];
  yearLabelById: Map<UUID, string>;
}) {
  const nodes = graph.nodes.filter((n) => selected.has(n.original_block_id));
  const classIds = new Set<UUID>();
  const years = new Set<string>();
  for (const node of nodes) {
    for (const c of node.classes) {
      classIds.add(c.id);
      years.add(yearLabelById.get(c.year_id) ?? "—");
    }
  }
  // Weeks on which the selected blocks collide with each other — the coverage
  // the group would actually resolve.
  const overlapWeeks = new Set<string>();
  for (const e of graph.edges) {
    if (selected.has(e.source) && selected.has(e.target)) {
      for (const w of e.weeks) overlapWeeks.add(w);
    }
  }
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-2">
        <SectionLabel>Seleção</SectionLabel>
        <span className="text-[10px] font-bold tabular-nums text-[#333]">
          {plural(nodes.length, "aula", "aulas")} · {plural(classIds.size, "turma", "turmas")}
        </span>
      </div>
      <span className="text-[10px] text-[#777]">{[...years].join(" · ")}</span>
      {overlapWeeks.size > 0 && (
        <div className="flex flex-col gap-1 border-t border-[#f0f0f0] pt-1.5">
          <SectionLabel>Semanas com sobreposição</SectionLabel>
          <WeekStrip grid={grid} marked={overlapWeeks} />
        </div>
      )}
    </Card>
  );
}

/**
 * The graph's info card, pinned to a corner of the viewport (stable, unlike a
 * cursor tooltip over physics-driven nodes). Shows the hovered node or edge;
 * with nothing hovered it summarises the current selection; hidden otherwise.
 */
export default function GraphInspector({
  graph,
  nodeById,
  hovered,
  selected,
  assigned,
  active,
  sessionTypeStyle,
}: GraphInspectorProps) {
  const yearLabelById = useMemo(() => {
    const map = new Map<UUID, string>();
    for (const y of graph.subject.years) map.set(y.id, `${y.degree.acronym} ${y.number}º ano`);
    return map;
  }, [graph.subject.years]);

  const grid = useMemo(() => weekGrid(graph.nodes), [graph.nodes]);

  if (hovered?.kind === "node") {
    const node = nodeById.get(hovered.id);
    if (node) {
      return (
        <NodeInfo
          node={node}
          graph={graph}
          selected={selected}
          assigned={assigned}
          active={active}
          grid={grid}
          yearLabelById={yearLabelById}
          nodeById={nodeById}
          sessionTypeStyle={sessionTypeStyle}
        />
      );
    }
  }
  if (hovered?.kind === "edge") {
    const edge = graph.edges[hovered.index];
    if (edge) {
      return (
        <EdgeInfo edge={edge} nodeById={nodeById} grid={grid} sessionTypeStyle={sessionTypeStyle} />
      );
    }
  }
  if (selected.size > 0) {
    return (
      <SelectionInfo graph={graph} selected={selected} grid={grid} yearLabelById={yearLabelById} />
    );
  }
  return null;
}
