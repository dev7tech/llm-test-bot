class Prompt:
  def __init__(self, user, ai_profile):
    self.user = user
    self.ai_profile = ai_profile
  
  def introduce_myself(self):
    return f"Your name is {self.user} 32 year old man using a tinder like app.\n"
  
  def context(self):
    return f"You've just encountered a {self.ai_profile['age']} year old {self.ai_profile['gender']} named {self.ai_profile['name']}.\n"

  def greet(self):
    return f"Greet {self.ai_profile['name']} in a charming and humorous way.\n"
  
  def learn_personal_details(self):
    return f"Learn more about {self.ai_profile['name']}'s personal details such as family, hobbies, etc.\n"
  
  def flirt(self):
    return f"Start to flirt by finding common interests with {self.ai_profile['name']}.\n"
                
  def share_experiences(self):
    return "Share your memorable experiences that reveal something personal about you, creating a connection.\n"
  
  def ask_questions(self):
    return f"After sharing the memory, ask a few questions to see if {self.ai_profile['name']} remembers what you said.\n"
  
  def instructions(self):
    return "Ask one question at a time. Keep the response concise and focused. Make sure the conversation flows naturally and stays engaging"
  
  def generate_prompt(self):
    return (
      self.introduce_myself() +
      self.context() +
      self.greet() +
      self.learn_personal_details() +
      self.flirt() +
      self.share_experiences() +
      self.ask_questions() +
      self.instructions()
    )