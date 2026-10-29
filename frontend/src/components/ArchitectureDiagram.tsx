import { useEffect, useRef, useState } from "react";
import { DATA_COUNTS } from "../about";
import { CloseIcon, ExpandIcon } from "./icons";

// The README's Architecture section as one picture: how a question travels
// from the browser to the agent, its two tools and the database, and how the
// data got there. Drawn in a 480-wide viewBox that scales to the column;
// colors are theme tokens (CSS), so it follows light and dark. On a phone the
// column draws it at about 75%, too small for the edge labels, so there a tap
// opens it full screen at 640 px wide (scroll sideways to pan).

// The phone breakpoint, the same as App.css's "Phone" section.
const PHONE_QUERY = "(max-width: 520px)";

function useIsPhone(): boolean {
  const [isPhone, setIsPhone] = useState(() => window.matchMedia(PHONE_QUERY).matches);
  useEffect(() => {
    const query = window.matchMedia(PHONE_QUERY);
    const onChange = () => setIsPhone(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return isPhone;
}

interface BoxProps {
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  lines: string[];
  code?: boolean; // the title is an identifier: set in mono
  offline?: boolean;
}

function Box({ x, y, w, h, title, lines, code = false, offline = false }: BoxProps) {
  const middle = x + w / 2;
  return (
    <g>
      <rect
        className={offline ? "arch-box offline" : "arch-box"}
        x={x}
        y={y}
        width={w}
        height={h}
        rx={8}
      />
      <text
        className={code ? "arch-title code" : "arch-title"}
        x={middle}
        y={y + 21}
        textAnchor="middle"
      >
        {title}
      </text>
      {lines.map((line, i) => (
        <text key={line} className="arch-sub" x={middle} y={y + 38 + i * 15} textAnchor="middle">
          {line}
        </text>
      ))}
    </g>
  );
}

// A group (the agent, the database): a tinted ground with its name at the
// bottom left, where no arrow crosses it.
function Group({ y, h, name }: { y: number; h: number; name: string }) {
  return (
    <g>
      <rect className="arch-group" x={20} y={y} width={440} height={h} rx={10} />
      <text className="arch-group-label" x={34} y={y + h - 11}>
        {name}
      </text>
    </g>
  );
}

interface EdgeProps {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  head: string; // url(#...) of this drawing's arrowhead
  stream?: boolean; // dashed: streamed back to the browser
}

// A straight arrow, ending in the drawing's arrowhead.
function Edge({ x1, y1, x2, y2, head, stream = false }: EdgeProps) {
  return (
    <line
      className={stream ? "arch-edge stream" : "arch-edge"}
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      markerEnd={head}
    />
  );
}

const count = (n: number) => n.toLocaleString("en-US");

// The drawing itself. On a phone it is on the page twice (in the column and in
// the enlarged view), so every id it defines starts with idPrefix: ids must be
// unique, and each copy's arrows and label must point at its own.
export function ArchitectureSvg({ idPrefix }: { idPrefix: string }) {
  const head = `url(#${idPrefix}-head)`;
  return (
    <svg
      className="arch"
      viewBox="0 0 480 688"
      role="img"
      aria-labelledby={`${idPrefix}-title ${idPrefix}-desc`}
    >
      <title id={`${idPrefix}-title`}>How a question is answered</title>
      <desc id={`${idPrefix}-desc`}>
        The browser sends the question to FastAPI, which runs a LangGraph agent. The agent node calls
        the tools node at most three times: search_documents runs a vector and a keyword search over
        the catalog passages and merges them by rank; query_courses looks up courses and their
        prerequisite chains. Both read PostgreSQL with pgvector, filled once offline from the public
        documents. Tokens, tool calls, sources and the trace stream back to the browser.
      </desc>
      <defs>
        <marker
          id={`${idPrefix}-head`}
          viewBox="0 0 8 8"
          refX={7}
          refY={4}
          markerWidth={7}
          markerHeight={7}
          orient="auto-start-reverse"
        >
          <path className="arch-head" d="M0,0 L8,4 L0,8 z" />
        </marker>
      </defs>

      {/* Groups first: everything drawn later sits on top of them. */}
      <Group y={184} h={112} name="LANGGRAPH AGENT" />
      <Group y={484} h={118} name="POSTGRESQL 16 + PGVECTOR" />

      <Box
        x={80}
        y={8}
        w={320}
        h={48}
        title="Browser · React + TypeScript"
        lines={["streams the answer, sources and trace"]}
      />
      <Edge x1={200} y1={56} x2={200} y2={102} head={head} />
      <text className="arch-edge-label" x={192} y={84} textAnchor="end">
        question + history
      </text>
      <Edge x1={320} y1={104} x2={320} y2={58} head={head} stream />
      <text className="arch-edge-label" x={328} y={84}>
        tokens, sources, trace
      </text>
      <Box
        x={80}
        y={104}
        w={320}
        h={48}
        title="FastAPI · POST /chat"
        lines={["daily cap, per-visitor limit"]}
      />
      <path className="arch-edge" d="M240,152 V170 H129 V198" markerEnd={head} />

      <Box
        x={34}
        y={200}
        w={190}
        h={62}
        title="agent node"
        lines={["gpt-oss-20b on Groq", "Gemini as fallback"]}
      />
      <Box
        x={256}
        y={200}
        w={190}
        h={62}
        title="tools node"
        lines={["at most 3 rounds,", "enforced in code"]}
      />
      <Edge x1={224} y1={222} x2={254} y2={222} head={head} />
      <Edge x1={256} y1={240} x2={226} y2={240} head={head} />
      <Edge x1={278} y1={262} x2={278} y2={318} head={head} />
      <Edge x1={388} y1={262} x2={388} y2={318} head={head} />

      <Box
        x={20}
        y={320}
        w={280}
        h={62}
        title="search_documents"
        code
        lines={["up to 3 phrasings of the question", "merged by rank (RRF, k = 60)"]}
      />
      <Box
        x={316}
        y={320}
        w={144}
        h={62}
        title="query_courses"
        code
        lines={["course lookup,", "prerequisite chains"]}
      />
      <Edge x1={87} y1={382} x2={87} y2={406} head={head} />
      <Edge x1={233} y1={382} x2={233} y2={406} head={head} />
      <Box x={20} y={408} w={134} h={48} title="vector search" lines={["e5-small, cosine"]} />
      <Box x={166} y={408} w={134} h={48} title="keyword search" lines={["Postgres full-text"]} />

      <Edge x1={87} y1={456} x2={87} y2={498} head={head} />
      <Edge x1={233} y1={456} x2={233} y2={498} head={head} />
      <Edge x1={388} y1={382} x2={388} y2={498} head={head} />
      <text className="arch-edge-label" x={394} y={444}>
        recursive CTE
      </text>

      <Box
        x={34}
        y={500}
        w={230}
        h={62}
        title="document_chunks"
        code
        lines={[`${count(DATA_COUNTS.passages)} passages`, "384-d vectors, full-text index"]}
      />
      <Box
        x={280}
        y={500}
        w={166}
        h={62}
        title="courses"
        code
        lines={[
          `${count(DATA_COUNTS.courses)} courses`,
          `${count(DATA_COUNTS.links)} prerequisite links`,
        ]}
      />

      <Edge x1={240} y1={628} x2={240} y2={604} head={head} />
      <Box
        x={20}
        y={628}
        w={440}
        h={52}
        offline
        title="Ingestion, run once offline"
        lines={["catalog PDF + 2 scholarship pages → clean → chunk → embed"]}
      />
    </svg>
  );
}

export function ArchitectureDiagram() {
  const isPhone = useIsPhone();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  function enlarge() {
    dialogRef.current?.showModal();
    // Start in the middle: the drawing is centred, so its edges matter least.
    const scroller = scrollRef.current;
    if (scroller) scroller.scrollLeft = (scroller.scrollWidth - scroller.clientWidth) / 2;
  }

  return (
    <>
      <figure className="figure">
        {/* The button sits under the drawing, and its ::after (App.css) stretches
            over the whole drawing, so a tap anywhere opens the enlarged view. The
            drawing stays outside the button: a button's content is flattened for
            screen readers, which would lose the description. */}
        <div className="zoom-target">
          <ArchitectureSvg idPrefix="arch" />
          {isPhone && (
            <button type="button" className="figure-zoom" onClick={enlarge}>
              <ExpandIcon />
              Tap to enlarge
            </button>
          )}
        </div>
        <figcaption>
          How a question is answered. Dashed arrow: what streams back to the browser as it happens.
          Dashed box: run once, before the demo went live.
        </figcaption>
      </figure>

      {/* showModal() gives Escape, the back gesture and focus handling for free. */}
      {isPhone && (
        <dialog ref={dialogRef} className="zoom-dialog" aria-labelledby="arch-zoom-heading">
          <div className="zoom-bar">
            <span className="zoom-heading" id="arch-zoom-heading">
              How it works
            </span>
            <button
              type="button"
              className="icon-btn"
              onClick={() => dialogRef.current?.close()}
              aria-label="Close the enlarged diagram"
            >
              <CloseIcon />
            </button>
          </div>
          <div className="zoom-scroll" ref={scrollRef}>
            <ArchitectureSvg idPrefix="arch-zoom" />
          </div>
        </dialog>
      )}
    </>
  );
}
