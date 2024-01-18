import random
from typing import Dict, List

import autogen
from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import AssistantAgent
from autogen.agentchat.groupchat import GroupChat

print(autogen.__version__)

# The default config list in notebook.
config_list = [
    {
        "model": "gpt-4",
        "api_key": "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"
    }
]

llm_config = {"config_list": config_list, "cache_seed": 42}

class CustomGroupChat(GroupChat):
    def __init__(self, agents, messages, max_round=10):
        super().__init__(agents, messages, max_round)
        self.previous_speaker = None  # Keep track of the previous speaker

    def select_speaker(self, last_speaker: Agent, selector: AssistantAgent):
        # Check if last message suggests a next speaker or termination
        last_message = self.messages[-1] if self.messages else None
        if last_message:
            if "NEXT:" in last_message["content"]:
                suggested_next = last_message["content"].split("NEXT: ")[-1].strip()
                print(f"Extracted suggested_next = {suggested_next}")
                try:
                    return self.agent_by_name(suggested_next)
                except ValueError:
                    pass  # If agent name is not valid, continue with normal selection
            elif "TERMINATE" in last_message["content"]:
                try:
                    return self.agent_by_name("User_proxy")
                except ValueError:
                    pass  # If 'User_proxy' is not a valid name, continue with normal selection

        team_leader_names = [agent.name for agent in self.agents if agent.name.endswith("1")]

        # when the product manager (A2) sends to the architect (A1), we want to then proceed to Team B and not come back to the PM
        # if ((last_speaker.name == "A1") and (self.previous_speaker.name == "A2")):
        #   possible_next_speakers = [self.agent_by_name("B1")]
        # elif:


        if last_speaker.name in team_leader_names:
            team_letter = last_speaker.name[0]
            possible_next_speakers = [
              agent
              for agent in self.agents if
              (agent.name.startswith(team_letter) or agent.name in team_leader_names)
              and agent != last_speaker
              and agent != self.previous_speaker
          ]
        else:
            team_letter = last_speaker.name[0]
            possible_next_speakers = [
                agent
                for agent in self.agents if
                agent.name.startswith(team_letter)
                and agent != last_speaker
                and agent != self.previous_speaker
            ]

        if self.previous_speaker is not None:
          print(f"*** SPEAKERS\nPrevSpeaker: {self.previous_speaker.name}, LastSpeaker:{last_speaker.name}, PossibleNextSpeakers = {[a.name for a in possible_next_speakers]}\n***")

        self.previous_speaker = last_speaker

        if possible_next_speakers:
            next_speaker = random.choice(possible_next_speakers)
            return next_speaker
        else:
            return None

# Termination message detection
def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "TERMINATE" in content["content"]:
        return True
    return False

how_you_behave = """How you behave:
- Take your time to think and work in a step by step manner.
- Be very business-like and to the point in your communications, to get the job completed satisfactorily in the least possible time.
- Avoid back and forth chatter. Complete your steps and then respond. Clearly indicate who you need response(s) from.
- DO NOT show gratitude.
- To suggest the next speaker to be A1 end your message with NEXT: A1
"""

