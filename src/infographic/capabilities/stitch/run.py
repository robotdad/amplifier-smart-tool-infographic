"""Deterministic panel assembly without cropping or distortion."""

from io import BytesIO
import math

from PIL import Image

from infographic.images import normalize
from infographic.schemas import InfographicError


def stitch(images: list[bytes], layout: str = "vertical") -> bytes:
    if not 1 <= len(images) <= 6 or layout not in {"vertical", "horizontal", "grid"}:
        raise InfographicError("Stitch requires 1 to 6 images and vertical, horizontal or grid layout.")
    panels = [Image.open(BytesIO(normalize(data))).convert("RGB") for data in images]
    columns = (
        1 if layout == "vertical" else len(panels) if layout == "horizontal" else math.ceil(math.sqrt(len(panels)))
    )
    rows = math.ceil(len(panels) / columns)
    width = max(image.width for image in panels)
    height = max(image.height for image in panels)
    output = Image.new("RGB", (columns * width, rows * height), "white")
    for index, image in enumerate(panels):
        output.paste(
            image,
            (
                (index % columns) * width + (width - image.width) // 2,
                (index // columns) * height + (height - image.height) // 2,
            ),
        )
    buffer = BytesIO()
    output.save(buffer, format="PNG")
    return buffer.getvalue()
