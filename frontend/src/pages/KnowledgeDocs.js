import React, { useMemo, useState } from "react";
import "./KnowledgeTree.css";

const sections = [
  {
    id: "system-overview",
    title: "System Overview",
    items: [
      { h: "Architecture", p: "Frontend (React) • Backend (Flask/FastAPI) • Workers (Celery/Redis) • DB (Postgres) • Storage (Azure Blob, “Knowledge Vault”) • AI (Azure OpenAI + in-house models)." },
      { h: "Data Flow", p: "Upload → Process (workers) → Persist (DB + Vault) → Surface (dashboard/tools)." },
    ],
  },
  {
    id: "roles-permissions",
    title: "Roles & Permissions",
    items: [
      { h: "Roles", p: "Learner, Educator, Professional, Organization (admin)." },
      { h: "Groups", p: "Project Teams, Study Groups, Classroom Cohorts." },
      { h: "Access", p: "Vault items can be private/shared; project roles: owner, collaborator, viewer." },
    ],
  },
  {
    id: "onboarding",
    title: "Onboarding Flows",
    items: [
      { h: "Learner", p: "Pick a Learning Path → start Discover stage." },
      { h: "Educator", p: "Create course → assign paths → track progress." },
      { h: "Professional", p: "Create research project → connect sources → analyze." },
      { h: "Organization", p: "SSO, bulk users, role provisioning, workspace setup." },
    ],
  },
  {
    id: "tools",
    title: "Stage-by-Stage Tools",
    items: [
      { h: "Discover", p: "Summarization, Sentiment, Segmentation, Chronology, Timeline Explorer, Comparison, Document Analysis, Visual Study Guide, Evidence Extractor, Readability/Style, Topic/Entity/Tag Miner." },
      { h: "Organize", p: "Cluster Builder, Tag & Taxonomy, Collections/Boards, Concept Graph, Saved Views, Consolidation, Cross-Doc Deduper & Merge, Knowledge Vault/Folders, Governance, Review Queue, Export/Sync." },
      { h: "Master", p: "Interactive Quiz, AI Homework Helper, Flashcards, Learn by Drawing, Language Games, Virtual Science Lab, Coding Playground (Kids), Math Visualizer, STEM Challenges, Ethical AI Tutor." },
      { h: "Create", p: "Historical Timelines, AI Presentations, Data Stories, Story→Comics, Interactive Comics, AI Art (Kids), 3D Models." },
      { h: "Collaborate", p: "Digital Debate, Mind Mapping, Co-authoring & Peer Review, Live Quizzes, Showcase & Share." },
    ],
  },
  {
    id: "learning-paths",
    title: "Learning Paths (6)",
    items: [
      { h: "Timeline", p: "Discover→Organize→Master→Create→Collaborate; strong chronology/timeline outputs." },
      { h: "CodeCraft & Systems", p: "Coding, systems thinking, ethical AI practice." },
      { h: "Deep Reading & Investigation", p: "Close reading, evidence-first analysis." },
      { h: "STEM Fundamentals", p: "Math/Science labs, standards alignment, challenges." },
      { h: "Language Learning", p: "Leveling (CEFR), vocab games, comics, peer review." },
      { h: "Creative Arts & Media", p: "Prompts, visualization, comics, AI art & 3D." },
    ],
  },
  {
  id: "research",
  title: "Research Workspace",
  items: [
    { h: "Modules", p: "API Scraper, AI Browser, AI Chat, Live Knowledge Tracking, Knowledge Vault." },
    { h: "API Scraper – Features", p: "Real-time data collection; JSON output; CSV/PDF export; on-screen JSON viewer; geo-smart proxies; high quality and uptime; immediate execution; curate datasets; access existing datasets." },
    { h: "API Scraper – Search Types", p: "Search Engine, Images, Shopping, Maps, Videos, Hotels, Entertainment Facilities." },
    { h: "API Scraper – Sources", p: "Social Media (Facebook, Instagram, Twitter, TikTok, LinkedIn, Pinterest, Snapchat, Tumblr, Quora, Flickr, YouTube, Dailymotion, Vimeo). Search Engines (Google, Bing, Baidu, Tor, Yandex). Music (Spotify, Apple iTunes). Educational/Library (Google Scholar, WorldWideScience.org, Google Books, WorldCat, OCL API, Medium, Open Library, Wikipedia, Udemy). App Stores (Google Play, Apple Store). E-commerce (Amazon, Ebay). Others (Google Reverse Image, Google Products, Stack Overflow). NOTE: Yahoo Answers shut down May 2021." },
    { h: "File Types & Limits", p: "PDF, DOCX, PPTX, CSV, TXT, JSON, Audio, Video; size up to ~500MB (configurable)." },
  ],
},
  {
    id: "api",
    title: "API (Example Spec)",
    items: [
      { h: "Auth: Login", p: "POST /api/auth/login { username, password } → { token }. Content-Type: application/json." },
      { h: "OAuth/JWT", p: "JWT bearer in Authorization header for protected endpoints." },
      { h: "Errors", p: "JSON error model: { error, code, details } with 4xx/5xx status codes." },
      { h: "Testing", p: "Use Postman collections; include environment for base URLs and auth." },
    ],
  },
  {
    id: "models",
    title: "AI Models",
    items: [
      { h: "Hosted GPT", p: "GPT-4/GPT-4o for reasoning, summarization, chat." },
      { h: "In-House", p: "Fine-tuned assistants for flashcards, recommendations, domain chats." },
      { h: "Open-Source", p: "LLaMA, Falcon, MPT for specific pipelines where allowed." },
      { h: "Mapping", p: "Which tool uses which model (e.g., Summarizer→GPT-4, Quiz Generator→FT-3.5, Recommender→in-house ranker)." },
    ],
  },
  {
    id: "governance",
    title: "Governance & Compliance",
    items: [
      { h: "Permissions", p: "Roles, folder access, project ACLs." },
      { h: "Privacy", p: "Data stored in Vault; retention policies; export/erase flows." },
      { h: "Quality", p: "Review queue, human-in-the-loop where needed." },
    ],
  },
  {
    id: "roadmap",
    title: "Roadmap / Future",
    items: [
      { h: "SRS", p: "Spaced-repetition flashcards." },
      { h: "Live Collab", p: "Co-editing, chat, annotation." },
      { h: "Tutor", p: "Contextual multi-session guidance." },
    ],
  },
];

