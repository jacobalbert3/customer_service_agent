#!/usr/bin/env python3
"""Customer Service Chatbot"""

import uuid
import os
import re
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from database import init_database, lookup_ticket, add_user, add_ticket
from langsmith import traceable, trace, Client
from langchain_core.prompts import ChatPromptTemplate
from langsmith.client import convert_prompt_to_openai_format

load_dotenv()

init_database()

ls_client = Client(api_key=os.getenv("LANGCHAIN_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@traceable(
    run_type="llm",
    metadata={"ls_model_name": "gpt-4o", "ls_provider": "openai"}
)
def call_openai(messages: list, model: str = "gpt-4o", temperature: float = 0.1) -> list:
    """Make call to OpenAI API"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    
    return [response.choices[0].message.role, response.choices[0].message.content]


#explicit prompt example (no push/pull from hub)
@traceable
def classify_request(message_content: str) -> Dict[str, str]:
    """Classify user's request and extract ticket ID if present"""
    classification_prompt = f"""
    Analyze this customer service message and classify it:
    Content: {message_content}
    
    Classification rules:
    - "ticket_info": If the user is asking about a past issue or a specific ticket
    - "ticket_request": If the user wants to create a new support ticket (they state a current problem)
    - "other": For casual conversation, greetings, or non-support related messages
    
    IMPORTANT: If the message contains a 5-character alphanumeric ticket ID (like 12345 or 61e4e), extract it as ticket_id.
    If no 5-character ticket ID is found, set ticket_id to null.
    
    Respond with JSON format:
    {{
        "intent": "one of: ticket_info, ticket_request, other",
        "summary": "brief summary of the message",
        "ticket_id": "5-digit number or null"
    }}
    """
    
    response = call_openai([{"role": "user", "content": classification_prompt}])
    
    response_content = response[1] if isinstance(response, list) else response
    
    # Parse JSON response
    try:
        json_match = re.search(r'\{[^}]*"intent"[^}]*\}', response_content, re.DOTALL)
        if json_match:
            classification = json.loads(json_match.group())
        else:
            # Fallback parsing
            lines = response_content.strip().split('\n')
            intent = "other"
            summary = response_content[:100]
            ticket_id = None
            
            for line in lines:
                if '"intent"' in line.lower():
                    intent_match = re.search(r'"intent":\s*"([^"]+)"', line)
                    if intent_match:
                        intent = intent_match.group(1)
                elif '"summary"' in line.lower():
                    summary_match = re.search(r'"summary":\s*"([^"]+)"', line)
                    if summary_match:
                        summary = summary_match.group(1)
                elif '"ticket_id"' in line.lower():
                    ticket_match = re.search(r'"ticket_id":\s*"([^"]+)"', line)
                    if ticket_match:
                        ticket_id = ticket_match.group(1)
                        # Convert "null" string to None
                        if ticket_id.lower() == "null":
                            ticket_id = None
            
            classification = {"intent": intent, "summary": summary, "ticket_id": ticket_id}
    except:
        classification = {"intent": "other", "summary": message_content[:100], "ticket_id": None}
    
    # Fallback: Try to extract 5-character alphanumeric ticket ID directly from message
    if not classification.get("ticket_id") or classification.get("ticket_id") == "null":
        ticket_pattern = r'\b([a-zA-Z0-9]{5})\b'
        ticket_match = re.search(ticket_pattern, message_content)
        if ticket_match:
            classification["ticket_id"] = ticket_match.group(1)
    
    return classification




def convert_doc(search_results: List[str]) -> List[Dict[str, Any]]:
    """Convert search results to a list of retriever-friendly documents."""
    return [
        {"page_content": doc, "type": "text", "metadata": {"source": "database"}}
        for doc in search_results
    ]



@traceable(
    run_type="retriever",
    metadata={"retriever": "ticket_lookup", "source": "sqlite"}
)
def search_ticket(ticket_id: Optional[str], username: str) -> List[Dict[str, Any]]:
    """Check if ticket ID exists and look up ticket"""
    if ticket_id:
        # User provided ticket ID, look it up
        try:
            ticket_data = lookup_ticket(ticket_id, username)
            if ticket_data:
                search_results = [
                    f"**Ticket #{ticket_data['ticket_id']} Status**",
                    f"Status: {ticket_data['status'].title()}",
                    f"Priority: {ticket_data['priority'].title()}",
                    f"Description: {ticket_data['description']}",
                    f"Created: {ticket_data['created_at']}",
                    f"Last Updated: {ticket_data['updated_at']}"
                ]

            else:
                search_results = [
                    f"Ticket #{ticket_id} not found for user '{username}'. Please check your ticket number and try again."
                ]
        except Exception as e:
            search_results = [f"Error querying ticket information: {str(e)}"]
    else:
        # No ticket ID provided, ask for it
        search_results = [
            "I understand you're asking about a past issue or ticket. Please provide your 5-digit ticket ID number so I can look up the details for you."
        ]
    
    return convert_doc(search_results)

def create_ticket(description: str, username: str) -> Dict[str, Any]:
    """Create a new ticket for the customer request"""
    # Generate ticket details
    ticket_id = f"{uuid.uuid4().hex[:5]}"  # 5-character ticket ID
    

    with trace(
        name="create_ticket",
        run_type="chain",
        inputs={"new_ticket_id": ticket_id, "description": description, "username": username},
        metadata={"example_metadata": "hello!"} #partial trace
    ) as ls_trace:
    # Add user to database if they don't exist
        add_user(username)
        
        # Create the ticket in the database
        success = add_ticket(
            ticket_id=ticket_id,
            username=username,
            status="open",
            description=description,
            priority="medium"  # Default
        )
        ls_trace.end(outputs={"example_output": "Finished creating ticket"})
    
    if success:
        # Return ticket details
        search_results = [
            f"**New Ticket Created Successfully**",
            f"Ticket ID: {ticket_id}",
            f"Status: Open",
            f"Priority: Medium",
            f"Description: {description}",
            f"Created for: {username}"
        ]
        return {
            "ticket_id": ticket_id,
            "search_results": search_results,
            "success": True
        }
    else:
        # Return error message
        search_results = ["Error creating ticket in database. Please try again or contact support."]
        return {
            "search_results": search_results,
            "success": False
        }

@traceable
def write_response(message_content: str, intent: str, summary: str, search_results: List[Dict[str, Any]], 
                  ticket_id: Optional[str] = None) -> str:
    """Generate response using context from previous steps"""
    
    # Determine the context and build appropriate response)
    context_sections = []
    response_guidelines = []

    if intent == "ticket_info":
        # Ticket lookup results
        if search_results:
            # Support both retriever-style dict docs and plain strings
            formatted_docs = "\n".join([
                f"- {d['page_content']}" if isinstance(d, dict) and 'page_content' in d else f"- {d}"
                for d in search_results
            ])
            context_sections.append(f"**Ticket Information:**\n{formatted_docs}")
            response_guidelines.append("Present the ticket information clearly")
            response_guidelines.append("Be helpful and professional")
            response_guidelines.append("Offer additional assistance if needed")
        else:
            response_guidelines.append("Acknowledge their ticket inquiry")
            response_guidelines.append("Let them know you're ready to help")

    elif intent == "ticket_request":
        # Ticket creation
        if ticket_id:
            context_sections.append(f"**New Ticket Created:**\nTicket ID: {ticket_id}")
            response_guidelines.append("Confirm the ticket has been created")
            response_guidelines.append("Provide the ticket ID for their reference")
            response_guidelines.append("Explain next steps or timeline")
        else:
            response_guidelines.append("Acknowledge their ticket request")
            response_guidelines.append("Explain the ticket creation process")

    else:  # intent == "other"
        # Direct chatbot flow
        response_guidelines.append("Respond naturally and helpfully")
        response_guidelines.append("Be conversational and friendly")

    

    #**** PULL PROMPT FROM HUB ****
    context_sections = chr(10).join(context_sections) if context_sections else ""
    response_guidelines =chr(10).join([f"- {guideline}" for guideline in response_guidelines])
    written_prompt= ls_client.pull_prompt("write_response_prompt_v2") 

    formatted_prompt = written_prompt.invoke({
        "message_content": message_content,
        "intent": intent,
        "summary": summary,
        "context_sections": "\n".join(context_sections),
        "response_guidelines": "\n".join(response_guidelines),
    })

    messages = convert_prompt_to_openai_format(formatted_prompt)["messages"]

    draft_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2,
    )

    #**** PUSH PROMPT TO HUB ****
    #prompt_template = ChatPromptTemplate.from_template(draft_prompt)
    #ls_client.push_prompt("write_response_prompt", object=prompt_template)

    # Extract content from [role, content] format
    return draft_response.choices[0].message.content

