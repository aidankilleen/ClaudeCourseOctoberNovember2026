"""
A first look at the Claude API.

This script sends one question to Claude and prints the answer. It is the
smallest useful example: one request, one response, no conversation history.

Before running it you need an API key from https://console.anthropic.com
stored in an environment variable called ANTHROPIC_API_KEY. In PowerShell:

    $env:ANTHROPIC_API_KEY = "sk-ant-..."

Then:

    pip install -r requirements.txt
    python hello_claude.py
    python hello_claude.py "Ask Claude something else"
"""

import os
import sys

import anthropic

# Which Claude model to talk to. Model names are plain strings; swapping this
# for "claude-sonnet-5-5" or "claude-haiku-5-5" gets you a cheaper, faster
# model without changing anything else in the script.
MODEL = "claude-haiku-5-5"


def main() -> int:
    # Fail early with a friendly message rather than a stack trace, because the
    # missing key is by far the most common reason this script does not work.

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "No API key found.\n"
            'Set one first:  $env:ANTHROPIC_API_KEY = "sk-ant-..."',
            file=sys.stderr,
        )
        return 1

    # Anything typed after the script name becomes the question, so you can
    # experiment without editing the file.
    question = " ".join(sys.argv[1:]) or "In two sentences, what is the Claude API?"

    # The client reads ANTHROPIC_API_KEY from the environment by itself. Never
    # paste a key into the code - it would end up in git.
    client = anthropic.Anthropic()

    print(f"Asking {MODEL}: {question}\n")

    # One request. "system" sets Claude's standing instructions, "messages" is
    # the conversation so far - here just the single question. max_tokens is a
    # ceiling on the length of the reply, not a target.
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system="You are a helpful assistant. Answer plainly, without jargon.",
        messages=[
            {"role": "user", "content": question},
        ],
    )

    # The reply comes back as a list of blocks rather than one string, because
    # Claude can return several kinds of content. We want the text ones.
    for block in response.content:
        if block.type == "text":
            print(block.text)

    # Every call is billed by the token, so it is worth seeing the count.
    print(
        f"\n[tokens: {response.usage.input_tokens} in, "
        f"{response.usage.output_tokens} out]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
