import { useState, useEffect, useRef } from "react";
import * as d3 from "d3";

// ─── DATA ────────────────────────────────────────────────────
const TOPICS = [
  { slug: "kubernetes-security", name: "Kubernetes Security", depth: 93, interactions: 15, lastActive: "Feb 7", status: "active", color: "#E8A838" },
  { slug: "oauth2", name: "OAuth2 / Authentication", depth: 82, interactions: 12, lastActive: "Feb 7", status: "growing", color: "#D4943A" },
  { slug: "python-dev", name: "Python Development", depth: 71, interactions: 9, lastActive: "Feb 5", status: "active", color: "#B87D3C" },
  { slug: "go-microservices", name: "Go Microservices", depth: 58, interactions: 7, lastActive: "Feb 4", status: "growing", color: "#9C6A3E" },
  { slug: "postgresql", name: "PostgreSQL", depth: 40, interactions: 5, lastActive: "Jan 28", status: "stable", color: "#7A5A42" },
  { slug: "vector-databases", name: "Vector Databases", depth: 22, interactions: 3, lastActive: "Jan 20", status: "new", color: "#5E4E48" },
  { slug: "network-security", name: "Network Security", depth: 11, interactions: 2, lastActive: "Jan 15", status: "dormant", color: "#4A4550" },
  { slug: "cloud-cost", name: "Cloud Cost Optimization", depth: 3, interactions: 1, lastActive: "Dec 10", status: "dormant", color: "#3E3E52" },
];

const CONSTELLATION_NODES = [
  { id: "oauth2", label: "OAuth2", x: 200, y: 150, size: 32, depth: 82 },
  { id: "jwt", label: "JWT", x: 120, y: 260, size: 28, depth: 75 },
  { id: "rbac", label: "RBAC", x: 310, y: 230, size: 26, depth: 70 },
  { id: "https", label: "HTTPS/TLS", x: 380, y: 130, size: 22, depth: 55 },
  { id: "k8s-sa", label: "K8s Service\nAccounts", x: 260, y: 350, size: 24, depth: 58 },
  { id: "pkce", label: "PKCE", x: 80, y: 130, size: 12, depth: 5 },
  { id: "cors", label: "CORS", x: 450, y: 250, size: 16, depth: 30 },
  { id: "rate-limit", label: "Rate\nLimiting", x: 430, y: 350, size: 14, depth: 20 },
  { id: "mtls", label: "mTLS", x: 480, y: 150, size: 10, depth: 3 },
  { id: "token-revoke", label: "Token\nRevocation", x: 100, y: 360, size: 11, depth: 8 },
];

const CONSTELLATION_EDGES = [
  { source: "oauth2", target: "jwt", strength: 0.9, label: "uses" },
  { source: "jwt", target: "https", strength: 0.7, label: "requires" },
  { source: "oauth2", target: "rbac", strength: 0.6, label: "authorizes" },
  { source: "rbac", target: "k8s-sa", strength: 0.8, label: "authenticates" },
  { source: "oauth2", target: "k8s-sa", strength: 0.5, label: "bridges", isNew: true },
  { source: "oauth2", target: "pkce", strength: 0.15, label: "recommended", isGap: true },
  { source: "https", target: "cors", strength: 0.4, label: "configures" },
  { source: "https", target: "mtls", strength: 0.2, label: "extends" },
  { source: "jwt", target: "token-revoke", strength: 0.2, label: "manages", isGap: true },
  { source: "cors", target: "rate-limit", strength: 0.3, label: "complements" },
];

