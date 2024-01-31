import csv
import os
import random
from typing import Annotated, Dict, List

import autogen
from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import AssistantAgent
from autogen.agentchat.groupchat import GroupChat, GroupChatManager
from autogen.agentchat.user_proxy_agent import UserProxyAgent

print(autogen.__version__)

# The default config list in notebook.
config_list = [
    {
        "model": "gpt-4-1106-preview",
        "api_key": "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"
    }
]

llm_config = {"config_list": config_list, "cache_seed": 42}

class CustomGroupChat(GroupChat):
    def __init__(self, agents, messages, max_round=10, admin_name="chat_manager"):
        super().__init__(agents, messages, max_round, admin_name)
        self.previous_speaker = None  # Keep track of the previous speaker

    def select_speaker(self, last_speaker: Agent, selector: AssistantAgent):
        # Check if last message suggests a next speaker or termination
        last_message = self.messages[-1] if self.messages else None
        if last_message:
            if "NEXT:" in last_message["content"]:
                suggested_next = last_message["content"].split("NEXT: ")[-1].strip()[:2] # added slicer in the end to account for just the first agent name if there are  more than one mentioned
                print(f"Extracted suggested_next = {suggested_next}")
                try:
                    next_speaker = self.agent_by_name(suggested_next)
                    self.previous_speaker = last_speaker
                    return next_speaker
                except ValueError:
                    pass  # If agent name is not valid, continue with normal selection
            elif "TERMINATE" in last_message["content"]:
                try:
                    next_speaker = self.agent_by_name("User_proxy")
                    self.previous_speaker = last_speaker
                    return next_speaker
                except ValueError:
                    pass  # If 'User_proxy' is not a valid name, continue with normal selection

        other_team_leader_agents = {a for a in self.agents if a.name.endswith("1")} - {last_speaker}
        num_ai_agents = len(set(self.agents)) - (1 if human_ceo in self.agents else 0) # remove the human_ceo if it exists in agent list
        three_or_more_agents = True if num_ai_agents>=3 else False
        two_or_more_agents = True if num_ai_agents>=2 else False
        
        last_speakers_team_agents = {a for a in self.agents if a.name.startswith(last_speaker.name[0])}

        possible_next_speakers = (
            last_speakers_team_agents
            - (set([last_speaker]) if two_or_more_agents else set()) # in sets for difference can use -
            - (set([self.previous_speaker]) if three_or_more_agents else set())
            | (other_team_leader_agents if last_speaker in other_team_leader_agents else set()) # in sets, to union/add use .union or |
        )
        
        if self.previous_speaker is not None:
          print(f"two_or_more_agents: {two_or_more_agents}, three_or_more_agents: {three_or_more_agents}\n*** SPEAKERS\nPrevSpeaker: {self.previous_speaker.name}, LastSpeaker:{last_speaker.name}, PossibleNextSpeakers = {[a.name for a in possible_next_speakers]}\n***")

        self.previous_speaker = last_speaker

        if possible_next_speakers:
            next_speaker = random.choice(list(possible_next_speakers))
            return next_speaker
        else:
            return None

# Termination message detection
def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "TERMINATE" in content["content"]:
        return True
    return False


# Skills
step_by_step = """
- Take your time to think, and work in a step by step manner.
"""

how_you_communicate = """How you behave:
- Be very business-like and to the point in your communications, to get the job completed satisfactorily in the least possible time. Avoid back and forth chatter. Complete your steps and then respond. 
- Respond precisely, do not expect the user to elaborate, or use 'etc.' or 'for example'
- DO NOT show gratitude.
- Based on the instructions if you know who needs to act next, clearly indicate so using the format "NEXT: A1", for example to have A1 be next
"""

incorporating_feedback = """
-- Whenever providing a response or incorporating feedback into a response, make sure the complete updated content is sent to the next reviewer. 
-- Do not have text indicating that 'something has not changed' etc., instead keep the unchanged content from before to keep building a complete document.
"""

write_a_savable_document = ("- When generating code you must indicate the script type in the code block. "
                            "If you want the user to save the code block you have created into a file, put # filename: <filename> inside the code block as the first line. "
                            "The user will save the code before executing it. Don't include multiple code blocks in one response. "
                            "Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.")

