# IRMDS — The Sovereign Vision

IRMDS is envisioned not just as a software application, but as a **Physical Space Operating System (PSOS)**. This document outlines the long-term roadmap for the 100 modules that will turn any physical environment into a self-protecting, autonomous "Sense Node."

## The "Android for Factories" Strategy
The goal is to provide the **Micro-Kernel** (Core) and the **API** (BaseModule SDK) so that developers can build specialized "Apps" (Modules) for any domain.

---

### Phase 1: The Sovereign Kernel (The "Brain")
1.  **Plugin Discovery Engine:** Automatic dynamic folder scanning. [DONE]
2.  **Internal EventBus:** Centralized Pub/Sub routing. [DONE]
3.  **BaseModule Contract:** The strict interface for all plugins. [DONE]
4.  **Metrics Collector:** Telemetry sink for real-time stats. [DONE]
5.  **Alert Manager:** Logic for deduplication and severity. [DONE]
6.  **Session Manager:** Tracking system uptime and sessions. [DONE]
7.  **Database ORM Layer:** Abstraction for SQL persistence. [DONE]
8.  **Config/Secret Management:** Secured environment handling. [DONE]
9.  **Logger:** Structured JSON logging for ELK compatibility. [DONE]
10. **Management API:** The foundation for external control. [DONE]

### Phase 2: Cybersecurity & Digital Integrity (The "Shield")
11. **Network Traffic Generator:** Controlled synthetic simulations. [DONE]
12. **Bounded Feature Extractor:** O(1) memory packet analysis. [DONE]
13. **Isolation Forest Engine:** Unsupervised ML anomaly detection. [DONE]
14. **EMA Z-Score Filter:** Volatility detection for baseline shifts. [DONE]
15. **PLC Logic Auditor:** Verifying machine code hasn't been modified.
... (Rest of the 100 modules) ...

[Refer to implementation_plan.md and task.md for current active engineering]