const CONVERSATIONS = [
  {
    query: "How do I implement mTLS between Go microservices in Kubernetes?",
    response: "For mTLS between Go microservices in Kubernetes, you have two main approaches. Since you're already familiar with Kubernetes service accounts and have been working with Go, I'll skip the basics and focus on implementation patterns...\n\n```go\n// Create TLS config with mutual authentication\ntlsConfig := &tls.Config{\n    Certificates: []tls.Certificate{cert},\n    ClientAuth:   tls.RequireAndVerifyClientCert,\n    ClientCAs:    caCertPool,\n}\n```\n\nGiven your OAuth2 token lifecycle expertise, you'll recognize the certificate rotation challenge — it's analogous to refresh token rotation but with X.509 certificates...",
    mode: "explore",
    modeLabel: "Exploration · 8 sources · 2 topic clusters",
    modeIcon: "🧠",
    consolidation: "deep",
    topics: ["mTLS", "Go", "Kubernetes"],
    expertise: "new",
    expertiseLabel: "🌱 New topic for you · Related to your HTTPS and Kubernetes knowledge",
    suggestion: { text: "Since you're exploring mTLS, you might want to look into cert-manager for automated certificate lifecycle in Kubernetes — it connects to your token lifecycle patterns.", action: "Tell me about cert-manager" },
  },
  {
    query: "What was the kubectl command I used for RBAC binding last week?",
    response: "The command you used on Feb 3 was:\n\n```bash\nkubectl create clusterrolebinding admin-binding \\\n  --clusterrole=cluster-admin \\\n  --serviceaccount=kube-system:admin-sa\n```\n\nYou also created a more restrictive binding for the staging namespace:\n\n```bash\nkubectl create rolebinding staging-deployer \\\n  --role=deployer \\\n  --serviceaccount=staging:deploy-sa\n```",
    mode: "exact",
    modeLabel: "Exact recall · 2 matches · Feb 3 session",
    modeIcon: "🔍",
    consolidation: "light",
    topics: ["kubectl", "RBAC"],
    expertise: "deep",
    expertiseLabel: "🔬 Deep topic · Building on 15 prior sessions",
    suggestion: null,
  },
  {
    query: "What time is it in Tokyo?",
    response: "It's currently 2:34 AM JST (Japan Standard Time), Monday February 10.",
    mode: null,
    modeLabel: null,
    modeIcon: null,
    consolidation: "ephemeral",
    topics: [],
    expertise: null,
    expertiseLabel: null,
    suggestion: null,
  },
];

const WEEKLY_DIGEST = {
  stats: { interactions: 47, consolidated: 12, newTopics: 3, deepened: 2, discoveries: 1 },
  breakthroughs: [
    { title: "Kubernetes RBAC + Service Accounts", date: "Feb 7", detail: "5 follow-ups · 23-min deep session. You connected RBAC policies to OAuth2 service account authentication — bridging your two strongest domains." },
    { title: "ACMS Knowledge Pipeline Architecture", date: "Feb 3", detail: "Extensive architecture review with code. Consolidated as core ACMS documentation." },
  ],
  evolution: [
    { topic: "OAuth2", before: 74, after: 82, delta: "+8%" },
    { topic: "Go Microservices", before: 46, after: 58, delta: "+12%" },
  ],
  newTopics: [{ topic: "mTLS", date: "Feb 7" }],
  dormant: [{ topic: "Docker Networking", days: 30 }],
  discovery: {
    clusterA: "Kubernetes Security",
    clusterB: "Investment Analysis",
    connection: "Your Kubernetes RBAC work and investment portfolio analysis share role-based access patterns — tiered permissions, audit logging, principle of least privilege.",
    shared: ["access control", "tiered permissions", "audit logging"],
  },
  health: { total: 847, consistent: 98.2, needsReview: 3 },
  suggestions: ["PKCE for OAuth2 (identified gap)", "Token Revocation strategies", "Admission Controllers in Kubernetes"],
};

const HEATMAP_DATA = (() => {
  const months = ["Dec", "Jan", "Feb"];
  const data = [];
  months.forEach((month, mi) => {
    for (let day = 0; day < 31; day++) {
      const rand = Math.random();
      let level = 0;
      if (rand > 0.92) level = 3;
      else if (rand > 0.78) level = 2;
      else if (rand > 0.55) level = 1;
      data.push({ month, day, level, mi });
    }
  });
  return data;
})();

