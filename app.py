from openai import AsyncOpenAI
from supabase import create_client, Client
from dotenv import dotenv_values
from datetime import datetime
import asyncio
import time
import pytz
import os

from Prompt import Prompt
from Conversation import Conversation

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

def get_items():
  response = supabase.table('items').select('*').order('created_at', desc=True).execute()
  return response.data

def insert_chat_message(message, rule, prompt_request = False, sleep_order = False, item_id=None):
  query = supabase.table('chat_messages').insert({"message": message, "rules": rule, "sender_id": userid , "receiver_id": ai_profile['id'], "conversations_id": conversationid, "items_id": item_id,  "sleep_order": sleep_order, "prompt_request": prompt_request})
  response = query.execute()
  return response
  
def get_ai_msg(created_at):
  chat_message = {}
  start_time = datetime.now()
  while True:
    try:
      difference = (datetime.now() - start_time).total_seconds()
      if difference >= 200:
        # insert_test_result(None, conversationid, conversation.get_conversation(), None, f"[Error] {ai_profile['name']} didn't send message in 100s.")
        print("Timed out error! Bot will be turned off.")
        os._exit(0)
      response = supabase.table('chat_messages').select('*').eq("sender_id", ai_profile['id']).eq("receiver_id", userid).eq("conversations_id", conversationid).gt('created_at', created_at).order('created_at', desc=True).limit(1).execute()
      supabase.realtime
      if len(response.data) == 0 or len(response.data[0]['message']) == 0:
        continue
      else:
        chat_message = response.data[0]
        break
    except Exception as e:
      # insert_test_result(None, conversationid, conversation.get_conversation(), None, f"[Error] {e}")
      print(f"An unexpected error occurred: {e}\nBot will be turned off.")
      os._exit(0)
    time.sleep(1)
  return chat_message

async def communicate_with_gpt(prompt, conversation) -> str:
  gpt4_msg = ''
  try:
    response = await open_ai.chat.completions.create(
      messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": conversation}
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
  Rate the following conversation on how human-like it is on a scale of 1 to 10, where 1 is very robotic and 10 is very human-like. Consider the following criteria for your rating:
  - Naturalness of the dialogue flow
  - Use of idiomatic expressions and colloquialisms
  - Relevance and coherence of responses
  - Emotional and empathetic responses
  - Presence of any awkward or unnatural phrasing
  - Consistency in personality and tone
  - Appropriateness and timing of responses
  - Depth of understanding and insight in responses
  - Ability to handle ambiguous or open-ended questions
  - Use of humor and cultural references
  
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
      max_tokens=150
    )
    gpt_response = response.choices[0].message.content
    rating, description = process_test_result(gpt_response)
  except ValueError:
    rating = None
    description = None
  return rating, description

async def main():
  
  # The Rules
  # rule="This is a conversation via text message."
  rule="Imgae testing"
  # Get My Anon Profile
  anon_profile = get_anon_profile()
  # User name
  username = anon_profile['name']
  # Get All AI Profiles
  ai_profiles = get_ai_profiles()
  # Sleep Order
  sleep_order = check_sleep_order()
  # Get All Items
  items = get_items()

  global ai_profile
  for ai_profile in ai_profiles:
    
    # Conversation ID
    global conversationid
    conversationid = get_conversation_id()
    
    if conversationid is None:
      print("Could not find conversation ID")
      os._exit(0)
    
    # Image Testing
    if rule == "Imgae testing":
      print("Image Testing ==>>")
      for item in items:
        print(f"\n{username}:\nMessage: \LORA {item['name']},  Items ID: {item['id']},  Prompt Request: True\n")
        
        # Insert Message into DB
        result = insert_chat_message(f"\LORA {item['name']}", rule, True, True if sleep_order else False, item['id'])
        sleep_order = False
        
        # If failed to insert a message into chat_messages table
        if len(result.data) == 0:
          print('Failed to insert a message.\n')
          break

        # Get response from Huma AI
        chat_message = get_ai_msg(result.data[0]['created_at'])
        generated_msg = chat_message['message']
        ai_image = chat_message['image']
        
        # Display a message generated from Huma AI
        print(f"{ai_profile['name']}:\nMessage: {generated_msg}, Image: {ai_image}\n")
        
    # Conversation via Text message
    else:
      newPrompt = Prompt(username, ai_profile)

      # Generate a Prompt
      global prompt
      prompt = newPrompt.generate_prompt()

      # Generate a Conversation
      global conversation
      conversation = Conversation()

      # Conversation Description
      print(f"\nThis is a conversation between {username} and {ai_profile['name']}:")
      
      # Initial message. You can change as you want.
      usermsg = f"Hello {ai_profile['name']}! How are you?"
      conversation.add_to_conversation(username, usermsg)
      
      while True:
        # Print user message
        print(f"\n{username}: ", usermsg)

        # Insert Message into DB
        result = insert_chat_message(usermsg, rule, False, True if sleep_order else False)
        sleep_order = False

        # If failed to insert a message into chat_messages table
        if len(result.data) == 0:
          print('Failed to insert a message.\n')
          break

        # Get response from Huma AI
        chat_message = get_ai_msg(result.data[0]['created_at'])
        generated_msg = chat_message['message']
        
        # Display a message generated from Huma AI
        print(f"\n{ai_profile['name']}: ", generated_msg)

        # Add to conversation
        conversation.add_to_conversation(ai_profile['name'], generated_msg)

        # If number of messages is 20
        if conversation.get_count() == 30:
          break

        # Generate user message using llm
        usermsg = ""
        while len(usermsg) == 0:
          usermsg = await communicate_with_gpt(prompt, (conversation.get_conversation() + f"{username}:"))
        
        # Add to conversation
        conversation.add_to_conversation(username, usermsg)

      # Rate how the conversation is human-like
      rating, description = await rate_conversation(conversation.get_conversation())
      print("\nRating: ", rating, f"\nDescription: {description}\n")
      
      # Insert test results into DB
      insert_test_result(rating, conversationid, conversation.get_conversation(), None, description)

asyncio.run(main())