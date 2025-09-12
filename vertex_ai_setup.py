import os
from typing import Optional
from langchain_google_vertexai import ChatVertexAI


def make_vertex_llm(
    model_name: Optional[str] = None,
    project: Optional[str] = None,
    location: Optional[str] = None,
):
    """
    Initializes and returns a ChatVertexAI client.

    Relies on Google Cloud Application Default Credentials (ADC).
    Authenticate via `gcloud auth application-default login` or set
    `GOOGLE_APPLICATION_CREDENTIALS` to a service account JSON.

    Args:
        model_name: Vertex AI model name (e.g., gemini-1.5-flash-001).
        project: Google Cloud project ID.
        location: Region (e.g., us-central1, us-east5, europe-west4).

    Returns:
        ChatVertexAI instance.
    """
    project_id = project or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT is required. Set the env var or pass project=."
        )

    return ChatVertexAI(
        model_name=(model_name or "gemini-1.5-flash-001"),
        project=project_id,
        location=(location or "us-central1"),
        model_kwargs={"request_timeout": 60},
    )


if __name__ == "__main__":
    # Example usage
    # os.environ["GOOGLE_CLOUD_PROJECT"] = "your-gcp-project-id"
    try:
        print("Initializing Vertex AI client...")
        llm = make_vertex_llm()
        print("Vertex AI client initialized successfully.")

        print("\nSending a test prompt...")
        response = llm.invoke("Hello, what is the weather in New York?")
        print("\nResponse from Vertex AI:")
        print(response.content)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("\nEnsure ADC is configured and GOOGLE_CLOUD_PROJECT is set.")
