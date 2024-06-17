from supabase import create_client, Client
from openai import AsyncOpenAI
import asyncio
import time

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

def insert_chat_message(message, rule):
  query = supabase.table('chat_messages').insert({"message": message, "rules": rule, "sender_id": userid , "receiver_id": ai_profile['id'], "conversations_id": conversationid})
  response = query.execute()
  return response
  
def get_ai_msg(created_at):
  generated_msg = ''
  while True:
    try:
      response = supabase.table('chat_messages').select('*').eq("sender_id", ai_profile['id']).eq("receiver_id", userid).eq("conversations_id", conversationid).gt('created_at', created_at).execute()
      supabase.realtime
      if(len(response.data) == 0 or response.data[0]['message'] is None):
        continue
      else:
        generated_msg = response.data[0]['message']
        break
    except Exception as e:
      print(f"An unexpected error occurred: {e}")
    time.sleep(1)
  return generated_msg

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
  
async def main():
  # The Rules
  rule="This is a conversation via text message."

  # Get My Anon Profile
  anon_profile = get_anon_profile()

  global username
  username = anon_profile['name']

  # Get All AI Profiles
  ai_profiles = get_ai_profiles()
  
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
      result = insert_chat_message(usermsg, rule)
      if len(result.data) == 0:
        print('Failed to insert a message.\n')
        break
      generated_msg = get_ai_msg(result.data[0]['created_at'])
      if generated_msg is not None:
        if generated_msg.strip().startswith("Me:"):
          generated_msg = generated_msg.split(":")[1].strip()
        print(f"\n{ai_profile['name']}: ", generated_msg)
        prompt += f"\n{generated_msg}\n\n{username}:"
        usermsg = await communicate_with_gpt(prompt)
        count += 1
        continue
      else:
        print("Database can't be reached or connection failed!n")
        break
asyncio.run(main())