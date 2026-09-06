"""
Robots.txt inspector for Phase 1 Gatekeeper.
Strictly maps to Phase1-PhaseC-Scraper-Implementation-Plan.md §4.
Fetches and caches robots.txt per domain; logs warnings rather than silently ignoring.
"""

import logging
from typing import Dict, List, Optional
import urllib.parse
import urllib.robotparser
import httpx

logger = logging.getLogger("phase1.acquisition.robots")

_ROBOTS_CACHE: Dict[str, urllib.robotparser.RobotFileParser] = {}


def check_robots(url: str, user_agent: str = "Phase1Gatekeeper/1.0", timeout: float = 5.0) -> bool:
    """
    Checks robots.txt for the given URL.
    Returns True if allowed. If disallowed, logs a WARNING and returns False.
    """
    parsed = urllib.parse.urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"

    if domain not in _ROBOTS_CACHE:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{domain}/robots.txt"
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(robots_url, headers={"User-Agent": user_agent})
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.allow_all = True
        except Exception as e:
            logger.debug(f"Could not fetch robots.txt from {robots_url}: {e}")
            rp.allow_all = True

        _ROBOTS_CACHE[domain] = rp

    rp = _ROBOTS_CACHE[domain]
    allowed = rp.can_fetch(user_agent, url)
    if not allowed:
        logger.warning(f"robots.txt rule disallows access to path '{parsed.path}' on {domain} for User-Agent '{user_agent}'")
    return allowed
