"""
Agent Framework for Trustworthy RAG
Multi-agent system for complex query handling, tool usage, and orchestration.
"""

import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from utils.logger import setup_logger
from utils.exceptions import GenerationException

logger = setup_logger(__name__)


class AgentRole(Enum):
    """Agent roles in the system."""
    ORCHESTRATOR = "orchestrator"
    RETRIEVER = "retriever"
    VALIDATOR = "validator"
    ANALYST = "analyst"
    SUMMARIZER = "summarizer"


@dataclass
class Tool:
    """A tool that can be used by agents."""
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        try:
            return self.function(**kwargs)
        except Exception as e:
            logger.error(f"Tool '{self.name}' execution failed: {e}")
            raise


@dataclass
class AgentAction:
    """An action taken by an agent."""
    agent_role: AgentRole
    action_type: str
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    success: bool = True
    error: Optional[str] = None


class BaseAgent:
    """Base class for all agents."""
    
    def __init__(
        self,
        role: AgentRole,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        tools: Optional[List[Tool]] = None
    ):
        """
        Initialize base agent.
        
        Args:
            role: Agent role
            model_name: LLM model to use
            temperature: LLM temperature
            tools: List of tools available to this agent
        """
        self.role = role
        self.tools = tools or []
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.action_history: List[AgentAction] = []
        
        try:
            self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize LLM for agent: {e}")
            self.llm = None
    
    def add_tool(self, tool: Tool):
        """Add a tool to the agent."""
        self.tools.append(tool)
        self.tool_map[tool.name] = tool
        logger.info(f"🔧 Added tool '{tool.name}' to {self.role.value} agent")
    
    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Use a specific tool."""
        if tool_name not in self.tool_map:
            raise ValueError(f"Tool '{tool_name}' not available to this agent")
        
        tool = self.tool_map[tool_name]
        logger.info(f"🔧 {self.role.value} agent using tool: {tool_name}")
        
        action = AgentAction(
            agent_role=self.role,
            action_type="tool_use",
            tool_name=tool_name,
            parameters=kwargs
        )
        
        try:
            result = tool.execute(**kwargs)
            action.result = result
            action.success = True
        except Exception as e:
            action.success = False
            action.error = str(e)
            raise
        finally:
            self.action_history.append(action)
        
        return result
    
    def think(self, prompt: str) -> str:
        """Use LLM to reason about a problem."""
        if not self.llm:
            return "[LLM not available]"
        
        try:
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Agent thinking failed: {e}")
            return f"Error: {str(e)}"
    
    def get_action_summary(self) -> str:
        """Get summary of actions taken."""
        successful = sum(1 for a in self.action_history if a.success)
        failed = len(self.action_history) - successful
        return f"{self.role.value}: {len(self.action_history)} actions ({successful} successful, {failed} failed)"


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that coordinates other agents.
    Handles complex queries by decomposing them and delegating to specialists.
    """
    
    def __init__(self, **kwargs):
        super().__init__(role=AgentRole.ORCHESTRATOR, **kwargs)
        self.sub_agents: Dict[AgentRole, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent):
        """Register a sub-agent."""
        self.sub_agents[agent.role] = agent
        logger.info(f"🤝 Registered {agent.role.value} agent with orchestrator")
    
    def decompose_query(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decompose a complex query into sub-tasks.
        
        Returns:
            List of sub-tasks with agent assignments
        """
        prompt = f"""You are an orchestrator agent. Break down this query into sub-tasks.
        
Query: {query}
Context: {json.dumps(context, indent=2)}

Available agents:
- retriever: Fetch relevant documents
- validator: Check permissions and validate data
- analyst: Analyze and extract insights
- summarizer: Create concise summaries

Return a JSON list of sub-tasks in this format:
[
  {{"agent": "retriever", "task": "fetch documents about...", "priority": 1}},
  {{"agent": "analyst", "task": "analyze the data...", "priority": 2}}
]
"""
        
        response = self.think(prompt)
        
        try:
            # Extract JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            tasks = json.loads(response.strip())
            return tasks
        except Exception as e:
            logger.warning(f"Failed to parse orchestrator response: {e}")
            # Fallback to simple retrieval
            return [{"agent": "retriever", "task": query, "priority": 1}]
    
    def execute_plan(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a plan by delegating to sub-agents."""
        results = {}
        
        # Sort by priority
        sorted_tasks = sorted(tasks, key=lambda x: x.get('priority', 999))
        
        for task in sorted_tasks:
            agent_role_str = task.get('agent', 'retriever')
            task_desc = task.get('task', '')
            
            # Map string to AgentRole enum
            try:
                agent_role = AgentRole(agent_role_str)
            except ValueError:
                agent_role = AgentRole.RETRIEVER
            
            if agent_role in self.sub_agents:
                agent = self.sub_agents[agent_role]
                logger.info(f"📋 Executing task with {agent_role.value}: {task_desc[:50]}...")
                
                # Simple execution - in production, this would be more sophisticated
                if agent.tools:
                    # Use first available tool
                    tool_name = agent.tools[0].name
                    result = agent.use_tool(tool_name, query=task_desc)
                    results[agent_role.value] = result
        
        return results


class MultiAgentRAG:
    """
    Multi-agent RAG system that coordinates specialized agents.
    """
    
    def __init__(
        self,
        retriever_tool: Tool,
        validator_tool: Tool,
        model_name: str = "gpt-3.5-turbo"
    ):
        """
        Initialize multi-agent system.
        
        Args:
            retriever_tool: Tool for document retrieval
            validator_tool: Tool for document validation
            model_name: LLM model name
        """
        # Create orchestrator
        self.orchestrator = OrchestratorAgent(model_name=model_name, temperature=0.3)
        
        # Create specialized agents
        self.retriever_agent = BaseAgent(
            role=AgentRole.RETRIEVER,
            model_name=model_name,
            temperature=0.5,
            tools=[retriever_tool]
        )
        
        self.validator_agent = BaseAgent(
            role=AgentRole.VALIDATOR,
            model_name=model_name,
            temperature=0.1,
            tools=[validator_tool]
        )
        
        self.analyst_agent = BaseAgent(
            role=AgentRole.ANALYST,
            model_name=model_name,
            temperature=0.7
        )
        
        self.summarizer_agent = BaseAgent(
            role=AgentRole.SUMMARIZER,
            model_name=model_name,
            temperature=0.5
        )
        
        # Register agents with orchestrator
        self.orchestrator.register_agent(self.retriever_agent)
        self.orchestrator.register_agent(self.validator_agent)
        self.orchestrator.register_agent(self.analyst_agent)
        self.orchestrator.register_agent(self.summarizer_agent)
        
        logger.info("✅ Multi-agent RAG system initialized")
    
    def process_query(
        self,
        query: str,
        user: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a query using multi-agent orchestration.
        
        Args:
            query: User query
            user: User information
            context: Additional context
        
        Returns:
            Results from agent execution
        """
        logger.info(f"🤖 Multi-agent processing query: {query[:50]}...")
        
        context = context or {}
        context['user'] = user
        
        # Step 1: Orchestrator decomposes the query
        tasks = self.orchestrator.decompose_query(query, context)
        logger.info(f"📋 Orchestrator created {len(tasks)} tasks")
        
        # Step 2: Execute tasks
        results = self.orchestrator.execute_plan(tasks)
        
        # Step 3: Synthesize results
        synthesis = self._synthesize_results(query, results)
        
        return {
            'query': query,
            'tasks': tasks,
            'results': results,
            'synthesis': synthesis,
            'agent_summary': self._get_all_agent_summaries()
        }
    
    def _synthesize_results(self, query: str, results: Dict[str, Any]) -> str:
        """Synthesize results from multiple agents."""
        if not results:
            return "No results available from agents."
        
        # Use summarizer agent to create final response
        synthesis_prompt = f"""Synthesize these results into a coherent answer:

Original Query: {query}

Agent Results:
{json.dumps(results, indent=2, default=str)}

Provide a clear, comprehensive answer."""
        
        return self.summarizer_agent.think(synthesis_prompt)
    
    def _get_all_agent_summaries(self) -> List[str]:
        """Get summaries from all agents."""
        agents = [
            self.orchestrator,
            self.retriever_agent,
            self.validator_agent,
            self.analyst_agent,
            self.summarizer_agent
        ]
        return [agent.get_action_summary() for agent in agents]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about agent performance."""
        total_actions = sum(
            len(agent.action_history)
            for agent in [
                self.orchestrator,
                self.retriever_agent,
                self.validator_agent,
                self.analyst_agent,
                self.summarizer_agent
            ]
        )
        
        return {
            'total_actions': total_actions,
            'agent_count': 5,
            'orchestrator_tasks': len(self.orchestrator.action_history)
        }

