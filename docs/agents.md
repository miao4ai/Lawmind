# Agent Design

## Philosophy

Agents in Mamimind are **autonomous, composable, and observable** units of work that:

1. Accept structured input via `AgentContext`
2. Execute a specific task using tools
3. Return structured output via `AgentResult`
4. Are fully traceable and retryable

## Agent Contract

Every agent implements the `Agent` base class:

```python
class Agent(ABC):
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Main execution logic"""
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input before execution"""
        pass

    async def before_execute(self, context: AgentContext) -> None:
        """Pre-execution hook"""
        pass

    async def after_execute(self, context: AgentContext, result: AgentResult) -> None:
        """Post-execution hook"""
        pass
```

## Agent Runtime

The `AgentRuntime` provides:
- ✅ Automatic retry with exponential backoff
- ✅ Timeout handling
- ✅ Distributed tracing
- ✅ Error recovery
- ✅ Lifecycle hooks

```python
runtime = AgentRuntime()
result = await runtime.run(
    agent=OCRAgent(),
    input_data={"doc_id": "...", "storage_path": "..."},
    user_id="user123",
    timeout=300,
)
```

## Agent Registry

Agents are registered at import time using the `@register_agent` decorator:

```python
@register_agent("ocr")
class OCRAgent(Agent):
    ...
```

This enables dynamic agent discovery and instantiation:

```python
agent_class = get_agent("ocr")
agent = agent_class()
```

## Built-in Agents

### 1. OCRAgent

**Purpose**: Extract text and layout from documents

**Input**:
```python
{
    "doc_id": "doc_123",
    "storage_path": "raw/user/doc_123/file.pdf",
    "language": "en"  # optional
}
```

**Output**:
```python
{
    "doc_id": "doc_123",
    "ocr_text": "Full extracted text...",
    "layout": [...],  # Layout blocks
    "page_count": 10,
    "language": "en"
}
```

**Tools Used**:
- OCRTool (Google Cloud Vision)
- LayoutAnalysisTool

### 2. IndexingAgent

**Purpose**: Chunk document and create vector embeddings

**Input**:
```python
{
    "doc_id": "doc_123",
    "ocr_result_path": "processed/doc_123/ocr_result.json",
    "user_id": "user123"
}
```

**Output**:
```python
{
    "doc_id": "doc_123",
    "chunks_created": 42,
    "collection": "mamimind_docs",
    "status": "indexed"
}
```

**Tools Used**:
- ChunkingTool
- EmbeddingTool
- VectorSearchTool (for indexing)

### 3. LegalReasoningAgent

**Purpose**: Answer queries with legal reasoning

**Input**:
```python
{
    "query": "What are the termination conditions?",
    "user_id": "user123",
    "doc_ids": ["doc_123"],  # optional
    "top_k": 5
}
```

**Output**:
```python
{
    "query": "What are the termination conditions?",
    "answer": "Based on the documents, termination can occur when...",
    "citations": [
        {
            "doc_id": "doc_123",
            "chunk_id": "doc_123_5",
            "text": "Either party may terminate...",
            "page_number": 7,
            "confidence": 0.92
        }
    ],
    "reasoning": "Step-by-step reasoning...",
    "confidence": 0.88
}
```

**Tools Used**:
- VectorSearchTool (for retrieval)
- LLMTool (for generation)

## Tool Composition

Agents can compose tools to build complex workflows:

```python
class LegalReasoningAgent(Agent):
    def __init__(self):
        self.vector_search = VectorSearchTool()
        self.llm = LLMTool()

    async def execute(self, context: AgentContext) -> AgentResult:
        # Step 1: Retrieve
        chunks = await self.vector_search.search(...)

        # Step 2: Reason
        answer = await self.llm.generate(...)

        # Step 3: Return structured result
        return AgentResult(...)
```

## Error Handling

Agents use structured error handling:

```python
try:
    result = await tool.execute()
except ToolError as e:
    return AgentResult(
        status=AgentStatus.FAILED,
        error=str(e),
        metadata={"error_type": "tool_error"}
    )
```

The runtime will automatically retry transient errors.

## Tracing

Every agent execution is automatically traced:

```
Trace: trace_abc123
  └─ agent.legal_reasoning (200ms)
      ├─ tool.vector_search (50ms)
      │   └─ qdrant.search (30ms)
      └─ tool.llm (150ms)
          └─ openai.chat.completions (140ms)
```

View traces in Cloud Trace console.

## Testing

Agents are easy to unit test due to strong contracts:

```python
def test_ocr_agent():
    agent = OCRAgent()

    context = AgentContext(
        agent_id="test",
        user_id="test_user",
        trace_id="test_trace",
        input_data={
            "doc_id": "doc_123",
            "storage_path": "test/path.pdf"
        }
    )

    result = await agent.execute(context)

    assert result.status == AgentStatus.SUCCESS
    assert "ocr_text" in result.output
```

## Best Practices

1. **Single Responsibility**: One agent, one task
2. **Idempotency**: Agents should be safe to retry
3. **Structured I/O**: Always use Pydantic models
4. **Tool Reuse**: Build tools that multiple agents can use
5. **Graceful Degradation**: Return partial results when possible
6. **Observability**: Log important state transitions
7. **Timeout Handling**: Set reasonable timeouts for tools

## Adding a New Agent

1. Create agent directory: `agents/my_agent/`
2. Implement agent class:
   ```python
   @register_agent("my_agent")
   class MyAgent(Agent):
       def validate_input(self, input_data):
           return "required_field" in input_data

       async def execute(self, context):
           # Implementation
           pass
   ```
3. Add schema.py for input/output models
4. Write tests
5. Register in service that will use it

## Performance Considerations

- **Cold Start**: First invocation may be slow (Cloud Functions)
- **Caching**: Cache expensive operations (embeddings, LLM calls)
- **Batching**: Batch API calls when possible
- **Streaming**: Use streaming for real-time responses

## Future: Multi-Agent Orchestration

Future enhancement: Agent orchestrator that coordinates multiple agents:

```python
orchestrator = AgentOrchestrator()
orchestrator.add_agent(OCRAgent())
orchestrator.add_agent(IndexingAgent())
orchestrator.add_agent(LegalReasoningAgent())

# Execute pipeline
result = await orchestrator.run_pipeline(
    input={"doc_path": "..."},
    user_id="user123"
)
```
