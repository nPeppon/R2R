import logging
import httpx
from shared.abstractions.tool import Tool
from core.base.abstractions import AggregateSearchResult
from shared.abstractions.search import ChunkSearchResult
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

class ColpaliVectorSearchTool(Tool):
    def __init__(self):
        super().__init__(
            name="colpali_vector_search",
            description=(
                "Search the Colpali vector database. "
                "Use this tool ONLY if the user explicitly asks for Colpali data, or if the user asks for information from images, "
                "or if no relevant information is found in other sources. Do not overuse this tool."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query to search in Colpali vector DB."},
                    "plant_name": {"type": "string", "description": "Plant name for Colpali collection."},
                    "collection_name": {"type": "string", "description": "Collection name in Colpali."},
                    "limit": {"type": "integer", "description": "Maximum number of results to return.", "default": 1},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "List of base64-encoded images to search with."},
                    "score_threshold": {"type": ["number", "null"], "description": "Score threshold for filtering results."},
                    "exclude_ids": {"type": ["array", "null"], "items": {"type": "string"}, "description": "IDs to exclude from results."},
                    "filenames": {"type": ["array", "null"], "items": {"type": "integer"}, "description": "Filenames to filter results."},
                    "pages": {"type": ["array", "null"], "items": {"type": "integer"}, "description": "Pages to filter results."},
                },
                "required": ["query", "plant_name", "collection_name"],
            },
            results_function=self.execute,
            llm_format_function=None,
        )

    async def execute(self, query: str, plant_name: str, collection_name: str, limit: int = 1, images: list = None, score_threshold=None, exclude_ids=None, filenames=None, pages=None, *args, **kwargs):
        context = self.context
        try:
            payload = {
                "query": query,
                "plant_name": plant_name,
                "collection_name": collection_name,
                "limit": limit,
                "images": images or [],
                "score_threshold": score_threshold,
                "exclude_ids": exclude_ids,
                "filenames": filenames,
                "pages": pages,
            }
            # Remove None values for cleaner payload
            payload = {k: v for k, v in payload.items() if v is not None}

            # Replace with your actual Colpali API URL
            COLPALI_API_URL = "http://COLPALI_HOST:PORT/retrive"

            async with httpx.AsyncClient() as client:
                response = await client.post(COLPALI_API_URL, json=payload)
                response.raise_for_status()
                result = response.json()

            chunk_results = []
            for doc in result.get("documents", []):
                chunk_results.append(
                    ChunkSearchResult(
                        id=UUID(str(doc.get("doc_id", uuid4()))),
                        document_id=UUID(str(doc.get("metadata", {}).get("document_id", uuid4()))),
                        owner_id=None,  # Fill if you have this info
                        collection_ids=[],  # Fill if you have this info
                        score=doc.get("score"),
                        text=doc.get("content", ""),
                        metadata=doc.get("metadata", {}),
                    )
                )

            agg_result = AggregateSearchResult(chunk_search_results=chunk_results)

            # Add to results collector if context has it
            if context and hasattr(context, "search_results_collector"):
                context.search_results_collector.add_aggregate_result(agg_result)

            return agg_result

        except Exception as e:
            logger.error(f"Colpali search failed: {e}")
            return AggregateSearchResult(chunk_search_results=[]) 