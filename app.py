from supabase import create_client, Client
from openai import AsyncOpenAI
import asyncio
import time
from datetime import datetime
import pytz
import os

open_ai = AsyncOpenAI(api_key="sk-proj-QAKYkuXwcgLdih99nJ9lT3BlbkFJmLMfrcezDHUvsV2TkK5d")
url: str = "https://ghmpkmcrsedpizfwgcqr.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdobXBrbWNyc2VkcGl6ZndnY3FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDc5NDYyMDcsImV4cCI6MjAyMzUyMjIwN30.xZLK0E6bjfy6UoKqwZkZCs38L6uXJd8-VkknTmX2ULg"
supabase: Client = create_client(url, key)

userid = "f018ee62-9fa5-5f34-9e62-724f1b40f75a"

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
      if difference >= 60:
        insert_test_result(None, conversationid, None, "Huma AI didn't send message in 60s.")
        print("Timed out error! Your Bot will be turned off soon.")
        os._exit(0)
      response = supabase.table('chat_messages').select('id', 'conversations_id', 'message').eq("sender_id", ai_profile['id']).eq("receiver_id", userid).eq("conversations_id", conversationid).gt('created_at', created_at).execute()
      supabase.realtime
      if len(response.data) == 0:
        continue
      else:
        chat_message = response.data[0]
        break
    except Exception as e:
      print(f"An unexpected error occurred: {e}")
    time.sleep(1)
  return chat_message

async def communicate_with_gpt(prompt) -> str:
  gpt4_msg = ''
  try:
    response = await open_ai.chat.completions.create(
      messages=[
        {"role": "system", "content": f"Your name is {username}, 32 year old man using a tinder like app to meet with strangers. You've just encountered a {ai_profile['age']} yo {ai_profile['gender']} named {ai_profile['name']}. You want to great warmly and then learn more about {ai_profile['name']}'s personal details. Then you start to flirt by finding common interests. Keep the response concise and to the point."},
        {"role": "user", "content": prompt}
      ],
      model="gpt-4"
    )
    gpt4_msg = response.choices[0].message.content.strip()
  except Exception as e:
    print(f"An error occured: {e}")
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

def get_ai_profiles():
  response = supabase.table('ai_profiles').select('*').execute()
  return response.data

def get_anon_profile():
  response = supabase.table('anon_profiles').select('*').eq('id', userid).execute()
  return response.data[0]
  
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

def insert_test_result(result, conversation_id, chat_message_id, description):
  supabase.table('test_results').insert({"conversations_id": conversation_id, "chat_messages_id": chat_message_id, "description": description}).execute()

async def main():
  # The Rules
  rule="This is a conversation via text message."

  # Get My Anon Profile
  anon_profile = get_anon_profile()

  global username
  username = anon_profile['name']

  # Get All AI Profiles
  ai_profiles = get_ai_profiles()
  
  sleep_order = check_sleep_order()
  
  global ai_profile
  for ai_profile in ai_profiles:    
    # Conversation Description
    print(f"\nThis is a conversation between {username} and {ai_profile['name']}:")

    # Conversation ID and Global It
    global conversationid
    conversationid = get_conversation_id()
    
    usermsg = f"Hi {ai_profile['name']}! How are you?"
    
    # A Variable To Count Number Of Messages
    count = 0
    
    prompt = f"\n{username}:"
    while(conversationid is not None):
      if count == 5:
        break
      print(f"\n{username}: ", usermsg)
      prompt += f"\n{usermsg}\n\n{ai_profile['name']}:"
      result = insert_chat_message(usermsg, rule, True if sleep_order else False)
      sleep_order = False
      if len(result.data) == 0:
        print('Failed to insert a message.\n')
        break
      chat_message = get_ai_msg(result.data[0]['created_at'])
      generated_msg = chat_message['message'].strip()
      if generated_msg is not None:
        if generated_msg.startswith("Me:"):
          insert_test_result(chat_message['message'], chat_message['conversations_id'], chat_message['id'], "Message from Huma AI starts with 'ME':")
          generated_msg = generated_msg.split(":")[1].strip()
        print(f"\n{ai_profile['name']}: ", generated_msg)
        prompt += f"\n{generated_msg}\n\n{username}:"
        usermsg = await communicate_with_gpt(prompt)
        count += 1
        continue
      else:
        insert_test_result(chat_message['message'], chat_message['conversations_id'], chat_message['id'], "Huma AI sent no message!")
        print("Noe message error occured! Your Bot will be turned off soon.")
        os._exit(0)
asyncio.run(main())