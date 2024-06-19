from supabase import create_client, Client
from openai import AsyncOpenAI
import asyncio
import time
from datetime import datetime
import pytz
import os
from dotenv import dotenv_values

env_vars = dotenv_values('.env')
api_key: str = env_vars.get("OPENAI_API_KEY")
url: str = env_vars.get("SUPABASE_URL")
key: str = env_vars.get("SUPABASE_KEY")
userid: str = env_vars.get("USER_ID")

open_ai = AsyncOpenAI(api_key=api_key)
supabase: Client = create_client(url, key)

def get_anon_profile():
  response = supabase.table('anon_profiles').select('*').eq('id', userid).execute()
  return response.data[0]

def get_ai_profiles():
  response = supabase.table('ai_profiles').select('*').order('created_at', desc=True).execute()
  return response.data

def get_latest_message_time():
  response = supabase.table('chat_messages').select('created_at').order('created_at', desc=True).limit(1).execute()
  return response.data[0]['created_at']

def check_sleep_order():
  current_time = pytz.utc.localize(datetime.utcnow())
  date_format = "%Y-%m-%dT%H:%M:%S.%f%z"
  latest_msg_time = datetime.strptime(get_latest_message_time(), date_format)
  time_difference = (current_time - latest_msg_time).total_seconds() / 60
  if time_difference >= 30:
    return True
  else:
    return False   

def generate_scenario():
  scenario = f"""
  Your name is {username}, a 32-year-old man who enjoys reminiscing about past experiences.
  You've just encountered a {ai_profile['age']} year old {ai_profile['gender']} named {ai_profile['name']} on a Tinder-like app.
  You want to great warmly and then share a memorable experience that reveals something personal about you, creating a connection.
  After sharing the memory, you want to ask a few questions to see if {ai_profile['name']} remembers what you said.
  Make sure the conversation flows naturally and stays engaging.
  """
  return scenario

def check_row_exists():
  try:
    query = supabase.table("conversations").select('id').eq('ai_profiles_id', ai_profile['id']).eq('anon_profiles_id', userid)
    response = query.execute()
    if len(response.data) == 0:
      raise Exception()
    return response.data[0]['id']
  except Exception as e:
    return None

def get_conversation_id():
  existing_row = check_row_exists()
  if existing_row is None:
    query = supabase.table("conversations").insert({"ai_profiles_id": ai_profile['id'], "anon_profiles_id": userid})
    response =  query.execute()
    if len(response.data) == 0:
      print("Inserting a row into table failed.")
      return None
    else:
      print("Inserting a row into table succeed.")
      return response.data[0]['id']
  else:
    return existing_row

def insert_chat_message(message, rule, sleep_order = False):
  query = supabase.table('chat_messages').insert({"message": message, "rules": rule, "sender_id": userid , "receiver_id": ai_profile['id'], "conversations_id": conversationid, "sleep_order": sleep_order})
  response = query.execute()
  return response
  
def get_ai_msg(created_at):
  chat_message = {}
  start_time = datetime.now()
  while True:
    try:
      difference = (datetime.now() - start_time).total_seconds()
      if difference >= 180:
        insert_test_result(None, conversationid, conversation, None, f"[Error] {ai_profile['name']} didn't send message in 180s.")
        print("Timed out error! Bot will be turned off.")
        os._exit(0)
      response = supabase.table('chat_messages').select('id', 'conversations_id', 'message').eq("sender_id", ai_profile['id']).eq("receiver_id", userid).eq("conversations_id", conversationid).gt('created_at', created_at).order('created_at', desc=True).limit(1).execute()
      supabase.realtime
      if len(response.data) == 0 or len(response.data[0]['message']) == 0:
        continue
      else:
        chat_message = response.data[0]
        break
    except Exception as e:
      insert_test_result(None, conversationid, conversation, None, f"[Error] {e}")
      print(f"An unexpected error occurred: {e}\nBot will be turned off.")
      os._exit(0)
    time.sleep(1)
  return chat_message

async def communicate_with_gpt(prompt) -> str:
  gpt4_msg = ''
  try:
    response = await open_ai.chat.completions.create(
      messages=[
        {"role": "system", "content": scenario},
        {"role": "user", "content": prompt}
      ],
      model="gpt-4",
      max_tokens=100
    )
    gpt4_msg = response.choices[0].message.content.strip()
  except Exception as e:
    print(f"\nAn error occured: {e}")
  return clear_message(gpt4_msg)

def clear_message(generated_msg):
  message = []
  for index, line in enumerate(generated_msg.split('\n')):
    if index == 1:
      break    
    if not line.strip():
      continue
    message = line.strip()
  return message
  
