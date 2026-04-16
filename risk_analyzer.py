"""
RiskAnalyzer: Behavioral Risk Scoring Module
Author: Sabina Nabieva
Analyzes SMS messages for psychological manipulation tactics
likely to trigger impulsive, high-risk behavior.

Components:
  TextAnalyzer: scores SMS on 4 behavioral dimensions
  URLAnalyzer: scores embedded URLs on structural/lexical features
  RiskAnalyzer: combines both into a final behavioral risk score

Datasets used:
  1. SMS Spam Collection (5,572 messages, 747 spam/smish)
  2. SMS Smishing Collection (5,574 messages, 747 smish) - 281 unique
  3. Phishing URLs Dataset (54,807 confirmed phishing URLs)
  4. New URL Dataset (822,010 URLs, 52% legit / 47% phishing)
     — Used to compute phishing/legit ratios per feature

Usage:
  from risk_analyzer import RiskAnalyzer
  analyzer = RiskAnalyzer()
  result = analyzer.analyze("URGENT: You won $1000! Call now.")
  print(result["behavioral_risk_score"])   # 0.0 – 1.0
  print(result["risk_level"])              # LOW / MEDIUM / HIGH / CRITICAL
"""

import re
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# TEXT KEYWORD LISTS
# Derived from SMS Spam Collection + SMS Smishing Collection datasets
# ---------------------------------------------------------------------------

# Present in ~42% of spam/smish messages
URGENCY_KEYWORDS = [
    "urgent", "urgently", "immediately", "expires", "expiring",
    "limited time", "act now", "hurry", "today only", "deadline",
    "last chance", "asap", "final notice", "dont delay", "don't delay",
    "ending soon", "closing soon", "time sensitive", "respond now",
    "reply now", "call now", "within 24", "within 48", "by tonight",
    "before midnight", "offer ends", "while stocks last", "todays",
    "today's draw", "last weekend", "this week only", "valid",
    "valid for", "awaits", "await", "attempt"
]

# Present in ~60% of spam/smish messages
REWARD_KEYWORDS = [
    "free", "win", "won", "winner", "prize", "cash", "claim",
    "awarded", "award", "bonus", "gift", "guaranteed", "selected",
    "congratulations", "congrats", "you have been chosen",
    "exclusive offer", "special offer", "jackpot", "reward",
    "discount", "savings", "voucher", "coupon", "holiday",
    "camera", "nokia", "ringtone", "tone", "weekly comp",
    "draw", "lucky", "thousand", "pounds", "dollars",
    "1000", "2000", "800 prize", "900 prize", "100,000",
    "chance", "collection", "prize collection"
]

# Account/financial threat language
LOSS_KEYWORDS = [
    "suspended", "suspend", "account closed", "will be closed",
    "unauthorized", "compromised", "blocked", "frozen", "deactivated",
    "overdue", "unpaid", "outstanding balance", "final warning",
    "legal action", "court", "arrest", "penalty", "fine",
    "verify your account", "confirm your details", "update your",
    "at risk", "unusual activity", "suspicious activity",
    "security alert", "fraud alert"
]

# Present in ~88% of spam/smish messages (strongest signal)
ACTION_KEYWORDS = [
    "reply", "call", "click", "txt", "send", "text", "contact",
    "visit", "apply", "subscribe", "opt in", "opt-in", "register",
    "sign up", "download", "install", "tap", "follow the link",
    "go to", "log in", "login", "verify now", "confirm now",
    "claim now", "call 09", "call 08", "box", "keyword",
    "to stop", "to cancel", "to unsubscribe", "collect",
    "land", "lands"
]

# Present in ~12% of spam/smish but high severity when present
AUTHORITY_KEYWORDS = [
    "bank", "hmrc", "irs", "government", "police", "court",
    "paypal", "amazon", "apple", "microsoft", "google", "netflix",
    "your provider", "network", "customer service", "support team",
    "official", "security team", "fraud team", "helpdesk",
    "natwest", "barclays", "lloyds", "hsbc", "halifax",
    "vodafone", "o2", "ee network", "three network",
    "your account", "your bank", "your card", "premier",
    "valued customer", "valued network customer"
]