# Initialization
agents_A = [
    AssistantAgent(
        name="A1",
        description="Enterprise Application Architect",
        system_message="""
Your role:
-You are an expert Enterprise Application Architect and are a Domain Driven Design practitioner.
-You follow the methodologies and patterns described by Martin Fowler, Eric Evans, and Vaughn Vernon.
Your skills:
- You are skilled at designing enterprise applications and finalizing the architecture of enterprise applications and creating a design document with all necessary components to allow the development team to work in parallel on developing the application.
What you do:
- You work with a product manager to get their buy-in on the architecture you are proposing to ensure it meets all the Product Manager's business requirements.
- You work with the development team consisting of the Engineering Manager; Backend, Frontend, and Quality Assurance Engineers to ensure the architecture and design you are producing and documenting are clearly understood by them and implementable by them.
- You incorporate any changes that come out of your conversations with the team, into the document, before finalizing the requirements document.
- Once they produce working code, you review the code to ensure it meets the requirements stated by the Product Manage, and the architectural requirements you set forth You suggest changes for the development team to make if needed, so the code can be updated and presented to you for review again.
- DO NOT suggest concrete code.
Your responsibilities:
- YOU are responsible for creating the design document, in markdown format. Make sure it contains details on all the enterprise application layers - typically the presentation, application, domain model, and infrastructure layers.
- Make sure all the details and choice of various enterprise application patterns for all the layers of the application are included.
- The development team should be able to implement the application independent of your participation, once this document is produced.
- SAVE the design document in a file named “design_document.md”, on disk, when it is completed.
""" + how_you_behave,
        llm_config=llm_config,
    ),
    AssistantAgent(
        name="A2",
        description="Product Manager",
        system_message="""
Your role:
- You are a Product Manager working to build highly scalable web applications that are very intuitive and easy to use, offering business users an excellent user experience.
Your skills:
- You have extensive experience representing the end-user (employees in large corporations) perspective on how business processes work and the various systems’ requirements associated with them.
- You present comprehensive requirements in the form of easy to understand but comprehensively defined user stories. The user stories in-turn contain use-cases covering all happy path and exception path scenarios
What you do:
- Work with the other team members to resolve any questions on requirements and to ensure they have a clear understanding.
- The team members typically include one or more of the following - Enterprise Application Architect, Engineering Manager, Backend Engineer, Frontend Engineer, Quality Assurance Engineer.
Your responsibilities:
- You are responsible for laying out the requirements for the enterprise applications we are building and for the final interpretation of any requirements.
- After you have clarified the requirements to the team, write down the final requirements to a file named “final_requirements.md”, in markdown format, on disk. If you don’t know how to write (or read) a file to (or from) the disk, ask the development team to help you.
- Depending on whether you only asked for a design or if you asked for a full working application, ONLY when your requirement is fully met, say out that the project is complete and append a new line with the word TERMINATE to your message.
""" + how_you_behave,
        llm_config=llm_config,
    )
]

dev_test_skills_what_they_do = """Your skills:
- You are very familiar with implementation of various Enterprise Application Architecture patterns. You are also very familiar with the best practices of Testing that can catch all the important corner cases.
- You solve tasks using your coding and language skills.
- You are an expert in the Python programming language. You are very familiar with a number of the popular libraries including pydantic, pytest, fastapi, and django.
- You write fully type specified code leveraging the Typing library, and use a functional programming style.
- You also are an expert in writing unix and windows shell scripts for you or others to execute.
What you do:
- You will work on the specifications provided by the Enterprise System Architect to write code for various parts of the application.
- When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, write a file to disk, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
- When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
- Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
- When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
- If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
- If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
- When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
"""

agents_B = [
    AssistantAgent(
        name="B1",
        description="Engineering Manager",
        system_message="""
Your role:
- You are a very experienced Engineering Manager.
Your skills:
- Breaking down a large body of work into smaller chunks and creating a work plan. You clearly identify the task with a number and the resource who is to work on it. You keep track of the status of each of the task to ensure they all finally get completed.
- Coordinating the tasks in the work plan among team members and ensuring they complete their assigned tasks.
What you do:
- You work with a team that typically has a Product Manager, Backend Engineer, Frontend Engineer, and a Quality Assurance Engineer to execute on your work breakdown plan.
- You talk to the Product Manager and the Enterprise Application Architect for any clarifications on the requirements or design.
- You provide feedback on the architectural assumptions or if the design need to be modified.
- You use the development engineers to check each other's work for mistakes.
Your responsibilities:
- You are responsible for coming up with the plan that includes the work break down structure and assignee
- Write this plan to a file named “work_plan.md”, in markdown format, on disk
- You are responsible for the engineers developing a high quality working application that meets the business and architectural requirements received from the Product Manager and Enterprise Application Architect.
- When it is time to publish the detailed design document, you are responsible to ensure that gets created and written to disk in a file called "detailed_design.md", in markdown format.
""" + how_you_behave,
        llm_config=llm_config, code_execution_config=False,
    ),
    AssistantAgent(
        name="B2",
        description="Backend Engineer",
        system_message="""Your role:
- You are an expert backend engineer.""" + dev_test_skills_what_they_do + """Your responsibilities:
- You deliver fully working, high quality, code that completely meets the requirement of the task that was assigned to you by the Engineering Manager.
""" + how_you_behave,
        llm_config=llm_config, code_execution_config=False,
    ),
    AssistantAgent(
        name="B3",
        description="Quality Assurance Engineer",
        system_message="""Your role:
- You are an expert quality assurance engineer.""" + dev_test_skills_what_they_do + """Your responsibilities:
- You deliver high quality unit, system, integration, and functional tests that completely meets the requirement of the task that was assigned to you by the Engineering Manager.
""" + how_you_behave,
        llm_config=llm_config, code_execution_config=False,
    ),
]