export default function KnowledgeDocs() {
  const [openIds, setOpenIds] = useState(new Set(sections.map(s => s.id))); // all open by default
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    if (!q) return sections;
    const t = q.toLowerCase();
    return sections
      .map(s => ({
        ...s,
        items: s.items.filter(it =>
          (it.h || "").toLowerCase().includes(t) ||
          (it.p || "").toLowerCase().includes(t) ||
          s.title.toLowerCase().includes(t)
        ),
      }))
      .filter(s => s.items.length > 0);
  }, [q]);

  function toggle(id) {
    setOpenIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="kg-docs">
      <div className="kg-docs-toolbar">
        <input
          className="kg-docs-search"
          placeholder="Search docs…"
          value={q}
          onChange={e => setQ(e.target.value)}
        />
        <div className="kg-docs-spacer" />
        <button className="kg-docs-btn" onClick={() => setOpenIds(new Set(sections.map(s => s.id)))}>Expand All</button>
        <button className="kg-docs-btn" onClick={() => setOpenIds(new Set())}>Collapse All</button>
      </div>

      <div className="kg-docs-sections">
        {filtered.map(sec => (
          <section key={sec.id} className="kg-docs-section" id={sec.id}>
            <button className="kg-docs-title" onClick={() => toggle(sec.id)} aria-expanded={openIds.has(sec.id)}>
              {sec.title}
              <span className={`kg-docs-caret ${openIds.has(sec.id) ? "open" : ""}`} />
            </button>

            {openIds.has(sec.id) && (
              <div className="kg-docs-content">
                {sec.items.map((it, i) => (
                  <div className="kg-docs-item" key={i}>
                    <h4>{it.h}</h4>
                    <p>{it.p}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
