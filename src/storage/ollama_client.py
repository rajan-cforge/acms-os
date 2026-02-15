"""Ollama client for ACMS embedding generation.

Uses all-minilm:22m model to generate 384-dimensional embeddings.
Connects to Ollama service at localhost:40434.

Features:
- 384-dim embeddings from all-minilm:22m
- Batch embedding generation
- Performance monitoring (<100ms p95 target)
- Model verification
"""

import time
import os
from typing import List, Union, Dict, Any

import requests


class OllamaClient:
    """Client for Ollama embedding generation.

    Uses all-minilm:22m model for 384-dimensional embeddings.

    Example:
        client = OllamaClient()
        embedding = client.generate_embedding("This is test text")
        # Returns list of 384 floats
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 40434,
        model: str = "all-minilm:22m",
    ):
        """Initialize Ollama client.

        Args:
            host: Ollama service host (default: localhost)
            port: Ollama service port (default: 40434)
            model: Embedding model name (default: all-minilm:22m)
        """
        self.host = host
        self.port = port
        self.model = model
        self.base_url = f"http://{host}:{port}"

        # Verify connection and model
        self._verify_connection()
        self._verify_model()

    def _verify_connection(self):
        """Verify Ollama service is accessible.

        Raises:
            ConnectionError: If Ollama not accessible
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.base_url}: {e}"
            )

    def _verify_model(self):
        """Verify embedding model is available.

        Raises:
            ValueError: If model not found
        """
        models = self.list_models()
        if self.model not in models:
            available = ", ".join(models)
            raise ValueError(
                f"Model '{self.model}' not found. Available models: {available}"
            )

    def list_models(self) -> List[str]:
        """List available Ollama models.

        Returns:
            List[str]: Model names
        """
        response = requests.get(f"{self.base_url}/api/tags", timeout=5)
        response.raise_for_status()

        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    def generate_embedding(self, text: str) -> List[float]:
        """Generate 384-dim embedding for text.

        Args:
            text: Input text to embed

        Returns:
            List[float]: 384-dimensional embedding vector

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        payload = {
            "model": self.model,
            "prompt": text,
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding")

            if not embedding:
                raise RuntimeError("No embedding returned from Ollama")

            if len(embedding) != 384:
                raise RuntimeError(
                    f"Expected 384-dim embedding, got {len(embedding)} dimensions"
                )

            return embedding

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Embedding generation failed: {e}")

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List[List[float]]: List of 384-dim embedding vectors

        Note:
            Currently processes sequentially. Could be optimized with async.
        """
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def generate(
        self,
        prompt: str,
        model: str = "llama3.2:1b",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """Generate text completion using Ollama (for RAG Q&A).

        Args:
            prompt: Input prompt for generation
            model: Model to use (default: llama3.2:1b for RAG)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            str: Generated text response

        Raises:
            RuntimeError: If generation fails

        Example:
            response = client.generate(
                prompt="What is Python?",
                model="llama3.2:1b"
            )
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # Get full response at once
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "stop": ["Question:", "Memory", "\n\n\n"]  # Stop sequences
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,  # 2 minutes timeout for complex queries
            )
            response.raise_for_status()

            data = response.json()
            generated_text = data.get("response", "")

            if not generated_text:
                raise RuntimeError("No response returned from Ollama")

            return generated_text.strip()

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Text generation failed: {e}")

    def measure_latency(self, text: str, runs: int = 10) -> Dict[str, float]:
        """Measure embedding generation latency.

        Args:
            text: Test text
            runs: Number of test runs

        Returns:
            dict: Latency statistics (mean, p50, p95, p99)
        """
        times = []

        for _ in range(runs):
            start = time.time()
            self.generate_embedding(text)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        times.sort()

        return {
            "mean": sum(times) / len(times),
            "p50": times[int(len(times) * 0.50)],
            "p95": times[int(len(times) * 0.95)],
            "p99": times[int(len(times) * 0.99)],
            "min": times[0],
            "max": times[-1],
            "runs": runs,
        }

    def check_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model.

        Returns:
            dict: Model information (name, size, family, etc.)
        """
        response = requests.get(f"{self.base_url}/api/tags", timeout=5)
        response.raise_for_status()

        data = response.json()
        models = data.get("models", [])

        for model in models:
            if model["name"] == self.model:
                return {
                    "name": model["name"],
                    "size": model.get("size"),
                    "digest": model.get("digest"),
                    "modified_at": model.get("modified_at"),
                    "details": model.get("details", {}),
                }

        return {}

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on Ollama service.

        Returns:
            dict: Health status and diagnostics
        """
        try:
            # Check connection
            start = time.time()
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            api_latency = (time.time() - start) * 1000

            # Check model
            models = self.list_models()
            model_available = self.model in models

            # Test embedding generation
            start = time.time()
            test_embedding = self.generate_embedding("test")
            embedding_latency = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "api_latency_ms": api_latency,
                "embedding_latency_ms": embedding_latency,
                "model_available": model_available,
                "models_count": len(models),
                "embedding_dimensions": len(test_embedding),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Global Ollama client instance
_global_client: "OllamaClient" = None


def get_global_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance.

    Returns:
        OllamaClient: Global Ollama client

    Note:
        Creates a new client if none exists.
        Configuration can be overridden with environment variables.
    """
    global _global_client

    if _global_client is None:
        host = os.getenv("ACMS_OLLAMA_HOST", "localhost")
        port = int(os.getenv("ACMS_OLLAMA_PORT", "40434"))
        model = os.getenv("ACMS_OLLAMA_MODEL", "all-minilm:22m")

        _global_client = OllamaClient(host=host, port=port, model=model)

    return _global_client


if __name__ == "__main__":
    # Test Ollama client
    print("Testing Ollama client...")

    try:
        client = OllamaClient()
        print(f"✅ Connected to Ollama at {client.base_url}")

        # List models
        models = client.list_models()
        print(f"Available models: {models}")

        # Check model info
        info = client.check_model_info()
        print(f"Model info: {info}")

        # Generate test embedding
        text = "This is a test sentence for embedding generation"
        print(f"\nGenerating embedding for: '{text}'")

        start = time.time()
        embedding = client.generate_embedding(text)
        elapsed = (time.time() - start) * 1000

        print(f"✅ Embedding generated in {elapsed:.1f}ms")
        print(f"Dimensions: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")

        # Measure latency
        print("\nMeasuring latency (20 runs)...")
        latency = client.measure_latency(text, runs=20)
        print(f"Mean: {latency['mean']:.1f}ms")
        print(f"P50: {latency['p50']:.1f}ms")
        print(f"P95: {latency['p95']:.1f}ms")
        print(f"P99: {latency['p99']:.1f}ms")

        if latency['p95'] < 100:
            print(f"✅ P95 latency ({latency['p95']:.1f}ms) meets <100ms target")
        else:
            print(f"⚠️  P95 latency ({latency['p95']:.1f}ms) exceeds 100ms target")

        # Health check
        print("\nPerforming health check...")
        health = client.health_check()
        print(f"Status: {health['status']}")
        if health['status'] == 'healthy':
            print(f"API latency: {health['api_latency_ms']:.1f}ms")
            print(f"Embedding latency: {health['embedding_latency_ms']:.1f}ms")
            print(f"Model available: {health['model_available']}")
            print(f"Embedding dimensions: {health['embedding_dimensions']}")

        print("\n✅ All Ollama tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
