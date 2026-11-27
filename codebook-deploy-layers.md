# Deployment codebook v4: the ownership layers an agent acts on

v4 is a separate pass with its own coders and output files; codebook-deploy.md (v2) and codebook-deploy-roleindep.md (v3) and their codes are unchanged. v4 replaces the single REACH category by a list of the layers, operated by parties other than the deployer, that the agent acts on. An owner sets an agent's policy within control layered among model vendor, deployer, user and tool operators, so every layer that another party operates counts, including a platform or service that the deployer contracts for: there is no contracted-platform exemption. The model vendor and the platform vendor are recorded as separate layers.

Code from the page text only, without outside knowledge of the organizations named. Code the deployment's documented default use, not features mentioned as possible. Several live agents on one page: code all of them, and list every layer any of them acts on.

STATUS: ok / blocked (the page body could not be read: an error, a login or cookie wall, or only navigation text) / not-deployment (the page is not about an AI agent deployment). Code the rest only when STATUS = ok; otherwise LIVE_AGENT = no.

LIVE_AGENT: yes if the page describes, as in use (not only planned or announced), software that takes multi-step actions on someone's behalf: it calls tools or systems, acts on records or executes tasks. Any write action the agent itself performs (creates or updates a record or case, resets a password, books, orders, files, sends a message) makes it yes. no if it only answers questions, summarizes, or drafts text or suggests a reply that a human reviews before anything happens, or if every agent on the page is planned. Code the rest only when LIVE_AGENT = yes.

OTHER_OWNER_LAYERS: a list with one entry per layer that a party other than the deployer operates and that the agent runs on, calls, writes to, transacts on or exchanges messages with. Each entry is {party_kind, action, quote}. If the same party operates two layers (a vendor's model and the same vendor's platform), give one entry per layer. If no such layer is stated, give exactly one entry {"party_kind": "none", "action": "none", "quote": ""}.

party_kind:
- model-vendor: the organization that operates the AI model beneath the agent, when the page names a hosted model or its vendor (for example a named GPT, Gemini or Claude model, or "Azure OpenAI").
- platform-vendor: the organization that operates the platform the agent is built on or runs on (an agent platform, cloud service, automation or CRM suite), and also any system of that same vendor the agent writes to (a CRM, service desk or data cloud hosted by the platform vendor).
- tool-operator: an organization, other than the model or platform vendor, that operates a tool, application, API or service the agent calls or writes to on the deployer's behalf (a hosted ERP, ticketing, email, payment or search service, a connector, an MCP server). A product named by its vendor counts as operated by that vendor unless the page says that the deployer runs it on its own infrastructure.
- counterparty-org: an organization the agent deals with for the deployer (a supplier, carrier, insurer, bank, merchant, marketplace seller, government agency) whose own system the agent writes to, files into or transacts on: an order posted into a supplier's portal, a claim filed in an insurer's system, a booking or payment on a third party's platform.
- other-org-agent: an AI agent that another organization operates and with which the agent exchanges messages.
- none: no layer of another party is stated.

action:
- runs-on: the agent itself runs on the party's model or platform (model-vendor and platform-vendor only).
- calls-tool: the agent invokes the party's tool, API or service, also to retrieve information from it.
- writes: the agent creates or changes records, cases, files or messages in the party's system.
- transacts: the agent orders, pays, books or files in the party's system.
- messages-agent: the agent exchanges messages with the party's AI agent (other-org-agent only).
- none: with party_kind none only.

quote: the shortest verbatim phrase from the page that shows the layer (empty only for none).

What is not an entry: systems the deployer itself builds and runs on its own infrastructure; reading public web pages or documents for information (content others wrote, not a layer the agent acts on); a party merely mentioned on the page (a partner, a reseller, an integrator that built the agent but does not operate any layer it runs on or acts on); messages to persons (those are OUTSIDE_PERSONS). An integrator or consultancy that operates the agent for the deployer is a platform-vendor entry.

OUTSIDE_PERSONS: yes if the agent exchanges messages with people outside the deployer (customers, citizens, students, patients, or staff of suppliers, partners or other organizations) by chat, voice, email, form or message; no otherwise.

Output one JSON object per page, all keys always present: {"id", "status" (ok / blocked / not-deployment), "live_agent" (yes / no), "other_owner_layers" (the list; [] when live_agent = no), "outside_persons" (yes / no; "na" when live_agent = no), "confidence" (high / medium / low)}. Example of one entry: {"party_kind": "platform-vendor", "action": "runs-on", "quote": "built on the vendor's agent platform"}.

Derived per page with a live agent (deploy_layers.py; not coded): acts_on_other_owner, any entry other than none; model_vendor_reach, any model-vendor entry; platform_vendor_reach, any platform-vendor entry; third_party_reach, any tool-operator, counterparty-org or other-org-agent entry; agent_to_agent, any other-org-agent entry; counterparty, OUTSIDE_PERSONS = yes.