def insert_test_result(result, conversations_id, conversation, chat_messages_id, description):
  supabase.table('test_results').insert({"result": result,"conversations_id": conversations_id, "conversation": conversation, "chat_messages_id": chat_messages_id, "description": description}).execute()

def process_test_result(gpt_response):
  gpt_response = gpt_response.split("\n")
  rating = gpt_response[0]
  description = gpt_response[1]
  return rating, description  

async def rate_conversation(conversation):
  prompt = f"""
  Rate the following conversation on how human-like it is on a scale of 1 to 10, where 1 is very robotic and 10 is very human-like. When providing your rating, consider the following criteria:
  - Naturalness of the dialogue flow
  - Use of idiomatic expressions and colloquialisms
  - Relevance and coherence of responses
  - Emotional and empathetic responses
  - Presence of any awkward or unnatural phrasing
  
  Please provide your rating as a single number or a decimal (e.g., 9.5, 10, 9, 8.5) without any additional text.
  
  Conversation:
  {conversation}
  
  Rating:
  Reasoning:
  """
  
  try:
    response = await open_ai.chat.completions.create(
      messages=[
        {"role": "user", "content": prompt},
      ],
      model="gpt-4",
      max_tokens=100
    )
    gpt_response = response.choices[0].message.content
    rating, description = process_test_result(gpt_response)
  except ValueError:
    rating = None
    description = None
  return rating, description

async def main():
  
  # The Rules
  rule="This is a conversation via text message."
  # Get My Anon Profile
  anon_profile = get_anon_profile()
  # User name and Global It
  global username
  username = anon_profile['name']
  # Get All AI Profiles
  ai_profiles = get_ai_profiles()
  # Sleep Order
  sleep_order = check_sleep_order()
  
  global scenario
  # scenario = f" Your name is {username}, 32 year old man using a tinder like app to meet with strangers."
  
  global ai_profile
  for ai_profile in ai_profiles:
    
    # scenario += f"""
    # You've just encountered a {ai_profile['age']} year old {ai_profile['gender']} named {ai_profile['name']}.
    # You want to great warmly and then plan to learn more about {ai_profile['name']}'s personal details.
    # Then you start to flirt by finding common interests.
    # Keep the response concise and to the point.
    # """
    # Generate a Scenario
    scenario = generate_scenario()    
    
    # Conversation Description
    print(f"\nThis is a conversation between {username} and {ai_profile['name']}:")
    # Conversation ID and Global It
    global conversationid
    conversationid = get_conversation_id()
    # The First User message
    usermsg = f"Hello {ai_profile['name']}! How is everything going?"
    # A Variable To Count Number Of Messages
    count = 0
    # Define a prompt
    prompt = ""
    # Define a conversation
    global conversation
    conversation = ""
    
    while(conversationid is not None):
      
      # Print message
      print(f"\n{username}: ", usermsg)
      # Update prompt
      prompt += f"\n{username}:\n{usermsg}\n\n"
      # Update conversation List
      conversation += f"{username}: {usermsg}\n"
      # Insert a message into chat_messages table
      result = insert_chat_message(usermsg, rule, True if sleep_order else False)
      sleep_order = False
      # If failed to insert a message into chat_messages table
      if len(result.data) == 0:
        print('Failed to insert a message.\n')
        break
      # Get response from Huma AI
      chat_message = get_ai_msg(result.data[0]['created_at'])
      generated_msg = chat_message['message']
      # If message from huma is not empty
      if len(generated_msg) != 0:
        if generated_msg.startswith("Me:"):
          insert_test_result(None, conversationid, conversation, chat_message["id"], f"[Error] Message from {ai_profile['name']} starts with 'ME:'")
          generated_msg = generated_msg.split(":")[1].strip()
        # Print message
        print(f"\n{ai_profile['name']}: ", generated_msg)
        # Update prompt
        prompt += f"{ai_profile['name']}:\n{generated_msg}\n"
        # Update conversation List
        conversation += f"{ai_profile['name']}: {generated_msg}\n"
        
        count += 1
        # Limit number of messages to 10
        if count == 10:
          break
        # Get response from LLM(gpt-4) with a prompt
        usermsg = ''
        while(len(usermsg) == 0):
          usermsg = await communicate_with_gpt(prompt + f"\n{username}:")
        continue
      # If message from huma is empty
      else:
        insert_test_result(None, conversationid, conversation, chat_message["id"], f"[Error] {ai_profile['name']} sent an empty message!")
        print("No message error occured! Bot will be turned off.")
        # Exit
        os._exit(0)
        
    rating, description = await rate_conversation(conversation)
    print("\nRating: ", rating, f"\n\nDescription: {description}")
    insert_test_result(rating, conversationid, conversation, None, description)
asyncio.run(main())