dev_test_skills_what_they_do = """Your skills:
- You are very familiar with implementation of various Enterprise Application Architecture patterns. You are also very familiar with the best practices of Testing that can catch all the important corner cases.
- You solve tasks using your coding and language skills.
- You are an expert in the Python programming language. You are very familiar with a number of the popular libraries including pydantic, pytest, fastapi, sqlalchemy, itertools, functools, and django.
- You write fully type specified code leveraging the Typing library, and use a functional programming style.
- You also are an expert in writing unix and windows shell scripts.
What you do:
- You will write code for various parts of the application as per specifications.
- When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, write a file to disk, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
- When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
"""
code_gen_guidelines = """
- The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. 
- The user can't modify your code. So do not suggest incomplete code which requires users to modify. 
- Don't use a code block if it's not intended to be executed by the user.
- If the result indicates there is an error in your script, fix the error and output the code again. Suggest the full code instead of partial code or code changes. 
- If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
- When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
"""

architect_skills = """Your skills:
- You are very familiar with Domain Driven Design and implementation of various Enterprise Application Architecture patterns. You are also very familiar with the best practices of Testing and Test Driven Developpment that can catch all the important corner cases.
- You solve tasks using your knowledge of enterprise software concepts and language skills.
- You are an expert in the Python programming language. You are very familiar with a number of the popular libraries including pydantic, pytest, fastapi, sqlalchemy, itertools, functools, and django.
- You are an expert at creating work break down structures and plans for developing and testing various parts of the application as per specifications. 
- You review enterprise software architecture and designs and provide comprehensive feedback.
"""

# persona base messages
EAA_system_message="""
Your role:
-You are an expert Enterprise Application Architect and are a Domain Driven Design practitioner.
-You follow the methodologies and patterns described by Martin Fowler, Eric Evans, and Vaughn Vernon.
Your skills:
- You are skilled at designing enterprise applications and finalizing the architecture of enterprise applications and creating a design document with all necessary components.
- You are skilled at identifying the architecture compoents including: 
 1. types of DDD objects like bounded contexts, modules, aggregates, entities, value objects, domain events, repositories, and factories.
 2. different layers of the enterprise application like - presentation, application, domain, and infrastructure.
 3. the enterprise architecture patterns relevant to each of the DDD objects and layers identified.
- When code is presented, you are skilled at reviewing code to ensure it meets the requirements and the architectural requirements of the project. You suggest changes for the development team to make if needed, so the code can be updated and presented to you for review again.
- DO NOT suggest concrete code.
"""

PM_system_message="""
Your role:
- You are a Product Manager working to build highly scalable enterprise applications that are very intuitive and easy to use, offering business users an excellent user experience.
Your skills:
- You have extensive experience representing the end-user (employees in large corporations) perspective on how business processes work and the various systems' requirements associated with them.
- You present comprehensive requirements in the form of easy to understand but comprehensively defined user stories. The user stories in-turn contain use-cases covering all happy path and exception path scenarios
What you do:
- Work with the other team members to resolve any questions on requirements and to ensure they have a clear understanding.
Your responsibilities:
- You are responsible for laying out the requirements for the enterprise applications we are building and for the final interpretation of any requirements.
- ONLY when your ask for the particualr project is fully met, say out that the project is complete and append a new line with the word TERMINATE to your message.
"""

engg_manager_system_message=""" You are a very experienced Engineering Manager who has worked extensively with DDD and in building enterprise applications.
Your responsibilities:
- Breaking down a large body of work into smaller chunks and creating a work plan. You clearly identify the task with a number and the resource who is to work on it. You keep track of the status of each of the task to ensure they all finally get completed.
- You are responsible for coordinating the engineers developing a high quality working application to meet the business and architectural requirements received from the Product Manager and Enterprise Application Architect.
- You use the development engineers to check each other's work for mistakes.
"""

# Initialization of agents
B7 = AssistantAgent(
        name="B7",
        description="Enterprise Application Architect",
        system_message=EAA_system_message + step_by_step + how_you_communicate + incorporating_feedback,
        llm_config=llm_config,
    )
    