# ---------------------------------------------------------------------------
# URL RISK FEATURES
# Derived from 822,010 URL dataset with phishing/legit ratios.
# Weights assigned proportional to phishing-to-legit ratio.
# ---------------------------------------------------------------------------

# URL shorteners  (hide true destination)
URL_SHORTENERS = [
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "tiny.cc",
    "is.gd", "buff.ly", "ift.tt", "short.io", "rebrand.ly",
    "cutt.ly", "shorte.st", "adf.ly", "snipurl.com", "tr.im"
]

# High-ratio abused hosting (ratio > 10x phishing vs legit)
# Ranked by phishing/legit ratio from dataset analysis:
# 000webhostapp: 7645x, firebaseapp: 402x, web.app: 248x,
# godaddysites: 218x, docs.google: 226x, netlify: 173x,
# wcomhost: 24x, sites.google: 7.2x, wix: 7.2x
HIGH_RISK_HOSTS = [
    "000webhostapp.com",    # 7645x ratio
    "firebaseapp.com",      # 402x ratio
    "web.app",              # 248x ratio
    "godaddysites.com",     # 218x ratio
    "docs.google.com",      # 226x ratio
    "netlify.app",          # 173x ratio
    "glitch.me",            # 52x ratio
    "myfreesites.net",      # 51x ratio
    "wcomhost.com",         # 24x ratio
    "github.io",            # 11x ratio
    "sites.google.com",     # 7.2x ratio
    "wixsite.com",          # 7.2x ratio
    "weeblysite.com",
    "weebly.com",           # 2.5x ratio
    "webwave.dev",
    "getresponsesite.com",
    "ipfs.io",
    "cloudflare-ipfs.com",
]

# Exclusively or near-exclusively phishing TLDs (ratio > 100x)
# .xyz: 1633x, .icu: 1305x, .ml: 1159x, .ga: 1002x,
# .cf: 917x, .gq: 686x, .online: 678x, .top: 333x, .tk: 132x
PHISHING_ONLY_TLDS = [
    ".xyz", ".icu", ".ml", ".ga", ".cf", ".gq",
    ".online", ".top", ".tk", ".pw", ".buzz"
]

# High-ratio TLDs (10x–100x)
HIGH_RATIO_TLDS = [
    ".info",   # 10x
    ".cn",     # 22x
    ".co",     # 40x
    ".site", ".click", ".loan", ".work", ".cc"
]

# URL keywords with very high phishing ratios (>20x):
# login: 184x, verify: 293x, secure: 56x, paypal: 3085x,
# confirm: 50x, account: 21x, update: 20x, wallet: 36x,
# invoice: 258x, refund: 28x
HIGH_RISK_URL_KEYWORDS = [
    "paypal",     # 3085x ratio
    "verify",     # 293x ratio
    "invoice",    # 258x ratio
    "secure",     # 56x ratio
    "wallet",     # 36x ratio
    "refund",     # 28x ratio
    "signin",     # 41x ratio
    "login",      # 184x ratio
    "confirm",    # 50x ratio
    "account",    # 21x ratio
    "update",     # 20x ratio
]

# Medium-risk URL keywords (2x–20x ratio)
MEDIUM_RISK_URL_KEYWORDS = [
    "support",    # 3.5x
    "apple",      # 3x
    "banking",    # 6x
    "password",   # 4x
    "credential",
    "submit",
    "claim",
    "winner",
    "prize",
]


# ---------------------------------------------------------------------------
# TEXT ANALYZER
# ---------------------------------------------------------------------------

