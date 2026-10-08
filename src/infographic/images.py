"""Image service interface and deterministic, bounded image normalization."""

from io import BytesIO
import os
from typing import Protocol

from PIL import Image, UnidentifiedImageError

from infographic.schemas import InfographicError

MAX_IMAGE_BYTES = 12 * 1024 * 1024


def normalize(data: bytes) -> bytes:
    if len(data) > MAX_IMAGE_BYTES:
        raise InfographicError("Image exceeds 12 MiB. Supply a smaller reference or image model output.")
    try:
        with Image.open(BytesIO(data)) as source:
            if source.width * source.height > 16_000_000:
                raise InfographicError("Image exceeds 16 megapixels. Supply a smaller image.")
            source.load()
            image = source.convert("RGB")
            image.thumbnail((1600, 1600))
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise InfographicError("Image is not a decodable raster image. Supply PNG, JPEG or WebP.") from exc


class ImageService(Protocol):
    def preflight(self) -> None: ...

    def render(self, prompt: str, references: list[bytes], model: str, ratio: str, timeout: int) -> bytes: ...


class GeminiImages:
    def preflight(self) -> None:
        if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
            raise InfographicError(
                "Image generation requires GOOGLE_API_KEY or GEMINI_API_KEY, for every reasoning provider."
            )

    def render(self, prompt: str, references: list[bytes], model: str, ratio: str, timeout: int) -> bytes:
        from google import genai
        from google.genai import types

        self.preflight()
        try:
            with genai.Client(
                api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"),
                http_options=types.HttpOptions(
                    timeout=timeout * 1000, retry_options=types.HttpRetryOptions(attempts=1)
                ),
            ) as client:
                response = client.models.generate_content(
                    model=model,
                    contents=types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)]
                        + [types.Part.from_bytes(data=data, mime_type="image/png") for data in references],
                    ),
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio=ratio),
                    ),
                )
            for part in response.parts or []:
                if not part.thought and part.inline_data and part.inline_data.data:
                    return normalize(part.inline_data.data)
            raise InfographicError(
                "Gemini returned no image, possibly a safety refusal. Revise the brief or image model."
            )
        except InfographicError:
            raise
        except Exception as exc:
            raise InfographicError(
                f"Gemini image request failed ({type(exc).__name__}). Check image model, key, quota and service; "
                "no automatic retry was made."
            ) from exc
