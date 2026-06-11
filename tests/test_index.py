from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.store.index import IndexStore
from simplebrain.models import Chunk


def test_knowledge_store_write_read(config):
    ks = KnowledgeStore(config)
    chunk = Chunk(content="MCP is great.", source_raw="test.txt",
                  tags=["#mcp"], user="alice", device="mac")
    path = ks.write(chunk, folder="projects")
    assert path.exists()
    loaded = ks.read(chunk.id)
    assert loaded.content == "MCP is great."
    assert loaded.tags == ["#mcp"]


def test_knowledge_store_unfiled(config):
    ks = KnowledgeStore(config)
    chunk = Chunk(content="Orphan note.", source_raw="test.txt",
                  user="alice")
    path = ks.write_unfiled(chunk)
    assert "_unfiled" in str(path)


def test_index_store_update_and_lookup(config):
    ks = KnowledgeStore(config)
    idx = IndexStore(config)
    chunk = Chunk(content="Test.", source_raw="t.txt",
                  tags=["#mcp", "#ai"], user="alice")
    path = ks.write(chunk, folder="projects")
    idx.update(chunk, path)

    tags = idx.load_tags()
    assert "#mcp" in tags
    assert chunk.id in tags["#mcp"]


def test_index_store_cross_links(config):
    ks = KnowledgeStore(config)
    idx = IndexStore(config)

    c1 = Chunk(content="A.", source_raw="t.txt", tags=["#mcp"], user="alice")
    c2 = Chunk(content="B.", source_raw="t.txt", tags=["#mcp"], user="alice")
    p1 = ks.write(c1, folder="projects")
    p2 = ks.write(c2, folder="projects")
    idx.update(c1, p1)
    idx.update(c2, p2)
    idx.update_cross_links([c1, c2], ks)

    updated_c1 = ks.read(c1.id)
    assert c2.id in updated_c1.links
