"""One tool-free public Agent turn in an isolated process."""

import asyncio
import base64
import json
from pathlib import Path
import sys

from infographic.intelligence.agent import AgentIntelligence
from infographic.intelligence.schemas import AgentRequest


def main() -> None:
    root = Path(sys.argv[1])
    payload = json.loads((root / "request.json").read_text(encoding="utf-8"))
    payload["images"] = [base64.b64decode(data, validate=True) for data in payload["images"]]
    result = asyncio.run(AgentIntelligence()._run(AgentRequest.model_validate(payload)))
    (root / "result.json").write_text(result.model_dump_json(), encoding="utf-8")


if __name__ == "__main__":
    main()
