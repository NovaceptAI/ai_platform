from dataclasses import dataclass
from uuid import UUID as UUID_t
from app.db import db
from app.models.research import ResearchSession, BrowserSearch, ScrapeSource, SessionNote, ResearchProject
from app.models.status import Progress

@dataclass
class LiveResearchService:
    session: any

    def start_session(self, user_id: UUID_t, project_id: UUID_t) -> ResearchSession:
        rs = ResearchSession(user_id=user_id, project_id=project_id, active=True)
        self.session.add(rs)
        self.session.commit()
        return rs

    def run_browser_search(self, search_id: UUID_t):
        bs: BrowserSearch = self.session.get(BrowserSearch, search_id)
        if not bs:
            return
        bs.status = 'running'
        self.session.commit()
        # TODO: integrate Bing/SerpAPI and normalize results
        bs.results = []
        bs.status = 'done'
        self.session.commit()

    def run_scrape(self, source_id: UUID_t):
        sc: ScrapeSource = self.session.get(ScrapeSource, source_id)
        if not sc:
            return
        sc.status = 'running'
        self.session.commit()
        # TODO: fetch HTML, sanitize, store to Azure Blob; set content_ref
        sc.content_ref = f"blob://{sc.session_id}/{sc.id}.json"
        sc.status = 'done'
        self.session.commit()

    def summarize_session(self, session_id: UUID_t, progress_id: UUID_t):
        prog: Progress = self.session.get(Progress, progress_id)
        notes = self.session.query(SessionNote).filter_by(session_id=session_id).order_by(SessionNote.created_at.asc()).all()
        # TODO: Azure OpenAI batching; update prog.percentage gradually
        prog.percentage = 100
        prog.status = 'completed'
        self.session.commit()
