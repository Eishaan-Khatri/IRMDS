# 🛠️ IRMDS Technical Deep-Dive: The Senior Engineer's Audit

This document is designed to prepare you for high-level technical interviews. It covers the actual code implementation logic, the computer science patterns, and the "why" behind the low-level choices.

---

## 1. System Boot & Inversion of Control (Registry Pattern)
**How do we load modules without the Core knowing what they are?**
We use a **Plugin Discovery Pattern** located in `core/plugin_registry.py`.

*   **Implementation:** We iterate through the `modules/` directory using `pathlib`. We use `importlib.import_module` to dynamically load the `pipeline.py` file of each module.
*   **The "Trick":** We use `inspect.getmembers()` to look for any class that inherits from `BaseModule`.
*   **The Benefit:** This is **Low Coupling**. The core doesn't have a single `import VisualModule` line. This is a classic "Inversion of Control" (IoC) principle—the library discovers the user's code, not the other way around.

---

## 2. The Multi-Threaded Sync/Async Bridge
**How do we run Visual/ML processing alongside a Web Server?**
FastAPI is built on `uvicorn` (an ASGI server) which lives on a single-threaded `asyncio` event loop. If we run a `.predict()` on YOLO inside a view, the entire website freezes.

*   **Logic:** Every `BaseModule` runs in a **Daemon Thread** via the `threading` module.
*   **The Bridge (`api/routes/ws.py`):**
    *   The `EventBus` is purely synchronous.
    *   The WebSocket endpoint is purely asynchronous.
    *   We use an `asyncio.Queue` and `asyncio.get_event_loop().call_soon_threadsafe()`.
*   **GIL Consideration:** Python's Global Interpreter Lock (GIL) means threads can't run math at the exact same time. However, for OpenCV and NumPy, the heavy lifting happens in **C++ extensions** which *release* the GIL. This allows our Visual module to run at 30 FPS while the API remains responsive.

---

## 3. Data Integrity & Validation (Pydantic v2)
**Why not use dictionaries for everything?**
Dictionaries lead to `KeyError` at runtime. We use **Strict Pydantic Models** throughout the `api/schemas.py` and `modules/network/schemas.py`.

*   **Coercion:** Pydantic automatically converts "12" (string) to 12 (int) at the boundary.
*   **Serialization:** We use `.model_dump(mode='json')` to ensure objects (like Timestamps) are converted to ISO strings before hitting the JSON response.
*   **Memory Efficiency:** Pydantic v2 is written in **Rust**, making validation significantly faster than standard Python `dict` operations.

---

## 4. Visual module: The Math of Anomaly Detection
**How do we turn pixels into "Meters per Second"?**
We don't have GPS—we only have a camera. We use **Perspective Transformation Mapping**.

*   **The Constant:** We define a `METER_PER_PIXEL` constant based on a reference object in the camera's FOV (Field of View).
*   **The Tracking Logic:** We store a `collections.deque` of the last 30 positions (centroids) for every object.
*   **Velocity Vector:** We calculate the Euclidean distance $d = \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$ between frames and divide by $\Delta t$.
*   **Zone Logic:** We represent zones as a `numpy` array of vertices. We use the **Ray Casting** algorithm (`cv2.pointPolygonTest`) to determine if a point is inside the mask.

---

## 5. Network module: The Hybrid ML Ensemble
**How do we detect anomalies without labeled "Attack" data?**
We use **Unsupervised Learning** via `sklearn.ensemble.IsolationForest`.

*   **Isolation Forest:** Instead of modeling "Normal," it builds decision trees that try to "isolate" a data point. If a point is isolated quickly (shallow tree depth), it is an anomaly.
*   **Stat Math (EMA Z-Score):**
    *   $Mean_{new} = \alpha \cdot Value_{curr} + (1-\alpha) \cdot Mean_{prev}$
    *   This is an **Infinite Impulse Response (IIR)** filter. 
    *   We use a $Z = \frac{|x - \mu|}{\sigma}$ test to check if the current value is more than 3 standard deviations away from the EMA mean.

---

## 6. Persistence: The SQLAlchemy 2.0 Pattern
**Why use an ORM instead of raw `.execute("INSERT INTO...")`?**
We use the **Data Mapper Pattern** (SQLAlchemy 2.0 style).

*   **Async Sessions:** In `api/dependencies.py`, we use an `async_session_maker`. This ensures that when 500 users query alerts, the API doesn't block while waiting for the Disk I/O.
*   **Agnosticism:** We use the ` declarative_base()` model. To move from SQLite to a massive AWS RDS PostgreSQL instance, you only change the Connection String, not the code.

---

## 7. Scaling Constraints & Trade-offs
**"How would you scale this to 1000 cameras?"** (Classic Interview Question)
*   **Bottleneck:** The current `VisualModule` runs a CPU/GPU loop per thread. 1000 threads will kill the OS scheduler.
*   **The Solution:** We would move to a **Microservices Architecture**.
    *   The `Registry` would connect to modules running on *other* servers via gRPC or Redis.
    *   The `EventBus` would be replaced by **RabbitMQ or Apache Kafka** to handle millions of messages per second.

---

### Key Interview Terms to Remember:
*   **Decoupling:** Modules don't depend on each other.
*   **Serialization:** Turning Python objects into JSON strings.
*   **Dependency Injection:** Passing the `EventBus` into the module instead of the module "creating" its own.
*   **Idempotency:** A concept for our API routes (like starting a module twice shouldn't break things).
*   **O(1) vs O(N):** We use `deque` for rolling windows to ensure memory lookup/append is always O(1) (constant time).