const CONSISTENCY_ITEMS = [
  { id: 1, title: "OAuth token expiration", issue: "Raw says 3600s, Knowledge says 7200s. Raw is newer (Feb 5).", severity: "medium" },
  { id: 2, title: "Kubernetes 1.28 RBAC changes", issue: "Knowledge entry may be outdated (extracted Nov 2025, Kubernetes 1.30 released since).", severity: "low" },
  { id: 3, title: "Session cookie authentication", issue: "Related to your correction on Feb 7 — flagged by propagated forgetting.", severity: "high" },
];

// ─── COMPONENTS ──────────────────────────────────────────────

function ConsolidationBadge({ level }) {
  if (level === "deep") return <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: "#E8A838" }}>◆ Deep memory</span>;
  if (level === "light") return <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: "#8B8694" }}>◇ Light memory</span>;
  return <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: "#5A5662" }}>○ Ephemeral</span>;
}

function ConversationStream() {
  const [expandedIdx, setExpandedIdx] = useState(null);
  const [dismissed, setDismissed] = useState({});

  return (
    <div className="space-y-4">
      {CONVERSATIONS.map((conv, i) => (
        <div key={i} className="rounded-xl overflow-hidden" style={{ backgroundColor: "#1E1B24", border: "1px solid #2A2731" }}>
          {/* User message */}
          <div className="px-5 pt-4 pb-2">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 shrink-0" style={{ backgroundColor: "#3A3545", color: "#C4BFD0" }}>R</div>
              <p className="text-sm leading-relaxed" style={{ color: "#E8E4F0" }}>{conv.query}</p>
            </div>
          </div>

          {/* Expertise indicator */}
          {conv.expertiseLabel && (
            <div className="mx-5 mt-1 mb-2 px-3 py-1.5 rounded-lg text-xs" style={{ backgroundColor: "#252230", color: "#9B93A8", border: "1px solid #2F2B3A" }}>
              {conv.expertiseLabel}
            </div>
          )}

          {/* Retrieval mode header */}
          {conv.modeLabel && (
            <div
              className="mx-5 mb-2 px-3 py-1.5 rounded-lg text-xs cursor-pointer transition-colors"
              style={{ backgroundColor: expandedIdx === i ? "#2A2535" : "#222030", color: "#7B7488", border: "1px solid #2A2636" }}
              onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
            >
              <span className="mr-1.5">{conv.modeIcon}</span>
              {conv.modeLabel}
              <span className="ml-2 opacity-50">{expandedIdx === i ? "▾" : "▸"}</span>
            </div>
          )}

          {/* Response */}
          <div className="px-5 pb-3">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full flex items-center justify-center mt-0.5 shrink-0" style={{ background: "linear-gradient(135deg, #E8A838, #D4943A)" }}>
                <span className="text-xs font-bold" style={{ color: "#1A1720" }}>A</span>
              </div>
              <div className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "#C4BFD0" }}>
                {conv.response.split("```").map((part, pi) => {
                  if (pi % 2 === 1) {
                    return (
                      <pre key={pi} className="my-2 px-3 py-2 rounded-lg text-xs overflow-x-auto" style={{ backgroundColor: "#16141B", color: "#A89EC0", border: "1px solid #2A2636" }}>
                        <code>{part.replace(/^(go|bash)\n/, "")}</code>
                      </pre>
                    );
                  }
                  return <span key={pi}>{part}</span>;
                })}
              </div>
            </div>
          </div>

          {/* Consolidation indicator */}
          <div className="px-5 pb-2 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ConsolidationBadge level={conv.consolidation} />
              {conv.topics.length > 0 && (
                <div className="flex gap-1.5">
                  {conv.topics.map((t, ti) => (
                    <span key={ti} className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: "#2A2535", color: "#8B8494" }}>{t}</span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 opacity-40 text-xs" style={{ color: "#8B8494" }}>
              <span className="cursor-pointer hover:opacity-80">👍</span>
              <span className="cursor-pointer hover:opacity-80">👎</span>
            </div>
          </div>

          {/* Proactive suggestion */}
          {conv.suggestion && !dismissed[i] && (
            <div className="mx-5 mb-4 px-4 py-3 rounded-lg" style={{ backgroundColor: "#1A1E2E", border: "1px solid #2A3040" }}>
              <p className="text-xs mb-2" style={{ color: "#7B9BC0" }}>
                💡 {conv.suggestion.text}
              </p>
              <div className="flex gap-2">
                <button className="text-xs px-3 py-1 rounded-md font-medium transition-colors" style={{ backgroundColor: "#2A3548", color: "#9BB8D8" }}
                  onClick={() => {}}>
                  {conv.suggestion.action}
                </button>
                <button className="text-xs px-3 py-1 rounded-md transition-colors" style={{ color: "#5A6678" }}
                  onClick={() => setDismissed({ ...dismissed, [i]: true })}>
                  Maybe later
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function KnowledgeCoverage() {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold mb-3" style={{ color: "#C4BFD0" }}>Knowledge Coverage</h3>
      {TOPICS.map((topic) => (
        <div key={topic.slug} className="flex items-center gap-3 group cursor-pointer">
          <div className="w-40 text-xs truncate" style={{ color: "#9B93A8" }}>{topic.name}</div>
          <div className="flex-1 h-3 rounded-full overflow-hidden" style={{ backgroundColor: "#1E1B24" }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${topic.depth}%`, backgroundColor: topic.color, opacity: 0.85 }}
            />
          </div>
          <div className="w-10 text-right text-xs tabular-nums" style={{ color: "#6B6578" }}>{topic.depth}%</div>
          <div className="w-16 text-right text-xs" style={{ color: topic.status === "growing" ? "#5AA86B" : topic.status === "new" ? "#5A8AD8" : topic.status === "dormant" ? "#5A5662" : "#8B8494" }}>
            {topic.status === "growing" && "↑ growing"}
            {topic.status === "new" && "✦ new"}
            {topic.status === "dormant" && "· dormant"}
            {topic.status === "active" && "● active"}
            {topic.status === "stable" && "─ stable"}
          </div>
        </div>
      ))}
    </div>
  );
}

function ConstellationGraph() {
  const svgRef = useRef(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    // Draw edges
    CONSTELLATION_EDGES.forEach((edge) => {
      const source = CONSTELLATION_NODES.find((n) => n.id === edge.source);
      const target = CONSTELLATION_NODES.find((n) => n.id === edge.target);
      if (!source || !target) return;

      g.append("line")
        .attr("x1", source.x).attr("y1", source.y)
        .attr("x2", target.x).attr("y2", target.y)
        .attr("stroke", edge.isNew ? "#5A8AD8" : edge.isGap ? "#5A5662" : "#3A3545")
        .attr("stroke-width", edge.strength * 3)
        .attr("stroke-dasharray", edge.isGap ? "4,4" : "none")
        .attr("opacity", 0.6);

      if (edge.isNew) {
        const mx = (source.x + target.x) / 2;
        const my = (source.y + target.y) / 2;
        g.append("text")
          .attr("x", mx).attr("y", my - 8)
          .attr("text-anchor", "middle")
          .attr("fill", "#5A8AD8")
          .attr("font-size", "9px")
          .text("⟐ new");
      }
    });

    // Draw nodes
    CONSTELLATION_NODES.forEach((node) => {
      const isGap = node.depth < 10;
      const baseColor = isGap ? "#3E3E52" : `hsl(${30 + node.depth * 0.3}, ${40 + node.depth * 0.3}%, ${30 + node.depth * 0.3}%)`;

      g.append("circle")
        .attr("cx", node.x).attr("cy", node.y)
        .attr("r", node.size)
        .attr("fill", baseColor)
        .attr("stroke", isGap ? "#5A5662" : "#E8A838")
        .attr("stroke-width", isGap ? 1 : 1.5)
        .attr("stroke-dasharray", isGap ? "3,3" : "none")
        .attr("opacity", 0.85)
        .attr("cursor", "pointer")
        .on("mouseenter", function() {
          d3.select(this).attr("opacity", 1).attr("stroke-width", 2.5);
          setHoveredNode(node.id);
          setTooltip({ x: node.x, y: node.y - node.size - 12, node });
        })
        .on("mouseleave", function() {
          d3.select(this).attr("opacity", 0.85).attr("stroke-width", isGap ? 1 : 1.5);
          setHoveredNode(null);
          setTooltip(null);
        });

      // Labels
      const lines = node.label.split("\n");
      lines.forEach((line, li) => {
        g.append("text")
          .attr("x", node.x).attr("y", node.y + 4 + (li - (lines.length - 1) / 2) * 11)
          .attr("text-anchor", "middle")
          .attr("fill", isGap ? "#6B6578" : "#E8E4F0")
          .attr("font-size", node.size > 20 ? "10px" : "8px")
          .attr("font-weight", "500")
          .attr("pointer-events", "none")
          .text(line);
      });
    });

  }, []);

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold mb-3" style={{ color: "#C4BFD0" }}>Knowledge Constellation</h3>
      <div className="rounded-xl overflow-hidden" style={{ backgroundColor: "#14121A", border: "1px solid #2A2636" }}>
        <svg ref={svgRef} viewBox="0 0 540 420" className="w-full" style={{ maxHeight: "360px" }} />
        {tooltip && (
          <div className="absolute px-3 py-2 rounded-lg text-xs pointer-events-none" style={{
            left: `${(tooltip.x / 540) * 100}%`,
            top: `${(tooltip.y / 420) * 100 - 4}%`,
            transform: "translate(-50%, -100%)",
            backgroundColor: "#2A2535",
            border: "1px solid #3A3545",
            color: "#C4BFD0",
            zIndex: 10,
          }}>
            <div className="font-medium">{tooltip.node.label.replace("\n", " ")}</div>
            <div style={{ color: "#8B8494" }}>
              {tooltip.node.depth < 10 ? "Knowledge gap" : `${tooltip.node.depth}% depth`}
            </div>
          </div>
        )}
      </div>
      <div className="flex gap-4 mt-2 text-xs" style={{ color: "#6B6578" }}>
        <span>● Strong knowledge</span>
        <span style={{ color: "#5A8AD8" }}>⟐ New connection</span>
        <span>┈ ○ Knowledge gap</span>
      </div>
    </div>
  );
}

function HeatMap() {
  const levels = ["#1E1B24", "#3A3040", "#7B5A38", "#E8A838"];
  return (
    <div>
      <h3 className="text-sm font-semibold mb-3" style={{ color: "#C4BFD0" }}>Memory Activity</h3>
      <div className="space-y-1.5">
        {["Dec", "Jan", "Feb"].map((month) => (
          <div key={month} className="flex items-center gap-2">
            <span className="text-xs w-8" style={{ color: "#6B6578" }}>{month}</span>
            <div className="flex gap-0.5">
              {HEATMAP_DATA.filter((d) => d.month === month).map((d, i) => (
                <div
                  key={i}
                  className="w-2.5 h-2.5 rounded-sm"
                  style={{ backgroundColor: levels[d.level] }}
                  title={d.level === 3 ? "Breakthrough" : d.level === 2 ? "Deep engagement" : d.level === 1 ? "Active" : "Quiet"}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-3 mt-2 text-xs" style={{ color: "#6B6578" }}>
        <span>░ Quiet</span><span>▒ Active</span><span style={{ color: "#7B5A38" }}>▓ Deep</span><span style={{ color: "#E8A838" }}>█ Breakthrough</span>
      </div>
    </div>
  );
}

function ConsistencyAlerts() {
  const [resolved, setResolved] = useState({});
  const sevColors = { high: "#D85A5A", medium: "#D89B5A", low: "#8B8494" };

  return (
    <div>
      <h3 className="text-sm font-semibold mb-1" style={{ color: "#C4BFD0" }}>Knowledge Health</h3>
      <p className="text-xs mb-3" style={{ color: "#5AA86B" }}>✓ 847 entries · 98.2% consistent</p>
      <div className="space-y-2">
        {CONSISTENCY_ITEMS.filter((item) => !resolved[item.id]).map((item) => (
          <div key={item.id} className="px-4 py-3 rounded-lg" style={{ backgroundColor: "#1E1B24", border: `1px solid ${sevColors[item.severity]}30` }}>
            <div className="flex items-start justify-between mb-1">
              <span className="text-xs font-medium" style={{ color: "#C4BFD0" }}>⚠ {item.title}</span>
              <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: `${sevColors[item.severity]}20`, color: sevColors[item.severity] }}>{item.severity}</span>
            </div>
            <p className="text-xs mb-2" style={{ color: "#8B8494" }}>{item.issue}</p>
            <div className="flex gap-2">
              <button className="text-xs px-2.5 py-1 rounded transition-colors" style={{ backgroundColor: "#2A2535", color: "#9B93A8" }} onClick={() => setResolved({ ...resolved, [item.id]: true })}>
                Resolve
              </button>
              <button className="text-xs px-2.5 py-1 rounded transition-colors" style={{ color: "#6B6578" }} onClick={() => setResolved({ ...resolved, [item.id]: true })}>
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WeeklyDigest() {
  const d = WEEKLY_DIGEST;
  return (
    <div className="space-y-4">
      <div className="text-center mb-4">
        <h3 className="text-base font-semibold" style={{ color: "#E8E4F0" }}>Weekly Cognitive Digest</h3>
        <p className="text-xs mt-1" style={{ color: "#8B8494" }}>Feb 3 – 9, 2026</p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: "Interactions", value: d.stats.interactions },
          { label: "Consolidated", value: d.stats.consolidated },
          { label: "New Topics", value: d.stats.newTopics },
          { label: "Discoveries", value: d.stats.discoveries },
        ].map((s) => (
          <div key={s.label} className="text-center py-2 rounded-lg" style={{ backgroundColor: "#1E1B24" }}>
            <div className="text-lg font-bold" style={{ color: "#E8A838" }}>{s.value}</div>
            <div className="text-xs" style={{ color: "#6B6578" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Breakthroughs */}
      <div className="px-4 py-3 rounded-xl" style={{ backgroundColor: "#1E1B24", border: "1px solid #2A2731" }}>
        <h4 className="text-xs font-semibold mb-2" style={{ color: "#E8A838" }}>★ Breakthrough Moments</h4>
        {d.breakthroughs.map((b, i) => (
          <div key={i} className={`${i > 0 ? "mt-3 pt-3" : ""}`} style={{ borderTop: i > 0 ? "1px solid #2A2636" : "none" }}>
            <div className="flex justify-between">
              <span className="text-xs font-medium" style={{ color: "#C4BFD0" }}>{b.title}</span>
              <span className="text-xs" style={{ color: "#6B6578" }}>{b.date}</span>
            </div>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: "#8B8494" }}>{b.detail}</p>
          </div>
        ))}
      </div>

      {/* Knowledge Evolution */}
      <div className="px-4 py-3 rounded-xl" style={{ backgroundColor: "#1E1B24", border: "1px solid #2A2731" }}>
        <h4 className="text-xs font-semibold mb-2" style={{ color: "#5AA86B" }}>Knowledge Evolution</h4>
        {d.evolution.map((e) => (
          <div key={e.topic} className="flex items-center gap-2 mb-1.5">
            <span className="text-xs w-28" style={{ color: "#9B93A8" }}>{e.topic}</span>
            <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: "#2A2535" }}>
              <div className="h-full rounded-full relative" style={{ width: `${e.after}%`, backgroundColor: "#5AA86B" }}>
                <div className="absolute right-0 top-0 h-full rounded-full" style={{ width: `${((e.after - e.before) / e.after) * 100}%`, backgroundColor: "#7BD88A" }} />
              </div>
            </div>
            <span className="text-xs w-8 text-right" style={{ color: "#5AA86B" }}>{e.delta}</span>
          </div>
        ))}
        <div className="mt-2 text-xs" style={{ color: "#5A8AD8" }}>
          ✦ New: mTLS (first appeared Feb 7)
        </div>
        <div className="text-xs mt-1" style={{ color: "#5A5662" }}>
          · Dormant: Docker Networking (30 days)
        </div>
      </div>

      {/* Cross-domain discovery */}
      <div className="px-4 py-3 rounded-xl" style={{ backgroundColor: "#1A1E2E", border: "1px solid #2A3548" }}>
        <h4 className="text-xs font-semibold mb-2" style={{ color: "#5A8AD8" }}>⟐ Cross-Domain Discovery</h4>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium" style={{ color: "#9BB8D8" }}>{d.discovery.clusterA}</span>
          <span style={{ color: "#5A8AD8" }}>↔</span>
          <span className="text-xs font-medium" style={{ color: "#9BB8D8" }}>{d.discovery.clusterB}</span>
        </div>
        <p className="text-xs leading-relaxed" style={{ color: "#7B9BC0" }}>{d.discovery.connection}</p>
        <div className="flex gap-1.5 mt-2">
          {d.discovery.shared.map((s) => (
            <span key={s} className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: "#1A2538", color: "#5A8AD8" }}>{s}</span>
          ))}
        </div>
      </div>

      {/* Suggestions */}
      <div className="px-4 py-3 rounded-xl" style={{ backgroundColor: "#1E1B24", border: "1px solid #2A2731" }}>
        <h4 className="text-xs font-semibold mb-2" style={{ color: "#9B93A8" }}>Suggested Explorations</h4>
        {d.suggestions.map((s, i) => (
          <div key={i} className="text-xs py-1 flex items-center gap-2" style={{ color: "#8B8494" }}>
            <span style={{ color: "#E8A838" }}>→</span> {s}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── MAIN APP ────────────────────────────────────────────────

export default function ACMSCognitiveUI() {
  const [activeTab, setActiveTab] = useState("conversation");

  const tabs = [
    { id: "conversation", label: "Conversation", icon: "💬" },
    { id: "dashboard", label: "Knowledge", icon: "🧠" },
    { id: "digest", label: "Weekly Digest", icon: "📋" },
  ];

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#14121A", color: "#C4BFD0" }}>
      {/* Header */}
      <div className="px-6 py-4" style={{ borderBottom: "1px solid #2A2636" }}>
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm" style={{ background: "linear-gradient(135deg, #E8A838, #D4943A)", color: "#14121A" }}>A</div>
            <div>
              <h1 className="text-sm font-semibold" style={{ color: "#E8E4F0" }}>ACMS Cognitive Architecture</h1>
              <p className="text-xs" style={{ color: "#6B6578" }}>UI Prototype — Architecture of Cognition Series</p>
            </div>
          </div>
          <div className="flex gap-1 p-1 rounded-lg" style={{ backgroundColor: "#1E1B24" }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="px-3 py-1.5 rounded-md text-xs font-medium transition-all"
                style={{
                  backgroundColor: activeTab === tab.id ? "#2A2535" : "transparent",
                  color: activeTab === tab.id ? "#E8E4F0" : "#6B6578",
                }}
              >
                <span className="mr-1.5">{tab.icon}</span>{tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 py-6">
        {activeTab === "conversation" && (
          <div>
            <p className="text-xs mb-4" style={{ color: "#6B6578" }}>
              Conversation stream with cognitive signals — consolidation indicators, retrieval modes, expertise calibration, and proactive suggestions.
            </p>
            <ConversationStream />
          </div>
        )}

        {activeTab === "dashboard" && (
          <div className="space-y-8">
            <p className="text-xs" style={{ color: "#6B6578" }}>
              Knowledge dashboard — your cognitive workspace for reviewing what ACMS knows, exploring connections, and maintaining knowledge health.
            </p>
            <KnowledgeCoverage />
            <ConstellationGraph />
            <div className="grid grid-cols-2 gap-6">
              <HeatMap />
              <ConsistencyAlerts />
            </div>
          </div>
        )}

        {activeTab === "digest" && (
          <div>
            <WeeklyDigest />
          </div>
        )}
      </div>
    </div>
  );
}
