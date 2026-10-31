# Ethical Compliance Declaration
## AI-Powered Chatbot for University Student Support — UniAssist

### HCLTech Career Shaper Programme — Digital-Data-AI / AIML Domain

---

## Declaration

I hereby declare that the UniAssist project — an AI-Powered Chatbot for University Student Support — has been developed in full compliance with ethical standards, data privacy regulations, and responsible AI principles as outlined by the HCLTech Career Shaper Programme and applicable institutional guidelines.

---

## 1. Data Privacy & Student PII Protection

| Principle | Implementation |
|---|---|
| **No PII Storage Beyond Session** | Student personally identifiable information (PII) including phone numbers, email addresses, and identification numbers is automatically masked using regex-based scrubbing before any data is persisted to the database. Session memory is cleared after a 30-minute time-to-live (TTL) window. |
| **PII Masking Patterns** | Indian mobile numbers (`+91`/`0` prefix, 10 digits) → `[PHONE_MASKED]`; Email addresses → `[EMAIL_MASKED]`; Aadhaar numbers (12-digit format) → `[ID_MASKED]` |
| **No External Data Sharing** | Student queries and responses are stored only in the local SQLite database for analytics purposes. No student data is transmitted to third-party services beyond the LLM API for generating responses. |
| **Minimal Data Collection** | Only session-level metadata (anonymized queries, response quality ratings, escalation tickets) is retained. No student names, enrollment numbers, or demographic data is stored in chat logs. |

## 2. Opt-Out Mechanism

- Students are **not required** to provide any personal information to use the chatbot.
- The chatbot operates on an **anonymous session basis** — no login or authentication is required for student users.
- Students may **clear their session** at any time using the "New Session" or "Clear Chat" controls, which immediately purges all conversation history from memory.
- The **"Talk to Human"** escalation feature is entirely voluntary — students choose whether to provide their name, student ID, and email when submitting a support ticket.

## 3. Human Escalation Transparency

- The chatbot **clearly indicates** when a query cannot be resolved automatically and provides explicit options for human escalation.
- Escalation tickets are generated with unique identifiers (`TICK-YYYYMMDD-XXXX`) and visible confirmation messages.
- Students receive clear communication that their query will be reviewed by a human support agent.
- The escalation button ("Talk to Human") is **prominently visible** on the chat interface at all times, ensuring students always have the option to reach a human agent.
- Automated responses clearly state when the chatbot is unable to provide a definitive answer and directs students to official university contacts.

## 4. Responsible AI & Safety Guardrails

| Guardrail | Purpose |
|---|---|
| **Prompt Injection Defense** | Prevents jailbreak attempts, system prompt extraction, and API key probing through regex pattern matching. |
| **Profanity & Abuse Filtering** | Maintains a respectful and professional interaction environment by detecting and deflecting abusive language. |
| **Out-of-Scope Detection** | Politely redirects queries unrelated to university topics (e.g., stock trading, entertainment) to prevent misuse. |
| **Hallucination Prevention** | All responses are grounded in official university knowledge base documents with cited sources. Queries with low similarity scores trigger fallback responses with official contact information. |

## 5. Bias Mitigation

- The chatbot treats all student queries equally regardless of the language style, phrasing, or topic complexity.
- The knowledge base covers a comprehensive range of university topics (12 policy documents) to ensure balanced information access across all student demographics.
- Sentiment analysis is applied uniformly to understand student satisfaction without discriminating based on query characteristics.
- Regular evaluation through the 30-question benchmark harness ensures consistent performance across all intent categories.

## 6. Transparency & Accountability

- The chatbot identifies itself as an **AI assistant** and does not impersonate a human agent.
- Source citations are provided with every response, allowing students to verify information independently.
- All chat interactions are logged (with PII masking) for quality assurance and audit purposes.
- The administrative dashboard provides transparency into chatbot performance metrics, satisfaction scores, and unresolved tickets.

## 7. Dataset Ethics

- The training/evaluation dataset (`dataset.csv`) contains **synthetic data only** — no real student queries or personal information is used.
- The dataset was generated using AI-based paraphrasing tools following the HCL-provided Dataset Generation Prompt.
- No copyrighted, proprietary, or sensitive educational records were used in dataset construction.

---

## Student Name: ____________________________

## Date: ____________________________

## Signature: ____________________________

---

*This declaration is submitted as part of the HCLTech Career Shaper Programme — III Year Industry Project (Digital-Data-AI / AIML Domain).*

