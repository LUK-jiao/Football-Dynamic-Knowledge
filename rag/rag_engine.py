"""
GraphRAG Engine for Football Knowledge Graph System

Main orchestrator that combines query analysis, graph retrieval, 
context building, and LLM generation.
"""

from typing import Dict, Any
from rag.query_analyzer import QueryAnalyzer
from rag.graph_retriever import GraphRetriever
from rag.context_builder import ContextBuilder
from rag.llm_backend import RAGLLMBackend


class GraphRAG:
    """
    Event-Centric, Temporal-Aware, Constraint-Guided, Explainable GraphRAG System.
    
    Orchestrates the complete RAG pipeline:
    1. Parse query → structured constraints
    2. Retrieve events from graph
    3. Build context
    4. Generate answer with LLM
    """
    
    def __init__(
        self,
        analyzer: QueryAnalyzer,
        retriever: GraphRetriever,
        builder: ContextBuilder,
        llm: RAGLLMBackend
    ):
        """
        Initialize GraphRAG engine.
        
        Args:
            analyzer: Query analyzer for parsing natural language
            retriever: Graph retriever for Neo4j queries
            builder: Context builder for formatting events
            llm: Language model backend for generation
        """
        self.analyzer = analyzer
        self.retriever = retriever
        self.builder = builder
        self.llm = llm
    
    def answer(self, query: str, return_context: bool = False) -> Dict[str, Any]:
        """
        Answer a natural language question using the knowledge graph.
        
        Args:
            query: Natural language question
            return_context: Whether to include full context in response
            
        Returns:
            Dictionary containing:
            - parsed_query: Structured query constraints
            - retrieved_events: List of events from graph
            - context: Formatted context (if return_context=True)
            - answer: Generated answer text
        """
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")
        
        # Step 1: Parse query
        print("[Step 1] Parsing query...")
        parsed_query = self.analyzer.parse(query)
        print(f"  ✓ Parsed: {parsed_query}")
        
        # Step 2: Retrieve events
        print("\n[Step 2] Retrieving events from graph...")
        events = self.retriever.retrieve(parsed_query)
        print(f"  ✓ Retrieved {len(events)} events")
        
        # Step 3: Build context
        print("\n[Step 3] Building context...")
        intent = parsed_query.get("intent", "fact")
        
        if intent == "summary":
            context = self.builder.build_summary_context(events)
        elif intent == "analysis":
            context = self.builder.build_analysis_context(events)
        else:
            context = self.builder.build(events)
        
        print(f"  ✓ Context built ({len(context)} characters)")
        
        # Step 4: Generate answer
        print("\n[Step 4] Generating answer...")
        answer = self._generate_answer(query, context, intent)
        print(f"  ✓ Answer generated ({len(answer)} characters)")
        
        # Build response
        response = {
            "parsed_query": parsed_query,
            "retrieved_events": events,
            "answer": answer
        }
        
        if return_context:
            response["context"] = context
        
        return response
    
    def _generate_answer(self, query: str, context: str, intent: str) -> str:
        """
        Generate answer using LLM.
        
        Args:
            query: Original question
            context: Formatted event context
            intent: Query intent (fact/summary/analysis)
            
        Returns:
            Generated answer text
        """
        # Build prompt based on intent
        if intent == "fact":
            prompt = self._build_fact_prompt(query, context)
        elif intent == "summary":
            prompt = self._build_summary_prompt(query, context)
        elif intent == "analysis":
            prompt = self._build_analysis_prompt(query, context)
        else:
            prompt = self._build_fact_prompt(query, context)
        
        # Generate answer
        answer = self.llm.chat(prompt, temperature=0.3)
        
        return answer
    
    def _build_fact_prompt(self, query: str, context: str) -> str:
        """Build prompt for factual queries."""
        return f"""You are a professional football analyst assistant.

Based ONLY on the provided events from the knowledge graph, answer the user's question accurately and concisely.

Question:
{query}

Context (Events from Knowledge Graph):
{context}

Instructions:
- Answer based ONLY on the provided events
- Do NOT make up information or hallucinate
- Cite event IDs in square brackets [event_id] when referencing specific events
- If the information is not in the context, say "I don't have enough information to answer this question."
- Be concise and factual
- Use the event dates to provide temporal context

Answer:"""
    
    def _build_summary_prompt(self, query: str, context: str) -> str:
        """Build prompt for summary queries."""
        return f"""You are a professional football analyst assistant.

Based on the provided events from the knowledge graph, provide a comprehensive summary answering the user's question.

Question:
{query}

Context (Events from Knowledge Graph):
{context}

Instructions:
- Summarize the key events and patterns
- Group related events together
- Provide statistics if relevant (e.g., number of goals, wins, losses)
- Identify trends over time
- Cite event IDs in square brackets [event_id] when making specific claims
- Do NOT hallucinate information not in the context
- Structure your answer with clear sections if appropriate

Answer:"""
    
    def _build_analysis_prompt(self, query: str, context: str) -> str:
        """Build prompt for analysis queries."""
        return f"""You are a professional football analyst with deep expertise in tactical and strategic analysis.

Based on the provided events from the knowledge graph, provide an in-depth analysis answering the user's question.

Question:
{query}

Context (Events from Knowledge Graph - Chronological Order):
{context}

Instructions:
- Analyze the temporal sequence of events
- Identify cause-and-effect relationships
- Explain patterns, trends, and their implications
- Consider multiple perspectives
- Use domain knowledge to interpret the events
- Cite event IDs in square brackets [event_id] when referencing specific events
- Base your analysis on the provided events, but you may use general football knowledge for interpretation
- Structure your analysis logically (e.g., Background → Key Events → Analysis → Implications)

Answer:"""
    
    def batch_answer(self, queries: list[str]) -> list[Dict[str, Any]]:
        """
        Answer multiple queries in batch.
        
        Args:
            queries: List of questions
            
        Returns:
            List of response dictionaries
        """
        responses = []
        
        for i, query in enumerate(queries, 1):
            print(f"\n{'#'*80}")
            print(f"Query {i}/{len(queries)}")
            print(f"{'#'*80}")
            
            response = self.answer(query)
            responses.append(response)
        
        return responses
    
    def interactive_mode(self):
        """
        Start interactive Q&A session.
        
        Allows users to ask questions interactively until they exit.
        """
        print("\n" + "="*80)
        print("Football Knowledge Graph - Interactive RAG System")
        print("="*80)
        print("\nType your questions below. Type 'exit' or 'quit' to stop.\n")
        
        while True:
            try:
                query = input("\n🔍 Question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['exit', 'quit', 'q']:
                    print("\nGoodbye! 👋")
                    break
                
                # Get answer
                response = self.answer(query)
                
                # Display answer
                print(f"\n{'='*80}")
                print("📊 ANSWER")
                print(f"{'='*80}\n")
                print(response["answer"])
                print(f"\n{'='*80}")
                print(f"📈 Retrieved {len(response['retrieved_events'])} events from knowledge graph")
                print(f"{'='*80}")
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
