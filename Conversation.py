class Conversation:
  def __init__(self):
    self.conversation = ""
    self.count = 0
    
  def add_to_conversation(self, user, message):
    self.conversation += f"{user}: {message}\n"
    self.count += 1
    
  def get_conversation(self):
    return self.conversation
  
  def get_count(self):
    return self.count