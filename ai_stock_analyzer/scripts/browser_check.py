"""Run a browser suite, annotating only safe source location/type on failure."""

import runpy
import sys
import traceback
from pathlib import Path


def main():
    args = sys.argv[1:]
    module = args[:1] == ["-m"]
    target = args[1] if module else args[0]
    sys.argv = [target]
    try:
        if module:
            runpy.run_module(target, run_name="__main__")
        else:
            runpy.run_path(target, run_name="__main__")
    except BaseException as exc:
        if isinstance(exc, SystemExit) and exc.code in (None, 0):
            raise
        root = Path(__file__).resolve().parents[1]
        frames = [
            frame
            for frame in traceback.extract_tb(exc.__traceback__)
            if Path(frame.filename).resolve().is_relative_to(root / "tests")
        ]
        location = ""
        if frames:
            frame = frames[-1]
            path = "ai_stock_analyzer/" + str(Path(frame.filename).resolve().relative_to(root))
            location = f"file={path},line={frame.lineno},"
        # No exception message, URL, input, account or credential is published
        # in the public annotation. The normal private job log keeps traceback.
        print(
            f"::error {location}title=Browser regression::{type(exc).__name__} in {target}",
            flush=True,
        )
        raise


if __name__ == "__main__":
    main()