A2 = AssistantAgent(
        name="A2",
        description="Product Manager",
        system_message=PM_system_message + step_by_step + how_you_communicate + incorporating_feedback,
        llm_config=llm_config,
    )
    
A3 = UserProxyAgent(
        name="A3",
        description="code executor",
        system_message="A proxy for the user that can run Python code or input command line commands at a Linux terminal and report back the execution results.",
        code_execution_config={"last_n_messages": "auto"},
        human_input_mode="NEVER",
    )
    

B1 = AssistantAgent(
        name="B1",
        description="Engineering Manager",
        system_message=engg_manager_system_message + step_by_step + how_you_communicate + incorporating_feedback,
        llm_config=llm_config, code_execution_config=False,
    )

B9 = AssistantAgent( # no file writing skills
        name="B9",
        description="Engineering Manager",
        system_message=engg_manager_system_message + step_by_step + how_you_communicate + incorporating_feedback,
        llm_config=llm_config, code_execution_config=False,
    )

B2 = AssistantAgent(
        name="B2",
        description="Backend Engineer",
        system_message="""Your role:
- You are an expert backend engineer.""" + dev_test_skills_what_they_do + write_a_savable_document + code_gen_guidelines + """Your responsibilities:
- You deliver fully working, high quality, code that completely meets the requirement of the task that was assigned to you by the Engineering Manager.
""" + how_you_communicate + incorporating_feedback,
        llm_config=llm_config, code_execution_config=False,
    )
    
B3 = AssistantAgent(
        name="B3",
        description="Quality Assurance Engineer",
        system_message="""Your role:
- You are an expert quality assurance engineer.""" + dev_test_skills_what_they_do + write_a_savable_document + code_gen_guidelines + """Your responsibilities:
- You deliver high quality unit, system, integration, and functional tests that completely meets the requirement of the task that was assigned to you by the Engineering Manager.
""" + how_you_communicate + incorporating_feedback,
        llm_config=llm_config, code_execution_config=False,
    )

B4 = UserProxyAgent(
    name="B4",
    description="code executor",
    system_message="A proxy for the user that can run Python code or input command line commands at a Linux terminal and report back the execution results.",
    code_execution_config={"last_n_messages": "auto"},
    human_input_mode="NEVER",
    )

B5 = AssistantAgent(
        name="B5",
        description="Backend Development and Quality Assurance Architect",
        system_message="You are an expert Backend Development and QA architect and planner. You excel in Test Driven Development and are equally proficient with planning development and testing tasks." + architect_skills + write_a_savable_document + how_you_communicate + incorporating_feedback,
        llm_config=llm_config, code_execution_config=False,
    )

B6 = AssistantAgent(
        name="B6",
        description="Quality Assurance Architect",
        system_message="You are an expert quality assurance architect and planner." + architect_skills + write_a_savable_document + how_you_communicate + incorporating_feedback,
        llm_config=llm_config, code_execution_config=False,
    )


#  Can terminate the conversation when TERMINATE is detected or jump in with a CTRL-C and participate. must include NEXT: Xn
human_ceo = UserProxyAgent(
    name="human_ceo",
    system_message="Company CEO",
    code_execution_config=False,
    is_termination_msg=is_termination_msg,
    human_input_mode="ALWAYS",
    )

# define and register tools
def print_current_working_directory():
    print(f"Current Working Directory: {os.getcwd()}")

@B6.register_for_execution()
@B5.register_for_execution()
@B1.register_for_llm(name="ReadFromFile", description="reads the file specified by the filename parameter from the project directory, from disk and returns the result.")
def read_from_file(filename: Annotated[str, "valid filename."], project: Annotated[str, "project name."]) -> str:
    def read_and_print_file(file_path):
        try:
            with open(file_path, 'r') as file:
                return(file.read())
        except FileNotFoundError:
            print(f"Error: {file_path} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")

    print_current_working_directory()
    return read_and_print_file(os.path.join(project,filename))