class TextAnalyzer:
    """
    Scores SMS text across 4 behavioral dimensions.
    Each dimension: 0–3. Returns weighted composite 0.0–1.0.

    Weights based on prevalence in combined SMS datasets:
      action_push:  88% of smishing messages -> weight 0.30
      reward_loss:  60% of smishing messages -> weight 0.30
      urgency:      42% of smishing messages -> weight 0.25
      authority:    12% of smishing messages -> weight 0.15
    """

    def analyze(self, text: str) -> dict:
        t = text.lower()

        urgency   = self._score_urgency(t)
        reward    = self._score_reward(t)
        authority = self._score_authority(t)
        action    = self._score_action(t)

        weighted = (
            urgency   * 0.25 +
            reward    * 0.30 +
            authority * 0.15 +
            action    * 0.30
        )
        composite = round(min(weighted / 3.0, 1.0), 3)

        # Multi-tactic amplifier: 3+ active dimensions = more dangerous
        nonzero = sum(1 for s in [urgency, reward, authority, action] if s > 0)
        if nonzero >= 3:
            composite = round(min(composite * 1.25, 1.0), 3)

        return {
            "urgency":            urgency,
            "reward_loss":        reward,
            "authority_coercion": authority,
            "action_push":        action,
            "text_risk_score":    composite,
            "dominant_tactic":    self._dominant(urgency, reward, authority, action),
        }

    def _score_urgency(self, t: str) -> int:
        hits = sum(1 for kw in URGENCY_KEYWORDS if kw in t)
        if re.search(r'\d+\s*(hr|hour|min|minute|day)s?\b', t):
            hits += 1
        if hits == 0: return 0
        if hits == 1: return 1
        if hits == 2: return 2
        return 3

    def _score_reward(self, t: str) -> int:
        reward_hits = sum(1 for kw in REWARD_KEYWORDS if kw in t)
        loss_hits   = sum(1 for kw in LOSS_KEYWORDS   if kw in t)
        hits = reward_hits + loss_hits
        if hits == 0: return 0
        if hits <= 2: return 1
        if hits <= 4: return 2
        return 3

    def _score_authority(self, t: str) -> int:
        hits = sum(1 for kw in AUTHORITY_KEYWORDS if kw in t)
        if hits == 0: return 0
        if hits == 1: return 1
        if hits == 2: return 2
        return 3

    def _score_action(self, t: str) -> int:
        hits = sum(1 for kw in ACTION_KEYWORDS if kw in t)
        if re.search(r'https?://\S+|www\.\S+', t):
            hits += 1
        # UK premium rate numbers (09xxx / 08xxx) — strong smishing signal
        if re.search(r'\b0[89]\d{8,9}\b', t):
            hits += 2
        if hits == 0: return 0
        if hits == 1: return 1
        if hits == 2: return 2
        return 3

    def _dominant(self, urgency, reward, authority, action) -> str:
        scores = {
            "urgency":     urgency,
            "reward_loss": reward,
            "authority":   authority,
            "action_push": action,
        }
        best = max(scores, key=scores.get)
        return "none" if scores[best] == 0 else best


# ---------------------------------------------------------------------------
# URL ANALYZER
# ---------------------------------------------------------------------------

