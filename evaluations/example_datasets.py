from langsmith import Client
from dotenv import load_dotenv
import os

load_dotenv()

client = Client()

dataset_id = os.getenv("DATASET_ID")


example_inputs = [
    (
        "can you check on the issue - my id is 61e4e",
        "Here’s the status for Ticket #61e4e: Status: Open. Priority: Medium. Description: Your reported issue. Let me know if you need anything else."
    ),
    (
        "what's the status of ticket 12345?",
        "Here’s the status for Ticket #12345: Status: Open. Priority: High. Description: Current issue details. I’m happy to help with next steps."
    ),
    (
        "I’m locked out of my account and can’t log in",
        "I’ve created a support ticket for your sign‑in issue. Ticket ID: 9ab12. We’ll investigate and follow up shortly."
    ),
    (
        "email notifications stopped working",
        "I’ve created a support ticket for your email notification issue. Ticket ID: 83cde. We’ll review logs and get back to you soon."
    ),
    (
        "hi there",
        "Hi! How can I help you today? If you’re asking about a past issue, please share your 5‑character ticket ID (e.g., 12345)."
    ),
    (
        "can you look up my last case?",
        "I can help with that. Please provide your 5‑character ticket ID (e.g., 12345) so I can pull up the details."
    ),
    (
        "Ticket 12346 — any updates?",
        "Here’s the status for Ticket #12346: Status: Closed. Priority: Medium. Description: Email notification not working. Let me know if you’d like to reopen."
    ),
    (
        "My dashboard loads really slowly lately",
        "I’ve created a support ticket for your slow dashboard issue. Ticket ID: 7f1a0. We’ll investigate performance and update you."
    ),
    (
        "uploading a profile picture fails",
        "I’ve created a support ticket for your upload issue. Ticket ID: 0bcd2. We’ll analyze the error and follow up with a fix."
    ),
    (
        "What does open mean on my ticket 12347?",
        "Ticket #12347 is currently Open. That means we’re actively investigating. I’ll share updates as soon as they’re available."
    ),
    (
        "close my ticket 12345 please",
        "I can help with that. To proceed, please confirm you’d like Ticket #12345 closed."
    ),
    (
        "thanks!",
        "You’re welcome! If you need anything else, just let me know."
    ),
]

# Convert to LangSmith example schema
inputs = [{"message_content": q, "username": "test_user"} for q, _ in example_inputs]
outputs = [{"output": a} for _, a in example_inputs]

client.create_examples(dataset_id=dataset_id, inputs=inputs, outputs=outputs)