@B6.register_for_execution()
@B5.register_for_execution()
@B1.register_for_llm(name="WriteFileToDisk", description="writes the content passed via the content parameter to disk in a file named filename. Returns 0 or 1 depending on whether the operation succeeded or not, respectively.")
@B7.register_for_llm(name="WriteFileToDisk", description="writes the content passed via the content parameter to disk in a file named filename. Returns 0 or 1 depending on whether the operation succeeded or not, respectively.")
def write_to_file(content: Annotated[str, "text content to be written to a file."], filename: Annotated[str, "valid filename."], project: Annotated[str, "project name."]) -> int:
    print_current_working_directory()
    try:
        with open(os.path.join(project, filename), 'w') as file:
            file.write(content)
        return 0  # Operation succeeded
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1  # Operation failed

mgr_llm_config = {
    "config_list": config_list,
    "cache_seed": None,
}  # cache_seed is None because we want to observe if there is any communication pattern difference if we reran the group chat.

# Create CustomGroupChat
arch_design_team_desc = """
- The team consistes of B7 (Enterprise Application Architect) and B5 (Backend Development and Quality Architect).  
- There is NO Frontend Engineer in this team. We will not take on any front end engineering tasks. If it does come up, reiterate this decision to all participants.
- Everyone cooperates to achieve the task defined for the project, by the product manager. 
- If you want a response from a specific person suggest their name as the next speaker.
- To suggest a person as the next speaker, you MUST use the format "NEXT: B1" to suggest talking to B1 for example; You can suggest ONLY ONE of the team members, by their name. You CANNOT suggest yourself. You can also decide not to suggest anybody.
"""
arch_design_config = {
    "agents": [B5, B7, human_ceo],  
    "messages": [arch_design_team_desc],
    "max_round": 12,
    "admin_name": "human_ceo"
}

arch_design_chat = CustomGroupChat(**arch_design_config)

# Create the manager for the arch design chat
arch_design_chat_mgr = GroupChatManager(groupchat=arch_design_chat, llm_config=mgr_llm_config)

project_name = 'revrec'

requirements = """
- Our company sells three kinds of products: word processors, databases, and spreadsheets.
- According to the rules, when you sign a sales contract for a word processor you can book all the revenue right away. If it's a spreadsheet, you can book one-third today, one-third in sixty days, and one-third in ninety days. If it's a database, you can book one-third today, one-third in thirty days, and one-third in sixty days.
- We need to accurately track the revenue recognition for this company.
"""

design_decisions = """
- We will use fastAPI for the backend. We will use SQLlite as the database for the persistence layer. If an ORM is needed, use Django.
"""

# Need only team of B5 and B7
gen_architecture_and_design = f"""
Our GOAL is to help B7 to architect the application according to DDD Principles, to meet the product requirements, following the design decision that have already been made: {design_decisions}. 
If there is ever any uncertainity on who should speak next, direct the conversation to B7. Strictly follow the following plan: 
1. B7 identifies the Bounded Contexts, Modules, Aggregates, Entities, Value Objects, Domain Events, Repositories, Factories, Domain Services, Presentation Layer, Application Layer, Infrastructure Layer, and Enterprise Architectre Design Patterns needed for the solution. B7 formats this as a simple numbered list with grouping and indentation as needed to create the first_version of the architecture and design. B7 publishes this to the team soliciting feedback. 
2. B5 takes time to review the proposed architecture and design and provides feedback. 
3. B7 incorporates feedback into the first_version and creates a new complete up-to-date architecture and design. Follow a similar format as the first version. Call this the second_version. Publish it to the team for next review.
4. B5 takes time to review the second_version and provides further feedback.
5. B7 looks back at the first_version, the second_version and the most recent feedback from B5, analyzes them, and creates a final recommended architecture and design document. Please ensure that no critical details from the original versions are lost in the final recommendation. Publish this to the team.
6. B7 formats the final version as a markdown file and uses the WriteFileToDisk to write the updated final architecture and design to a file called design_document.md for the '{project_name}' project. Ensure the file gets written to disk successfully.
7. The final markdown file is reformatted in the form of a pipe ('|') delimited file where the first column is the topic heading from the markdown, and the second represents the detail under the heading. Call the columns Architecture Component and Design Detail. Add a work breakdown structure (dotted decimal) to each row as the first column. Prefix the generated WBS number with 'D-'. Call this column the 'Design Requirement #'.
8. B7 decides that the tool WriteFileToDisk is to be used to write the above pipe delimited content to file called design_document.csv for the '{project_name}' project. 
9. Once the design_document.csv file has been successfully written to disk, close the project by sending just the word terminate (in upper case).
NEXT: B7
"""

