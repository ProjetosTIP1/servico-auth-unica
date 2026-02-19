"""
Prometheus métricas centralizadas para a aplicação.
Isso garante que tanto o aplicativo FastAPI quanto os workers do Celery usem os mesmos nomes e rótulos de métricas.
"""
from prometheus_client import Counter, Histogram, Gauge

# --- FastAPI Metrics ---

# HTTP Request Latency
# Um Histogram para rastrear a duração das requisições HTTP.
# Ele agrupa as requisições por duração, ajudando a calcular percentis (por exemplo, 95º, 99º).
APP_REQUEST_LATENCY = Histogram(
    "app_request_latency_seconds",
    "Application Request Latency",
    ["method", "endpoint", "http_status"]
)

# Total HTTP Requests
# Um Counter para rastrear o número total de requisições HTTP.
APP_REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total Application Requests",
    ["method", "endpoint", "http_status"]
)

# --- Celery Task Metrics ---

# Celery Task Execution Time
# Um Histogram para rastrear quanto tempo as tarefas levam para serem executadas.
CELERY_TASK_LATENCY = Histogram(
    "celery_task_latency_seconds",
    "Celery Task Latency",
    ["task_name"]
)

# Celery Task Status Counter
# Um Counter para rastrear o número total de tarefas pelo seu estado final (por exemplo, SUCESSO, FALHA).
CELERY_TASK_COUNT = Counter(
    "celery_tasks_total",
    "Total Celery Tasks",
    ["task_name", "state"]
)

# Active Celery Tasks
# Um Gauge para mostrar o número de tarefas que estão sendo executadas atualmente pelos workers.
# Isso é útil para monitorar a carga dos workers em tempo real.
CELERY_ACTIVE_TASKS = Gauge(
    "celery_active_tasks",
    "Current number of active Celery tasks",
    ["task_name"]
)

# --- Agno AI Specific Metrics (Business Logic) ---

# AI Model Prediction Counter
# Um contador para rastrear previsões feitas por um modelo específico.
# Ajuda a monitorar o uso e o desempenho do modelo.
MODEL_PREDICTIONS_TOTAL = Counter(
    "ai_model_predictions_total",
    "Total predictions made by an AI model.",
    ["model_version"]
)

# AI Model Processing Time
# Um Histogram para medir a latência das previsões do modelo.
# Crucial para identificar gargalos de desempenho na lógica da IA.
MODEL_PROCESSING_TIME_SECONDS = Histogram(
    "ai_model_processing_time_seconds",
    "Time spent processing a request by an AI model.",
    ["model_version"]
)

# --- Unregister default metrics to avoid duplicates if running multiple apps ---
# This can be useful in complex setups, but for this example, we'll keep them.
# from prometheus_client import unregister
# unregister(prometheus_client.PROCESS_COLLECTOR)
# unregister(prometheus_client.PLATFORM_COLLECTOR)
# unregister(prometheus_client.GC_COLLECTOR)
