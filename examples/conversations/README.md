# Conversation examples

This directory must contain three to five genuine English conversations before
challenge delivery. No real-model conversations have been recorded or claimed yet:
provider verification is currently **BLOCKED** by the missing Gemini API key.
This README is a recording plan, not one of the required conversations.

After configuring the key and loading the original data, start an English session:

```sh
python -m emporio_music chat --language en --show-tools
```

Record actual user messages and actual model replies without rewriting them into
ideal answers. Include the execution date, model identifier, source snapshot,
relevant tool/source references, and a factual verification note. Remove credentials
and personal customer information. If a reply is incorrect, preserve that finding
in the validation evidence and correct the implementation before delivery.

Suggested coverage for five recordings:

1. Ask for available acoustic guitars under BRL 1000 and continue with a reference
   to a previously suggested product. Verify category, price, availability, and
   cross-turn context against the source CSVs.
2. Ask about the Takamine GD20, then about an active promotional instrument and
   whether PIX can be combined with its discount. Verify exact arithmetic and
   policy page 6. This provides a nontrivial data-and-policy scenario.
3. Ask for the store address and opening hours. Verify policy page 2; ask for a
   contact number to check transparent handling of conflicting pages 1–2 and 6.
4. Say that you regret a purchase and want to return it. Verify that the agent
   asks for necessary purchase/receipt/condition information and does not claim
   to have processed a return or refund.
5. Ask a question outside the store scope and then search for a nonexistent model.
   Verify polite redirection, a truthful no-result response, and no invented offer.

Use `/reset` or a fresh process between independent sessions. Session context is
in memory only; persistent conversation history is an optional project feature.
Scripted prompts, mocked provider replies, tool JSON outputs, and these instructions
do not satisfy the requirement for real model conversations.