# Initiates the chat by seeding a message from B1
B7.initiate_chat(arch_design_chat_mgr, message=requirements + gen_architecture_and_design)
print("***done with phase 1***")



prepare_engg_plan_p1 = f"""
Our GOAL is to generate a detailed engineering work plan to cover all development and testing tasks to build a headless API layer (no front end is needed) using python and necessary libraries like fastapi, pydantic, sqlalchemy, django etc, with a sqllite backend database, to meet the requirements using the design and architecture provided.
B1 will coodinate while strictly follow the following plan: 

# initial publishing of component type and component name, and design_document
1. Sharing of design and architecture document and identification of DDD component types and names
 1a. B1 decides to read the design_document.csv file for the {project_name} project and share with the team. Let's call this the design_document
 1b. The design_document is analyzed and all the DDD Components are identified and categorized into the following DDD Componenty Types: bounded contexts, modules, aggregates, entities, value objects, domains events, repositories, factories, domain services, application layer, infrastructure layer, and enterprise architecture patterns. 
   <Consider this example: for a project if there are two different bounded contexts identified then each is a Component of the Bounded Context Component Type. Similarly if there were three value objects, each of those is a separate Component of the Value Object Component Type. If there were five domain events then each of those would be a separate Component of the Domain Event Component Type. So in this example we would have a total of two plus three plus five, giving us 10 different Components for the project.>
 This list of Component Type and Component Names is formatted as a pipe delimited list with column headers and published to the team. Let's call this the component_list

# Quality architect and planner creates testing task list
2. B6 will strategize and create the detailed test plan to meet the shared design and architecture following these steps:
 2a. B6 starts with the component_list and formulates a testing strategy that includes unit tests, integration tests, system tests, and acceptance tests ensuring the coverage of all the Component Names identified in the previous step.
 2b. B6 creates ALL the detailed tasks for testing each of the identified DDD component names. Include any environment setup steps that might be needed. Have a separate task for each DDD component name that has been identified, do not combine multiple DDD component names into a single task. DO NOT say things like '# Additional Tests Based on Other Design Components'. List down just three attribtues: the detailed Task Description, Component Type, and the DDD Component Name it's for. Do this in a pipe delimited list. Call this the first_attempt.

# second pass and reconciliation
3. B6 takes another pass by repeating the instructions of steps 2a, 2b, and 2c, but ignoring what it had generated previously as part of the first_attempt. Call this new output as the second_attempt
4. Reconciling both attempts and adding additional information
 4a. B6 analyzes the results of the first_attempt and the second_attempt to create a final recommendation. Ensure that all details provided for each task is retained. Ensure there is no duplication or repetition of tasks paying attention to the task and the identified DDD component name to see if they may be an overlap. Do not miss out any DDD component name that may have had an identified task as part of this reconciliation. B1 then arranges to write this to a file called consolidated_test_tasks to disk for project {project_name}.
 4b. In this final list, to the detailed task description, Component Type, and DDD component name, also add the filename for the Python script to be created
 4c. Map each task to the relevant Design Requirement Number(s) from the design document to ensure all requirements are met.   
 4d. B6 cross verifies with the design document to ensure all the Design Requirement Numbers there are addressed by at least one testing related task that was added to the detailed plan. 
5a. B6 shares comprehensive list of testing tasks with the team. Call this the comprehensive_test_task_list
5b. B1 gets the comprehensive_test_task_list written to disk in a file named comprehensive_test_task_list.csv for the {project_name} project.

# Backend architect and planner creates development task list
6. B5 will strategize and create the detailed development plan to meet the shared design and architecture, using the comprehensive_test_task_list that B6 had previously created as an additional reference to ensure we follow TDD practices. Do the following steps:  
 6a. B5 starts with the published component_list published and defines ALL the development tasks needed to implement each of the DDD component names identified in the previous step. Also include steps for setting up the project structure, integrating with the database and event store. Have a separate task for each DDD component name  that has been identified. DO NOT say things like '# Additional Development Tasks Based on Other Design Components'. List down just three attribtues - the detailed task description, Component Type, and the DDD component name it's for. Do this in a pipe delimited list. Call this the first_dev_attempt.

# second pass and reconciliation
7. B5 takes another pass by repeating the instructions of step 6a, but ignoring what it had generated previously as part of the first_dev_attempt. Call this new output as the second_dev_attempt
8a. B5 analyzes the results of the first_dev_attempt and the second_dev_attempt to create a final recommendation. Ensure that all details provided for each task is retained. Ensure there is no duplication or repetition of tasks, paying attention to the task and the identified DDD component names to see if they may be an overlap. B1 then arranges to write this to a file called consolidated_dev_tasks to disk for project {project_name}.
8c. B5, to this final list which has the detailed task description, Component Type, and DDD component name, also adds the filename for the Python script to be created.
8d. Map each task to the relevant Design Requirement Number(s) from the design_document to ensure all requirements are met.  
8e. B5 cross verifies with the design document to ensure all the requirements there are addressed by at least one development related task that was added to the detailed plan.
9a. B5 shares comprehensive list of development tasks with the team. Call this the comprehensive_dev_task_list
9b. B1 gets the comprehensive_dev_task_list written to disk in a file named comprehensive_dev_task_list.csv for the {project_name} project.
10. Close project. Write terminate (in upper case) on a separate line.
NEXT: B1
"""