class URLAnalyzer:
    """
    Extracts and scores URLs in SMS text using features derived from
    822,010 labeled URLs (phishing/legit ratio analysis).

    Feature weights are proportional to observed phishing/legit ratios.
    """

    def analyze(self, text: str) -> dict:
        urls = self._extract_urls(text)

        if not urls:
            return {
                "urls_found":     0,
                "url_risk_score": 0.0,
                "url_flags":      [],
                "riskiest_url":   None,
            }

        scored = [(u, self._score_url(u)) for u in urls]
        scored.sort(key=lambda x: x[1]["url_risk_score"], reverse=True)
        worst_url, worst_result = scored[0]
        worst_result["urls_found"]   = len(urls)
        worst_result["riskiest_url"] = worst_url
        return worst_result

    def _extract_urls(self, text: str) -> list:
        return re.findall(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', text)

    def _score_url(self, url: str) -> dict:
        flags = []
        score = 0.0

        try:
            normalized = url if url.startswith("http") else "http://" + url
            parsed = urlparse(normalized)
            domain = parsed.netloc.lower()
            full   = url.lower()
        except Exception:
            return {"url_risk_score": 0.5, "url_flags": ["parse_error"]}

        # Rule 1: URL shortener (hides destination) 
        if any(s in domain for s in URL_SHORTENERS):
            flags.append("url_shortener")
            score += 0.40

        # Rule 2: High-risk abused hosting (ratio > 7x) 
        if any(h in domain for h in HIGH_RISK_HOSTS):
            flags.append("abused_hosting")
            score += 0.35

        # Rule 3: Phishing-only TLD (ratio > 100x) 
        if any((tld + "/") in full or (tld + "?") in full or (tld + "#") in full
               or full.endswith(tld) for tld in PHISHING_ONLY_TLDS):
            flags.append("phishing_only_tld")
            score += 0.35

        # Rule 4: High-ratio TLD (ratio 10x–100x) 
        elif any((tld + "/") in full or (tld + "?") in full
                 or full.endswith(tld) for tld in HIGH_RATIO_TLDS):
            flags.append("high_risk_tld")
            score += 0.20

        # Rule 5: High-risk keywords in URL (ratio > 20x) 
        high_kw_hits = [kw for kw in HIGH_RISK_URL_KEYWORDS if kw in full]
        if high_kw_hits:
            flags.append(f"high_risk_keywords:{','.join(high_kw_hits[:3])}")
            score += min(len(high_kw_hits) * 0.12, 0.35)

        # Rule 6: Medium-risk keywords (ratio 2x–20x) 
        elif not high_kw_hits:
            med_kw_hits = [kw for kw in MEDIUM_RISK_URL_KEYWORDS if kw in full]
            if med_kw_hits:
                flags.append(f"medium_risk_keywords:{','.join(med_kw_hits[:3])}")
                score += min(len(med_kw_hits) * 0.07, 0.20)

        # Rule 7: IP address instead of domain (ratio 56x) 
        if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
            flags.append("ip_address_url")
            score += 0.40

        # Rule 8: Excessive subdomains (depth 3+ has 4.5x ratio) 
        subdomain_depth = len(domain.split(".")) - 2
        if subdomain_depth >= 3:
            flags.append("excessive_subdomains")
            score += 0.15

        # Rule 9: Unusually long URL
        if len(url) > 200:
            flags.append("unusually_long_url")
            score += 0.10

        return {
            "url_risk_score": round(min(score, 1.0), 3),
            "url_flags":      flags,
        }


# ---------------------------------------------------------------------------
# RISK ANALYZER (main entry point)
# ---------------------------------------------------------------------------

class RiskAnalyzer:
    """
    Combines TextAnalyzer + URLAnalyzer into a single behavioral
    risk score for an SMS message.

    Risk levels:
      LOW      0.00–0.39  Likely safe
      MEDIUM   0.40–0.64  Suspicious, warrants caution
      HIGH     0.65–0.84  Strong manipulation signals
      CRITICAL 0.85–1.00  Extreme risk, intervene immediately

    Final score = text_score * 0.60 + url_score * 0.40  (if URL present)
    Final score = text_score                              (if no URL)
    """

    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.url_analyzer  = URLAnalyzer()

    def analyze(self, sms_text: str) -> dict:
        if not sms_text or not sms_text.strip():
            return self._empty_result()

        text_result = self.text_analyzer.analyze(sms_text)
        url_result  = self.url_analyzer.analyze(sms_text)

        has_url = url_result["urls_found"] > 0

        if has_url:
            final_score = round(
                text_result["text_risk_score"] * 0.60 +
                url_result["url_risk_score"]   * 0.40,
                3
            )
        else:
            final_score = text_result["text_risk_score"]

        return {
            # Primary outputs — read by intervention system
            "behavioral_risk_score": final_score,
            "risk_level":            self._risk_level(final_score),
            "dominant_tactic":       text_result["dominant_tactic"],

            # Text dimension breakdown
            "text_scores": {
                "urgency":            text_result["urgency"],
                "reward_loss":        text_result["reward_loss"],
                "authority_coercion": text_result["authority_coercion"],
                "action_push":        text_result["action_push"],
                "text_risk_score":    text_result["text_risk_score"],
            },

            # URL analysis
            "url_analysis": {
                "urls_found":     url_result["urls_found"],
                "url_risk_score": url_result["url_risk_score"],
                "url_flags":      url_result["url_flags"],
                "riskiest_url":   url_result.get("riskiest_url"),
            },
        }

    def _risk_level(self, score: float) -> str:
        if score < 0.40: return "LOW"
        if score < 0.65: return "MEDIUM"
        if score < 0.85: return "HIGH"
        return "CRITICAL"

    def _empty_result(self) -> dict:
        return {
            "behavioral_risk_score": 0.0,
            "risk_level":            "LOW",
            "dominant_tactic":       "none",
            "text_scores": {
                "urgency": 0, "reward_loss": 0,
                "authority_coercion": 0, "action_push": 0,
                "text_risk_score": 0.0,
            },
            "url_analysis": {
                "urls_found": 0, "url_risk_score": 0.0,
                "url_flags": [], "riskiest_url": None,
            },
        }


# ---------------------------------------------------------------------------
# KIVY INTEGRATION HELPER
# ---------------------------------------------------------------------------

def analyze_in_background(sms_text: str, on_result) -> None:
    """
    Run RiskAnalyzer in a background thread so Kivy UI never freezes.
    on_result(result_dict) is called safely on the Kivy main thread.

    Usage in HomeScreen:
        from risk_analyzer import analyze_in_background

        def on_sms_received(self, sms_text):
            self.header.set_status('SCANNING...', color=(0.9, 0.68, 0.22, 1))
            analyze_in_background(sms_text, self.on_analysis_done)

        def on_analysis_done(self, result):
            self.header.set_status(result['risk_level'])
            self.s_avg.update(result['behavioral_risk_score'])
            # pass to intervention system
    """
    from threading import Thread
    try:
        from kivy.clock import Clock

        def _run():
            result = RiskAnalyzer().analyze(sms_text)
            Clock.schedule_once(lambda dt: on_result(result))

        Thread(target=_run, daemon=True).start()

    except ImportError:
        # Kivy not available (unit tests) — run directly
        on_result(RiskAnalyzer().analyze(sms_text))


# ---------------------------------------------------------------------------
# TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    analyzer = RiskAnalyzer()

    test_cases = [
        # --- Expected CRITICAL ---
        ("CRITICAL: urgency + reward + action + premium number",
         "URGENT: You have WON a £1000 prize GUARANTEED! Claim NOW before it expires. Call 09061701461"),

        ("CRITICAL: multi-tactic smishing",
         "WINNER!! As a valued network customer you have been selected to receive a £900 prize reward! To claim call 09061701461. Valid 12 hours only."),

        #  Expected HIGH 
        ("HIGH: authority + loss + phishing URL (000webhostapp)",
         "Your bank account has been suspended. Verify immediately at http://secure-bank-login.000webhostapp.com"),

        ("HIGH: government impersonation + phishing TLD",
         "HMRC: You are owed a tax refund of £248. Visit http://hmrc-refund.xyz/claim to process now."),

        ("HIGH: paypal phishing URL (3085x ratio keyword)",
         "Your PayPal account needs verification. Click: http://secure-paypal-login.firebaseapp.com"),

        #  Expected MEDIUM 
        ("MEDIUM: reward + action, no URL",
         "Free entry to win a Nokia phone! Text WIN to 87099. Guaranteed prize every week."),

        ("MEDIUM: URL shortener",
         "Exclusive offer just for you: https://bit.ly/3xFkP9q - don't miss out!"),

        #  Expected LOW 
        ("LOW: legitimate message",
         "Hey, are you coming to dinner tonight? Let me know by 6pm."),

        ("LOW: delivery notification",
         "Your parcel will be delivered tomorrow between 9am-1pm. No action needed."),
    ]

    print("=" * 68)
    print("RiskAnalyzer v2 — Behavioral Risk Scoring (4-dataset build)")
    print("=" * 68)

    for label, msg in test_cases:
        result = analyzer.analyze(msg)
        print(f"\n[{label}]")
        print(f"  MSG   : {msg[:85]}{'...' if len(msg)>85 else ''}")
        print(f"  SCORE : {result['behavioral_risk_score']}  ->  {result['risk_level']}")
        print(f"  TACTIC: {result['dominant_tactic']}")
        ts = result['text_scores']
        print(f"  DIMS  : urgency={ts['urgency']}  reward={ts['reward_loss']}  "
              f"authority={ts['authority_coercion']}  action={ts['action_push']}")
        ua = result['url_analysis']
        if ua['urls_found'] > 0:
            print(f"  URL   : score={ua['url_risk_score']}  flags={ua['url_flags']}")
        print("-" * 68)
