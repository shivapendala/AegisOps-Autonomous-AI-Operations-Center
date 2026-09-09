# AegisOps AI System & Pluggable Architecture

## 1. Multi-Variate Anomaly Detection (scikit-learn)

AegisOps utilizes an unsupervised `IsolationForest` pipeline paired with `StandardScaler` from `scikit-learn`:

* **Feature Vector**:
  $$\mathbf{x} = [\text{cpu\_percent}, \text{memory\_percent}, \text{disk\_percent}, \text{process\_count}]$$
* **Standardization**: Zero-mean, unit-variance scaling prevents features with higher numerical ranges from skewing tree splits.
* **Cold-Start Resilience**: The detector is pre-seeded on startup with a synthetic baseline of nominal operational metrics. As real telemetry flows through the orchestrator, custom refitting can be performed using `fit_from_telemetry()`.
* **Decision Function**: Inliers yield positive scores, while anomalies produce negative decision values.
* **Heuristic Attribution**: When an anomaly is detected, the detector maps specific threshold deviations (e.g. CPU > 85%, RAM > 88%, Disk > 92%) into human-readable descriptions and affected metric tags.

---

## 2. Pluggable LLM Service Interface

The LLM integration is decoupled from vendor implementations using the Strategy Pattern via `BaseLLMService`:

```python
class BaseLLMService(ABC):
    @abstractmethod
    async def analyze_incident(self, incident_data: Dict[str, Any]) -> LLMAnalysisResult:
        """Analyzes incident telemetry and returns root cause assessment."""
        pass

    @abstractmethod
    async def suggest_remediation(self, incident_data: Dict[str, Any]) -> List[str]:
        """Provides actionable mitigation recommendations."""
        pass
```

### Supported Providers

1. **MockLLMService (`provider="mock"`)**:
   - Zero-dependency, offline default for local development, testing, and continuous integration.
   - Applies deterministic contextual operational logic based on telemetry metrics to synthesize root cause analyses and mitigation actions.

2. **OpenAILLMService (`provider="openai"`)**:
   - Production provider calling OpenAI API (or any OpenAI-compatible endpoint such as Azure OpenAI, Ollama, or vLLM).
   - Gracefully falls back to `MockLLMService` if the API key is unconfigured or a network failure occurs.

3. **Extending with Custom Providers**:
   Any new provider (e.g., Anthropic Claude, Google Gemini, local Hugging Face model) can be added simply by inheriting from `BaseLLMService` and registering it in `get_llm_service()` in `aegisops/ai/llm_service.py`.
