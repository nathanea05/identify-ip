from __future__ import annotations

import random
import argparse
import sys
from ipaddress import ip_address
from typing import Literal
import time
from requests.adapters import HTTPAdapter
import requests
from urllib3.util.retry import Retry

BASE_URL = "https://rdap.arin.net/registry/ip/"
REQUESTS_TIMEOUT = 15
HEADERS = {"Accept": "application/rdap+json"}

MIN_SECONDS_BETWEEN_CALLS = 0.2
_last_call_ts = 0.0

def _throttle():
    global _last_call_ts
    if MIN_SECONDS_BETWEEN_CALLS <= 0:
        return
    now = time.monotonic()
    wait = MIN_SECONDS_BETWEEN_CALLS - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()

def _make_session() -> requests.Session:
    s = requests.Session()

    retry = Retry(
        total=6,
        connect=6,
        read=6,
        status=6,
        backoff_factor=0.8,  # exponential backoff
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,  # honors Retry-After for 429/503
        raise_on_status=False,            # we will call raise_for_status ourselves
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    return s

_SESSION = _make_session()

def parse_vcard_array(vcard_array: list) -> dict:
    """Converts an RDAP vcardArray (jCard) into a dict."""
    if not isinstance(vcard_array, list) or len(vcard_array) != 2:
        return {}

    kind, properties = vcard_array
    if kind != "vcard" or not isinstance(properties, list):
        return {}

    result: dict = {}
    for prop in properties:
        if not (isinstance(prop, list) and len(prop) == 4):
            continue
        name, params, value_type, value = prop
        result[name] = value
    return result


def get_vcard_name(vcard: dict) -> str | None:
    """Returns the most likely name of the registrant from a parsed vcard dict."""
    return (
        vcard.get("fn")  # Formatted Name
        or vcard.get("org")
        or vcard.get("name")
        or vcard.get("handle")
    )


def parse_entities(entities: list[dict]) -> str | None:
    """Depth-first search for registrant name in RDAP entities."""
    if not entities:
        return None

    # Prefer registrant at this level
    for entity in entities:
        roles = entity.get("roles") or []
        if "registrant" in roles:
            vcard_array = entity.get("vcardArray")
            if vcard_array:
                vcard = parse_vcard_array(vcard_array)
                name = get_vcard_name(vcard)
                if name:
                    return name

    # Recurse into nested entities
    for entity in entities:
        nested = entity.get("entities") or []
        if nested:
            name = parse_entities(nested)
            if name:
                return name

    return None

class RdapRateLimited(RuntimeError):
    """Raised when RDAP returns 429 and we choose not to (or cannot) recover."""
    pass

def _retry_after_seconds(resp: requests.Response) -> int | None:
    ra = resp.headers.get("Retry-After")
    if not ra:
        return None
    try:
        return int(ra)
    except ValueError:
        # Sometimes Retry-After can be an HTTP date; ignoring for simplicity.
        return None

def get_ip_registrant(ip_str: str, *, base_url: str = BASE_URL) -> str | None:
    """Returns the registrant organization/person name for an IP."""
    url = base_url + ip_str

    # Basic throttle so you don't hammer RDAP in loops
    _throttle()

    try:
        resp = _SESSION.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    except requests.RequestException as e:
        # Network glitch, TLS reset, DNS issue, etc.
        return None

    # If still rate-limited after urllib3 retries, handle here
    if resp.status_code == 429:
        ra = _retry_after_seconds(resp)
        # If server told us how long, we can optionally wait once then retry
        if ra is not None and ra <= 60:
            time.sleep(ra + random.uniform(0, 0.5))  # small jitter
            _throttle()
            try:
                resp = _SESSION.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
            except requests.RequestException:
                return None
        else:
            # Don't block forever inside library code; let caller decide what to do.
            # Returning None keeps your "caching handled by caller" approach.
            return None

    # For other HTTP errors, bail out cleanly
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        return None

    data = resp.json()
    entities = data.get("entities") or []
    return parse_entities(entities)

def get_ip_version(ip_str: str) -> int:
    """Returns IP protocol version (4 or 6). Raises ValueError if invalid."""
    ip = ip_address(ip_str)
    return ip.version


def get_ip_info(ip_str: str, filt: Literal["all", "registrant", "version"] = "all") -> str:
    """Returns a human-readable string based on filter."""
    ip = ip_address(ip_str)
    registrant = get_ip_registrant(ip_str)

    if filt == "registrant":
        return registrant or f"registrant not found for IP Address {ip}"
    if filt == "version":
        return str(ip.version)

    return f"{ip} is an IPv{ip.version} IP Address Registered by '{registrant}'."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Identify an IP Address")
    parser.add_argument("ip_string", help="IP Address to Identify")

    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "-r", "--registrant", action="store_true",
        help="Print the registrant of the IP address to STDOUT",
    )
    filter_group.add_argument(
        "-v", "--version", action="store_true",
        help="Print the IP protocol version number to STDOUT",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.registrant:
        filt = "registrant"
    elif args.version:
        filt = "version"
    else:
        filt = "all"

    try:
        out = get_ip_info(args.ip_string, filt=filt)
        print(out)
        return 0
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    except requests.HTTPError as e:
        # Optional: nicer error message
        print(f"RDAP lookup failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