prepare_engg_plan_p2 = f"""
# Engineering manager creates and shares consolidated task list with WBS
10a. B1 reads the files comprehensive_test_task_list.csv and comprehensive_dev_task_list.csv from disk, for project {project_name} and publishes to the group
10b. B1 reorders the tasks that were just published to ensure that the test and development tasks for a DDD component name (where they exist) are placed one after the other, and the file names proposed for each task are appropriate, and that the design requirements are addressed. Also sequence the tasks in the order in which an expert enterprise applications engineering manager would typically have them executed. Ensure the task list has all these fields: Detailed task description, DDD Component Type, DDD Component Name, development code python file name, test python file name, design document requirement number(s)
10c. B1 assigns a serial number to each of these tasks
10d. B1 publishes this finalized consolidated task list to the team using a pipe-delimited format. ENSURE THAT THE COMPLETE data set is created, and not just a sample. Call this the engineering_plan.
10e. B1 uses tool WriteFileToDisk to write engineering_plan to disk in a file named 'engineering_plan.csv' for the {project_name} project
11. Close project. Write terminate (in upper case) on a separate line.
NEXT: B1
"""

engg_plan_team = """
- The team consistes of  B1 (Engineering Manager), B5 (backend development architect and planner), and B6 (quality assurance architect and planner). All their services are available for the entire project. 
- There is NO Frontend Engineer in this team. We will not take on any front end engineering tasks. If it does come up, reiterate this decision to all participants.
- Everyone cooperates to achieve the tasks defined for the project by the engineering manager. 
- If you want a response from a specific person suggest their name as the next speaker. 
- To suggest a person as the next speaker, you MUST use the format "NEXT: B1" to suggest talking to B1 for example; You can suggest ONLY ONE of the team members, by their name. You cannot suggest yourself. You can also decide not to suggest anybody.
- ONLY when the project manager's ask for the particular project is fully met, say out that the project is complete and append a new line with the word TERMINATE to your message.
"""
engg_plan_chat = CustomGroupChat(
    agents=[B1, B5, B6, human_ceo],  # Include all B agents and the human_ceo who can use Ctrl C to get in on the conversation. Must include NEXT: X1 as last text to continue
    messages=[engg_plan_team],
    max_round=15,
    admin_name="human_ceo"
)
engg_plan_chat_mgr = GroupChatManager(groupchat=engg_plan_chat, llm_config=mgr_llm_config)

