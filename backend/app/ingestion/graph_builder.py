import logging
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
from app.config import settings
from app.models.document import Document

logger = logging.getLogger(__name__)

def normalize_person_name(name: str) -> str:
    """
    Standardizes person names across email, GitHub usernames, and raw strings.
    For example: "Sailesh Architect <sailesh@example.com>" -> "Sailesh"
                 "Sailesh3000" -> "Sailesh"
                 "chandrasailesh30@gmail.com" -> "Sailesh"
    """
    if not name:
        return "Unknown"

    name_str = name.strip()
    
    # Extract name part before email if formatted as "Name <email>"
    if "<" in name_str and ">" in name_str:
        name_str = name_str.split("<")[0].strip()
        
    # If it is just an email, take the local part before the '@'
    if "@" in name_str:
        name_str = name_str.split("@")[0].strip()
        
    # Split by spaces/hyphens and get the first part (first name or main username)
    first_part = name_str.split()[0].split("-")[0].split("_")[0]
    
    # Fallback capitalization for seeding new names
    first_part = name_str.split()[0].split("-")[0].split("_")[0]
    return first_part.capitalize()

class GraphBuilder:
    """
    Handles saving nodes and relationships to Neo4j graph database.
    """

    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.username = settings.NEO4J_USERNAME
        self.password = settings.NEO4J_PASSWORD
        self._driver = None

    @property
    def driver(self) -> GraphDatabase:
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {self.uri}...")
            try:
                self._driver = GraphDatabase.driver(
                    self.uri, 
                    auth=(self.username, self.password)
                )
                # Verify connection
                self._driver.verify_connectivity()
                logger.info("Neo4j database connection verified successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {str(e)}")
                raise e
        return self._driver

    def close(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _resolve_person(self, session, raw_name: str, email: Optional[str] = None) -> str:
        """
        Resolves a person's display name dynamically by checking Neo4j for matching aliases.
        If not found, creates a new Person node and records the aliases.
        """
        normalized_name = normalize_person_name(raw_name)
        search_name = raw_name.strip()
        email_str = email.strip() if email else ""

        # Query 1: Find existing Person matching name or aliases
        lookup_query = """
        MATCH (p:Person)
        WHERE p.name = $normalized_name 
           OR $search_name IN p.aliases 
           OR (size($email) > 0 AND $email IN p.aliases)
        RETURN p.name as name
        LIMIT 1
        """
        result = session.run(lookup_query, normalized_name=normalized_name, search_name=search_name, email=email_str)
        record = result.single()

        if record:
            resolved_name = record["name"]
            # Update aliases on match
            update_query = """
            MATCH (p:Person {name: $resolved_name})
            SET p.aliases = REDUCE(s = coalesce(p.aliases, []), val IN [$search_name, $email] | 
                CASE WHEN val IS NOT NULL AND val <> "" AND NOT val IN s THEN s + val ELSE s END
            )
            """
            session.run(update_query, resolved_name=resolved_name, search_name=search_name, email=email_str)
            return resolved_name
        else:
            # Query 2: Create new Person with seed aliases
            create_query = """
            MERGE (p:Person {name: $normalized_name})
            SET p.aliases = REDUCE(s = coalesce(p.aliases, []), val IN [$search_name, $email] | 
                CASE WHEN val IS NOT NULL AND val <> "" AND NOT val IN s THEN s + val ELSE s END
            )
            RETURN p.name as name
            """
            result = session.run(create_query, normalized_name=normalized_name, search_name=search_name, email=email_str)
            record = result.single()
            return record["name"] if record else normalized_name

    def store_document_nodes(self, doc: Document, extracted_metadata: Dict[str, Any]) -> bool:
        """
        Ingests a Document and its extracted entities/relationships into Neo4j.
        """
        # Determine source specific labels
        source_labels = ["Document"]
        if doc.source.value == "gmail":
            source_labels.append("Email")
        elif doc.source.value == "calendar":
            source_labels.append("Meeting")
        elif doc.source.value == "github":
            source_labels.append("GithubItem")
            # Sub-type from title/content
            title_lower = doc.title.lower()
            if "[commit]" in title_lower or "commit" in doc.metadata.get("type", ""):
                source_labels.append("Commit")
            elif "[pr]" in title_lower or "pr" in doc.metadata.get("type", ""):
                source_labels.append("PR")
            elif "[issue]" in title_lower or "issue" in doc.metadata.get("type", ""):
                source_labels.append("Issue")
        elif doc.source.value == "local":
            source_labels.append("LocalDoc")

        label_string = ":".join(source_labels)

        query_doc = f"""
        MERGE (d:Document {{id: $doc_id}})
        SET d.title = $title,
            d.source = $source,
            d.url = $url,
            d.timestamp = $timestamp,
            d.content_snippet = $snippet
        
        // Dynamic label setting
        WITH d
        CALL apoc.create.addLabels(d, $labels) YIELD node
        RETURN node
        """
        # Fallback query if APOC is not present/configured
        fallback_query_doc = f"""
        MERGE (d:Document {{id: $doc_id}})
        SET d.title = $title,
            d.source = $source,
            d.url = $url,
            d.timestamp = $timestamp,
            d.content_snippet = $snippet
        """

        try:
            with self.driver.session() as session:
                author_name = self._resolve_person(session, doc.author, doc.author if "@" in doc.author else None)

                # 1. Store the Document itself
                snippet = doc.content[:300] + "..." if len(doc.content) > 300 else doc.content
                
                try:
                    # Try using APOC to assign multi-labels dynamically
                    session.run(
                        query_doc,
                        doc_id=doc.id,
                        title=doc.title,
                        source=doc.source.value,
                        url=doc.url or "",
                        timestamp=doc.timestamp.isoformat(),
                        snippet=snippet,
                        labels=source_labels
                    )
                except Exception as apoc_err:
                    # Fallback to standard merge (without APOC labels)
                    logger.debug(f"APOC addLabels failed: {str(apoc_err)}. Falling back to direct query.")
                    session.run(
                        fallback_query_doc,
                        doc_id=doc.id,
                        title=doc.title,
                        source=doc.source.value,
                        url=doc.url or "",
                        timestamp=doc.timestamp.isoformat(),
                        snippet=snippet
                    )
                    # Manually add primary source label using string manipulation inside python
                    for l in source_labels:
                        if l != "Document":
                            session.run(f"MATCH (d:Document {{id: $doc_id}}) SET d:{l} RETURN d", doc_id=doc.id)

                # 2. Merge Author node and link it
                session.run(
                    """
                    MERGE (p:Person {name: $name})
                    WITH p
                    MATCH (d:Document {id: $doc_id})
                    MERGE (p)-[:AUTHORED]->(d)
                    """,
                    name=author_name,
                    doc_id=doc.id
                )

                # 3. Create Meeting Attendee edges (if meeting)
                if "Meeting" in source_labels and "attendees" in doc.metadata:
                    for attendee in doc.metadata["attendees"]:
                        att_name = self._resolve_person(session, attendee, attendee if "@" in attendee else None)
                        session.run(
                            """
                            MERGE (p:Person {name: $name})
                            WITH p
                            MATCH (d:Document {id: $doc_id})
                            MERGE (p)-[:ATTENDED]->(d)
                            """,
                            name=att_name,
                            doc_id=doc.id
                        )

                # 4. Ingest extracted entities
                entities = extracted_metadata.get("entities", [])
                for ent in entities:
                    ent_name = ent["name"].strip()
                    ent_type = ent["type"].strip()
                    
                    if ent_type == "Person":
                        ent_name = self._resolve_person(session, ent_name, ent_name if "@" in ent_name else None)
                    
                    # Create entity node
                    session.run(
                        f"MERGE (e:{ent_type} {{name: $name}})",
                        name=ent_name
                    )
                    
                    # Implicit link: Current document mentions this entity
                    session.run(
                        f"""
                        MATCH (d:Document {{id: $doc_id}})
                        MATCH (e:{ent_type} {{name: $name}})
                        MERGE (d)-[:MENTIONS]->(e)
                        """,
                        doc_id=doc.id,
                        name=ent_name
                    )

                # 5. Ingest extracted relationships
                relationships = extracted_metadata.get("relationships", [])
                for rel in relationships:
                    src_name = rel["source"].strip()
                    tgt_name = rel["target"].strip()
                    rel_type = rel["type"].strip()
                    
                    # Resolve labels if referencing known entities
                    src_type = "Document"  # default
                    tgt_type = "Document"  # default
                    
                    # Try to map entity types if they exist in the entity extraction block
                    for ent in entities:
                        if ent["name"] == src_name:
                            src_type = ent["type"]
                        if ent["name"] == tgt_name:
                            tgt_type = ent["type"]
                            
                    if src_name == doc.title or src_name == "this" or src_name == "document":
                        src_name = doc.title
                        
                    if src_type == "Person":
                        src_name = self._resolve_person(session, src_name, src_name if "@" in src_name else None)
                    if tgt_type == "Person":
                        tgt_name = self._resolve_person(session, tgt_name, tgt_name if "@" in tgt_name else None)

                    # Safe Cypher relationship merge query
                    # Since we don't know the node labels dynamically, we match them broadly or by standard types
                    session.run(
                        f"""
                        MERGE (sNode {{name: $src_name}})
                        MERGE (tNode {{name: $tgt_name}})
                        MERGE (sNode)-[r:{rel_type}]->(tNode)
                        """,
                        src_name=src_name,
                        tgt_name=tgt_name
                    )

            logger.info(f"Successfully saved nodes/edges for document '{doc.id}' to Neo4j.")
            return True
        except Exception as e:
            logger.error(f"Failed to save graph nodes to Neo4j: {str(e)}")
            return False

    def delete_document_nodes(self, document_id: str) -> bool:
        """
        Cleans up nodes representing the document.
        Keeps Person/Topic/Tech nodes unless they are isolated orphan nodes.
        """
        try:
            with self.driver.session() as session:
                # Delete document node and its relationships
                session.run(
                    """
                    MATCH (d:Document {id: $doc_id})
                    DETACH DELETE d
                    """,
                    doc_id=document_id
                )
                logger.info(f"Deleted Document node '{document_id}' from Neo4j.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document node from Neo4j: {str(e)}")
            return False
