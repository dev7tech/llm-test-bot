class LLMScenario:
  def __init__(self, user, context):
    self.user = user
    self.context = context
    self.prompts = []
    self.prompt = ""
    self.history = ""
    self.prompt_index = 0
    self.count = 0

  def set_prompt_list(self, prompts):
    self.prompts = prompts

  def set_prompt(self):
    self.prompt = f"""
    Context: {self.context}
    Instructions: {self.prompts[self.prompt_index]['content']}
    """
    print(f"\n{self.prompts[self.prompt_index]['description']}:\n")
  
  def add_prompt(self, prompt):
    self.prompts.append(prompt)

  def add_to_history(self, user, message):
    self.history += f"{user}: {message}\n"
    self.count += 1
    if self.count == 10:
      self.prompt_index += 1
      if self.prompt_index == len(self.prompts):
        return False
      self.count = 0
      self.set_prompt()
    return True

  def get_history(self):
    return self.history
  
  async def run_scenario(self, llm):
    gpt_msg = ''
    while len(gpt_msg) == 0:
      gpt_msg = await llm(self.prompt, self.history + f"{self.user}: ")
    response = self.add_to_history(self.user, gpt_msg)
    return gpt_msg, response