@traceable
def process_customer_message(message_content: str, username: str) -> str:
    """Main function to process customer messages"""
    
    # Step 1: Classify the request
    classification = classify_request(message_content)
    intent = classification.get("intent", "other")
    summary = classification.get("summary", "")
    ticket_id = classification.get("ticket_id")
    
    # Step 2: Route based on intent
    search_results = []
    final_ticket_id = None
    
    if intent == "ticket_info":
        search_results = search_ticket(ticket_id, username)
        
    elif intent == "ticket_request":
        ticket_result = create_ticket(summary, username)
        search_results = ticket_result["search_results"]
        final_ticket_id = ticket_result.get("ticket_id")
        
    else:  # intent == "other"
        search_results = []
    
    # Step 3: Generate response
    response = write_response(
        message_content=message_content,
        intent=intent,
        summary=summary,
        search_results=search_results,
        ticket_id=final_ticket_id
    )
    
    return response


# Interactive terminal interface
if __name__ == "__main__":
    print("Customer Service Chatbot")
    print("=" * 50)
    print()
    
    # Get username
    username = input("Enter your username: ").strip()
    if not username:
        username = "guest"
    
    print(f"Welcome, {username}!")
    print()

    #create thread id 
    thread_id = uuid.uuid4()
    
    while True:
        try:
            # Get user input
            user_input = input(f"{username}: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye! Have a great day!")
                break
            
            # Skip empty input
            if not user_input:
                continue
            
            # Process the message
            print("Processing...")
            response = process_customer_message(user_input, username, langsmith_extra = {"metadata": {"thread_id": thread_id}})
            
            # Display response
            print(f"Bot: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! Have a great day!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Please try again or type 'quit' to exit.")
            print()