B1.initiate_chat(engg_plan_chat_mgr, message=prepare_engg_plan_p1)
print("***done with phase 2.1***")
B1.initiate_chat(engg_plan_chat_mgr, message=prepare_engg_plan_p2)
print("***done with phase 2.2***")


engg_exec_team = """
- The team consistes of  B1 (Engineering Manager), B2 (backend engineer), and B3 (quality assurance engineer), and B4 (code executor). All their services are available for the entire project. 
- There is NO Frontend Engineer in this team. We will not take on any front end engineering tasks. If it does come up, reiterate this decision to all participants.
- B4 can be used to execute code to save code files to disk, run the code, and the test cases.
- Everyone cooperates to achieve the tasks defined for the project by the engineering manager. 
- If you want a response from a specific person suggest their name as the next speaker. 
- To suggest a person as the next speaker, you MUST use the format "NEXT: B1" to suggest talking to B1 for example; You can suggest ONLY ONE of the team members, by their name. You cannot suggest yourself. You can also decide not to suggest anybody.
- ONLY when the engineering manager's ask for the particular project is fully met, say out that the project is complete and append a new line with the word TERMINATE to your message.
"""

build_app = """
Our GOAL is to generate and save to disk all the python code for a headless API layer (no front end is needed) using necessary libraries like fastapi, sqlalchemy, django etc, with a sqllite backend database, 
 to meet the requirements (provided below and henceforth called Reqmts )
 using the design and architecture (provided below and henceforth called DesArch)
 following the engineering plan (provided below henceforth called the EnggPlan).

The team will strictly work one task (a DDD component) at a time from the engg_plan, on generating the tests and the actual code to meet the shared design and architecture, ensuring it addresses all business requirements relevant to that DDD component. That task will also be identified below (by CurrentTask). 

Follow the following plan ONLY FOR the identified task:
1. B3 creates tests, in keeping with TDD principles, as per the Requirements following the design and architecture provided and publishes to team.
2. B2 creates the actual code as per the instructions in the engg_plan, requirements, and following the design and architecture provided and publishes to team, ensuring the code will work with B3's test code.
3. B2 and B3 work together to make sure the tests and actual code reference the right classes and methods such that they will work well when executed. They ensure the code is properly indented and that the import statements are correctly stated.
4. Only after they have both reviewed the code at least once and believe that the code will work correctly together should B9 be asked to sequence the code such that the dev code file blocks are sequenced before the test code file blocks in the message being sent to B4 to create the files and execute the code.
5. B9, B2, and B3 should remember that B4 may be able to successfully create only some of the code files sent in a meessage. In such cases the code execution result should be analyzed, necessary fixes made, and all the code file blocks that need to be created or updated need to be sent again to B4 in one message.
6. B9 ends the task when all the code for this task has been create, fully tested and is working by saying terminate (in upper case) as the only word on a separate line.
NEXT: B3
"""
engg_exec_chat = CustomGroupChat(
    agents=[B2, B3, B4, B9, human_ceo],  # Include all B agents and the human_ceo who can use Ctrl C to get in on the conversation. Must include NEXT: X1 as last text to continue
    messages=[engg_exec_team],
    max_round=10,
    admin_name="human_ceo"
)
engg_exec_chat_mgr = GroupChatManager(groupchat=engg_exec_chat, llm_config=mgr_llm_config)

def extract_task_numbers(filename, project_folder):
    with open(os.path.join(project_folder,filename), 'r') as file:
        reader = csv.reader(file, delimiter='|')
        headers = next(reader)  # Skip the header
        task_numbers = [int(row[0]) for row in reader]
    return task_numbers

reqmts = '\n\nReqmts::\n' + requirements
design = '\n\nDesArch::\n' + read_from_file('design_document.csv', project_name)
engg_plan = '\n\nEnggPlan::\n' + read_from_file('engineering_plan.csv', project_name)
current_task = '\n\nCurrentTask:: ' + '6'
B9.initiate_chat(engg_exec_chat_mgr, message = build_app + reqmts + design + engg_plan + current_task)
print(f"***done with phase 3.{current_task}***")