# code execution assistant
code_executor = autogen.UserProxyAgent(
    name="code_executor",
    system_message="A user that can run Python code or input command line commands at a Linux terminal and report back the execution results.",
    code_execution_config={"work_dir": "coding"},
    is_termination_msg=is_termination_msg,
    human_input_mode="NEVER",
)

# Terminates the conversation when TERMINATE is detected.
user_proxy = autogen.UserProxyAgent(
    name="User_proxy",
    system_message="Terminator admin.",
    code_execution_config=False,
    is_termination_msg=is_termination_msg,
    human_input_mode="NEVER",
)

list_of_agents = agents_A + agents_B
list_of_agents.append(user_proxy)
list_of_agents.append(code_executor)

# Create CustomGroupChat
initial_groupchat_msg_dict = {"content": """
- The team consistes of A1 (Product Manager), A2 (Enterprise Application Architect), B1 (Engineering Manager), B2 (Backend Engineer), B3 (Quality Assurance Engineer), and code_executor (code execution assistant).  There is no Frontend Engineer in this team.
- Everyone cooperates to achieve the task defined for the project, by the project manager. If you want a response from a specific person suggest their name as the next speaker.
- To suggest a person as the next speaker, you must use "NEXT: B1" to suggest talking to B1 for example; You can suggest only one person, you cannot suggest yourself; You can also not suggest anybody.
"""}
# group_chat = CustomGroupChat(
group_chat = GroupChat(
    agents=list_of_agents,  # Include all agents
    messages=[initial_groupchat_msg_dict],
    max_round=30
)

# Create the manager
llm_config = {
    "config_list": config_list,
    "cache_seed": None,
}  # cache_seed is None because we want to observe if there is any communication pattern difference if we reran the group chat.

manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=llm_config)

# Initiates the chat by seeding a message from A2
problem_statement_pt1 = """
- We have a company that sells three kinds of products: word processors, databases, and spreadsheets.
- According to the rules, when you sign a contract for a word processor you can book all the revenue right away.
- If it’s a spreadsheet, you can book one-third today, one-third in sixty days, and one-third in ninety days.
- If it’s a database, you can book one-third today, one-third in thirty days, and one-third in sixty days.
- I want help in building an enterprise web application to accurately track the orders and revenue recognition for this company.
- We need to build the entire application eventually, but for now will focus only on the back end of the application.
- The team has world class engineers who have worked at awesome enterprise software companies.
- I'm relying on A1 to architect the application according to DDD Principles and then instruct the engineers to help build the application with complete working code."""
problem_statement_pt2a = """- For the first phase, we are only looking to complete the finalized architecture and design and write it to a file named "design_document.md". We are DONE when the finalized design document is written to disk
NEXT: A1
"""
agents_A[1].initiate_chat(manager, message=problem_statement_pt1 + problem_statement_pt2a)
print("***done with phase 1***")

"""We will next work on the second phase. We will read the previously written design document and then expand to get all the code files without full implementation written out"""

problem_statement_pt2b = """- For the second phase, we will use the 'design_document.md' which contains the high level architectural design and create a Detailed Design (document named detailed_design.md, saved to disk in markdown format).
This detailed design document will contain only code stubs for all the required classes and interfaces with enough detail on parameters and comments on what the various methods and variables will be doing. However we will not have any implementation
We are DONE when the detailed design document is written to disk
NEXT: A1
"""

agents_A[1].initiate_chat(manager, message=problem_statement_pt1 + problem_statement_pt2b)
print("***done with phase 2***")