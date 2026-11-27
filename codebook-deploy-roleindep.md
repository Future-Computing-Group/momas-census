# Deployment codebook, role-independent cross-owner rule (v3; re-code of the 83 live agent deployments with a stated reach under a role-independent rule)

v3 changes REACH only. In v2 the cross-owner category listed kinds of other party (suppliers, other firms' agents, government portals, third-party financial systems), while counterparty listed customers, citizens, students and patients; an agent that emails a supplier's staff was cross-owner, and one that emails a customer was counterparty. v3 decides by what the agent acts on, not by the role of the other party. STATUS, LIVE, AGENT, MARKET and A2A are as in codebook-deploy.md v2 and are not re-coded; code REACH for the live agent described on the page.

Code from the page text only. Code the deployment's documented default use, not features mentioned as possible. Several agents on one page: code the live agent with the widest REACH (cross-owner > counterparty > internal).

REACH:
- internal: the agent acts only on systems and data that the deployer owns or operates, or licenses and runs for its own operations (a vendor platform, SaaS or cloud service the deployer contracts for counts as the deployer's own), and serves the deployer's own staff.
- counterparty: the agent acts for the deployer on the deployer's own (owned or contracted) systems and exchanges messages with humans outside the deployer: customers, citizens, students, patients, and also the staff of suppliers, partners, insurers or other organizations (sending them an email, a form, a message or a chat reply is counterparty, whoever the outside person works for).
- cross-owner: the agent itself writes to, transacts on, files into or exchanges messages with a system or an AI agent that another party operates and that the deployer does not contract to control: placing an order in a supplier's system, filing into a government portal, paying or booking on a third party's platform, calling another organization's API to act (not merely to read), or exchanging with another organization's agent.
- na: the page does not say what the agent acts on.

Reading public third-party web pages or retrieving information from another party's system without acting on it is not cross-owner. The vendor of the platform the agent runs on is not a third party for REACH: the deployer contracts for that platform (record the vendor layer separately below).

VENDOR_LAYER: yes if the page says that the agent runs on a platform or model operated by a vendor other than the deployer (for example a cloud agent platform or a hosted model); no if the page says the deployer built and runs it on its own systems; na if the page does not say.

Output one JSON object per page: {"id", "reach" (internal / counterparty / cross-owner / na), "vendor_layer" (yes / no / na), "confidence" (high / medium / low), "quote" (the shortest verbatim phrase from the page that decided REACH)}.
