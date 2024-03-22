import time
from pathlib import Path
from typing import Iterable
import json
import os

import requests
from openai import AzureOpenAI
from openai.types import FileObject
from openai.types.beta import Thread
from openai.types.beta.threads import Run
from openai.types.beta.threads.messages import MessageFile
import logging

import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger ContosoChatAssistant function processed a request.')

    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        id = req_body.get('customerId')
        user_message = req_body.get('question')
        chat_history = req_body.get('chat_history')

    api_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("OPENAI_API_VERSION")
    
    client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=api_endpoint)

    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    assistant = client.beta.assistants.retrieve(assistant_id)
    # if chat_history has at least one item, then we have a thread_id
    if chat_history:
        thread_id = str(chat_history[0])
    
    if thread_id:
        thread = client.beta.threads.retrieve(thread_id)
    else:
        thread = client.beta.threads.create()

    user_message = user_message + ". My customer id is " + str(id)
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_message)

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    print("processing...")
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            formated_messages = format_messages(messages)
            break
        if run.status == "failed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            formated_messages = format_messages(messages)
            # Handle failed
            break
        if run.status == "expired":
            # Handle expired
            break
        if run.status == "cancelled":
            # Handle cancelled
            break
        if run.status == "requires_action":
            call_functions(client, thread, run)
        else:
            time.sleep(5)

    if formated_messages:
        formated_response = {"thread_id": thread.id, "answer": formated_messages}
        return func.HttpResponse(json.dumps(formated_response), status_code=200)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a user message in in the request body for a response.",
             status_code=200
        )


def get_customer_info(id: str) -> str:
    get_customer_api = os.getenv("CUSTOMER_INFO_API")

    # ?id=1&partitionKeyValue=1
    response = requests.get(f"{get_customer_api}?id={id}&partitionKeyValue={id}")
    return json.dumps(response.json())


def call_functions(client: AzureOpenAI, thread: Thread, run: Run) -> None:
    print("Function Calling")
    required_actions = run.required_action.submit_tool_outputs.model_dump()
    print(required_actions)
    tool_outputs = []
    import json

    for action in required_actions["tool_calls"]:
        func_name = action["function"]["name"]
        arguments = json.loads(action["function"]["arguments"])

        if func_name == "get_customer_info":
            output = get_customer_info(id=arguments["id"])
            tool_outputs.append({"tool_call_id": action["id"], "output": output})
        else:
            raise ValueError(f"Unknown function: {func_name}")

    print("Submitting outputs back to the Assistant...")
    client.beta.threads.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)


def format_messages(messages: Iterable[MessageFile]) -> str:
    message_list = []

    # Get all the messages till the last user message
    for message in messages:
        message_list.append(message)
        if message.role == "user":
            break

    # Reverse the messages to show the last user message first
    message_list.reverse()

    # Print the user or Assistant messages or images
    messages_list = []
    for message in message_list:
        for item in message.content:
            # print(f"{message.role}:\n{item.text.value}\n")
            if (message.role == "assistant"):
                messages_list.append(item.text.value)


    return "\n".join(messages_list)
