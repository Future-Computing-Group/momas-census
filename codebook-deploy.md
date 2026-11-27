# Deployment codebook v2 (D3: share of documented agent deployments that cross an ownership line)

v2 changes (2026-11-06, after a two-coder pilot on 20 cases: 17/20 agreement on AGENT and REACH, all three disagreements from the two rules below): STATUS added for fetch failures; LIVE added, planned-only agents excluded; a page describing several agents is coded on the widest-reach live agent; MARKET flag for marketplaces.

Unit: one publicly documented deployment of an AI agent by a named organization (the deployer), as described on a vendor or deployer page (customer story, case study, press release). Code from the page text only. Code the deployment's documented default use, not features mentioned as possible.

STATUS: ok / blocked (the page body could not be read) / not-deployment (the page is not about an AI agent deployment). Code the rest only when STATUS = ok.

LIVE: live (the page describes the agent as in use) / planned (only future-tense or announced features). Code AGENT and REACH for the live use only; a page with only planned agents is LIVE = planned and AGENT = no.

AGENT: yes if the page describes software that takes multi-step actions (calls tools or systems, acts on records, executes tasks) on someone's behalf; no if it only answers questions, summarizes or drafts text for a human to act on. Code the rest only when AGENT = yes.

REACH (whose systems the agent acts on or exchanges with):
- internal: only systems and data the deployer owns or licenses for its own operations, serving the deployer's own staff (a licensed SaaS the deployer runs on its own data counts as internal);
- customer: it acts for the deployer toward the deployer's outside customers, citizens, students or patients (e.g. customer service that changes the customer's order); two principals, one controller;
- cross-owner: it transacts, negotiates, books, buys, files or coordinates with systems or agents owned by a third party outside the deployer's control (external suppliers, other firms' agents, external marketplaces or payment at third-party merchants, government portals it files into, other organizations' APIs that it acts on rather than merely reads);
- na: the page does not say what the agent acts on.

Several agents on one page: code the live agent with the widest REACH (cross-owner > customer > internal).

Drafting, summarizing or suggesting a reply that a human reviews before anything happens is AGENT = no; any write action the agent itself performs (creates or updates a record or case, resets a password, books, orders, files) is AGENT = yes.

Reading public third-party web pages for information only is not cross-owner; acting on a third party's system is.

MARKET: yes if the deployer is a marketplace or platform and the agent's action creates a transaction with an independent third party (seller, restaurant, carrier) through the deployer's own system; REACH stays as defined (the agent acts on the deployer's system), and MARKET is reported as a sensitivity.

A2A: yes if the page says the agent exchanges with another organization's AI agent; no otherwise.

Output one JSON object per case: {"id", "status", "live", "agent", "reach", "market", "a2a", "confidence" (high/medium/low), "quote" (the shortest verbatim phrase from the page that decided REACH)}.
