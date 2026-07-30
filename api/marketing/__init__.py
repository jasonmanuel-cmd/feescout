"""
FeeScout Marketing API Router
==============================
Exposes all 6 marketing skill modules as REST API endpoints.

Modules:
  - seo-ops:        Keyword intelligence, GSC optimization, trend detection
  - content-ops:    Content quality scoring via expert panel
  - growth-engine:  Experiment management, playbook, scorecards
  - conversion-ops: CRO audits, survey-to-lead-magnet
  - outbound-engine: Cold outbound campaign management
  - sales-pipeline: Visitor intent, suppression, deal resurrection
"""
from fastapi import APIRouter

from . import seo, content, growth, conversion, outbound, sales

router = APIRouter(prefix="/api/marketing", tags=["marketing"])

router.include_router(seo.router, prefix="/seo", tags=["seo-ops"])
router.include_router(content.router, prefix="/content", tags=["content-ops"])
router.include_router(growth.router, prefix="/growth", tags=["growth-engine"])
router.include_router(conversion.router, prefix="/conversion", tags=["conversion-ops"])
router.include_router(outbound.router, prefix="/outbound", tags=["outbound-engine"])
router.include_router(sales.router, prefix="/sales", tags=["sales-pipeline"])
