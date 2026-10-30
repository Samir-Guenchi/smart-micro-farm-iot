"""Ask one question from the command line: python -m greenloop_assistant "When do I plant potatoes in Latvia?" """
import sys

from . import load_env
from .core import Assistant


def main():
    load_env()
    if len(sys.argv) < 2:
        sys.exit('usage: python -m greenloop_assistant "your question"')
    answer = Assistant().ask(" ".join(sys.argv[1:]))
    print(answer.text)
    if answer.sources:
        print("\nSources:", ", ".join(s.get("slug", "crop calendar") for s in answer.sources))


if __name__ == "__main__":
    main()
